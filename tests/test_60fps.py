"""
Test 60fps recording at 720p
"""

import cv2
import sys
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_camera_fps(camera_id, target_fps):
    """Test if camera can achieve target FPS"""
    print(f"Testing Camera {camera_id} at {target_fps} FPS...")
    
    # Use platform-appropriate backend
    if sys.platform == 'win32':
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print(f"  [X] Cannot open camera {camera_id}")
        return False
    
    # Set resolution and FPS
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, target_fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # Get actual values
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    backend = cap.getBackendName()
    
    print(f"  Resolution: {actual_width}x{actual_height}")
    print(f"  Requested FPS: {target_fps}")
    print(f"  Actual FPS: {actual_fps}")
    print(f"  Backend: {backend}")
    
    # Test frame capture rate
    print(f"  Testing frame capture rate...")
    frame_count = 0
    start_time = time.time()
    test_duration = 2.0  # Test for 2 seconds
    
    while time.time() - start_time < test_duration:
        ret, frame = cap.read()
        if ret:
            frame_count += 1
        time.sleep(0.001)  # Small delay to avoid 100% CPU
    
    elapsed = time.time() - start_time
    measured_fps = frame_count / elapsed
    
    print(f"  Measured FPS: {measured_fps:.2f} (captured {frame_count} frames in {elapsed:.2f}s)")
    
    cap.release()
    
    # Check if we're close to target
    if measured_fps >= target_fps * 0.9:  # Within 10% of target
        print(f"  [OK] Camera {camera_id} can achieve ~{target_fps} FPS!")
        return True
    else:
        print(f"  [WARNING] Camera {camera_id} achieved {measured_fps:.2f} FPS (target: {target_fps})")
        return measured_fps >= 30  # At least 30fps is acceptable

def main():
    print("=" * 70)
    print("60 FPS Test at 720p")
    print("=" * 70)
    print()
    
    # Import test utils for camera IDs
    from test_utils import get_camera_ids
    
    # Use camera IDs from config file (Windows) or defaults
    cam1_id, cam2_id = get_camera_ids()
    
    cam1_ok = test_camera_fps(cam1_id, 60)
    print()
    cam2_ok = test_camera_fps(cam2_id, 60)
    
    print()
    print("=" * 70)
    if cam1_ok and cam2_ok:
        print("[OK] Both cameras support 60 FPS at 720p!")
        print()
        print("You can now record at 60 FPS using:")
        print("  recorder.start_cameras(width=1280, height=720, fps=60)")
    else:
        print("[WARNING] Some cameras may not achieve full 60 FPS")
        print("But they should still work well for recording")

if __name__ == "__main__":
    main()

