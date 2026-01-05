"""
Recording script optimized for MediaPipe analysis
Uses 1080p @ 60fps for maximum fidelity
"""

import sys
import os
import time

# Add src directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from dual_camera_recorder import DualCameraRecorder
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def main():
    print("=" * 70)
    print("MediaPipe-Optimized Dual Camera Recorder")
    print("=" * 70)
    print()
    print("Settings: 1280x720 @ 60 FPS (optimal for accurate recording)")
    print("  - Both cameras exceed 60 FPS (103-104 FPS measured)")
    print("  - VideoWriter supports 60 FPS, zero frame drops")
    print("  - Good detail for landmark detection")
    print("  - Smooth motion capture")
    print("  - Note: 1080p cannot maintain 60 FPS (only 44-53 FPS measured)")
    print()
    print("Using cameras:")
    print("  Camera 1: Index 0 (HD USB Camera)")
    print("  Camera 2: Index 2 (HD USB Camera)")
    print()
    
    recorder = DualCameraRecorder(camera1_id=0, camera2_id=2)
    
    try:
        # Start cameras at optimal settings for accurate recording
        # 720p @ 60fps: Both cameras exceed 60 FPS, VideoWriter supports it, zero frame drops
        print("Starting cameras at 720p @ 60fps...")
        recorder.start_cameras(width=1280, height=720, fps=60)
        print()
        
        # Get output name
        output_name = input("Enter output name (or press Enter for timestamp): ").strip()
        if not output_name:
            output_name = f"mediapipe_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start recording
        print(f"\nStarting recording: {output_name}")
        recorder.start_recording(output_name)
        
        print("\nRecording... Press Ctrl+C to stop")
        print("Note: 1080p @ 60fps creates large files (~50-100 MB/min per camera)")
        print()
        
        # Monitor recording
        start_time = time.time()
        last_stats_time = start_time
        
        try:
            while True:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Print stats every 5 seconds
                if current_time - last_stats_time >= 5.0:
                    stats = {
                        'camera1_frames': recorder.camera1.frame_count,
                        'camera2_frames': recorder.camera2.frame_count,
                        'frames_written': recorder.frames_written,
                        'frames_dropped': recorder.frames_dropped
                    }
                    print(f"[{elapsed:.1f}s] Written: {stats['frames_written']}, "
                          f"Dropped: {stats['frames_dropped']}, "
                          f"Cam1: {stats['camera1_frames']}, "
                          f"Cam2: {stats['camera2_frames']}")
                    last_stats_time = current_time
                
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\nStopping recording...")
        
        # Stop recording
        recorder.stop_recording()
        
        # Final stats
        final_stats = {
            'camera1_frames': recorder.camera1.frame_count,
            'camera2_frames': recorder.camera2.frame_count,
            'frames_written': recorder.frames_written,
            'frames_dropped': recorder.frames_dropped
        }
        
        print()
        print("=" * 70)
        print("Recording Complete!")
        print("=" * 70)
        print(f"Frames written: {final_stats['frames_written']}")
        print(f"Frames dropped: {final_stats['frames_dropped']}")
        print(f"Duration: {elapsed:.1f} seconds")
        print()
        print("Files saved to recordings/ directory:")
        print(f"  {output_name}_camera1.mp4")
        print(f"  {output_name}_camera2.mp4")
        print()
        print("Ready for MediaPipe analysis!")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        recorder.stop_cameras()
        print("\nCameras stopped.")

if __name__ == "__main__":
    main()

