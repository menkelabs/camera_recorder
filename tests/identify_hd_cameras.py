"""
Identify HD USB cameras and test them
"""

import cv2
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_camera_detailed(index):
    """Test a camera and get detailed info"""
    try:
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            return None
        
        # Try to read a frame
        ret, frame = cap.read()
        if not ret:
            cap.release()
            return None
        
        # Get properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        backend = cap.getBackendName()
        
        # Try to get supported resolutions (test common HD resolutions)
        resolutions = []
        test_resolutions = [
            (1920, 1080),  # Full HD
            (1280, 720),   # HD
            (640, 480),    # VGA
            (640, 360),    # 360p
        ]
        
        for w, h in test_resolutions:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
            actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if actual_w == w and actual_h == h:
                resolutions.append((w, h))
        
        cap.release()
        
        return {
            'index': index,
            'width': width,
            'height': height,
            'fps': fps,
            'backend': backend,
            'resolutions': resolutions,
            'current_resolution': (width, height)
        }
    except Exception as e:
        return None

def main():
    print("=" * 70)
    print("HD USB Camera Identifier")
    print("=" * 70)
    print()
    print("Scanning for cameras...")
    print()
    
    cameras = []
    
    # Test cameras 0-9
    for i in range(10):
        info = test_camera_detailed(i)
        if info:
            cameras.append(info)
    
    if not cameras:
        print("[X] No cameras found!")
        return
    
    print(f"Found {len(cameras)} camera(s):")
    print()
    
    hd_cameras = []
    
    for cam in cameras:
        w, h = cam['current_resolution']
        is_hd = w >= 1280 or h >= 720
        
        status = "[HD]" if is_hd else "[SD]"
        print(f"Camera {cam['index']}: {status}")
        print(f"  Current: {w}x{h}")
        print(f"  Supported resolutions: {cam['resolutions']}")
        print(f"  Backend: {cam['backend']}")
        print()
        
        if is_hd or len(cameras) <= 2:
            hd_cameras.append(cam['index'])
    
    print("=" * 70)
    
    if len(cameras) >= 2:
        # Recommend the first 2 cameras
        cam1 = cameras[0]['index']
        cam2 = cameras[1]['index'] if len(cameras) > 1 else cameras[0]['index']
        
        print(f"Recommended camera IDs for dual recording:")
        print(f"  Camera 1: index {cam1}")
        print(f"  Camera 2: index {cam2}")
        print()
        print("Test command:")
        print(f"  python debug_recorder.py --test 1 --camera1 {cam1} --camera2 {cam2}")
        print()
        
        # Test if both can be opened simultaneously
        print("Testing simultaneous access...")
        cap1 = cv2.VideoCapture(cam1, cv2.CAP_DSHOW)
        cap2 = cv2.VideoCapture(cam2, cv2.CAP_DSHOW)
        
        if cap1.isOpened() and cap2.isOpened():
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()
            
            if ret1 and ret2:
                print("[OK] Both cameras can be accessed simultaneously!")
                print(f"  Camera {cam1}: {frame1.shape[1]}x{frame1.shape[0]}")
                print(f"  Camera {cam2}: {frame2.shape[1]}x{frame2.shape[0]}")
            else:
                print("[WARNING] Cameras opened but cannot read frames simultaneously")
        else:
            print("[WARNING] Cannot open both cameras simultaneously")
        
        cap1.release()
        cap2.release()
    else:
        print(f"[WARNING] Only found {len(cameras)} camera(s). Need 2 for dual recording.")

if __name__ == "__main__":
    main()

