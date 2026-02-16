from flask import Flask, jsonify, request, send_file, make_response
from flask_cors import CORS
import os
import json
import logging
import sys

app = Flask(__name__)

# Enhanced CORS configuration
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     allow_headers=["*"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     expose_headers=["*"],
     supports_credentials=False,
     max_age=3600
)

# Ensure responses have proper headers
@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Content-Length'
    response.headers['Connection'] = 'close'
    response.headers['Content-Type'] = 'application/json'
    return response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Log all incoming requests (minimal)
@app.before_request
def log_request_info():
    logger.info(f'{request.method} {request.path}')

# Firmware information
FIRMWARE_INFO = {
    "version": "0x00020000",  # Version 2.0.0
    "filename": "firmware_v2.bin",
    "size": 0,  # Will be set when file exists
    "id": "ota_update_001"
}

# Dual routes to support both /api/ prefix and without (for STM32 compatibility)
@app.route('/api/ota/devices/<device_id>/check', methods=['POST', 'GET', 'OPTIONS'])
@app.route('/ota/devices/<device_id>/check', methods=['POST', 'GET', 'OPTIONS'])
def ota_check(device_id):
    """
    OTA check endpoint - returns firmware update info if available
    Expected request body: {"device_id": "...", "firmware_version": "...", "config_version": "...", "secret": "..."}
    """
    # Handle preflight OPTIONS requests
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        logger.info(f"OTA Check - Device: {device_id}")
        
        # Support both JSON and form data
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict() if request.form else {}
        
        current_version = data.get('firmware_version', '0x00010000')
        
        # Check if firmware file exists
        firmware_path = os.path.join(os.path.dirname(__file__), '..', 'firmware', FIRMWARE_INFO['filename'])
        
        if os.path.exists(firmware_path):
            FIRMWARE_INFO['size'] = os.path.getsize(firmware_path)
            
            # Construct absolute URL for firmware download
            # Use VERCEL_URL environment variable if available, otherwise fall back to request.host_url
            base_url = os.getenv('VERCEL_URL')
            if base_url:
                base_url = f"https://{base_url}"
            else:
                base_url = request.host_url.rstrip('/')
            
            # Use /firmware/ path (without /api/) for STM32 compatibility
            firmware_url = f"{base_url}/firmware/{FIRMWARE_INFO['filename']}"
            logger.info(f"Firmware update available: {firmware_url}")
            
            response = {
                "status": 1,  # 1 = update available, 0 = no update
                "version": FIRMWARE_INFO['version'],
                "url": firmware_url,
                "size": FIRMWARE_INFO['size'],
                "id": FIRMWARE_INFO['id']
            }
        else:
            # No firmware available
            logger.warning(f"Firmware file not found: {firmware_path}")
            response = {
                "status": 0,
                "version": current_version,
                "message": "No firmware update available"
            }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"OTA Check Error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "status": 0}), 500


@app.route('/api/firmware/<filename>', methods=['GET', 'OPTIONS'])
@app.route('/firmware/<filename>', methods=['GET', 'OPTIONS'])
def download_firmware(filename):
    """
    Firmware download endpoint - serves the firmware binary file
    Supports HTTP Range requests for chunk-by-chunk download
    """
    # Handle preflight OPTIONS requests
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        logger.info(f"Firmware request: {filename}")
        firmware_path = os.path.join(os.path.dirname(__file__), '..', 'firmware', filename)
        
        if not os.path.exists(firmware_path):
            logger.warning(f"Firmware not found: {filename}")
            return jsonify({"error": "Firmware not found"}), 404
        
        # Support Range requests for chunk download
        range_header = request.headers.get('Range', None)
        
        if range_header:
            # Parse range header: "bytes=0-1023"
            byte_range = range_header.replace('bytes=', '').split('-')
            start = int(byte_range[0]) if byte_range[0] else 0
            
            file_size = os.path.getsize(firmware_path)
            end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
            
            length = end - start + 1
            
            with open(firmware_path, 'rb') as f:
                f.seek(start)
                data = f.read(length)
            
            response = app.response_class(
                data,
                206,  # Partial Content
                mimetype='application/octet-stream',
                direct_passthrough=True
            )
            response.headers['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response.headers['Accept-Ranges'] = 'bytes'
            response.headers['Content-Length'] = str(length)
            response.headers['Content-Type'] = 'application/octet-stream'
            response.headers['Access-Control-Allow-Origin'] = '*'
            logger.info(f"Sending partial content: {start}-{end}/{file_size}")
            
            return response
        else:
            # Full file download
            logger.info(f"Sending full firmware file: {filename}")
            return send_file(
                firmware_path,
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name=filename
            )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ota/devices/<device_id>/ack', methods=['POST', 'OPTIONS'])
@app.route('/ota/devices/<device_id>/ack', methods=['POST', 'OPTIONS'])
def ota_ack(device_id):
    """
    OTA acknowledgment endpoint - receives status updates from device
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # Support both JSON and form data
        if request.is_json:
            data = request.get_json() or {}
        else:
            data = request.form.to_dict() if request.form else {}
        
        logger.info(f"[OTA ACK] Device: {device_id}, Status: {data}")
        logger.debug(f"Headers: {dict(request.headers)}")
        
        return jsonify({"status": "ok", "device_id": device_id}), 200
        
    except Exception as e:
        logger.error(f"OTA ACK Error: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    fw_file = os.path.join(os.path.dirname(__file__), '..', 'firmware', FIRMWARE_INFO['filename'])
    return jsonify({
        "status": "healthy",
        "service": "OTA Server",
        "firmware_available": os.path.exists(fw_file)
    }), 200


@app.route('/', methods=['GET'])
def root():
    """Root endpoint - provides API documentation"""
    return jsonify({
        "service": "OTA Server",
        "version": "1.0.0",
        "endpoints": {
            "check_update": "/ota/devices/{device_id}/check (POST)",
            "download_firmware": "/firmware/{filename} (GET)",
            "acknowledge": "/ota/devices/{device_id}/ack (POST)",
            "health": "/health (GET)",
            "debug": "/debug/echo (POST) - Echo back request details"
        },
        "note": "All endpoints also available with /api/ prefix",
        "timestamp": str(os.getenv('VERCEL_REGION', 'local'))
    }), 200


# Super-minimal test endpoints for connectivity testing
@app.route('/test', methods=['GET', 'POST'])
@app.route('/api/test', methods=['GET', 'POST'])
@app.route('/ping', methods=['GET', 'POST'])
@app.route('/api/ping', methods=['GET', 'POST'])
def test():
    """Minimal test endpoint - responds immediately"""
    return jsonify({"status": "ok", "test": "success"}), 200
@app.route('/api/debug/echo', methods=['POST', 'GET', 'OPTIONS'])
def debug_echo():
    """Debug endpoint - echoes back all request details"""
    if request.method == 'OPTIONS':
        return '', 204
    
    return jsonify({
        "method": request.method,
        "url": request.url,
        "path": request.path,
        "headers": dict(request.headers),
        "args": dict(request.args),
        "form": dict(request.form),
        "json": request.get_json(silent=True),
        "data": request.data.decode('utf-8', errors='ignore')[:500],
        "remote_addr": request.remote_addr,
        "user_agent": request.user_agent.string if request.user_agent else None
    }), 200


# Catch-all route to log unmatched requests
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def catch_all(path):
    """Catch-all route to log requests that don't match any endpoint"""
    logger.warning(f'UNMATCHED ROUTE: {request.method} /{path}')
    logger.warning(f'Full URL: {request.url}')
    return jsonify({
        "error": "Endpoint not found",
        "path": f"/{path}",
        "method": request.method,
        "available_endpoints": [
            "/ota/devices/{device_id}/check",
            "/api/ota/devices/{device_id}/check",
            "/firmware/{filename}",
            "/health",
            "/debug/echo"
        ]
    }), 404


# For local testing
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
