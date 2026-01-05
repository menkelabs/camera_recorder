#!/usr/bin/env python3
"""
Detect Windows cameras and generate config_windows.json configuration file
Run this script to automatically detect and configure camera IDs for Windows
"""

import cv2
import sys
import os
import json
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(project_root, 'config_windows.json')


def test_camera(camera_id: int):
    """Test if a camera can be opened and read from, and check if it's HD USB"""
    try:
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        
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
                'is_hd_usb': False
            }
        
        # Get camera properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        backend = cap.getBackendName()
        
        # Test if it supports 720p@60fps (indicator of HD USB camera)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 60)
        
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Test frame capture rate
        frame_count = 0
        import time
        start_time = time.time()
        test_duration = 0.5  # Shorter test
        
        while time.time() - start_time < test_duration:
            ret, _ = cap.read()
            if ret:
                frame_count += 1
            time.sleep(0.001)
        
        measured_fps = frame_count / (time.time() - start_time) if (time.time() - start_time) > 0 else 0
        
        cap.release()
        
        # Determine if this is likely an HD USB camera
        is_hd_usb = (
            actual_width == 1280 and 
            actual_height == 720 and 
            actual_fps >= 50 and  # Can set to 60fps
            measured_fps >= 30    # Can actually capture at reasonable rate
        )
        
        return {
            'id': camera_id,
            'status': 'working',
            'description': 'Opens and can read frames',
            'resolution': f"{width}x{height}",
            'fps': float(fps),
            'backend': backend,
            'is_hd_usb': is_hd_usb,
            'supports_720p_60fps': is_hd_usb,
            'measured_fps': measured_fps
        }
    except Exception as e:
        return {
            'id': camera_id,
            'status': 'error',
            'description': f'Error: {str(e)}',
            'is_hd_usb': False
        }


def detect_cameras():
    """Detect all available cameras"""
    print("=" * 70)
    print("Windows Camera Detection")
    print("=" * 70)
    print("\nScanning cameras 0-9...\n")
    
    detected_cameras = []
    working_cameras = []
    hd_usb_cameras = []
    
    # Test cameras 0-9
    for i in range(10):
        print(f"Testing Camera {i}...", end=" ")
        result = test_camera(i)
        
        if result:
            detected_cameras.append(result)
            if result['status'] == 'working':
                working_cameras.append(result['id'])
                if result.get('is_hd_usb', False):
                    hd_usb_cameras.append(result['id'])
                    print(f"[OK] HD USB - {result.get('resolution', 'N/A')} @ {result.get('measured_fps', 0):.1f}fps (720p@60fps supported)")
                else:
                    print(f"[OK] Working - {result.get('resolution', 'N/A')} @ {result.get('fps', 0):.1f}fps (not HD USB)")
            elif result['status'] == 'opens_but_no_frames':
                print("[WARNING] Opens but cannot read frames")
            else:
                print(f"[ERROR] {result.get('description', 'Unknown error')}")
        else:
            print("[SKIP] Not available")
    
    print("\n" + "=" * 70)
    print(f"Detection Results: {len(working_cameras)} working camera(s), {len(hd_usb_cameras)} HD USB camera(s)")
    print("=" * 70)
    
    # Prefer HD USB cameras for dual recording
    if len(hd_usb_cameras) >= 2:
        camera1_id = hd_usb_cameras[0]
        camera2_id = hd_usb_cameras[1]
        print(f"\n[OK] Found 2 HD USB cameras!")
        print(f"  Camera 1: ID {camera1_id} (HD USB)")
        print(f"  Camera 2: ID {camera2_id} (HD USB)")
    elif len(hd_usb_cameras) == 1 and len(working_cameras) >= 2:
        camera1_id = hd_usb_cameras[0]
        # Use another working camera if available
        other_cameras = [c for c in working_cameras if c != camera1_id]
        camera2_id = other_cameras[0] if other_cameras else camera1_id
        print(f"\n[WARNING] Found 1 HD USB camera and {len(other_cameras)} other working camera(s)")
        print(f"  Camera 1: ID {camera1_id} (HD USB)")
        print(f"  Camera 2: ID {camera2_id} ({'HD USB' if camera2_id in hd_usb_cameras else 'Other'})")
    elif len(working_cameras) >= 2:
        camera1_id = working_cameras[0]
        camera2_id = working_cameras[1]
        print(f"\n[WARNING] Found 2 working cameras but none are HD USB")
        print(f"  Camera 1: ID {camera1_id}")
        print(f"  Camera 2: ID {camera2_id}")
    elif len(working_cameras) == 1:
        camera1_id = working_cameras[0]
        camera2_id = working_cameras[0]  # Use same camera if only one available
        print(f"\n[WARNING] Only found 1 working camera (ID {camera1_id})")
        print(f"  Camera 1: ID {camera1_id}")
        print(f"  Camera 2: ID {camera2_id} (same as Camera 1 - connect another camera)")
    else:
        # Fallback: use cameras that open but can't read frames
        opens_cameras = [c['id'] for c in detected_cameras if c['status'] == 'opens_but_no_frames']
        if len(opens_cameras) >= 2:
            camera1_id = opens_cameras[0]
            camera2_id = opens_cameras[1]
            print(f"\n[WARNING] No fully working cameras, but found cameras that open:")
            print(f"  Camera 1: ID {camera1_id} (opens but may not read frames)")
            print(f"  Camera 2: ID {camera2_id} (opens but may not read frames)")
        elif len(opens_cameras) >= 1:
            camera1_id = opens_cameras[0]
            camera2_id = opens_cameras[0]
            print(f"\n[WARNING] No fully working cameras, but found camera that opens:")
            print(f"  Camera 1: ID {camera1_id} (opens but may not read frames)")
            print(f"  Camera 2: ID {camera2_id} (same as Camera 1)")
        else:
            camera1_id = 0
            camera2_id = 2
            print(f"\n[ERROR] No cameras detected!")
            print(f"  Using default IDs: Camera 1 = {camera1_id}, Camera 2 = {camera2_id}")
    
    return {
        'platform': 'windows',
        'camera1_id': camera1_id,
        'camera2_id': camera2_id,
        'detected_cameras': detected_cameras,
        'detection_date': datetime.now().strftime('%Y-%m-%d'),
        'notes': f'Camera detection completed. {len(working_cameras)} working camera(s) found, {len(hd_usb_cameras)} HD USB camera(s).'
    }


def generate_config():
    """Generate Windows configuration file"""
    config = detect_cameras()
    
    print("\n" + "=" * 70)
    print("Generating config_windows.json...")
    print("=" * 70)
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"\n[OK] Configuration file created: {config_path}")
        print("\nConfiguration:")
        print(f"  Camera 1 ID: {config['camera1_id']}")
        print(f"  Camera 2 ID: {config['camera2_id']}")
        print(f"  Detected cameras: {len(config['detected_cameras'])}")
        print(f"  Working cameras: {len([c for c in config['detected_cameras'] if c['status'] == 'working'])}")
        
        print("\nThe application will now use these camera IDs on Windows.")
        print("To regenerate this file, run this script again.")
        
        return 0
    except Exception as e:
        print(f"\n[ERROR] Failed to write config file: {e}")
        return 1


if __name__ == "__main__":
    if sys.platform != 'win32':
        print("Warning: This script is designed for Windows. Running anyway...\n")
    
    sys.exit(generate_config())

