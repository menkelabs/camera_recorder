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
        # Start cameras at optimal resolution for MediaPipe - 1080p @ 60fps
        # For maximum fidelity, use 1920x1080 @ 60fps
        # Alternative: 1280x720 @ 60fps for smaller files
        print("Starting cameras at 1920x1080 @ 60fps (optimal for MediaPipe)...")
        print("(For smaller files, change to 1280x720 @ 60fps)")
        recorder.start_cameras(width=1920, height=1080, fps=60)
        
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

