from flask import Flask, jsonify, request, send_file
import os
import json

app = Flask(__name__)

# Firmware information
FIRMWARE_INFO = {
    "version": "0x00020000",  # Version 2.0.0
    "filename": "firmware_v2.bin",
    "size": 0,  # Will be set when file exists
    "id": "ota_update_001"
}

@app.route('/api/ota/devices/<device_id>/check', methods=['POST'])
def ota_check(device_id):
    """
    OTA check endpoint - returns firmware update info if available
    Expected request body: {"device_id": "...", "firmware_version": "...", "config_version": "...", "secret": "..."}
    """
    try:
        data = request.get_json() or {}
        
        # Optional: Validate device credentials (secret token)
        # device_secret = data.get('secret', '')
        # if not device_secret:
        #     return jsonify({"error": "Unauthorized", "status": 0}), 401
        
        current_version = data.get('firmware_version', '0x00010000')
        
        # Check if firmware file exists
        firmware_path = os.path.join(os.path.dirname(__file__), '..', 'firmware', FIRMWARE_INFO['filename'])
        
        if os.path.exists(firmware_path):
            FIRMWARE_INFO['size'] = os.path.getsize(firmware_path)
            
            # Construct absolute URL for firmware download
            base_url = request.host_url.rstrip('/')
            firmware_url = f"{base_url}/api/firmware/{FIRMWARE_INFO['filename']}"
            
            response = {
                "status": 1,  # 1 = update available, 0 = no update
                "version": FIRMWARE_INFO['version'],
                "url": firmware_url,
                "size": FIRMWARE_INFO['size'],
                "id": FIRMWARE_INFO['id']
            }
        else:
            # No firmware available
            response = {
                "status": 0,
                "version": current_version,
                "url": "",
                "size": 0,
                "id": ""
            }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({"error": str(e), "status": 0}), 500


@app.route('/api/firmware/<filename>', methods=['GET'])
def download_firmware(filename):
    """
    Firmware download endpoint - serves the firmware binary file
    Supports HTTP Range requests for chunk-by-chunk download
    """
    try:
        firmware_path = os.path.join(os.path.dirname(__file__), '..', 'firmware', filename)
        
        if not os.path.exists(firmware_path):
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
            
            return response
        else:
            # Full file download
            return send_file(
                firmware_path,
                mimetype='application/octet-stream',
                as_attachment=True,
                download_name=filename
            )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/ota/devices/<device_id>/ack', methods=['POST'])
def ota_ack(device_id):
    """
    OTA acknowledgment endpoint - receives status updates from device
    """
    try:
        data = request.get_json() or {}
        
        print(f"[OTA ACK] Device: {device_id}, Status: {data}")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "OTA Server",
        "firmware_available": os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'firmware', FIRMWARE_INFO['filename']))
    }), 200


# For local testing
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
