"""
Test camera resolutions and frame rates for MediaPipe analysis
MediaPipe works best with high resolution and good frame rates
"""

import cv2
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_utils import create_camera_capture, fix_console_encoding, get_camera_ids, print_platform_banner

fix_console_encoding()

def test_resolution_fps(camera_id, width, height, target_fps):
    """Test if camera supports a specific resolution and FPS"""
    try:
        cap = create_camera_capture(camera_id)
    except ValueError:
        return None

    try:
        # Set resolution and FPS
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, target_fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Get actual values
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Test frame capture
        frame_count = 0
        start_time = time.time()
        test_duration = 1.0
        
        while time.time() - start_time < test_duration:
            ret, frame = cap.read()
            if ret:
                frame_count += 1
            time.sleep(0.001)
        
        measured_fps = frame_count / (time.time() - start_time)
        
        cap.release()
        
        # Check if it matches what we requested
        matches = (actual_width == width and actual_height == height)
        fps_ok = actual_fps >= target_fps * 0.9  # Within 10%
        
        return {
            'width': actual_width,
            'height': actual_height,
            'fps': actual_fps,
            'measured_fps': measured_fps,
            'matches': matches,
            'fps_ok': fps_ok,
            'works': matches and fps_ok
        }
    except Exception as e:
        return None

def main():
    print("=" * 70)
    print("MediaPipe Optimal Resolution Test")
    print("=" * 70)
    print()
    print("Testing cameras 0 and 2 (HD USB cameras)")
    print()
    
    # Test resolutions - MediaPipe works best with higher resolution
    # Common resolutions for MediaPipe: 720p, 1080p
    test_configs = [
        # (width, height, fps, description)
        (1920, 1080, 30, "1080p @ 30fps - High detail, smooth motion"),
        (1920, 1080, 60, "1080p @ 60fps - Maximum detail + smooth motion"),
        (1280, 720, 60, "720p @ 60fps - Good detail, very smooth"),
        (1280, 720, 30, "720p @ 30fps - Good detail, smooth"),
        (640, 480, 60, "480p @ 60fps - Lower detail, very smooth"),
    ]
    
    # Import test utils for camera IDs
    from test_utils import get_camera_ids
    
    # Use camera IDs from config file (Windows) or defaults
    cam1_id, cam2_id = get_camera_ids()
    cameras = [cam1_id, cam2_id]
    results = {}
    
    for cam_id in cameras:
        print(f"Testing Camera {cam_id}:")
        print("-" * 70)
        results[cam_id] = {}
        
        for width, height, fps, desc in test_configs:
            result = test_resolution_fps(cam_id, width, height, fps)
            if result:
                status = "[OK]" if result['works'] else "[PARTIAL]"
                print(f"{status} {desc}")
                print(f"     Actual: {result['width']}x{result['height']} @ {result['fps']:.1f}fps")
                print(f"     Measured: {result['measured_fps']:.1f} FPS")
                results[cam_id][(width, height, fps)] = result
            else:
                print(f"[FAIL] {desc}")
                results[cam_id][(width, height, fps)] = None
            print()
    
    # Recommendations
    print("=" * 70)
    print("Recommendations for MediaPipe Analysis")
    print("=" * 70)
    print()
    
    # Check what works for both cameras
    working_configs = []
    for config in test_configs:
        width, height, fps, desc = config
        cam1_ok = results[cam1_id].get((width, height, fps), {}).get('works', False) if results[cam1_id].get((width, height, fps)) else False
        cam2_ok = results[cam2_id].get((width, height, fps), {}).get('works', False) if results[cam2_id].get((width, height, fps)) else False
        
        if cam1_ok and cam2_ok:
            working_configs.append((width, height, fps, desc))
    
    if working_configs:
        print("✅ Both cameras support these configurations:")
        print()
        for width, height, fps, desc in working_configs:
            print(f"  • {width}x{height} @ {fps}fps - {desc}")
        print()
        
        # Best recommendation
        print("🎯 BEST RECOMMENDATION for MediaPipe:")
        print()
        
        # Prefer 1080p if available, then 720p@60fps
        best = None
        for width, height, fps, desc in working_configs:
            if width == 1920 and height == 1080:
                if best is None or (best[2] < fps):
                    best = (width, height, fps, desc)
        
        if best is None:
            # Fall back to highest FPS 720p
            for width, height, fps, desc in working_configs:
                if width == 1280 and height == 720:
                    if best is None or (best[2] < fps):
                        best = (width, height, fps, desc)
        
        if best:
            width, height, fps, desc = best
            print(f"  Resolution: {width}x{height}")
            print(f"  Frame Rate: {fps} FPS")
            print(f"  Why: {desc}")
            print()
            print("  Code to use:")
            print(f"  recorder.start_cameras(width={width}, height={height}, fps={fps})")
            print()
            print("  Benefits for MediaPipe:")
            if width == 1920:
                print("    • Maximum detail for pose/hand/face detection")
                print("    • Better accuracy for landmark detection")
                print("    • More pixels = better tracking precision")
            if fps >= 60:
                print("    • Smooth motion capture")
                print("    • Better tracking of fast movements")
                print("    • Reduced motion blur in analysis")
            if width == 1920 and fps >= 60:
                print("    • BEST: Maximum detail + smooth motion")
            elif width == 1920:
                print("    • High detail, good for detailed analysis")
            elif fps >= 60:
                print("    • Good detail, excellent for motion tracking")
    else:
        print("⚠️  No configurations work for both cameras")
        print("   Check individual camera results above")

if __name__ == "__main__":
    main()

