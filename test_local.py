#!/usr/bin/env python3
"""
Local test script for OTA server
Run this to test the OTA endpoints locally before deploying to Vercel
"""

import requests
import json

BASE_URL = "http://localhost:5000"
DEVICE_ID = "TEST_DEVICE_001"

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_ota_check():
    """Test OTA check endpoint"""
    print("\n=== Testing OTA Check Endpoint ===")
    
    payload = {
        "device_id": DEVICE_ID,
        "firmware_version": "0x00010000",
        "config_version": "config_v1"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/ota/devices/{DEVICE_ID}/check",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_firmware_download():
    """Test firmware download endpoint"""
    print("\n=== Testing Firmware Download (Full) ===")
    
    response = requests.get(f"{BASE_URL}/api/firmware/firmware_v2.bin")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Downloaded {len(response.content)} bytes")
    else:
        print(f"Response: {response.text}")
    
    return response.status_code == 200 or response.status_code == 404

def test_firmware_range():
    """Test firmware download with Range header (chunk download)"""
    print("\n=== Testing Firmware Download (Range Request) ===")
    
    # Request first 1KB
    headers = {"Range": "bytes=0-1023"}
    response = requests.get(
        f"{BASE_URL}/api/firmware/firmware_v2.bin",
        headers=headers
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 206:
        print(f"Partial content: {len(response.content)} bytes")
        print(f"Content-Range: {response.headers.get('Content-Range')}")
    else:
        print(f"Response: {response.text}")
    
    return response.status_code == 206 or response.status_code == 404

def test_ota_ack():
    """Test OTA acknowledgment endpoint"""
    print("\n=== Testing OTA ACK Endpoint ===")
    
    payload = {
        "device_id": DEVICE_ID,
        "status": "success",
        "version": "0x00020000"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/ota/devices/{DEVICE_ID}/ack",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

if __name__ == "__main__":
    print("=" * 60)
    print("OTA SERVER LOCAL TEST")
    print("=" * 60)
    print("\nMake sure the server is running:")
    print("  python api/ota.py")
    print("\nOr use: python -m flask --app api/ota run")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health),
        ("OTA Check", test_ota_check),
        ("Firmware Download", test_firmware_download),
        ("Firmware Range Request", test_firmware_range),
        ("OTA ACK", test_ota_ack),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n[ERROR] {name}: {e}")
            results[name] = False
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    print("=" * 60)
