#!/usr/bin/env python3
"""
Cross-platform Camera Configuration Tool
Detects cameras on Windows and Linux and generates camera_config.json
"""

import cv2
import sys
import os
import json
import time
from datetime import datetime
import platform

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from config_manager import ConfigManager

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def get_platform_backend():
    """Get the appropriate OpenCV backend for the current platform"""
    if sys.platform == 'win32':
        return cv2.CAP_DSHOW
    else:
        return cv2.CAP_ANY  # Default for Linux/Mac (usually V4L2)

def test_camera(camera_id, backend):
    """Test if a camera works and get its capabilities"""
    try:
        cap = cv2.VideoCapture(camera_id, backend)
        
        if not cap.isOpened():
            return None
        
        # Try to read a frame
        ret, frame = cap.read()
        if not ret:
            cap.release()
            return {
                'id': camera_id,
                'status': 'opens_but_no_frames',
                'description': 'Opens successfully but cannot read frames',
                'is_hd': False
            }
        
        # Get basic properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Test HD capability (720p @ 60fps check)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 60)
        
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Quick FPS measurement
        frame_count = 0
        start_time = time.time()
        test_duration = 0.5
        while time.time() - start_time < test_duration:
            ret, _ = cap.read()
            if ret:
                frame_count += 1
            time.sleep(0.001)
        
        measured_fps = frame_count / (time.time() - start_time) if (time.time() - start_time) > 0 else 0
        cap.release()
        
        is_hd = (actual_width >= 1280 and actual_height >= 720)
        
        return {
            'id': camera_id,
            'status': 'working',
            'description': f'{actual_width}x{actual_height} @ {measured_fps:.1f}fps',
            'resolution': f"{actual_width}x{actual_height}",
            'fps': float(fps),
            'measured_fps': measured_fps,
            'is_hd': is_hd
        }
    except Exception as e:
        return {
            'id': camera_id,
            'status': 'error',
            'description': f'Error: {str(e)}',
            'is_hd': False
        }

def scan_cameras():
    """Scan for available cameras"""
    print(f"Scanning cameras on {platform.system()}...")
    backend = get_platform_backend()
    
    found_cameras = []
    
    # Scan range 0-10
    # On Linux, these map to /dev/videoN
    for i in range(10):
        print(f"Checking Camera {i}...", end="\r")
        result = test_camera(i, backend)
        if result:
            found_cameras.append(result)
            print(f"Checking Camera {i}: Found - {result['status']}")
        else:
            # print(f"Checking Camera {i}: Not found")
            pass
            
    print("\nScan complete.")
    return found_cameras

def interactive_configure():
    """Run interactive configuration"""
    print("\n" + "="*60)
    print("Camera Configuration Wizard")
    print("="*60)
    
    cameras = scan_cameras()
    working = [c for c in cameras if c['status'] == 'working']
    
    if not working:
        print("\nNo working cameras found! configuration cannot continue.")
        if sys.platform == 'linux':
            print("Tip: On Linux, ensure you are in the 'video' group:")
            print("  sudo usermod -a -G video $USER")
            print("  (You will need to log out and back in)")
        return 1
        
    print(f"\nFound {len(working)} working camera(s):")
    for i, cam in enumerate(working):
        hd_tag = "[HD]" if cam['is_hd'] else ""
        print(f"  {i+1}) ID: {cam['id']} - {cam['description']} {hd_tag}")
        
    print("\nNote: For the golf swing studio, we need two cameras:")
    print("  1. Face-On Camera (Camera 1)")
    print("  2. Down-the-Line Camera (Camera 2)")
    
    # Select Camera 1
    cam1_idx = -1
    while True:
        try:
            val = input("\nSelect Camera 1 (Face-On) [1-{}]: ".format(len(working)))
            cam1_idx = int(val) - 1
            if 0 <= cam1_idx < len(working):
                break
            print("Invalid selection.")
        except ValueError:
            print("Please enter a number.")
            
    # Select Camera 2
    cam2_idx = -1
    if len(working) > 1:
        while True:
            try:
                val = input("Select Camera 2 (Down-the-Line) [1-{}]: ".format(len(working)))
                cam2_idx = int(val) - 1
                if 0 <= cam2_idx < len(working):
                    break
                print("Invalid selection.")
            except ValueError:
                print("Please enter a number.")
    else:
        print("\nOnly one camera found. Using same camera for both views (Testing Mode).")
        cam2_idx = cam1_idx
        
    cam1 = working[cam1_idx]
    cam2 = working[cam2_idx]
    
    config = {
        "platform": sys.platform,
        "camera1_id": cam1['id'],
        "camera2_id": cam2['id'],
        "camera1_details": cam1,
        "camera2_details": cam2,
        "detection_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Save
    if ConfigManager.save(config):
        print(f"\nConfiguration saved to {ConfigManager.get_config_path()}")
        print(f"Camera 1: {cam1['id']}")
        print(f"Camera 2: {cam2['id']}")
        return 0
    else:
        print(f"Failed to save config.")
        return 1

if __name__ == "__main__":
    sys.exit(interactive_configure())
