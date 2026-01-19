"""
Find the 2 HD USB cameras (exclude built-in system camera)
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
        
        # Test if it supports 60fps at 720p
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 60)
        
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Test frame capture rate at 60fps
        frame_count = 0
        import time
        start_time = time.time()
        test_duration = 1.0
        
        while time.time() - start_time < test_duration:
            ret, _ = cap.read()
            if ret:
                frame_count += 1
            time.sleep(0.001)
        
        measured_fps = frame_count / (time.time() - start_time)
        
        cap.release()
        
        # Determine if this is likely a USB camera (not built-in)
        # Built-in cameras typically can't do 60fps at 720p
        is_hd_usb = (
            actual_width == 1280 and 
            actual_height == 720 and 
            actual_fps >= 50 and  # Can set to 60fps
            measured_fps >= 30    # Can actually capture at reasonable rate
        )
        
        return {
            'index': index,
            'width': width,
            'height': height,
            'fps': fps,
            'backend': backend,
            'supports_720p_60fps': is_hd_usb,
            'actual_fps_at_720p': actual_fps,
            'measured_fps': measured_fps,
            'current_resolution': (width, height)
        }
    except Exception as e:
        return None

def main():
    print("=" * 70)
    print("HD USB Camera Finder")
    print("=" * 70)
    print()
    print("Scanning cameras to find the 2 HD USB cameras...")
    print("(Excluding built-in system camera)")
    print()
    
    cameras = []
    hd_usb_cameras = []
    
    # Test cameras 0-9
    for i in range(10):
        info = test_camera_detailed(i)
        if info:
            cameras.append(info)
            if info['supports_720p_60fps']:
                hd_usb_cameras.append(info)
    
    print(f"Found {len(cameras)} total camera(s):")
    print()
    
    for cam in cameras:
        status = "[HD USB]" if cam['supports_720p_60fps'] else "[Built-in/Other]"
        print(f"Camera {cam['index']}: {status}")
        print(f"  Current: {cam['width']}x{cam['height']}")
        print(f"  Supports 720p@60fps: {cam['supports_720p_60fps']}")
        if cam['supports_720p_60fps']:
            print(f"  Actual FPS at 720p: {cam['actual_fps_at_720p']:.1f}")
            print(f"  Measured capture rate: {cam['measured_fps']:.1f} FPS")
        print()
    
    print("=" * 70)
    
    if len(hd_usb_cameras) >= 2:
        cam1 = hd_usb_cameras[0]['index']
        cam2 = hd_usb_cameras[1]['index']
        
        print(f"[OK] Found 2 HD USB cameras!")
        print()
        print(f"Recommended camera IDs:")
        print(f"  Camera 1: index {cam1}")
        print(f"  Camera 2: index {cam2}")
        print()
        print("Test command:")
        print(f"  python debug_recorder.py --test 1 --camera1 {cam1} --camera2 {cam2}")
        print()
        print("Or update your code to use:")
        print(f"  recorder = DualCameraRecorder(camera1_id={cam1}, camera2_id={cam2})")
        
        # Test simultaneous access
        print()
        print("Testing simultaneous access...")
        cap1 = cv2.VideoCapture(cam1, cv2.CAP_DSHOW)
        cap2 = cv2.VideoCapture(cam2, cv2.CAP_DSHOW)
        
        if cap1.isOpened() and cap2.isOpened():
            cap1.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap1.set(cv2.CAP_PROP_FPS, 60)
            cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            cap2.set(cv2.CAP_PROP_FPS, 60)
            
            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()
            
            if ret1 and ret2:
                print("[OK] Both HD USB cameras can be accessed simultaneously at 60fps!")
                print(f"  Camera {cam1}: {frame1.shape[1]}x{frame1.shape[0]}")
                print(f"  Camera {cam2}: {frame2.shape[1]}x{frame2.shape[0]}")
            else:
                print("[WARNING] Cameras opened but cannot read frames simultaneously")
        else:
            print("[WARNING] Cannot open both cameras simultaneously")
        
        cap1.release()
        cap2.release()
        
    elif len(hd_usb_cameras) == 1:
        print(f"[WARNING] Only found 1 HD USB camera (index {hd_usb_cameras[0]['index']})")
        print("Make sure both HD USB cameras are connected and not being used by other apps")
    else:
        print("[ERROR] No HD USB cameras found that support 720p@60fps")
        print("Make sure your HD USB cameras are connected")

if __name__ == "__main__":
    main()

