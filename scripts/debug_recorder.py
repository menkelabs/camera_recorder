"""
Debug version of the dual camera recorder with verbose logging
Run this to see detailed information about what's happening
"""

import cv2
import threading
import time
import queue
import os
import sys
import argparse
from datetime import datetime
from typing import Optional, Tuple
import numpy as np
import traceback

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class DebugCameraCapture:
    """Debug version with verbose logging"""
    
    def __init__(self, camera_id, name: str = "", buffer_size: int = 2):
        # Support both int (index) and str (device path)
        self.camera_id = camera_id
        self.name = name or f"Camera{camera_id}"
        self.cap = None
        self.frame_queue = queue.Queue(maxsize=buffer_size)
        self.running = False
        self.thread = None
        self.last_frame_time = None
        self.frame_count = 0
        self.error_count = 0
        
    def start(self, width: int = 1280, height: int = 720, fps: int = 30):
        """Start camera capture thread"""
        print(f"[{self.name}] Attempting to open camera {self.camera_id}...")
        
        # Try different methods to open camera
        if isinstance(self.camera_id, str):
            # Try as DirectShow device path first
            print(f"[{self.name}] Trying DirectShow backend with path...")
            self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                # Try as regular string
                print(f"[{self.name}] Trying default backend with path...")
                self.cap = cv2.VideoCapture(self.camera_id)
        else:
            # Integer index - try DirectShow first on Windows
            if sys.platform == 'win32':
                self.cap = cv2.VideoCapture(self.camera_id, cv2.CAP_DSHOW)
                if not self.cap.isOpened():
                    # Fallback to default backend
                    self.cap = cv2.VideoCapture(self.camera_id)
            else:
                self.cap = cv2.VideoCapture(self.camera_id)
        
        if not self.cap.isOpened():
            error_msg = f"[{self.name}] [X] FAILED to open camera {self.camera_id}"
            print(error_msg)
            raise ValueError(error_msg)
        
        print(f"[{self.name}] [OK] Camera opened successfully")
        
        # Set camera properties
        print(f"[{self.name}] Setting properties: {width}x{height} @ {fps} FPS")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Get actual properties
        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        backend = self.cap.getBackendName()
        
        print(f"[{self.name}] Actual properties:")
        print(f"  Resolution: {actual_width}x{actual_height}")
        print(f"  FPS: {actual_fps}")
        print(f"  Backend: {backend}")
        
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True, name=f"{self.name}_thread")
        self.thread.start()
        print(f"[{self.name}] [OK] Capture thread started")
        
        return (actual_width, actual_height, actual_fps)
    
    def _capture_loop(self):
        """Internal capture loop running in separate thread"""
        consecutive_failures = 0
        print(f"[{self.name}] Capture loop started")
        
        while self.running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    consecutive_failures = 0
                    timestamp = time.time()
                    
                    # Drop old frames if queue is full
                    if self.frame_queue.full():
                        try:
                            self.frame_queue.get_nowait()
                        except queue.Empty:
                            pass
                    
                    try:
                        self.frame_queue.put((frame.copy(), timestamp), block=False)
                        self.last_frame_time = timestamp
                        self.frame_count += 1
                        
                        if self.frame_count % 30 == 0:  # Log every 30 frames
                            print(f"[{self.name}] Captured {self.frame_count} frames")
                    except queue.Full:
                        pass
                else:
                    consecutive_failures += 1
                    if consecutive_failures == 1:
                        print(f"[{self.name}] [WARNING] Failed to read frame")
                    elif consecutive_failures > 100:
                        print(f"[{self.name}] [ERROR] {consecutive_failures} consecutive read failures")
                        self.error_count += 1
                        consecutive_failures = 0
                    time.sleep(0.01)
            except Exception as e:
                print(f"[{self.name}] [ERROR] Exception in capture loop: {e}")
                traceback.print_exc()
                self.error_count += 1
                time.sleep(0.1)
        
        print(f"[{self.name}] Capture loop stopped (total frames: {self.frame_count}, errors: {self.error_count})")
    
    def get_frame(self, timeout: float = 0.1) -> Optional[Tuple[np.ndarray, float]]:
        """Get latest frame with timestamp"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
        except Exception as e:
            print(f"[{self.name}] Error getting frame: {e}")
            return None
    
    def stop(self):
        """Stop camera capture"""
        print(f"[{self.name}] Stopping...")
        self.running = False
        if self.thread:
            self.thread.join(timeout=3.0)
            if self.thread.is_alive():
                print(f"[{self.name}] [WARNING] Thread did not stop cleanly")
        if self.cap:
            self.cap.release()
        print(f"[{self.name}] [OK] Stopped (total frames captured: {self.frame_count})")


def test_basic_capture(camera1_id = 0, camera2_id = 1):
    """Test basic camera capture"""
    print("\n" + "="*60)
    print("TEST 1: Basic Camera Capture")
    print("="*60)
    
    # Try to get input if in interactive mode, otherwise use defaults
    try:
        if sys.stdin.isatty():  # Check if running interactively
            cam1_input = input("Enter Camera 1 ID (default 0): ").strip()
            camera1_id = int(cam1_input) if cam1_input else 0
            cam2_input = input("Enter Camera 2 ID (default 1): ").strip()
            camera2_id = int(cam2_input) if cam2_input else 1
    except (EOFError, ValueError):
        # Use provided defaults
        pass
    
    cam1 = DebugCameraCapture(camera1_id, "Camera1")
    cam2 = DebugCameraCapture(camera2_id, "Camera2")
    
    try:
        print("\nStarting cameras...")
        cam1.start(1280, 720, 30)
        time.sleep(0.5)
        cam2.start(1280, 720, 30)
        
        print("\nWaiting for frames...")
        time.sleep(2.0)
        
        # Try to get frames
        print("\nAttempting to get frames...")
        for i in range(5):
            frame1 = cam1.get_frame(timeout=1.0)
            frame2 = cam2.get_frame(timeout=1.0)
            
            if frame1:
                f1, ts1 = frame1
                print(f"  Camera1: Got frame {i+1} - Shape: {f1.shape}, Timestamp: {ts1:.3f}")
            else:
                print(f"  Camera1: No frame available")
            
            if frame2:
                f2, ts2 = frame2
                print(f"  Camera2: Got frame {i+1} - Shape: {f2.shape}, Timestamp: {ts2:.3f}")
            else:
                print(f"  Camera2: No frame available")
            
            time.sleep(0.5)
        
        print(f"\nCamera1 stats: {cam1.frame_count} frames, {cam1.error_count} errors")
        print(f"Camera2 stats: {cam2.frame_count} frames, {cam2.error_count} errors")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        traceback.print_exc()
    finally:
        cam1.stop()
        cam2.stop()


def test_recording(camera1_id = 0, camera2_id = 1):
    """Test recording functionality"""
    print("\n" + "="*60)
    print("TEST 2: Recording Test")
    print("="*60)
    
    # Try to get input if in interactive mode, otherwise use defaults
    try:
        if sys.stdin.isatty():  # Check if running interactively
            cam1_input = input("Enter Camera 1 ID (default 0): ").strip()
            camera1_id = int(cam1_input) if cam1_input else 0
            cam2_input = input("Enter Camera 2 ID (default 1): ").strip()
            camera2_id = int(cam2_input) if cam2_input else 1
    except (EOFError, ValueError):
        # Use provided defaults
        pass
    
    cam1 = DebugCameraCapture(camera1_id, "Camera1")
    cam2 = DebugCameraCapture(camera2_id, "Camera2")
    
    try:
        print("\nStarting cameras...")
        cam1.start(1280, 720, 60)
        time.sleep(0.5)
        cam2.start(1280, 720, 60)
        time.sleep(2.0)
        
        # Get frames to determine dimensions
        print("\nGetting initial frames...")
        frame1_data = cam1.get_frame(timeout=2.0)
        frame2_data = cam2.get_frame(timeout=2.0)
        
        if not frame1_data or not frame2_data:
            print("[ERROR] Could not get initial frames")
            return
        
        frame1, _ = frame1_data
        frame2, _ = frame2_data
        h, w = frame1.shape[:2]
        print(f"Frame dimensions: {w}x{h}")
        
        # Test codec
        print("\nTesting codecs...")
        codec_options = ['H264', 'XVID', 'mp4v', 'MJPG']
        fourcc = None
        
        os.makedirs("recordings", exist_ok=True)
        
        for codec in codec_options:
            try:
                test_fourcc = cv2.VideoWriter_fourcc(*codec)
                test_path = os.path.join("recordings", "test_temp.mp4")
                test_writer = cv2.VideoWriter(test_path, test_fourcc, 60.0, (w, h))
                if test_writer.isOpened():
                    test_writer.release()
                    try:
                        if os.path.exists(test_path):
                            os.remove(test_path)
                    except:
                        pass
                    fourcc = test_fourcc
                    print(f"  [OK] Codec '{codec}' works")
                    break
                else:
                    print(f"  ✗ Codec '{codec}' failed to open")
            except Exception as e:
                print(f"  ✗ Codec '{codec}' error: {e}")
        
        if fourcc is None:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            print("  Using fallback codec: mp4v")
        
        # Create video writers
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path1 = os.path.join("recordings", f"debug_test_camera1_{timestamp}.mp4")
        path2 = os.path.join("recordings", f"debug_test_camera2_{timestamp}.mp4")
        
        print(f"\nCreating video writers...")
        print(f"  Output 1: {path1}")
        print(f"  Output 2: {path2}")
        
        writer1 = cv2.VideoWriter(path1, fourcc, 30.0, (w, h))
        writer2 = cv2.VideoWriter(path2, fourcc, 30.0, (w, h))
        
        if not writer1.isOpened():
            print("[ERROR] Video writer 1 failed to open")
            return
        if not writer2.isOpened():
            print("[ERROR] Video writer 2 failed to open")
            return
        
        print("[OK] Video writers opened successfully")
        
        # Get actual FPS from cameras
        fps = 60.0
        if cam1.cap:
            cam_fps = cam1.cap.get(cv2.CAP_PROP_FPS)
            if cam_fps > 0:
                fps = cam_fps
        
        # Record for 5 seconds
        print(f"\nRecording for 5 seconds at {fps} FPS...")
        start_time = time.time()
        frames_written = 0
        
        while time.time() - start_time < 5.0:
            frame1_data = cam1.get_frame(timeout=0.1)
            frame2_data = cam2.get_frame(timeout=0.1)
            
            if frame1_data and frame2_data:
                f1, ts1 = frame1_data
                f2, ts2 = frame2_data
                
                time_diff = abs(ts1 - ts2)
                if time_diff < 0.017:  # 17ms threshold (1 frame at 60fps)
                    writer1.write(f1)
                    writer2.write(f2)
                    frames_written += 1
                    
                    if frames_written % 30 == 0:
                        print(f"  Written {frames_written} frames (sync diff: {time_diff*1000:.1f}ms)")
            
            time.sleep(0.001)
        
        writer1.release()
        writer2.release()
        
        print(f"\n[OK] Recording complete: {frames_written} frames written")
        print(f"  Files saved to recordings/ directory")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        traceback.print_exc()
    finally:
        cam1.stop()
        cam2.stop()


def main():
    parser = argparse.ArgumentParser(description='Dual Camera Recorder - Debug Mode')
    parser.add_argument('--test', type=int, choices=[1, 2, 3], 
                       help='Test to run: 1=Basic capture, 2=Recording, 3=Both')
    parser.add_argument('--interactive', action='store_true',
                       help='Run in interactive mode (prompt for input)')
    parser.add_argument('--camera1', type=str, default='0',
                       help='Camera 1 ID or path (default: 0)')
    parser.add_argument('--camera2', type=str, default='1',
                       help='Camera 2 ID or path (default: 1)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("Dual Camera Recorder - Debug Mode")
    print("="*60)
    
    if args.interactive or args.test is None:
        print("\nSelect test:")
        print("  1. Basic capture test (check if cameras work)")
        print("  2. Recording test (test full recording pipeline)")
        print("  3. Run both tests")
        
        try:
            choice = input("\nEnter choice (1/2/3): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nNo input available. Use --test argument or --interactive mode.")
            print("Example: python debug_recorder.py --test 1")
            return
    else:
        choice = str(args.test)
    
    # Convert camera IDs - try int first, otherwise keep as string
    def parse_camera_id(cam_id_str):
        try:
            return int(cam_id_str)
        except ValueError:
            return cam_id_str
    
    cam1_id = parse_camera_id(args.camera1)
    cam2_id = parse_camera_id(args.camera2)
    
    if choice == "1":
        test_basic_capture(cam1_id, cam2_id)
    elif choice == "2":
        test_recording(cam1_id, cam2_id)
    elif choice == "3":
        test_basic_capture(cam1_id, cam2_id)
        if args.interactive:
            input("\nPress Enter to continue to recording test...")
        else:
            print("\nContinuing to recording test...")
            time.sleep(2)
        test_recording(cam1_id, cam2_id)
    else:
        print("Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        traceback.print_exc()

