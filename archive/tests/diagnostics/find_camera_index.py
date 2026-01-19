"""
Find camera index from device path
"""

import cv2
import sys

def find_camera_by_path(target_path: str):
    """Try to find camera index that matches the given device path"""
    print(f"Looking for camera with path: {target_path}")
    print("=" * 60)
    
    # Try direct access with the path as string
    print("\nTrying to open camera directly with path...")
    try:
        cap = cv2.VideoCapture(target_path)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"[OK] Camera opened directly with path!")
                print(f"  Frame size: {frame.shape[1]}x{frame.shape[0]}")
                cap.release()
                return target_path
            else:
                print("[X] Camera opened but cannot read frames")
                cap.release()
        else:
            print("[X] Cannot open camera directly with path")
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
    
    # Try to enumerate cameras and check their backends
    print("\nEnumerating cameras by index...")
    for i in range(10):
        try:
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)  # Try DirectShow backend
            if cap.isOpened():
                backend = cap.getBackendName()
                print(f"  Camera {i}: Backend={backend}", end="")
                
                # Try to get device info if available
                try:
                    # Some backends support getting device path
                    backend_name = cap.getBackendName()
                    print(f", Backend={backend_name}")
                except:
                    pass
                
                ret, frame = cap.read()
                if ret:
                    print(f" [OK] - Can read frames ({frame.shape[1]}x{frame.shape[0]})")
                    # Check if this might be our camera
                    # We can't directly get the path, but we can test if it works
                else:
                    print(f" [X] - Cannot read frames")
                cap.release()
        except Exception as e:
            pass
    
    return None

if __name__ == "__main__":
    camera_path = "0000.0014.0000.002.000.000.000.000.000"
    
    print("=" * 60)
    print("Camera Path Finder")
    print("=" * 60)
    
    result = find_camera_by_path(camera_path)
    
    if result:
        print(f"\n[OK] Use this path/ID: {result}")
    else:
        print("\n[X] Could not find camera with that path")
        print("\nTrying alternative: Use the path as a string in cv2.VideoCapture()")
        print("Example: cap = cv2.VideoCapture('0000.0014.0000.002.000.000.000.000.000')")

