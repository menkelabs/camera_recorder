"""
Dual USB Camera Recorder
Captures and records synchronized video from 2 USB cameras with low CPU usage.
Optimized for MediaPipe analysis pipeline.
"""

import cv2
import threading
import time
import queue
import os
from datetime import datetime
from typing import Optional, Tuple
import numpy as np


class CameraCapture:
    """Handles individual camera capture with buffering"""
    
    def __init__(self, camera_id, buffer_size: int = 2):
        # Support both int (index) and str (device path)
        self.camera_id = camera_id
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.running = False
        self.thread = None
        self.last_frame_time = None
        self.frame_count = 0
        
    def start(self, width: int = 1280, height: int = 720, fps: int = 30):
        """Start camera capture thread"""
        # Use platform-appropriate backend
        import sys
        if sys.platform == 'win32' and isinstance(self.camera_id, int):
            # Windows: Use DirectShow backend for better compatibility
            self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
        else:
            # Linux/Other: Use default backend (V4L2 on Linux)
            self.cap = cv2.VideoCapture(self.camera_id)
        if not self.cap.isOpened():
            raise ValueError(f"Failed to open camera {self.camera_id}")
        
        # Set camera properties for better performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer to minimize latency
        
        # Get actual properties
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        
        print(f"Camera {self.camera_id}: {actual_width}x{actual_height} @ {actual_fps} FPS")
        
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        
        return (actual_width, actual_height, actual_fps)
    
    def _capture_loop(self):
        """Internal capture loop running in separate thread"""
        consecutive_failures = 0
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                consecutive_failures = 0
                timestamp = time.time()
                # Drop old frames if queue is full (keep latest)
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                
                try:
                    self.frame_queue.put((frame.copy(), timestamp), block=False)
                    self.last_frame_time = timestamp
                    self.frame_count += 1
                except queue.Full:
                    # Queue is full, skip this frame
                    pass
            else:
                consecutive_failures += 1
                if consecutive_failures > 100:
                    print(f"Warning: Camera {self.camera_id} failed to read {consecutive_failures} consecutive frames")
                    consecutive_failures = 0
                time.sleep(0.01)  # Small delay if read fails
    
    def get_frame(self, timeout: float = 0.1) -> Optional[Tuple[np.ndarray, float]]:
        """Get latest frame with timestamp"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
        except Exception as e:
            print(f"Error getting frame from camera {self.camera_id}: {e}")
            return None
    
    def stop(self):
        """Stop camera capture"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()


class DualCameraRecorder:
    """Main recorder class for dual camera synchronized recording"""
    
    def __init__(self, camera1_id = None, camera2_id = None):
        # Use platform-appropriate defaults if not specified
        import sys
        if sys.platform == 'win32':
            # Windows: Use cameras 0 and 2 (skip built-in at 1)
            camera1_id = camera1_id if camera1_id is not None else 0
            camera2_id = camera2_id if camera2_id is not None else 2
        else:
            # Linux/Other: Use cameras 0 and 1
            camera1_id = camera1_id if camera1_id is not None else 0
            camera2_id = camera2_id if camera2_id is not None else 1
        
        self.camera1 = CameraCapture(camera1_id)
        self.camera2 = CameraCapture(camera2_id)
        self.recording = False
        self.video_writer1 = None
        self.video_writer2 = None
        self.output_dir = "recordings"
        self.sync_threshold = 0.017  # ~17ms tolerance for sync (1 frame at 60fps)
        self.frames_written = 0
        self.frames_dropped = 0
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
    
    def start_cameras(self, width: int = 1280, height: int = 720, fps: int = 60):
        """Initialize and start both cameras"""
        self.requested_fps = fps  # Store requested FPS for video writer
        # Adjust sync threshold based on FPS (1 frame time)
        self.sync_threshold = 1.0 / fps  # e.g., 240fps = 4.17ms, 60fps = 16.67ms
        print("Starting cameras...")
        try:
            dims1 = self.camera1.start(width, height, fps)
            dims2 = self.camera2.start(width, height, fps)
            
            # Wait a bit for cameras to stabilize
            time.sleep(1.0)
            
            print("Cameras started successfully!")
            return dims1, dims2
        except Exception as e:
            print(f"Error starting cameras: {e}")
            self.stop_cameras()
            raise
    
    def stop_cameras(self):
        """Stop both cameras"""
        print("Stopping cameras...")
        self.camera1.stop()
        self.camera2.stop()
    
    def start_recording(self, output_name: Optional[str] = None):
        """Start synchronized recording"""
        if self.recording:
            print("Already recording!")
            return
        
        if output_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"dual_capture_{timestamp}"
        
        # Setup video writers with efficient codec
        # Try hardware-accelerated codecs first (lower CPU usage)
        fourcc = None
        codec_options = ['H264', 'XVID', 'mp4v', 'MJPG']
        
        for codec in codec_options:
            try:
                test_fourcc = cv2.VideoWriter_fourcc(*codec)
                # Test if codec works by creating a temporary writer
                test_path = os.path.join(self.output_dir, 'test_temp.mp4')
                test_writer = cv2.VideoWriter(test_path, test_fourcc, 60.0, (640, 480))
                if test_writer.isOpened():
                    test_writer.release()
                    # Clean up test file
                    try:
                        if os.path.exists(test_path):
                            os.remove(test_path)
                    except:
                        pass
                    fourcc = test_fourcc
                    print(f"Using codec: {codec}")
                    break
            except Exception as e:
                continue
        
        if fourcc is None:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Fallback
            print("Using fallback codec: mp4v")
        
        path1 = os.path.join(self.output_dir, f"{output_name}_camera1.mp4")
        path2 = os.path.join(self.output_dir, f"{output_name}_camera2.mp4")
        
        # Get frame dimensions from first frames
        frame1, _ = self.camera1.get_frame(timeout=2.0)
        frame2, _ = self.camera2.get_frame(timeout=2.0)
        
        if frame1 is None or frame2 is None:
            print("Error: Could not get initial frames from cameras")
            return
        
        h, w = frame1.shape[:2]
        # Use the requested FPS (stored when cameras were started)
        # However, VideoWriter may have limitations - cap at 120fps for H264
        requested_fps = float(self.requested_fps)
        
        # OpenCV VideoWriter with H264 typically maxes out around 120fps
        # For higher FPS, we'll write at 120fps but cameras still capture at full speed
        # This gives us better frame selection for sync
        if requested_fps > 120:
            print(f"Note: VideoWriter limited to 120fps (cameras capturing at {requested_fps}fps)")
            print(f"      All frames will be written, but video will play at 120fps")
            fps = 120.0  # Cap at 120fps for video file
            self.high_speed_mode = True  # Flag to indicate we're capturing faster than writing
        else:
            fps = requested_fps
            self.high_speed_mode = False
        
        self.video_writer1 = cv2.VideoWriter(path1, fourcc, fps, (w, h))
        self.video_writer2 = cv2.VideoWriter(path2, fourcc, fps, (w, h))
        
        if not self.video_writer1.isOpened() or not self.video_writer2.isOpened():
            print("Error: Could not initialize video writers")
            return
        
        self.recording = True
        self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.recording_thread.start()
        
        print(f"Recording started: {output_name}")
        print(f"  Camera 1: {path1}")
        print(f"  Camera 2: {path2}")
    
    def _recording_loop(self):
        """Recording loop that synchronizes frames from both cameras"""
        last_written_ts1 = None
        last_written_ts2 = None
        self.frames_written = 0
        self.frames_dropped = 0
        
        while self.recording:
            try:
                # Get latest frames from both cameras
                frame1_data = self.camera1.get_frame(timeout=0.05)
                frame2_data = self.camera2.get_frame(timeout=0.05)
                
                # Simple synchronization: write frames if timestamps are close enough
                if frame1_data and frame2_data:
                    frame1, ts1 = frame1_data
                    frame2, ts2 = frame2_data
                    
                    # Check if frames are synchronized (within threshold)
                    time_diff = abs(ts1 - ts2)
                    
                    if time_diff < self.sync_threshold:
                        # Only write if we haven't written these exact frames
                        if (last_written_ts1 != ts1) and (last_written_ts2 != ts2):
                            try:
                                self.video_writer1.write(frame1)
                                self.video_writer2.write(frame2)
                                last_written_ts1 = ts1
                                last_written_ts2 = ts2
                                self.frames_written += 1
                                
                                # In high-speed mode, we might write multiple times per "video frame"
                                # but that's OK - the video will play at the correct speed
                                
                                if self.frames_written % 100 == 0:
                                    print(f"Recorded {self.frames_written} frames (dropped {self.frames_dropped})")
                            except Exception as e:
                                print(f"Error writing frames: {e}")
                                break
                    elif ts1 < ts2:
                        # Camera 1 is behind, try to get a newer frame from camera 1
                        newer_frame1 = self.camera1.get_frame(timeout=0.01)
                        if newer_frame1:
                            frame1, ts1 = newer_frame1
                            time_diff = abs(ts1 - ts2)
                            if time_diff < self.sync_threshold:
                                try:
                                    self.video_writer1.write(frame1)
                                    self.video_writer2.write(frame2)
                                    last_written_ts1 = ts1
                                    last_written_ts2 = ts2
                                    self.frames_written += 1
                                except Exception as e:
                                    print(f"Error writing frames: {e}")
                                    break
                        else:
                            self.frames_dropped += 1
                    else:
                        # Camera 2 is behind, try to get a newer frame from camera 2
                        newer_frame2 = self.camera2.get_frame(timeout=0.01)
                        if newer_frame2:
                            frame2, ts2 = newer_frame2
                            time_diff = abs(ts1 - ts2)
                            if time_diff < self.sync_threshold:
                                try:
                                    self.video_writer1.write(frame1)
                                    self.video_writer2.write(frame2)
                                    last_written_ts1 = ts1
                                    last_written_ts2 = ts2
                                    self.frames_written += 1
                                except Exception as e:
                                    print(f"Error writing frames: {e}")
                                    break
                        else:
                            self.frames_dropped += 1
                elif frame1_data is None:
                    print("Warning: Camera 1 not providing frames")
                elif frame2_data is None:
                    print("Warning: Camera 2 not providing frames")
                
            except Exception as e:
                print(f"Error in recording loop: {e}")
                import traceback
                traceback.print_exc()
                break
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.001)
        
        print(f"\nRecording complete: {self.frames_written} frames written, {self.frames_dropped} frames dropped")
    
    def stop_recording(self):
        """Stop recording and save videos"""
        if not self.recording:
            print("Not recording!")
            return
        
        self.recording = False
        if hasattr(self, 'recording_thread'):
            self.recording_thread.join(timeout=2.0)
        
        if self.video_writer1:
            self.video_writer1.release()
        if self.video_writer2:
            self.video_writer2.release()
        
        print("Recording stopped and saved!")
    
    def preview(self, duration: float = 5.0):
        """Preview both camera feeds for specified duration"""
        print(f"Previewing cameras for {duration} seconds...")
        print("Press 'q' to quit preview early")
        
        start_time = time.time()
        while time.time() - start_time < duration:
            frame1_data = self.camera1.get_frame(timeout=0.1)
            frame2_data = self.camera2.get_frame(timeout=0.1)
            
            if frame1_data and frame2_data:
                frame1, _ = frame1_data
                frame2, _ = frame2_data
                
                # Resize for display if too large
                display1 = cv2.resize(frame1, (640, 360)) if frame1.shape[1] > 640 else frame1
                display2 = cv2.resize(frame2, (640, 360)) if frame2.shape[1] > 640 else frame2
                
                # Combine frames side by side
                combined = np.hstack([display1, display2])
                cv2.putText(combined, "Camera 1", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(combined, "Camera 2", (650, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                cv2.imshow('Dual Camera Preview', combined)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        cv2.destroyAllWindows()


def main():
    """Main application with interactive controls"""
    print("=" * 60)
    print("Dual USB Camera Recorder")
    print("=" * 60)
    
    # Get camera IDs
    print("\nAvailable cameras:")
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"  Camera {i}: Available")
            cap.release()
    
    camera1_id = int(input("\nEnter Camera 1 ID (default 0): ") or "0")
    camera2_id = int(input("Enter Camera 2 ID (default 1): ") or "1")
    
    # Get recording settings
    width = int(input("Enter width (default 1280): ") or "1280")
    height = int(input("Enter height (default 720): ") or "720")
    fps = int(input("Enter FPS (default 30): ") or "30")
    
    recorder = DualCameraRecorder(camera1_id, camera2_id)
    
    try:
        # Start cameras
        recorder.start_cameras(width, height, fps)
        
        # Preview
        preview_choice = input("\nPreview cameras? (y/n, default y): ") or "y"
        if preview_choice.lower() == 'y':
            recorder.preview(duration=5.0)
        
        # Recording loop
        print("\n" + "=" * 60)
        print("Controls:")
        print("  'r' - Start/Stop recording")
        print("  'p' - Preview cameras")
        print("  'q' - Quit")
        print("=" * 60)
        
        while True:
            command = input("\nEnter command (r/p/q): ").lower()
            
            if command == 'r':
                if recorder.recording:
                    recorder.stop_recording()
                else:
                    output_name = input("Enter output name (or press Enter for auto): ") or None
                    recorder.start_recording(output_name)
            
            elif command == 'p':
                duration = float(input("Preview duration in seconds (default 5): ") or "5")
                recorder.preview(duration)
            
            elif command == 'q':
                break
            
            else:
                print("Invalid command!")
        
        # Cleanup
        if recorder.recording:
            recorder.stop_recording()
        recorder.stop_cameras()
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        if recorder.recording:
            recorder.stop_recording()
        recorder.stop_cameras()
    except Exception as e:
        print(f"\nError: {e}")
        if recorder.recording:
            recorder.stop_recording()
        recorder.stop_cameras()
        raise
    
    print("\nExiting...")


if __name__ == "__main__":
    main()

