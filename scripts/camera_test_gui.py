"""
High-Performance Camera Test GUI
Real-time preview with camera property controls for focus, brightness, saturation, etc.
Optimized for low latency and smooth preview.
"""

import cv2
import sys
import os
import threading
import time
from typing import Optional, Tuple

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from dual_camera_recorder import CameraCapture


class CameraTestGUI:
    """High-performance camera test GUI with property controls"""
    
    # OpenCV camera property constants
    PROP_BRIGHTNESS = cv2.CAP_PROP_BRIGHTNESS
    PROP_CONTRAST = cv2.CAP_PROP_CONTRAST
    PROP_SATURATION = cv2.CAP_PROP_SATURATION
    PROP_EXPOSURE = cv2.CAP_PROP_EXPOSURE
    PROP_GAIN = cv2.CAP_PROP_GAIN
    PROP_FOCUS = cv2.CAP_PROP_FOCUS
    PROP_WHITE_BALANCE = cv2.CAP_PROP_WHITE_BALANCE_BLUE_U
    PROP_SHARPNESS = cv2.CAP_PROP_SHARPNESS
    PROP_BACKLIGHT = cv2.CAP_PROP_BACKLIGHT
    PROP_GAMMA = cv2.CAP_PROP_GAMMA
    
    def __init__(self, camera1_id: int = 0, camera2_id: int = 2, 
                 width: int = 1280, height: int = 720, fps: int = 60):
        self.camera1_id = camera1_id
        self.camera2_id = camera2_id
        self.width = width
        self.height = height
        self.fps = fps
        
        self.cap1 = None
        self.cap2 = None
        self.running = False
        
        # Property ranges (typical values, may vary by camera)
        self.prop_ranges = {
            'brightness': (0, 255, 128),
            'contrast': (0, 255, 32),
            'saturation': (0, 255, 64),
            'exposure': (-13, 1, -6),  # Log scale, typically -13 to 1
            'gain': (0, 100, 0),
            'focus': (0, 255, 0),
            'white_balance': (2000, 6500, 4000),  # Temperature in Kelvin
            'sharpness': (0, 255, 0),
            'backlight': (0, 1, 0),
            'gamma': (0, 200, 100),
        }
        
        # Current property values
        self.prop_values = {}
        
        # Window names
        self.window1 = "Camera 1 - Test & Adjust"
        self.window2 = "Camera 2 - Test & Adjust"
        
    def create_trackbars(self, window_name: str, camera_num: int):
        """Create trackbars for camera properties"""
        # Brightness
        cv2.createTrackbar('Brightness', window_name, 
                          self.prop_ranges['brightness'][2], 
                          self.prop_ranges['brightness'][1],
                          lambda x: self.on_trackbar_change('brightness', camera_num, x))
        
        # Contrast
        cv2.createTrackbar('Contrast', window_name,
                          self.prop_ranges['contrast'][2],
                          self.prop_ranges['contrast'][1],
                          lambda x: self.on_trackbar_change('contrast', camera_num, x))
        
        # Saturation
        cv2.createTrackbar('Saturation', window_name,
                          self.prop_ranges['saturation'][2],
                          self.prop_ranges['saturation'][1],
                          lambda x: self.on_trackbar_change('saturation', camera_num, x))
        
        # Exposure (mapped from 0-100 to actual exposure range)
        cv2.createTrackbar('Exposure', window_name,
                          50, 100,  # 0-100 scale
                          lambda x: self.on_trackbar_change('exposure', camera_num, x))
        
        # Gain
        cv2.createTrackbar('Gain', window_name,
                          self.prop_ranges['gain'][2],
                          self.prop_ranges['gain'][1],
                          lambda x: self.on_trackbar_change('gain', camera_num, x))
        
        # Focus
        cv2.createTrackbar('Focus', window_name,
                          self.prop_ranges['focus'][2],
                          self.prop_ranges['focus'][1],
                          lambda x: self.on_trackbar_change('focus', camera_num, x))
        
        # White Balance (mapped from 0-100 to temperature range)
        cv2.createTrackbar('White Balance', window_name,
                          50, 100,  # 0-100 scale
                          lambda x: self.on_trackbar_change('white_balance', camera_num, x))
        
        # Sharpness
        cv2.createTrackbar('Sharpness', window_name,
                          self.prop_ranges['sharpness'][2],
                          self.prop_ranges['sharpness'][1],
                          lambda x: self.on_trackbar_change('sharpness', camera_num, x))
        
        # Gamma
        cv2.createTrackbar('Gamma', window_name,
                          self.prop_ranges['gamma'][2],
                          self.prop_ranges['gamma'][1],
                          lambda x: self.on_trackbar_change('gamma', camera_num, x))
    
    def on_trackbar_change(self, prop_name: str, camera_num: int, value: int):
        """Handle trackbar changes"""
        cap = self.cap1 if camera_num == 1 else self.cap2
        if cap is None or not cap.isOpened():
            return
        
        # Map trackbar value to actual property value
        if prop_name == 'exposure':
            # Map 0-100 to exposure range (-13 to 1)
            min_val, max_val, _ = self.prop_ranges['exposure']
            actual_value = min_val + (max_val - min_val) * (value / 100.0)
        elif prop_name == 'white_balance':
            # Map 0-100 to temperature range (2000-6500K)
            min_val, max_val, _ = self.prop_ranges['white_balance']
            actual_value = min_val + (max_val - min_val) * (value / 100.0)
        else:
            actual_value = value
        
        # Set property
        prop_map = {
            'brightness': self.PROP_BRIGHTNESS,
            'contrast': self.PROP_CONTRAST,
            'saturation': self.PROP_SATURATION,
            'exposure': self.PROP_EXPOSURE,
            'gain': self.PROP_GAIN,
            'focus': self.PROP_FOCUS,
            'white_balance': self.PROP_WHITE_BALANCE,
            'sharpness': self.PROP_SHARPNESS,
            'gamma': self.PROP_GAMMA,
        }
        
        if prop_name in prop_map:
            success = cap.set(prop_map[prop_name], actual_value)
            if success:
                self.prop_values[f'camera{camera_num}_{prop_name}'] = actual_value
                # Read back actual value (camera may adjust it)
                actual = cap.get(prop_map[prop_name])
                print(f"Camera {camera_num} {prop_name}: {actual:.2f} (requested: {actual_value:.2f})")
    
    def get_camera_info(self, cap, camera_num: int) -> str:
        """Get camera information string"""
        if cap is None or not cap.isOpened():
            return f"Camera {camera_num}: Not available"
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        brightness = cap.get(self.PROP_BRIGHTNESS)
        saturation = cap.get(self.PROP_SATURATION)
        exposure = cap.get(self.PROP_EXPOSURE)
        focus = cap.get(self.PROP_FOCUS)
        
        info = f"Camera {camera_num} | {width}x{height} @ {fps:.1f}fps\n"
        info += f"Brightness: {brightness:.0f} | Saturation: {saturation:.0f}\n"
        info += f"Exposure: {exposure:.2f} | Focus: {focus:.0f}"
        
        return info
    
    def draw_info_overlay(self, frame, info: str, show_controls: bool = True):
        """Draw information overlay on frame"""
        # Create overlay
        overlay = frame.copy()
        h, w = frame.shape[:2]
        
        # Draw semi-transparent background for info
        cv2.rectangle(overlay, (10, 10), (w - 10, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Draw text
        lines = info.split('\n')
        y_offset = 30
        for line in lines:
            cv2.putText(frame, line, (20, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            y_offset += 25
        
        # Draw controls at bottom
        if show_controls:
            controls_y = h - 80
            cv2.rectangle(overlay, (10, controls_y - 5), (w - 10, h - 10), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)
            
            control_text = [
                "Q/ESC: Quit  |  S: Save Settings  |  R: Reset  |  1/2: Toggle Camera"
            ]
            y_pos = controls_y + 20
            for text in control_text:
                cv2.putText(frame, text, (20, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                y_pos += 20
    
    def start(self):
        """Start camera capture and GUI"""
        print("Starting Camera Test GUI...")
        print("Controls:")
        print("  - Adjust trackbars to change camera properties")
        print("  - Press 'Q' or 'ESC' to quit")
        print("  - Press 'S' to save current settings")
        print("  - Press 'R' to reset to defaults")
        print("  - Press '1' to show/hide Camera 1")
        print("  - Press '2' to show/hide Camera 2")
        print("  - Controls are also shown at bottom of each window")
        print()
        
        # Open cameras
        if sys.platform == 'win32':
            self.cap1 = cv2.VideoCapture(self.camera1_id, cv2.CAP_DSHOW)
            self.cap2 = cv2.VideoCapture(self.camera2_id, cv2.CAP_DSHOW)
        else:
            self.cap1 = cv2.VideoCapture(self.camera1_id)
            self.cap2 = cv2.VideoCapture(self.camera2_id)
        
        if not self.cap1.isOpened():
            print(f"ERROR: Failed to open Camera 1 (ID: {self.camera1_id})")
            return False
        
        if not self.cap2.isOpened():
            print(f"ERROR: Failed to open Camera 2 (ID: {self.camera2_id})")
            return False
        
        # Set resolution and FPS
        self.cap1.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap1.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap1.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        self.cap2.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap2.set(cv2.CAP_PROP_FPS, self.fps)
        self.cap2.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Enable auto-exposure off for manual control
        self.cap1.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual mode
        self.cap2.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        
        # Get actual properties
        actual_w1 = int(self.cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h1 = int(self.cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps1 = self.cap1.get(cv2.CAP_PROP_FPS)
        
        actual_w2 = int(self.cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h2 = int(self.cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps2 = self.cap2.get(cv2.CAP_PROP_FPS)
        
        print(f"Camera 1: {actual_w1}x{actual_h1} @ {actual_fps1:.1f}fps")
        print(f"Camera 2: {actual_w2}x{actual_h2} @ {actual_fps2:.1f}fps")
        print()
        
        # Create windows with trackbars
        cv2.namedWindow(self.window1, cv2.WINDOW_NORMAL)
        cv2.namedWindow(self.window2, cv2.WINDOW_NORMAL)
        
        # Resize windows
        cv2.resizeWindow(self.window1, 800, 600)
        cv2.resizeWindow(self.window2, 800, 600)
        
        # Create trackbars
        self.create_trackbars(self.window1, 1)
        self.create_trackbars(self.window2, 2)
        
        # Window visibility
        show_cam1 = True
        show_cam2 = True
        
        # Status messages
        status_message = ""
        status_time = 0
        status_duration = 2.0  # Show status for 2 seconds
        
        self.running = True
        frame_time = 1.0 / self.fps
        
        print("GUI Ready! Adjust trackbars to test camera settings.")
        print("Controls are shown at the bottom of each window.")
        print()
        
        try:
            while self.running:
                start_time = time.time()
                
                # Read frames
                ret1, frame1 = self.cap1.read()
                ret2, frame2 = self.cap2.read()
                
                if not ret1:
                    print("Warning: Failed to read from Camera 1")
                if not ret2:
                    print("Warning: Failed to read from Camera 2")
                
                # Draw info overlays
                if ret1:
                    info1 = self.get_camera_info(self.cap1, 1)
                    self.draw_info_overlay(frame1, info1, show_controls=True)
                    
                    # Draw status message if active
                    if status_message and (time.time() - status_time) < status_duration:
                        h, w = frame1.shape[:2]
                        text_size = cv2.getTextSize(status_message, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                        text_x = (w - text_size[0]) // 2
                        text_y = h // 2
                        cv2.rectangle(frame1, (text_x - 10, text_y - 25), 
                                     (text_x + text_size[0] + 10, text_y + 10), (0, 0, 0), -1)
                        cv2.putText(frame1, status_message, (text_x, text_y), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    
                    if show_cam1:
                        cv2.imshow(self.window1, frame1)
                
                if ret2:
                    info2 = self.get_camera_info(self.cap2, 2)
                    self.draw_info_overlay(frame2, info2, show_controls=True)
                    
                    # Draw status message if active
                    if status_message and (time.time() - status_time) < status_duration:
                        h, w = frame2.shape[:2]
                        text_size = cv2.getTextSize(status_message, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                        text_x = (w - text_size[0]) // 2
                        text_y = h // 2
                        cv2.rectangle(frame2, (text_x - 10, text_y - 25), 
                                     (text_x + text_size[0] + 10, text_y + 10), (0, 0, 0), -1)
                        cv2.putText(frame2, status_message, (text_x, text_y), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                    
                    if show_cam2:
                        cv2.imshow(self.window2, frame2)
                
                # Handle keyboard input - check both windows
                # Use longer wait time and check for window focus
                key = cv2.waitKey(30) & 0xFF
                
                if key == ord('q') or key == 27:  # 'q' or ESC
                    print("\nQuitting...")
                    break
                elif key == ord('s') or key == ord('S'):
                    filename = self.save_settings()
                    if filename:
                        status_message = f"Settings saved to {filename}"
                        status_time = time.time()
                        print(f"\n{status_message}")
                    else:
                        status_message = "Failed to save settings"
                        status_time = time.time()
                        print(f"\n{status_message}")
                elif key == ord('r') or key == ord('R'):
                    self.reset_settings()
                    status_message = "Settings reset to defaults"
                    status_time = time.time()
                    print(f"\n{status_message}")
                elif key == ord('1'):
                    show_cam1 = not show_cam1
                    if not show_cam1:
                        cv2.destroyWindow(self.window1)
                    else:
                        cv2.namedWindow(self.window1, cv2.WINDOW_NORMAL)
                        cv2.resizeWindow(self.window1, 800, 600)
                        self.create_trackbars(self.window1, 1)
                elif key == ord('2'):
                    show_cam2 = not show_cam2
                    if not show_cam2:
                        cv2.destroyWindow(self.window2)
                    else:
                        cv2.namedWindow(self.window2, cv2.WINDOW_NORMAL)
                        cv2.resizeWindow(self.window2, 800, 600)
                        self.create_trackbars(self.window2, 2)
                
                # Check if windows are closed
                if show_cam1 and cv2.getWindowProperty(self.window1, cv2.WND_PROP_VISIBLE) < 1:
                    show_cam1 = False
                if show_cam2 and cv2.getWindowProperty(self.window2, cv2.WND_PROP_VISIBLE) < 1:
                    show_cam2 = False
                
                # Exit if both windows closed
                if not show_cam1 and not show_cam2:
                    print("\nAll windows closed. Exiting...")
                    break
                
                # Maintain frame rate
                elapsed = time.time() - start_time
                if elapsed < frame_time:
                    time.sleep(frame_time - elapsed)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        
        finally:
            self.stop()
        
        return True
    
    def save_settings(self):
        """Save current camera settings to file"""
        settings = {}
        
        for cam_num in [1, 2]:
            cap = self.cap1 if cam_num == 1 else self.cap2
            if cap and cap.isOpened():
                settings[f'camera{cam_num}'] = {
                    'brightness': float(cap.get(self.PROP_BRIGHTNESS)),
                    'contrast': float(cap.get(self.PROP_CONTRAST)),
                    'saturation': float(cap.get(self.PROP_SATURATION)),
                    'exposure': float(cap.get(self.PROP_EXPOSURE)),
                    'gain': float(cap.get(self.PROP_GAIN)),
                    'focus': float(cap.get(self.PROP_FOCUS)),
                    'white_balance': float(cap.get(self.PROP_WHITE_BALANCE)),
                    'sharpness': float(cap.get(self.PROP_SHARPNESS)),
                    'gamma': float(cap.get(self.PROP_GAMMA)),
                }
        
        # Save to file
        import json
        from datetime import datetime
        
        filename = f"camera_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(os.getcwd(), filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(settings, f, indent=2)
            return filename
        except Exception as e:
            print(f"Error saving settings: {e}")
            return None
    
    def reset_settings(self):
        """Reset camera settings to defaults"""
        print("\nResetting to default settings...")
        
        for cam_num in [1, 2]:
            cap = self.cap1 if cam_num == 1 else self.cap2
            window = self.window1 if cam_num == 1 else self.window2
            
            if cap and cap.isOpened():
                # Reset to default values
                cap.set(self.PROP_BRIGHTNESS, self.prop_ranges['brightness'][2])
                cap.set(self.PROP_CONTRAST, self.prop_ranges['contrast'][2])
                cap.set(self.PROP_SATURATION, self.prop_ranges['saturation'][2])
                cap.set(self.PROP_EXPOSURE, self.prop_ranges['exposure'][2])
                cap.set(self.PROP_GAIN, self.prop_ranges['gain'][2])
                cap.set(self.PROP_FOCUS, self.prop_ranges['focus'][2])
                cap.set(self.PROP_WHITE_BALANCE, self.prop_ranges['white_balance'][2])
                cap.set(self.PROP_SHARPNESS, self.prop_ranges['sharpness'][2])
                cap.set(self.PROP_GAMMA, self.prop_ranges['gamma'][2])
                
                # Reset trackbars
                cv2.setTrackbarPos('Brightness', window, self.prop_ranges['brightness'][2])
                cv2.setTrackbarPos('Contrast', window, self.prop_ranges['contrast'][2])
                cv2.setTrackbarPos('Saturation', window, self.prop_ranges['saturation'][2])
                cv2.setTrackbarPos('Exposure', window, 50)
                cv2.setTrackbarPos('Gain', window, self.prop_ranges['gain'][2])
                cv2.setTrackbarPos('Focus', window, self.prop_ranges['focus'][2])
                cv2.setTrackbarPos('White Balance', window, 50)
                cv2.setTrackbarPos('Sharpness', window, self.prop_ranges['sharpness'][2])
                cv2.setTrackbarPos('Gamma', window, self.prop_ranges['gamma'][2])
        
        print("Settings reset complete")
    
    def stop(self):
        """Stop camera capture and cleanup"""
        self.running = False
        
        if self.cap1:
            self.cap1.release()
        if self.cap2:
            self.cap2.release()
        
        cv2.destroyAllWindows()
        print("Camera Test GUI stopped")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Camera Test GUI - Adjust focus, brightness, saturation, etc.')
    parser.add_argument('--camera1', type=int, default=0, help='Camera 1 ID (default: 0)')
    parser.add_argument('--camera2', type=int, default=2, help='Camera 2 ID (default: 2)')
    parser.add_argument('--width', type=int, default=1280, help='Resolution width (default: 1280)')
    parser.add_argument('--height', type=int, default=720, help='Resolution height (default: 720)')
    parser.add_argument('--fps', type=int, default=60, help='Frame rate (default: 60)')
    
    args = parser.parse_args()
    
    gui = CameraTestGUI(
        camera1_id=args.camera1,
        camera2_id=args.camera2,
        width=args.width,
        height=args.height,
        fps=args.fps
    )
    
    try:
        gui.start()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

