"""
Quick test script to check if cameras are accessible
Run this first to debug camera issues
"""

import cv2
import sys
import os

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def test_camera(camera_id: int):
    """Test if a camera can be opened and read from"""
    print(f"\nTesting Camera {camera_id}...")
    cap = cv2.VideoCapture(camera_id)
    
    if not cap.isOpened():
        print(f"  [X] Camera {camera_id} failed to open")
        return False
    
    print(f"  [OK] Camera {camera_id} opened successfully")
    
    # Try to read a frame
    ret, frame = cap.read()
    if not ret:
        print(f"  [X] Camera {camera_id} opened but cannot read frames")
        cap.release()
        return False
    
    print(f"  [OK] Camera {camera_id} can read frames")
    print(f"  Frame size: {frame.shape[1]}x{frame.shape[0]}")
    
    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    backend = cap.getBackendName()
    
    print(f"  Properties:")
    print(f"    Resolution: {width}x{height}")
    print(f"    FPS: {fps}")
    print(f"    Backend: {backend}")
    
    cap.release()
    return True


def main():
    print("=" * 60)
    print("Camera Diagnostic Tool")
    print("=" * 60)
    
    # Test cameras 0-4
    available_cameras = []
    for i in range(5):
        if test_camera(i):
            available_cameras.append(i)
    
    print("\n" + "=" * 60)
    if available_cameras:
        print(f"[OK] Found {len(available_cameras)} available camera(s): {available_cameras}")
        print("\nYou can use these camera IDs in the main application:")
        for cam_id in available_cameras:
            print(f"  Camera {cam_id}")
    else:
        print("[X] No cameras found!")
        print("\nTroubleshooting:")
        print("  1. Make sure cameras are connected via USB")
        print("  2. Check if cameras are being used by other applications")
        print("  3. Try unplugging and replugging the cameras")
        print("  4. On Windows, check Device Manager for camera issues")
        sys.exit(1)
    
    # Test simultaneous access
    if len(available_cameras) >= 2:
        print("\n" + "=" * 60)
        print("Testing simultaneous access to 2 cameras...")
        cap1 = cv2.VideoCapture(available_cameras[0])
        cap2 = cv2.VideoCapture(available_cameras[1])
        
        if cap1.isOpened() and cap2.isOpened():
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()
            
            if ret1 and ret2:
                print("[OK] Both cameras can be accessed simultaneously!")
            else:
                print("[WARNING] Cameras opened but cannot read frames simultaneously")
                if not ret1:
                    print(f"  Camera {available_cameras[0]} failed to read")
                if not ret2:
                    print(f"  Camera {available_cameras[1]} failed to read")
        else:
            print("[X] Cannot open both cameras simultaneously")
            if not cap1.isOpened():
                print(f"  Camera {available_cameras[0]} failed")
            if not cap2.isOpened():
                print(f"  Camera {available_cameras[1]} failed")
        
        cap1.release()
        cap2.release()


if __name__ == "__main__":
    main()

