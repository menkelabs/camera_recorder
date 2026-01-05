"""
Test 240fps recording to confirm no frame drops from both cameras
"""

import cv2
import sys
import time
import os
from datetime import datetime
import sys
import os
# Add src directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from dual_camera_recorder import DualCameraRecorder

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def count_frames_in_video(video_path):
    """Count actual frames in a video file"""
    if not os.path.exists(video_path):
        return None
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_count += 1
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count_prop = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0
    
    cap.release()
    
    return {
        'counted': frame_count,
        'property': frame_count_prop,
        'fps': fps,
        'duration': duration
    }

def main():
    print("=" * 70)
    print("240 FPS Frame Drop Test - Both Cameras")
    print("=" * 70)
    print()
    
    # Test parameters
    test_duration = 5  # seconds - shorter for high-speed test
    target_fps = 240
    expected_frames = test_duration * target_fps  # 5 seconds * 240fps = 1200 frames
    
    print(f"Test Configuration:")
    print(f"  Resolution: 640x480")
    print(f"  Frame Rate: {target_fps} FPS")
    print(f"  Duration: {test_duration} seconds")
    print(f"  Expected frames: {expected_frames}")
    print()
    print("This will verify:")
    print("  ✓ Both cameras can achieve 240fps")
    print("  ✓ No frame drops in recording pipeline")
    print("  ✓ Synchronized recording works at high speed")
    print()
    
    # Import test utils for camera IDs
    from test_utils import get_camera_ids
    
    # Use camera IDs from config file (Windows) or defaults
    cam1_id, cam2_id = get_camera_ids()
    recorder = DualCameraRecorder(camera1_id=cam1_id, camera2_id=cam2_id)
    
    try:
        # Start cameras at 240fps
        print("Starting cameras at 640x480 @ 240fps...")
        recorder.start_cameras(width=640, height=480, fps=240)
        print()
        
        # Create test output name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"240fps_test_{timestamp}"
        
        print(f"Starting recording: {output_name}")
        print(f"Recording for {test_duration} seconds...")
        print()
        
        # Start recording
        recorder.start_recording(output_name)
        
        # Monitor recording
        start_time = time.time()
        last_stats_time = start_time
        stats_interval = 1.0  # Print stats every second
        
        while time.time() - start_time < test_duration:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Print stats every second
            if current_time - last_stats_time >= stats_interval:
                stats = {
                    'camera1_frames': recorder.camera1.frame_count,
                    'camera2_frames': recorder.camera2.frame_count,
                    'frames_written': recorder.frames_written,
                    'frames_dropped': recorder.frames_dropped
                }
                
                # Calculate expected frames so far
                expected_so_far = int(elapsed * target_fps)
                
                print(f"[{elapsed:.1f}s] "
                      f"Cam1: {stats['camera1_frames']} (exp: ~{expected_so_far}), "
                      f"Cam2: {stats['camera2_frames']} (exp: ~{expected_so_far}), "
                      f"Written: {stats['frames_written']}, "
                      f"Dropped: {stats['frames_dropped']}")
                last_stats_time = current_time
            
            time.sleep(0.1)
        
        # Stop recording
        print()
        print("Stopping recording...")
        recorder.stop_recording()
        
        # Get final stats
        final_stats = {
            'camera1_frames': recorder.camera1.frame_count,
            'camera2_frames': recorder.camera2.frame_count,
            'frames_written': recorder.frames_written,
            'frames_dropped': recorder.frames_dropped
        }
        
        print()
        print("=" * 70)
        print("Recording Statistics")
        print("=" * 70)
        print()
        
        print(f"Camera 1 frames captured: {final_stats['camera1_frames']}")
        print(f"Camera 2 frames captured: {final_stats['camera2_frames']}")
        print(f"Frames written (synchronized): {final_stats['frames_written']}")
        print(f"Frames dropped: {final_stats['frames_dropped']}")
        print()
        
        # Calculate frame rates
        cam1_fps = final_stats['camera1_frames'] / test_duration
        cam2_fps = final_stats['camera2_frames'] / test_duration
        written_fps = final_stats['frames_written'] / test_duration
        
        print(f"Measured frame rates:")
        print(f"  Camera 1: {cam1_fps:.1f} FPS (target: {target_fps} FPS)")
        print(f"  Camera 2: {cam2_fps:.1f} FPS (target: {target_fps} FPS)")
        print(f"  Written: {written_fps:.1f} FPS (target: {target_fps} FPS)")
        print()
        
        # Check if cameras achieved target FPS
        cam1_ok = cam1_fps >= target_fps * 0.9  # Within 10%
        cam2_ok = cam2_fps >= target_fps * 0.9
        written_ok = written_fps >= target_fps * 0.9
        
        # Frame drop rate
        if final_stats['frames_written'] > 0:
            drop_rate = (final_stats['frames_dropped'] / final_stats['frames_written']) * 100
            print(f"Frame drop rate: {drop_rate:.2f}%")
        print()
        
        # Check against expected
        print(f"Expected frames (for {test_duration}s @ {target_fps}fps): {expected_frames}")
        print(f"Actual frames written: {final_stats['frames_written']}")
        
        if final_stats['frames_written'] >= expected_frames * 0.9:  # Within 10%
            print("[OK] Frame count is within acceptable range!")
        else:
            diff = expected_frames - final_stats['frames_written']
            print(f"[WARNING] Missing {diff} frames ({diff/expected_frames*100:.1f}%)")
        print()
        
        # Verify video files
        print("=" * 70)
        print("Video File Verification")
        print("=" * 70)
        print()
        
        video1_path = os.path.join("recordings", f"{output_name}_camera1.mp4")
        video2_path = os.path.join("recordings", f"{output_name}_camera2.mp4")
        
        print(f"Checking: {video1_path}")
        info1 = count_frames_in_video(video1_path)
        if info1:
            print(f"  Frames (counted): {info1['counted']}")
            print(f"  Frames (property): {info1['property']}")
            print(f"  FPS: {info1['fps']:.2f}")
            print(f"  Duration: {info1['duration']:.2f} seconds")
            print(f"  Expected: {expected_frames} frames")
            
            if abs(info1['counted'] - expected_frames) <= expected_frames * 0.1:
                print(f"  [OK] Frame count matches expected!")
            else:
                diff = expected_frames - info1['counted']
                print(f"  [WARNING] Difference: {diff} frames ({diff/expected_frames*100:.1f}%)")
        else:
            print("  [ERROR] Could not read video file")
        
        print()
        print(f"Checking: {video2_path}")
        info2 = count_frames_in_video(video2_path)
        if info2:
            print(f"  Frames (counted): {info2['counted']}")
            print(f"  Frames (property): {info2['property']}")
            print(f"  FPS: {info2['fps']:.2f}")
            print(f"  Duration: {info2['duration']:.2f} seconds")
            print(f"  Expected: {expected_frames} frames")
            
            if abs(info2['counted'] - expected_frames) <= expected_frames * 0.1:
                print(f"  [OK] Frame count matches expected!")
            else:
                diff = expected_frames - info2['counted']
                print(f"  [WARNING] Difference: {diff} frames ({diff/expected_frames*100:.1f}%)")
        else:
            print("  [ERROR] Could not read video file")
        
        # Final summary
        print()
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        print()
        
        all_good = (
            cam1_ok and cam2_ok and written_ok and
            final_stats['frames_dropped'] == 0 and
            info1 and info2 and
            abs(info1['counted'] - expected_frames) <= expected_frames * 0.1 and
            abs(info2['counted'] - expected_frames) <= expected_frames * 0.1
        )
        
        if all_good:
            print("✅ CONFIRMED: 240 FPS WITHOUT FRAME DROPS!")
            print()
            print(f"  ✓ Camera 1: {cam1_fps:.1f} FPS (target: {target_fps})")
            print(f"  ✓ Camera 2: {cam2_fps:.1f} FPS (target: {target_fps})")
            print(f"  ✓ Frames written: {final_stats['frames_written']}")
            print(f"  ✓ Frames dropped: {final_stats['frames_dropped']}")
            print(f"  ✓ Video files contain expected frame counts")
            print()
            print("  Both cameras can record at 240fps without dropping frames!")
        else:
            print("⚠️  Some issues detected:")
            if not cam1_ok:
                print(f"  - Camera 1 not achieving target FPS ({cam1_fps:.1f} < {target_fps})")
            if not cam2_ok:
                print(f"  - Camera 2 not achieving target FPS ({cam2_fps:.1f} < {target_fps})")
            if final_stats['frames_dropped'] > 0:
                print(f"  - {final_stats['frames_dropped']} frames dropped")
            if info1 and abs(info1['counted'] - expected_frames) > expected_frames * 0.1:
                print(f"  - Camera 1 video has frame count mismatch")
            if info2 and abs(info2['counted'] - expected_frames) > expected_frames * 0.1:
                print(f"  - Camera 2 video has frame count mismatch")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        recorder.stop_cameras()
        print("\nCameras stopped.")

if __name__ == "__main__":
    main()

