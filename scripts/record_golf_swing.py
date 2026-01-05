"""
Golf Swing Recording Script
Optimized for capturing fast golf swings at 240fps
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
    print("Golf Swing Recorder - Ultra High Speed Capture")
    print("=" * 70)
    print()
    print("Recommended: 1280x720 @ 120 FPS")
    print("  - Zero frame drops at 120 FPS (tested)")
    print("  - Both cameras exceed 120 FPS (232-217 FPS measured)")
    print("  - VideoWriter supports 120 FPS")
    print("  - High frame rate for fast golf swings")
    print("  - Captures impact moment in detail")
    print("  - Perfect for clubhead speed analysis")
    print("  - Optimal balance of speed and detail")
    print()
    print("Alternative options:")
    print("  - 640p @ 120fps: Maximum speed, lower detail")
    print("  - 1080p @ 60fps: Maximum detail, slower motion")
    print()
    print("Using cameras:")
    print("  Camera 1: Index 0 (HD USB Camera)")
    print("  Camera 2: Index 2 (HD USB Camera)")
    print()
    
    # Ask for settings
    print("Select recording mode:")
    print("  1. 720p @ 120fps (RECOMMENDED - Best for golf swings)")
    print("  2. 640p @ 120fps (Maximum speed, lower detail)")
    print("  3. 1080p @ 60fps (High detail, slower motion)")
    print()
    print("Note: VideoWriter limited to 120fps max")
    print("      Option 1 captures at 120fps and writes at 120fps (optimal)")
    print()
    
    choice = input("Enter choice (1/2/3, default=1): ").strip() or "1"
    
    if choice == "1":
        width, height, fps = 1280, 720, 120
        desc = "720p @ 120fps - RECOMMENDED for golf swings"
    elif choice == "2":
        width, height, fps = 640, 480, 120
        desc = "640p @ 120fps - Maximum speed"
    elif choice == "3":
        width, height, fps = 1920, 1080, 60
        desc = "1080p @ 60fps - High detail"
    else:
        width, height, fps = 1280, 720, 120
        desc = "720p @ 120fps - RECOMMENDED for golf swings"
    
    recorder = DualCameraRecorder(camera1_id=0, camera2_id=2)
    
    try:
        # Start cameras
        print(f"\nStarting cameras at {desc}...")
        recorder.start_cameras(width=width, height=height, fps=fps)
        print()
        
        # Get output name
        output_name = input("Enter output name (or press Enter for timestamp): ").strip()
        if not output_name:
            output_name = f"golf_swing_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start recording
        print(f"\nStarting recording: {output_name}")
        print("Recording... Press Ctrl+C to stop")
        print()
        
        if fps >= 120:
            print("⚠️  HIGH SPEED RECORDING:")
            print(f"   - {fps}fps creates large files (~100-200 MB/min per camera)")
            print("   - Record in short clips (10-30 seconds per swing)")
            print("   - Ensure fast storage (SSD recommended)")
            print()
        
        recorder.start_recording(output_name)
        
        # Monitor recording
        start_time = time.time()
        last_stats_time = start_time
        
        try:
            while True:
                current_time = time.time()
                elapsed = current_time - start_time
                
                # Print stats every 2 seconds for high-speed recording
                if current_time - last_stats_time >= 2.0:
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
        print(f"Settings: {width}x{height} @ {fps}fps")
        print(f"Frames written: {final_stats['frames_written']}")
        print(f"Frames dropped: {final_stats['frames_dropped']}")
        print(f"Duration: {elapsed:.1f} seconds")
        print()
        print("Files saved to recordings/ directory:")
        print(f"  {output_name}_camera1.mp4")
        print(f"  {output_name}_camera2.mp4")
        print()
        
        if fps >= 120:
            print("💡 Tip: Use video player to slow down playback for analysis")
            print("   Most players can slow 240fps to 0.1x speed (24fps playback)")
            print("   This gives you 10x slow motion!")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        recorder.stop_cameras()
        print("\nCameras stopped.")

if __name__ == "__main__":
    main()

