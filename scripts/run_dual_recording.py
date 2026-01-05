"""
Simple script to run dual camera recording with the 2 HD USB cameras
"""

import sys
import os

# Add src directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from dual_camera_recorder import DualCameraRecorder
import time

def main():
    print("=" * 60)
    print("Dual HD USB Camera Recorder")
    print("=" * 60)
    print()
    print("Using cameras:")
    print("  Camera 1: Index 0 (HD USB Camera)")
    print("  Camera 2: Index 2 (HD USB Camera)")
    print("  (Note: Index 1 is the built-in system camera)")
    print()
    
    # Create recorder with the 2 HD USB cameras (0 and 2, not 1 which is built-in)
    recorder = DualCameraRecorder(camera1_id=0, camera2_id=2)
    
    try:
        # Start cameras at optimal settings for accurate recording - 720p @ 60fps
        # Based on test results: Both cameras exceed 60 FPS (103-104 FPS measured)
        # VideoWriter supports 60 FPS, zero frame drops in tests
        # Note: 1080p cannot maintain 60 FPS (only 44-53 FPS measured)
        print("Starting cameras at 1280x720 @ 60fps (optimal for accurate recording)...")
        print("(Both cameras exceed 60 FPS, VideoWriter supports it, zero frame drops)")
        recorder.start_cameras(width=1280, height=720, fps=60)
        
        # Get output name
        output_name = input("\nEnter output name (or press Enter for timestamp): ").strip()
        if not output_name:
            from datetime import datetime
            output_name = f"dual_recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start recording
        print(f"\nStarting recording: {output_name}")
        recorder.start_recording(output_name)
        
        print("\nRecording... Press Ctrl+C to stop")
        
        # Record until interrupted
        try:
            while True:
                time.sleep(1)
                stats = recorder.get_stats()
                if stats:
                    print(f"\rFrames: Camera1={stats['camera1_frames']}, Camera2={stats['camera2_frames']}, "
                          f"Written={stats['frames_written']}, Dropped={stats['frames_dropped']}", end="")
        except KeyboardInterrupt:
            print("\n\nStopping recording...")
        
        # Stop recording
        recorder.stop_recording()
        print("Recording saved!")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        recorder.stop_cameras()
        print("\nCameras stopped.")

if __name__ == "__main__":
    main()

