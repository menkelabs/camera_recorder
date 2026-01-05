"""
Test script to verify no frame drops at 60fps
Records for a known duration and verifies frame count
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
    print("60 FPS Frame Drop Test")
    print("=" * 70)
    print()
    
    # Test parameters
    test_duration = 10  # seconds
    target_fps = 60
    expected_frames = test_duration * target_fps
    
    print(f"Test Configuration:")
    print(f"  Duration: {test_duration} seconds")
    print(f"  Target FPS: {target_fps}")
    print(f"  Expected frames: {expected_frames}")
    print()
    
    # Import test utils for camera IDs
    from test_utils import get_camera_ids
    
    # Use camera IDs from config file (Windows) or defaults
    cam1_id, cam2_id = get_camera_ids()
    recorder = DualCameraRecorder(camera1_id=cam1_id, camera2_id=cam2_id)
    
    try:
        # Start cameras at 60fps
        print("Starting cameras at 1280x720 @ 60fps...")
        recorder.start_cameras(width=1280, height=720, fps=60)
        print()
        
        # Create test output name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"frame_drop_test_{timestamp}"
        
        print(f"Starting recording: {output_name}")
        print(f"Recording for {test_duration} seconds...")
        print()
        
        # Start recording
        recorder.start_recording(output_name)
        
        # Wait for recording to start
        time.sleep(0.5)
        
        # Monitor recording
        start_time = time.time()
        last_stats_time = start_time
        stats_interval = 1.0  # Print stats every second
        
        while time.time() - start_time < test_duration:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Print stats every second
            if current_time - last_stats_time >= stats_interval:
                # Access stats directly from recorder
                stats = {
                    'camera1_frames': recorder.camera1.frame_count,
                    'camera2_frames': recorder.camera2.frame_count,
                    'frames_written': recorder.frames_written,
                    'frames_dropped': recorder.frames_dropped
                }
                print(f"[{elapsed:.1f}s] Frames: Cam1={stats['camera1_frames']}, "
                      f"Cam2={stats['camera2_frames']}, "
                      f"Written={stats['frames_written']}, "
                      f"Dropped={stats['frames_dropped']}")
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
        
        if final_stats:
            print(f"Camera 1 frames captured: {final_stats['camera1_frames']}")
            print(f"Camera 2 frames captured: {final_stats['camera2_frames']}")
            print(f"Frames written (synchronized): {final_stats['frames_written']}")
            print(f"Frames dropped: {final_stats['frames_dropped']}")
            print()
            
            # Calculate frame drop rate
            total_captured = min(final_stats['camera1_frames'], final_stats['camera2_frames'])
            if total_captured > 0:
                drop_rate = (final_stats['frames_dropped'] / total_captured) * 100
                print(f"Frame drop rate: {drop_rate:.2f}%")
            
            # Check against expected
            print()
            print(f"Expected frames (for {test_duration}s @ {target_fps}fps): {expected_frames}")
            print(f"Actual frames written: {final_stats['frames_written']}")
            
            if final_stats['frames_written'] >= expected_frames * 0.95:  # Within 5%
                print("[OK] Frame count is within acceptable range!")
            else:
                diff = expected_frames - final_stats['frames_written']
                print(f"[WARNING] Missing {diff} frames ({diff/expected_frames*100:.1f}%)")
        
        # Verify video files
        print()
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
            
            if abs(info1['counted'] - expected_frames) <= expected_frames * 0.05:
                print(f"  [OK] Frame count matches expected!")
            else:
                diff = expected_frames - info1['counted']
                print(f"  [WARNING] Difference: {diff} frames")
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
            
            if abs(info2['counted'] - expected_frames) <= expected_frames * 0.05:
                print(f"  [OK] Frame count matches expected!")
            else:
                diff = expected_frames - info2['counted']
                print(f"  [WARNING] Difference: {diff} frames")
        else:
            print("  [ERROR] Could not read video file")
        
        # Final summary
        print()
        print("=" * 70)
        print("Summary")
        print("=" * 70)
        
        if final_stats and info1 and info2:
            all_good = (
                final_stats['frames_dropped'] == 0 and
                abs(info1['counted'] - expected_frames) <= expected_frames * 0.05 and
                abs(info2['counted'] - expected_frames) <= expected_frames * 0.05
            )
            
            if all_good:
                print("[OK] NO FRAME DROPS DETECTED!")
                print(f"  - {final_stats['frames_written']} frames written")
                print(f"  - {final_stats['frames_dropped']} frames dropped")
                print(f"  - Video files contain expected frame counts")
            else:
                print("[WARNING] Some frame drops or discrepancies detected")
                print("  Check the details above")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        recorder.stop_cameras()
        print("\nCameras stopped.")

if __name__ == "__main__":
    main()

