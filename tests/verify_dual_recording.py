"""
Verify that both USB cameras are recording simultaneously
"""

import cv2
import sys
import time
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

def main():
    print("=" * 70)
    print("Dual USB Camera Simultaneous Recording Verification")
    print("=" * 70)
    print()
    
    print("Configuration:")
    print("  Camera 1: Index 0 (HD USB Camera)")
    print("  Camera 2: Index 2 (HD USB Camera)")
    print("  Resolution: 1280x720 @ 120fps")
    print()
    
    recorder = DualCameraRecorder(camera1_id=0, camera2_id=2)
    
    try:
        print("Step 1: Starting both cameras simultaneously...")
        recorder.start_cameras(width=1280, height=720, fps=120)
        print("  ✓ Both cameras started")
        print()
        
        # Wait a moment for stabilization
        time.sleep(1.0)
        
        print("Step 2: Verifying both cameras are capturing frames...")
        frame1_data = recorder.camera1.get_frame(timeout=1.0)
        frame2_data = recorder.camera2.get_frame(timeout=1.0)
        
        if frame1_data and frame2_data:
            f1, ts1 = frame1_data
            f2, ts2 = frame2_data
            print(f"  ✓ Camera 1: Frame captured - Shape: {f1.shape}, Timestamp: {ts1:.3f}")
            print(f"  ✓ Camera 2: Frame captured - Shape: {f2.shape}, Timestamp: {ts2:.3f}")
            print(f"  ✓ Time difference: {abs(ts1 - ts2)*1000:.2f}ms")
            print()
        else:
            print("  ✗ Failed to get frames from one or both cameras")
            return
        
        print("Step 3: Starting simultaneous recording...")
        from datetime import datetime
        output_name = f"dual_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        recorder.start_recording(output_name)
        print("  ✓ Recording started")
        print()
        
        print("Step 4: Recording for 3 seconds...")
        print("  Monitoring frame counts from both cameras...")
        print()
        
        start_time = time.time()
        last_print = start_time
        
        while time.time() - start_time < 3.0:
            elapsed = time.time() - start_time
            
            if time.time() - last_print >= 0.5:  # Print every 0.5 seconds
                cam1_frames = recorder.camera1.frame_count
                cam2_frames = recorder.camera2.frame_count
                written = recorder.frames_written
                dropped = recorder.frames_dropped
                
                print(f"  [{elapsed:.1f}s] Cam1: {cam1_frames}, Cam2: {cam2_frames}, "
                      f"Written: {written}, Dropped: {dropped}")
                last_print = time.time()
            
            time.sleep(0.1)
        
        recorder.stop_recording()
        print()
        
        # Final verification
        print("Step 5: Final verification...")
        print("=" * 70)
        print()
        
        final_stats = {
            'camera1_frames': recorder.camera1.frame_count,
            'camera2_frames': recorder.camera2.frame_count,
            'frames_written': recorder.frames_written,
            'frames_dropped': recorder.frames_dropped
        }
        
        print("Results:")
        print(f"  Camera 1 (USB) frames captured: {final_stats['camera1_frames']}")
        print(f"  Camera 2 (USB) frames captured: {final_stats['camera2_frames']}")
        print(f"  Synchronized frames written: {final_stats['frames_written']}")
        print(f"  Frames dropped: {final_stats['frames_dropped']}")
        print()
        
        # Calculate frame rates
        duration = 3.0
        cam1_fps = final_stats['camera1_frames'] / duration
        cam2_fps = final_stats['camera2_frames'] / duration
        written_fps = final_stats['frames_written'] / duration
        
        print("Frame rates:")
        print(f"  Camera 1: {cam1_fps:.1f} FPS")
        print(f"  Camera 2: {cam2_fps:.1f} FPS")
        print(f"  Written (synchronized): {written_fps:.1f} FPS")
        print()
        
        # Verification
        both_working = (
            final_stats['camera1_frames'] > 0 and
            final_stats['camera2_frames'] > 0 and
            final_stats['frames_written'] > 0 and
            final_stats['frames_dropped'] == 0
        )
        
        if both_working:
            print("✅ CONFIRMED: Both USB cameras recording simultaneously!")
            print()
            print("  ✓ Camera 1 (Index 0) is capturing")
            print("  ✓ Camera 2 (Index 2) is capturing")
            print("  ✓ Both cameras are synchronized")
            print("  ✓ Frames are being written to video files")
            print("  ✓ Zero frame drops")
        else:
            print("⚠️  Some issues detected - check results above")
        
        print()
        print("Video files created:")
        import os
        video1 = os.path.join("recordings", f"{output_name}_camera1.mp4")
        video2 = os.path.join("recordings", f"{output_name}_camera2.mp4")
        print(f"  {video1}")
        print(f"  {video2}")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        recorder.stop_cameras()
        print("\nCameras stopped.")

if __name__ == "__main__":
    main()

