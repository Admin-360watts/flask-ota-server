#!/usr/bin/env python3
"""
Create test firmware binary for OTA testing
Generates a dummy firmware file with specified size
"""

import os
import struct
import hashlib

def create_test_firmware(filename="firmware_v2.bin", size_kb=512):
    """
    Create a test firmware binary file
    
    Args:
        filename: Output filename
        size_kb: Size in KB (default 512KB)
    """
    
    # Create firmware directory if it doesn't exist
    firmware_dir = os.path.join(os.path.dirname(__file__), 'firmware')
    os.makedirs(firmware_dir, exist_ok=True)
    
    filepath = os.path.join(firmware_dir, filename)
    size_bytes = size_kb * 1024
    
    print(f"Creating test firmware: {filepath}")
    print(f"Size: {size_kb} KB ({size_bytes} bytes)")
    
    with open(filepath, 'wb') as f:
        # Write a simple header
        header = struct.pack('<4sIII', 
                            b'FWUP',           # Magic
                            0x00020000,        # Version 2.0.0
                            size_bytes,        # Size
                            0x12345678)        # CRC placeholder
        f.write(header)
        
        # Fill with pattern (easier to debug than random)
        pattern = bytearray(range(256))
        remaining = size_bytes - len(header)
        
        while remaining > 0:
            chunk_size = min(len(pattern), remaining)
            f.write(pattern[:chunk_size])
            remaining -= chunk_size
    
    # Calculate actual file hash
    with open(filepath, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    
    print(f"✅ Created: {filepath}")
    print(f"MD5: {file_hash}")
    print(f"Actual size: {os.path.getsize(filepath)} bytes")
    
    return filepath

if __name__ == "__main__":
    import sys
    
    size = 512  # Default 512KB
    if len(sys.argv) > 1:
        size = int(sys.argv[1])
    
    # Create test firmware (default 512KB, max 896KB for STM32)
    if size > 896:
        print(f"⚠️  Warning: Size {size}KB exceeds STM32 slot limit (896KB)")
        print("Creating anyway for testing purposes...")
    
    create_test_firmware("firmware_v2.bin", size)
    
    print("\n📝 Next steps:")
    print("1. Start local server: python api/ota.py")
    print("2. Test endpoints: python test_local.py")
    print("3. Deploy to Vercel: vercel deploy")
