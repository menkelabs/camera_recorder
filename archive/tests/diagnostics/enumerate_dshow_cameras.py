"""
Enumerate DirectShow cameras and try to match device paths
"""

import cv2
import sys

def enumerate_cameras():
    """Try to enumerate and test all available cameras"""
    print("=" * 60)
    print("DirectShow Camera Enumerator")
    print("=" * 60)
    print()
    
    target_path = "0000.0014.0000.002.000.000.000.000.000"
    print(f"Looking for camera with path: {target_path}")
    print()
    
    # Try cameras 0-10
    working_cameras = []
    
    for i in range(10):
        try:
            print(f"Testing camera index {i}...", end=" ")
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    backend = cap.getBackendName()
                    
                    print(f"[OK] - {width}x{height} @ {fps}fps, Backend: {backend}")
                    working_cameras.append({
                        'index': i,
                        'width': width,
                        'height': height,
                        'fps': fps,
                        'backend': backend
                    })
                else:
                    print("[X] - Opened but cannot read frames")
                cap.release()
            else:
                print("[X] - Cannot open")
        except Exception as e:
            print(f"[ERROR] - {e}")
    
    print()
    print("=" * 60)
    print(f"Found {len(working_cameras)} working camera(s):")
    for cam in working_cameras:
        print(f"  Camera {cam['index']}: {cam['width']}x{cam['height']} @ {cam['fps']}fps")
    
    print()
    print("Note: The device path format may not be directly supported by OpenCV.")
    print("Try using the camera index instead:")
    if working_cameras:
        print(f"  Camera 1 (first camera): index {working_cameras[0]['index']}")
        if len(working_cameras) > 1:
            print(f"  Camera 2 (second camera): index {working_cameras[1]['index']}")
    
    # Try alternative: maybe the path needs to be formatted differently
    print()
    print("Trying alternative path formats...")
    alternative_paths = [
        target_path,
        f"@device:pnp:\\\\?\\{target_path}",
        f"@device:sw:{target_path}",
        f"\\\\?\\{target_path}",
    ]
    
    for alt_path in alternative_paths:
        try:
            cap = cv2.VideoCapture(alt_path, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    print(f"[OK] Found working path format: {alt_path}")
                    cap.release()
                    return alt_path
                cap.release()
        except:
            pass
    
    print("[X] No alternative path format worked")
    return None

if __name__ == "__main__":
    result = enumerate_cameras()
    if result:
        print(f"\nUse this path: {result}")
    else:
        print("\nRecommendation: Use camera index instead of device path")

