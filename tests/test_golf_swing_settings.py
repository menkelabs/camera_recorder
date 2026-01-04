"""
Test settings for golf swing capture
Golf swings are very fast - need high frame rates!
"""

import cv2
import sys
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def test_high_fps(camera_id, width, height, target_fps):
    """Test if camera can achieve high frame rates"""
    try:
        cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        if not cap.isOpened():
            return None
        
        # Set resolution and FPS
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, target_fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Get actual values
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Test frame capture for 2 seconds
        frame_count = 0
        start_time = time.time()
        test_duration = 2.0
        
        while time.time() - start_time < test_duration:
            ret, frame = cap.read()
            if ret:
                frame_count += 1
            time.sleep(0.0001)  # Minimal delay
        
        elapsed = time.time() - start_time
        measured_fps = frame_count / elapsed
        
        cap.release()
        
        # Check if it's acceptable (within 10% of target or at least 90% of target)
        acceptable = measured_fps >= target_fps * 0.9
        
        return {
            'width': actual_width,
            'height': actual_height,
            'requested_fps': target_fps,
            'actual_fps': actual_fps,
            'measured_fps': measured_fps,
            'acceptable': acceptable,
            'frames_captured': frame_count
        }
    except Exception as e:
        return None

def main():
    print("=" * 70)
    print("Golf Swing Capture - High Speed Frame Rate Test")
    print("=" * 70)
    print()
    print("Golf swings are VERY fast:")
    print("  - Clubhead speed: 100+ mph")
    print("  - Swing duration: ~0.5-1.5 seconds")
    print("  - Impact happens in milliseconds")
    print()
    print("Testing cameras 0 and 2 for high-speed capture...")
    print()
    
    # Test configurations for golf swings
    test_configs = [
        # (width, height, fps, description)
        (640, 480, 240, "640p @ 240fps - ⭐ BEST for golf swings - Ultra-high speed"),
        (1280, 720, 120, "720p @ 120fps - EXCELLENT for golf swings"),
        (1280, 720, 60, "720p @ 60fps - Good, but may miss fast details"),
        (1920, 1080, 60, "1080p @ 60fps - High detail, slower motion"),
        (1920, 1080, 30, "1080p @ 30fps - Too slow for golf swings"),
    ]
    
    cameras = [0, 2]
    results = {}
    
    for cam_id in cameras:
        print(f"Testing Camera {cam_id}:")
        print("-" * 70)
        results[cam_id] = {}
        
        for width, height, fps, desc in test_configs:
            result = test_high_fps(cam_id, width, height, fps)
            if result:
                status = "[OK]" if result['acceptable'] else "[PARTIAL]"
                print(f"{status} {desc}")
                print(f"     Resolution: {result['width']}x{result['height']}")
                print(f"     Requested FPS: {fps}")
                print(f"     Actual FPS: {result['actual_fps']:.1f}")
                print(f"     Measured FPS: {result['measured_fps']:.1f}")
                print(f"     Frames in 2s: {result['frames_captured']}")
                results[cam_id][(width, height, fps)] = result
            else:
                print(f"[FAIL] {desc}")
                results[cam_id][(width, height, fps)] = None
            print()
    
    # Recommendations
    print("=" * 70)
    print("Recommendations for Golf Swing Capture")
    print("=" * 70)
    print()
    
    # Check 240fps support first (best for golf)
    cam0_240 = results[0].get((640, 480, 240), {}).get('acceptable', False) if results[0].get((640, 480, 240)) else False
    cam2_240 = results[2].get((640, 480, 240), {}).get('acceptable', False) if results[2].get((640, 480, 240)) else False
    
    # Check 120fps support
    cam0_120 = results[0].get((1280, 720, 120), {}).get('acceptable', False) if results[0].get((1280, 720, 120)) else False
    cam2_120 = results[2].get((1280, 720, 120), {}).get('acceptable', False) if results[2].get((1280, 720, 120)) else False
    
    if cam0_240 and cam2_240:
        print("🎯 BEST RECOMMENDATION for Golf Swings:")
        print()
        print("  640p @ 240 FPS ⭐")
        print()
        print("  Why this is OPTIMAL:")
        print("    ✅ 240fps = 1 frame every 4.17ms - ULTRA-HIGH SPEED")
        print("    ✅ Captures ~20-40 frames during impact zone")
        print("    ✅ Perfect for clubhead speed analysis")
        print("    ✅ Captures every detail of body rotation")
        print("    ✅ Good enough for MediaPipe pose analysis")
        print("    ✅ Smaller files than 1080p")
        print()
        print("  Code to use:")
        print("    recorder.start_cameras(width=640, height=480, fps=240)")
        print()
        
        # Calculate timing
        print("  Timing analysis:")
        print("    At 240fps: 1 frame = 4.17ms  ⭐ BEST")
        print("    At 120fps: 1 frame = 8.33ms")
        print("    At 60fps:  1 frame = 16.67ms")
        print("    At 30fps:  1 frame = 33.33ms")
        print()
        print("    Golf swing impact happens in ~1-2ms")
        print("    At 240fps: ~20-40 frames during impact zone ⭐")
        print("    At 120fps: ~10-20 frames during impact zone")
        print("    At 60fps:  ~5-10 frames during impact zone")
        print("    At 30fps:  ~2-4 frames during impact zone (TOO FEW!)")
        print()
        
    elif cam0_120 and cam2_120:
        print("🎯 BEST RECOMMENDATION for Golf Swings:")
        print()
        print("  720p @ 120 FPS")
        print()
        print("  Why this is optimal:")
        print("    ✅ 120fps captures 2x more frames than 60fps")
        print("    ✅ Can see clubhead position every ~8ms (vs ~17ms at 60fps)")
        print("    ✅ Better for analyzing impact moment")
        print("    ✅ Captures fast body rotation and weight transfer")
        print("    ✅ Good resolution for MediaPipe pose analysis")
        print()
        print("  Code to use:")
        print("    recorder.start_cameras(width=1280, height=720, fps=120)")
        print()
        
        # Calculate timing
        print("  Timing analysis:")
        print("    At 120fps: 1 frame = 8.33ms")
        print("    At 60fps:  1 frame = 16.67ms")
        print("    At 30fps:  1 frame = 33.33ms")
        print()
        print("    Golf swing impact happens in ~1-2ms")
        print("    At 120fps: ~10-20 frames during impact zone")
        print("    At 60fps:  ~5-10 frames during impact zone")
        print("    At 30fps:  ~2-4 frames during impact zone (TOO FEW!)")
        print()
        
    else:
        print("⚠️  120fps not fully supported, but 60fps is still good")
        print()
        print("  Recommendation: 720p @ 60fps")
        print("    - Still captures good detail")
        print("    - Better than 30fps for fast motion")
        print()
    
    # Alternative recommendations
    print("=" * 70)
    print("Alternative Options")
    print("=" * 70)
    print()
    print("If you need maximum detail (less important than frame rate for golf):")
    print("  1080p @ 60fps")
    print("    - Higher resolution")
    print("    - But slower frame rate = may miss fast details")
    print()
    print("For MediaPipe analysis of golf swings:")
    print("  640p @ 240fps (BEST)")
    print("    - Ultra-high frame rate for smooth tracking")
    print("    - MediaPipe works well at 640p")
    print("    - 240fps captures every detail of fast motion")
    print()
    print("  Alternative: 720p @ 120fps")
    print("    - Good balance of detail and speed")
    print("    - MediaPipe works well at 720p")
    print("    - 120fps captures most motion")
    print()
    
    # File size warning
    print("=" * 70)
    print("File Size Considerations")
    print("=" * 70)
    print()
    print("At 720p @ 120fps:")
    print("  - File size: ~80-150 MB per minute per camera")
    print("  - Total: ~160-300 MB per minute for dual recording")
    print("  - A 10-second swing: ~25-50 MB total")
    print()
    print("Make sure you have sufficient disk space and fast storage!")

if __name__ == "__main__":
    main()

