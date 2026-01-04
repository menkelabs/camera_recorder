"""
Camera Setup & Recording GUI
Single window with 4 tabs: Camera 1 Setup, Camera 2 Setup, Recording, Analysis
"""

import cv2
import sys
import os
import threading
import time
import numpy as np
from typing import Optional, Tuple
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from dual_camera_recorder import DualCameraRecorder
from pose_processor import PoseProcessor
from sway_calculator import SwayCalculator


class TabbedCameraGUI:
    """Single window GUI with tabs for camera setup and recording"""
    
    # OpenCV camera property constants
    PROP_BRIGHTNESS = cv2.CAP_PROP_BRIGHTNESS
    PROP_CONTRAST = cv2.CAP_PROP_CONTRAST
    PROP_SATURATION = cv2.CAP_PROP_SATURATION
    PROP_EXPOSURE = cv2.CAP_PROP_EXPOSURE
    PROP_GAIN = cv2.CAP_PROP_GAIN
    PROP_FOCUS = cv2.CAP_PROP_FOCUS
    PROP_WHITE_BALANCE = cv2.CAP_PROP_WHITE_BALANCE_BLUE_U
    PROP_SHARPNESS = cv2.CAP_PROP_SHARPNESS
    PROP_GAMMA = cv2.CAP_PROP_GAMMA
    
    def __init__(self, camera1_id: int = None, camera2_id: int = None, 
                 width: int = 1280, height: int = 720, fps: int = 60):
        # Use platform-appropriate defaults if not specified
        if sys.platform == 'win32':
            # Windows: Use cameras 0 and 2 (skip built-in at 1)
            self.camera1_id = camera1_id if camera1_id is not None else 0
            self.camera2_id = camera2_id if camera2_id is not None else 2
        else:
            # Linux/Other: Use cameras 0 and 1
            self.camera1_id = camera1_id if camera1_id is not None else 0
            self.camera2_id = camera2_id if camera2_id is not None else 1
        self.width = width
        self.height = height
        self.fps = fps
        
        self.cap1 = None
        self.cap2 = None
        self.cameras_available = False  # Track if cameras are actually available
        self.recorder = None
        self.running = False
        
        # Tab management
        self.current_tab = 0  # 0=Cam1, 1=Cam2, 2=Recording, 3=Analysis
        self.tab_names = ["Camera 1 Setup", "Camera 2 Setup", "Recording", "Analysis"]
        
        # Recording state
        self.is_recording = False
        self.recording_start_time = None
        self.recording_files = None
        
        # Analysis state
        self.is_analyzing = False
        self.analysis_camera1 = None
        self.analysis_camera2 = None
        self.analysis_progress = ""
        self.analysis_start_time = None
        self.analysis_frame_index = 0  # Current frame index for navigation
        
        # Property ranges
        self.prop_ranges = {
            'brightness': (0, 255, 128),
            'contrast': (0, 255, 32),
            'saturation': (0, 255, 64),
            'exposure': (-13, 1, -6),
            'gain': (0, 100, 0),
            'focus': (0, 255, 0),
            'white_balance': (2000, 6500, 4000),
            'sharpness': (0, 255, 0),
            'gamma': (0, 200, 100),
        }
        
        # Window setup
        self.window_name = "Camera Setup & Recording"
        self.window_width = 1600
        self.window_height = 900
        self.tab_height = 40
        self.preview_width = 640
        self.preview_height = 360
        
        # Status messages
        self.status_message = ""
        self.status_time = 0
        self.status_duration = 2.0
        
    def create_trackbars(self, camera_num: int):
        """Create trackbars for camera properties"""
        # Trackbars are created in the tab display area
        pass
    
    def on_trackbar_change(self, prop_name: str, camera_num: int, value: int):
        """Handle trackbar changes"""
        cap = self.cap1 if camera_num == 1 else self.cap2
        if cap is None or not cap.isOpened():
            return
        
        # Map trackbar value to actual property value
        if prop_name == 'exposure':
            min_val, max_val, _ = self.prop_ranges['exposure']
            actual_value = min_val + (max_val - min_val) * (value / 100.0)
        elif prop_name == 'white_balance':
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
            cap.set(prop_map[prop_name], actual_value)
    
    def draw_tabs(self, frame):
        """Draw tab buttons at the top"""
        h, w = frame.shape[:2]
        tab_width = w // len(self.tab_names)
        
        # Draw tab background
        cv2.rectangle(frame, (0, 0), (w, self.tab_height), (50, 50, 50), -1)
        cv2.line(frame, (0, self.tab_height), (w, self.tab_height), (200, 200, 200), 2)
        
        # Draw each tab
        for i, name in enumerate(self.tab_names):
            x1 = i * tab_width
            x2 = (i + 1) * tab_width
            
            # Highlight active tab
            if i == self.current_tab:
                cv2.rectangle(frame, (x1 + 2, 2), (x2 - 2, self.tab_height - 2), (100, 150, 200), -1)
                color = (255, 255, 255)
            else:
                color = (180, 180, 180)
            
            # Draw tab text
            text_size = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            text_x = x1 + (tab_width - text_size[0]) // 2
            text_y = (self.tab_height + text_size[1]) // 2
            cv2.putText(frame, name, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Tab number hint
            hint = f"[{i+1}]"
            hint_size = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
            cv2.putText(frame, hint, (x2 - hint_size[0] - 10, 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)
    
    def draw_camera_setup_tab(self, frame, camera_num: int):
        """Draw camera setup tab content"""
        h, w = frame.shape[:2]
        content_y = self.tab_height + 10
        content_h = h - content_y - 10
        
        # Split into preview and controls
        preview_x = 10
        preview_y = content_y
        controls_x = self.preview_width + 30
        controls_y = content_y
        controls_w = w - controls_x - 10
        
        # Get camera
        cap = self.cap1 if camera_num == 1 else self.cap2
        if cap is None or not cap.isOpened():
            # Draw "Camera not available" message
            text = f"Camera {camera_num} not available"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
            text_x = (w - text_size[0]) // 2
            text_y = h // 2
            cv2.putText(frame, text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            return
        
        # Read frame
        ret, cam_frame = cap.read()
        if not ret:
            return
        
        # Resize preview
        preview = cv2.resize(cam_frame, (self.preview_width, self.preview_height))
        
        # Draw preview with border
        frame[preview_y:preview_y+self.preview_height, preview_x:preview_x+self.preview_width] = preview
        cv2.rectangle(frame, (preview_x, preview_y), 
                     (preview_x+self.preview_width, preview_y+self.preview_height), 
                     (255, 255, 255), 2)
        
        # Draw camera info
        info_y = preview_y + self.preview_height + 20
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        info_text = f"Camera {camera_num}: {width}x{height} @ {fps:.1f}fps"
        cv2.putText(frame, info_text, (preview_x, info_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Draw controls area (simulated trackbars with text)
        controls_start_y = controls_y + 20
        line_height = 35
        y_pos = controls_start_y
        
        # Get current values
        brightness = int(cap.get(self.PROP_BRIGHTNESS))
        contrast = int(cap.get(self.PROP_CONTRAST))
        saturation = int(cap.get(self.PROP_SATURATION))
        exposure = cap.get(self.PROP_EXPOSURE)
        gain = int(cap.get(self.PROP_GAIN))
        focus = int(cap.get(self.PROP_FOCUS))
        white_balance = cap.get(self.PROP_WHITE_BALANCE)
        sharpness = int(cap.get(self.PROP_SHARPNESS))
        gamma = int(cap.get(self.PROP_GAMMA))
        
        # Draw property labels and values
        properties = [
            ("Brightness", brightness, 0, 255, 'brightness'),
            ("Contrast", contrast, 0, 255, 'contrast'),
            ("Saturation", saturation, 0, 255, 'saturation'),
            ("Exposure", f"{exposure:.2f}", -13, 1, 'exposure'),
            ("Gain", gain, 0, 100, 'gain'),
            ("Focus", focus, 0, 255, 'focus'),
            ("White Balance", f"{white_balance:.0f}K", 2000, 6500, 'white_balance'),
            ("Sharpness", sharpness, 0, 255, 'sharpness'),
            ("Gamma", gamma, 0, 200, 'gamma'),
        ]
        
        # Get current property index for highlighting
        prop_list = ['brightness', 'contrast', 'saturation', 'exposure', 
                     'gain', 'focus', 'white_balance', 'sharpness', 'gamma']
        current_prop_key = prop_list[self.current_prop_index % len(prop_list)]
        
        for i, (prop_name, value, min_val, max_val, prop_key) in enumerate(properties):
            # Highlight selected property
            if prop_key == current_prop_key:
                # Highlight background
                cv2.rectangle(frame, (controls_x - 5, y_pos - 20), 
                           (controls_x + controls_w - 5, y_pos + 10), (50, 100, 150), -1)
                text_color = (255, 255, 0)
                value_color = (0, 255, 255)
            else:
                text_color = (255, 255, 255)
                value_color = (0, 255, 255)
            
            # Property name with selection indicator
            prop_text = f"{'>>' if prop_key == current_prop_key else '  '} {prop_name}:"
            cv2.putText(frame, prop_text, (controls_x, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
            
            # Value
            value_text = str(value)
            value_x = controls_x + 150
            cv2.putText(frame, value_text, (value_x, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, value_color, 1)
            
            y_pos += line_height
        
        # Instructions
        inst_y = y_pos + 10
        cv2.putText(frame, "W/X: Select property | +/-: Adjust value", 
                   (controls_x, inst_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Instructions at bottom
        inst_y = h - 60
        cv2.putText(frame, "W/X: Select | +/-: Adjust | S: Save | R: Reset | Tab/1/2/3/4: Switch tabs", 
                   (10, inst_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    def draw_recording_tab(self, frame):
        """Draw recording tab content"""
        h, w = frame.shape[:2]
        content_y = self.tab_height + 10
        
        # Split screen for dual preview
        preview_width = (w - 30) // 2
        preview_height = int(preview_width * 9 / 16)  # 16:9 aspect
        
        # Camera 1 preview
        if self.cap1 and self.cap1.isOpened():
            ret1, frame1 = self.cap1.read()
            if ret1:
                preview1 = cv2.resize(frame1, (preview_width, preview_height))
                x1 = 10
                y1 = content_y
                frame[y1:y1+preview_height, x1:x1+preview_width] = preview1
                cv2.rectangle(frame, (x1, y1), (x1+preview_width, y1+preview_height), 
                             (255, 255, 255), 2)
                cv2.putText(frame, "Camera 1", (x1 + 10, y1 + 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Camera 2 preview
        if self.cap2 and self.cap2.isOpened():
            ret2, frame2 = self.cap2.read()
            if ret2:
                preview2 = cv2.resize(frame2, (preview_width, preview_height))
                x2 = preview_width + 20
                y2 = content_y
                frame[y2:y2+preview_height, x2:x2+preview_width] = preview2
                cv2.rectangle(frame, (x2, y2), (x2+preview_width, y2+preview_height), 
                             (255, 255, 255), 2)
                cv2.putText(frame, "Camera 2", (x2 + 10, y2 + 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Recording controls area
        controls_y = content_y + preview_height + 20
        controls_h = h - controls_y - 10
        
        # Recording status
        status_y = controls_y + 30
        if self.is_recording:
            # Red recording indicator
            cv2.circle(frame, (20, status_y), 10, (0, 0, 255), -1)
            cv2.putText(frame, "RECORDING", (40, status_y + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Recording duration
            if self.recording_start_time:
                duration = time.time() - self.recording_start_time
                duration_text = f"Duration: {duration:.1f}s"
                cv2.putText(frame, duration_text, (200, status_y + 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # File paths
            if self.recording_files:
                file_y = status_y + 35
                cv2.putText(frame, f"Camera 1: {os.path.basename(self.recording_files[0])}", 
                           (20, file_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                cv2.putText(frame, f"Camera 2: {os.path.basename(self.recording_files[1])}", 
                           (20, file_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            
            # Stop button (visual)
            stop_x = w - 200
            stop_y = status_y - 10
            cv2.rectangle(frame, (stop_x, stop_y), (stop_x + 150, stop_y + 40), (0, 0, 200), -1)
            cv2.rectangle(frame, (stop_x, stop_y), (stop_x + 150, stop_y + 40), (255, 255, 255), 2)
            cv2.putText(frame, "STOP [Space]", (stop_x + 20, stop_y + 28), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        else:
            # Ready to record
            cv2.putText(frame, "Ready to Record", (20, status_y + 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Start button (visual)
            start_x = w - 200
            start_y = status_y - 10
            cv2.rectangle(frame, (start_x, start_y), (start_x + 150, start_y + 40), (0, 200, 0), -1)
            cv2.rectangle(frame, (start_x, start_y), (start_x + 150, start_y + 40), (255, 255, 255), 2)
            cv2.putText(frame, "START [Space]", (start_x + 15, start_y + 28), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Instructions
        inst_y = h - 30
        cv2.putText(frame, "Press SPACE to start/stop recording | Tab/1/2/3/4 to switch tabs | Q/ESC to quit", 
                   (10, inst_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    def draw_analysis_tab(self, frame):
        """Draw analysis tab content"""
        h, w = frame.shape[:2]
        content_y = self.tab_height + 10
        
        # Check if analyzing
        if self.is_analyzing:
            # Show progress message
            text_y = h // 2
            text_size = cv2.getTextSize(self.analysis_progress, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
            text_x = (w - text_size[0]) // 2
            cv2.putText(frame, self.analysis_progress, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            
            # Show elapsed time if available
            if self.analysis_start_time:
                elapsed = time.time() - self.analysis_start_time
                elapsed_text = f"Elapsed: {elapsed:.1f}s"
                elapsed_size = cv2.getTextSize(elapsed_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                elapsed_x = (w - elapsed_size[0]) // 2
                cv2.putText(frame, elapsed_text, (elapsed_x, text_y + 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
            return
        
        # Show results if available
        if self.analysis_camera1 is None and self.analysis_camera2 is None:
            # No analysis results yet
            text = "No analysis results available"
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2)[0]
            text_x = (w - text_size[0]) // 2
            text_y = h // 2
            cv2.putText(frame, text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (150, 150, 150), 2)
            
            hint = "Record a video and it will be analyzed automatically"
            hint_size = cv2.getTextSize(hint, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
            hint_x = (w - hint_size[0]) // 2
            cv2.putText(frame, hint, (hint_x, text_y + 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
            return
        
        # Display results - summary at top
        y_pos = content_y + 20
        title_size = cv2.getTextSize("SWING ANALYSIS RESULTS", cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        title_x = (w - title_size[0]) // 2
        cv2.putText(frame, "SWING ANALYSIS RESULTS", (title_x, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        y_pos += 40
        
        # Get frame count for navigation
        max_frames = 0
        if self.analysis_camera1:
            max_frames = max(max_frames, len(self.analysis_camera1.get('sway', [])))
        if self.analysis_camera2:
            max_frames = max(max_frames, len(self.analysis_camera2.get('shoulder_turn', [])))
        
        # Ensure frame index is valid
        if max_frames > 0:
            self.analysis_frame_index = max(0, min(max_frames - 1, self.analysis_frame_index))
        else:
            self.analysis_frame_index = 0
        
        # Frame navigation info
        frame_info_y = y_pos
        if max_frames > 0:
            frame_text = f"Frame: {self.analysis_frame_index + 1}/{max_frames}  (A/← Previous, D/→ Next)"
            cv2.putText(frame, frame_text, (20, frame_info_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        frame_info_y += 25
        
        # MAX METRICS SECTION (prominently displayed)
        summary_y = frame_info_y + 5
        cv2.putText(frame, "MAX VALUES:", (20, summary_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        summary_y += 25
        line_height = 28
        
        # Get summary data (max values are already stored in summary)
        summary1 = self.analysis_camera1.get('summary', {}) if self.analysis_camera1 else {}
        summary2 = self.analysis_camera2.get('summary', {}) if self.analysis_camera2 else {}
        
        # Max Shoulder Turn (from camera 2 - down-the-line)
        max_shoulder = summary2.get('max_shoulder_turn')
        if max_shoulder is not None:
            text = f"Max Shoulder Turn: {max_shoulder:+.1f}°"
            cv2.putText(frame, text, (30, summary_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            summary_y += line_height
        
        # Max Hip Turn (from camera 2)
        max_hip = summary2.get('max_hip_turn')
        if max_hip is not None:
            text = f"Max Hip Turn: {max_hip:+.1f}°"
            cv2.putText(frame, text, (30, summary_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            summary_y += line_height
        
        # Max X-Factor (from camera 2)
        max_xfactor = summary2.get('max_x_factor')
        if max_xfactor is not None:
            text = f"Max X-Factor: {max_xfactor:.1f}°"
            cv2.putText(frame, text, (30, summary_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            summary_y += line_height
        
        # Lateral Sway (from camera 1 - face-on)
        max_sway_l = summary1.get('max_sway_left')
        max_sway_r = summary1.get('max_sway_right')
        if max_sway_l is not None or max_sway_r is not None:
            sway_text = "Max Lateral Sway: "
            if max_sway_l is not None:
                sway_text += f"Left {abs(max_sway_l):.0f}px"
                if max_sway_r is not None:
                    sway_text += ", "
            if max_sway_r is not None:
                sway_text += f"Right {max_sway_r:.0f}px"
            cv2.putText(frame, sway_text, (30, summary_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            summary_y += line_height
        
        summary_y += 15
        
        # LIVE METRICS SECTION (current frame values)
        live_y = summary_y
        cv2.putText(frame, "CURRENT FRAME VALUES:", (20, live_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        live_y += 25
        
        # Get current frame data
        frame_idx = self.analysis_frame_index if max_frames > 0 else 0
        
        # Current Shoulder Turn
        if self.analysis_camera2 and frame_idx < len(self.analysis_camera2.get('shoulder_turn', [])):
            current_shoulder = self.analysis_camera2['shoulder_turn'][frame_idx]
            if current_shoulder is not None:
                text = f"Shoulder Turn: {current_shoulder:+.1f}°"
                cv2.putText(frame, text, (30, live_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
                live_y += 22
        
        # Current Hip Turn
        if self.analysis_camera2 and frame_idx < len(self.analysis_camera2.get('hip_turn', [])):
            current_hip = self.analysis_camera2['hip_turn'][frame_idx]
            if current_hip is not None:
                text = f"Hip Turn: {current_hip:+.1f}°"
                cv2.putText(frame, text, (30, live_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
                live_y += 22
        
        # Current X-Factor
        if self.analysis_camera2 and frame_idx < len(self.analysis_camera2.get('x_factor', [])):
            current_xfactor = self.analysis_camera2['x_factor'][frame_idx]
            if current_xfactor is not None:
                text = f"X-Factor: {current_xfactor:.1f}°"
                cv2.putText(frame, text, (30, live_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
                live_y += 22
        
        # Current Lateral Sway
        if self.analysis_camera1 and frame_idx < len(self.analysis_camera1.get('sway', [])):
            current_sway = self.analysis_camera1['sway'][frame_idx]
            if current_sway is not None:
                text = f"Lateral Sway: {current_sway:+.0f}px"
                cv2.putText(frame, text, (30, live_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
                live_y += 22
        
        live_y += 15
        
        # Two-column layout for per-camera results
        col_width = (w - 40) // 2
        left_col_x = 20
        right_col_x = col_width + 30
        
        # Left column: Camera 1 (Face-on - Sway metrics)
        cam1_y = summary_y
        cv2.putText(frame, "Camera 1 (Face-On):", (left_col_x, cam1_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cam1_y += 25
        
        if self.analysis_camera1:
            detection_rate1 = self.analysis_camera1.get('detection_rate', 0)
            cv2.putText(frame, f"Detection: {detection_rate1:.1f}%", 
                       (left_col_x, cam1_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cam1_y += 20
            
            sway_summary = summary1
            if sway_summary.get('max_sway_left') is not None:
                text = f"Max Sway Left: {abs(sway_summary['max_sway_left']):.0f}px"
                cv2.putText(frame, text, (left_col_x, cam1_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cam1_y += 20
            if sway_summary.get('max_sway_right') is not None:
                text = f"Max Sway Right: {sway_summary['max_sway_right']:.0f}px"
                cv2.putText(frame, text, (left_col_x, cam1_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Right column: Camera 2 (Down-the-Line - Rotation metrics)
        cam2_y = summary_y
        cv2.putText(frame, "Camera 2 (Down-the-Line):", (right_col_x, cam2_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cam2_y += 25
        
        if self.analysis_camera2:
            detection_rate2 = self.analysis_camera2.get('detection_rate', 0)
            cv2.putText(frame, f"Detection: {detection_rate2:.1f}%", 
                       (right_col_x, cam2_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cam2_y += 20
            
            rot_summary = summary2
            if rot_summary.get('max_shoulder_turn') is not None:
                text = f"Max Shoulder: {rot_summary['max_shoulder_turn']:+.1f}°"
                cv2.putText(frame, text, (right_col_x, cam2_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cam2_y += 20
            if rot_summary.get('max_hip_turn') is not None:
                text = f"Max Hip: {rot_summary['max_hip_turn']:+.1f}°"
                cv2.putText(frame, text, (right_col_x, cam2_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cam2_y += 20
            if rot_summary.get('max_x_factor') is not None:
                text = f"Max X-Factor: {rot_summary['max_x_factor']:.1f}°"
                cv2.putText(frame, text, (right_col_x, cam2_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Instructions
        inst_y = h - 30
        cv2.putText(frame, "Tab/1/2/3/4 to switch tabs | Q/ESC to quit", 
                   (10, inst_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    def start_recording(self):
        """Start recording"""
        if self.is_recording:
            return
        
        # Check if cameras are available (logical check - don't try if they failed at startup)
        if not self.cameras_available:
            self.status_message = "Cameras not available - cannot record"
            self.status_time = time.time()
            print(f"ERROR: Cameras not available (cameras_available={self.cameras_available}) - cannot start recording")
            print("Make sure cameras are connected and not in use by another application")
            return
        
        # Double-check: cameras should be available if we get here
        if not (self.cap1 and self.cap1.isOpened() and self.cap2 and self.cap2.isOpened()):
            self.status_message = "Cameras not available - cannot record"
            self.status_time = time.time()
            print(f"ERROR: Camera state mismatch (cameras_available={self.cameras_available}, cap1={self.cap1 is not None}, cap2={self.cap2 is not None})")
            return
        
        try:
            # Store camera settings BEFORE releasing GUI cameras (so we can apply them to recorder)
            camera1_settings = {}
            camera2_settings = {}
            
            if self.cap1 and self.cap1.isOpened():
                for prop_name, prop_const in [
                    ('brightness', self.PROP_BRIGHTNESS),
                    ('contrast', self.PROP_CONTRAST),
                    ('saturation', self.PROP_SATURATION),
                    ('exposure', self.PROP_EXPOSURE),
                    ('gain', self.PROP_GAIN),
                    ('focus', self.PROP_FOCUS),
                    ('white_balance', self.PROP_WHITE_BALANCE),
                    ('sharpness', self.PROP_SHARPNESS),
                    ('gamma', self.PROP_GAMMA),
                ]:
                    camera1_settings[prop_const] = self.cap1.get(prop_const)
            
            if self.cap2 and self.cap2.isOpened():
                for prop_name, prop_const in [
                    ('brightness', self.PROP_BRIGHTNESS),
                    ('contrast', self.PROP_CONTRAST),
                    ('saturation', self.PROP_SATURATION),
                    ('exposure', self.PROP_EXPOSURE),
                    ('gain', self.PROP_GAIN),
                    ('focus', self.PROP_FOCUS),
                    ('white_balance', self.PROP_WHITE_BALANCE),
                    ('sharpness', self.PROP_SHARPNESS),
                    ('gamma', self.PROP_GAMMA),
                ]:
                    camera2_settings[prop_const] = self.cap2.get(prop_const)
            
            # Always release GUI cameras before recorder opens them (can't be open twice on Linux)
            if self.cap1 and self.cap1.isOpened():
                try:
                    self.cap1.release()
                except:
                    pass
            if self.cap2 and self.cap2.isOpened():
                try:
                    self.cap2.release()
                except:
                    pass
            
            # Always create a fresh recorder (old one was cleaned up in stop_recording)
            self.recorder = DualCameraRecorder(
                camera1_id=self.camera1_id,
                camera2_id=self.camera2_id
            )
            self.recorder.start_cameras(width=self.width, height=self.height, fps=self.fps)
            
            # Apply stored camera settings to recorder cameras
            for prop_const, value in camera1_settings.items():
                try:
                    self.recorder.camera1.cap.set(prop_const, value)
                except:
                    pass  # Some properties may not be settable
            
            for prop_const, value in camera2_settings.items():
                try:
                    self.recorder.camera2.cap.set(prop_const, value)
                except:
                    pass  # Some properties may not be settable
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"recording_{timestamp}"
            
            self.recorder.start_recording(filename)
            self.is_recording = True
            self.recording_start_time = time.time()
            # Store video file paths (constructed from filename like DualCameraRecorder does)
            self.recording_files = [
                os.path.join(self.recorder.output_dir, f"{filename}_camera1.mp4"),
                os.path.join(self.recorder.output_dir, f"{filename}_camera2.mp4")
            ]
            
            self.status_message = "Recording started"
            self.status_time = time.time()
            print(f"\nRecording started: {filename}")
        except ValueError as e:
            # Camera failed to open
            self.status_message = f"Failed to start recording: {str(e)}"
            self.status_time = time.time()
            print(f"ERROR: Failed to start recording: {e}")
            self.is_recording = False
            if self.recorder:
                try:
                    self.recorder.stop_cameras()
                except:
                    pass
                self.recorder = None
        except Exception as e:
            # Other errors
            self.status_message = f"Recording error: {str(e)}"
            self.status_time = time.time()
            print(f"ERROR: Recording error: {e}")
            self.is_recording = False
            if self.recorder:
                try:
                    self.recorder.stop_cameras()
                except:
                    pass
                self.recorder = None
    
    def stop_recording(self):
        """Stop recording"""
        if not self.is_recording:
            return
        
        if not self.recorder:
            self.is_recording = False
            self.status_message = "No active recording"
            self.status_time = time.time()
            return
        
        try:
            self.recorder.stop_recording()
            self.recorder.stop_cameras()  # Stop cameras first
            self.is_recording = False
            
            duration = time.time() - self.recording_start_time if self.recording_start_time else 0
            self.status_message = f"Recording stopped ({duration:.1f}s)"
            self.status_time = time.time()
            
            print(f"\nRecording stopped. Duration: {duration:.1f}s")
            if self.recording_files:
                print(f"Files saved:")
                for f in self.recording_files:
                    print(f"  {f}")
            
            self.recording_start_time = None
            
            # Wait a moment for video files to be fully written before reopening cameras
            time.sleep(0.5)  # Give recorder time to finish writing files
            
            # Reopen cameras for GUI preview (only if cameras were available)
            if self.cameras_available:
                try:
                    if sys.platform == 'win32':
                        self.cap1 = cv2.VideoCapture(self.camera1_id, cv2.CAP_DSHOW)
                        self.cap2 = cv2.VideoCapture(self.camera2_id, cv2.CAP_DSHOW)
                    else:
                        self.cap1 = cv2.VideoCapture(self.camera1_id)
                        self.cap2 = cv2.VideoCapture(self.camera2_id)
                    
                    # Reconfigure cameras
                    if self.cap1 and self.cap1.isOpened():
                        self.cap1.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        self.cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        self.cap1.set(cv2.CAP_PROP_FPS, self.fps)
                        self.cap1.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    else:
                        print("WARNING: Failed to reopen Camera 1 after recording")
                        self.cap1 = None
                    
                    if self.cap2 and self.cap2.isOpened():
                        self.cap2.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        self.cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        self.cap2.set(cv2.CAP_PROP_FPS, self.fps)
                        self.cap2.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    else:
                        print("WARNING: Failed to reopen Camera 2 after recording")
                        self.cap2 = None
                except Exception as e:
                    print(f"WARNING: Error reopening cameras: {e}")
                    self.cap1 = None
                    self.cap2 = None
            
            # Wait a bit more before starting analysis to ensure video files are fully written
            time.sleep(0.5)
            
            # Clean up recorder (cameras are already stopped, create fresh recorder for next recording)
            self.recorder = None
            
            # Start analysis automatically
            if self.recording_files and len(self.recording_files) == 2:
                self.start_analysis()
        except Exception as e:
            self.is_recording = False
            self.status_message = f"Error stopping recording: {str(e)}"
            self.status_time = time.time()
            print(f"ERROR: Error stopping recording: {e}")
            if self.recorder:
                try:
                    self.recorder.stop_cameras()
                except:
                    pass
    
    def adjust_property(self, camera_num: int, prop_name: str, delta: int):
        """Adjust a camera property"""
        cap = self.cap1 if camera_num == 1 else self.cap2
        if not cap or not cap.isOpened():
            return
        
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
        
        if prop_name not in prop_map:
            return
        
        current = cap.get(prop_map[prop_name])
        
        if prop_name == 'exposure':
            # Exposure is logarithmic, adjust by 0.5 steps
            new_value = current + (delta * 0.5)
            new_value = max(self.prop_ranges['exposure'][0], 
                          min(self.prop_ranges['exposure'][1], new_value))
        elif prop_name == 'white_balance':
            # White balance in Kelvin, adjust by 100K steps
            new_value = current + (delta * 100)
            new_value = max(self.prop_ranges['white_balance'][0], 
                          min(self.prop_ranges['white_balance'][1], new_value))
        else:
            # Linear adjustment
            min_val, max_val, _ = self.prop_ranges[prop_name]
            step = (max_val - min_val) / 100  # 1% steps
            new_value = current + (delta * step)
            new_value = max(min_val, min(max_val, new_value))
        
        cap.set(prop_map[prop_name], new_value)
    
    def start(self):
        """Start the GUI"""
        print("Starting Camera Setup & Recording GUI...")
        print("Tabs: [1] Camera 1 Setup | [2] Camera 2 Setup | [3] Recording | [4] Analysis")
        print("Controls:")
        print("  - Tab/1/2/3/4: Switch tabs")
        print("  - W/X: Select property (in setup tabs)")
        print("  - +/-: Adjust current property (in setup tabs)")
        print("  - S: Save camera settings")
        print("  - R: Reset camera settings")
        print("  - Space: Start/Stop recording (in recording tab)")
        print("  - Q/ESC: Quit")
        print()
        
        # Open cameras with platform-appropriate backend
        if sys.platform == 'win32':
            # Windows: Use DirectShow backend for better compatibility
            self.cap1 = cv2.VideoCapture(self.camera1_id, cv2.CAP_DSHOW)
            self.cap2 = cv2.VideoCapture(self.camera2_id, cv2.CAP_DSHOW)
        else:
            # Linux/Other: Use default backend (V4L2 on Linux)
            self.cap1 = cv2.VideoCapture(self.camera1_id)
            self.cap2 = cv2.VideoCapture(self.camera2_id)
        
        # Check if cameras opened successfully
        cam1_available = self.cap1.isOpened()
        cam2_available = self.cap2.isOpened()
        self.cameras_available = cam1_available and cam2_available
        
        if not cam1_available:
            print(f"WARNING: Failed to open Camera 1 (ID: {self.camera1_id})")
            print("Camera may be in use by another application. GUI will continue without camera 1.")
            try:
                self.cap1.release()  # Clean up failed camera
            except:
                pass
            self.cap1 = None
        
        if not cam2_available:
            print(f"WARNING: Failed to open Camera 2 (ID: {self.camera2_id})")
            print("Camera may be in use by another application. GUI will continue without camera 2.")
            try:
                self.cap2.release()  # Clean up failed camera
            except:
                pass
            self.cap2 = None
        
        # Continue even if cameras fail - user can still navigate tabs
        
        # Set camera properties (only if cameras are open)
        if self.cap1 and self.cap1.isOpened():
            self.cap1.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap1.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap1.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap1.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual mode
        
        if self.cap2 and self.cap2.isOpened():
            self.cap2.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap2.set(cv2.CAP_PROP_FPS, self.fps)
            self.cap2.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap2.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Manual mode
        
        # Get actual properties (only if cameras are open)
        if self.cap1 and self.cap1.isOpened():
            actual_w1 = int(self.cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h1 = int(self.cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps1 = self.cap1.get(cv2.CAP_PROP_FPS)
            print(f"Camera 1: {actual_w1}x{actual_h1} @ {actual_fps1:.1f}fps")
        else:
            print(f"Camera 1: Not available")
        
        if self.cap2 and self.cap2.isOpened():
            actual_w2 = int(self.cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h2 = int(self.cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps2 = self.cap2.get(cv2.CAP_PROP_FPS)
            print(f"Camera 2: {actual_w2}x{actual_h2} @ {actual_fps2:.1f}fps")
        else:
            print(f"Camera 2: Not available")
        
        print()
        
        # Create window
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, self.window_width, self.window_height)
        
        # Property adjustment state (per camera)
        self.current_prop_index = 0
        prop_list = ['brightness', 'contrast', 'saturation', 'exposure', 
                     'gain', 'focus', 'white_balance', 'sharpness', 'gamma']
        
        self.running = True
        frame_time = 1.0 / self.fps
        
        print("GUI Ready!")
        print()
        
        try:
            while self.running:
                start_time = time.time()
                
                # Create frame
                frame = np.zeros((self.window_height, self.window_width, 3), dtype=np.uint8)
                
                # Draw tabs
                self.draw_tabs(frame)
                
                # Draw current tab content
                if self.current_tab == 0:
                    self.draw_camera_setup_tab(frame, 1)
                elif self.current_tab == 1:
                    self.draw_camera_setup_tab(frame, 2)
                elif self.current_tab == 2:
                    self.draw_recording_tab(frame)
                elif self.current_tab == 3:
                    self.draw_analysis_tab(frame)
                
                # Draw status message
                if self.status_message and (time.time() - self.status_time) < self.status_duration:
                    h, w = frame.shape[:2]
                    text_size = cv2.getTextSize(self.status_message, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                    text_x = (w - text_size[0]) // 2
                    text_y = h // 2
                    cv2.rectangle(frame, (text_x - 20, text_y - 30), 
                                 (text_x + text_size[0] + 20, text_y + 10), (0, 0, 0), -1)
                    cv2.putText(frame, self.status_message, (text_x, text_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # Show frame
                cv2.imshow(self.window_name, frame)
                
                # Handle keyboard input
                key = cv2.waitKey(30)
                if key == -1:
                    key = 0
                key_code = key & 0xFF
                
                if key_code == ord('q') or key_code == 27:  # Q or ESC
                    if self.is_recording:
                        self.stop_recording()
                    print("\nQuitting...")
                    break
                elif key_code == ord('\t') or key_code == 9:  # Tab key
                    self.current_tab = (self.current_tab + 1) % 4
                elif key_code == ord('1'):
                    self.current_tab = 0
                elif key_code == ord('2'):
                    self.current_tab = 1
                elif key_code == ord('3'):
                    self.current_tab = 2
                elif key_code == ord('4'):
                    self.current_tab = 3
                elif key_code == ord(' ') and self.current_tab == 2:  # Space in recording tab
                    if self.is_recording:
                        self.stop_recording()
                    else:
                        self.start_recording()
                elif self.current_tab == 3:  # Analysis tab - frame navigation
                    # Arrow keys: check full key value (not key_code)
                    # Left arrow: 81 (masked) or 65361 (full), Right arrow: 83 (masked) or 65363 (full)
                    if key_code == ord('a') or key_code == ord('A') or key == 81 or key == 65361:  # A key or left arrow
                        # Previous frame
                        if self.analysis_camera1 or self.analysis_camera2:
                            # Get max frame count from either camera
                            max_frames = 0
                            if self.analysis_camera1:
                                max_frames = max(max_frames, len(self.analysis_camera1.get('sway', [])))
                            if self.analysis_camera2:
                                max_frames = max(max_frames, len(self.analysis_camera2.get('shoulder_turn', [])))
                            if max_frames > 0:
                                self.analysis_frame_index = max(0, self.analysis_frame_index - 1)
                    elif key_code == ord('d') or key_code == ord('D') or key == 83 or key == 65363:  # D key or right arrow
                        # Next frame
                        if self.analysis_camera1 or self.analysis_camera2:
                            # Get max frame count from either camera
                            max_frames = 0
                            if self.analysis_camera1:
                                max_frames = max(max_frames, len(self.analysis_camera1.get('sway', [])))
                            if self.analysis_camera2:
                                max_frames = max(max_frames, len(self.analysis_camera2.get('shoulder_turn', [])))
                            if max_frames > 0:
                                self.analysis_frame_index = min(max_frames - 1, self.analysis_frame_index + 1)
                elif self.current_tab in [0, 1]:  # Setup tabs
                    camera_num = self.current_tab + 1
                    if key_code == ord('w') or key_code == ord('W'):  # W for up/previous property
                        self.current_prop_index = (self.current_prop_index - 1) % len(prop_list)
                    elif key_code == ord('x') or key_code == ord('X'):  # X for down/next property
                        self.current_prop_index = (self.current_prop_index + 1) % len(prop_list)
                    elif key_code == ord('+') or key_code == ord('='):
                        prop_name = prop_list[self.current_prop_index % len(prop_list)]
                        self.adjust_property(camera_num, prop_name, 1)
                    elif key_code == ord('-') or key_code == ord('_'):
                        prop_name = prop_list[self.current_prop_index % len(prop_list)]
                        self.adjust_property(camera_num, prop_name, -1)
                    elif key_code == ord('s') or key_code == ord('S'):  # Save
                        self.save_settings()
                    elif key_code == ord('r') or key_code == ord('R'):  # Reset
                        self.reset_settings(camera_num)
                
                # Check if window closed
                if cv2.getWindowProperty(self.window_name, cv2.WND_PROP_VISIBLE) < 1:
                    break
                
                # Maintain frame rate
                elapsed = time.time() - start_time
                if elapsed < frame_time:
                    time.sleep(frame_time - elapsed)
        
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        except Exception as e:
            print(f"\nError in GUI loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                self.stop()
            except:
                pass
        
        return True
    
    def save_settings(self):
        """Save current camera settings"""
        import json
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
        
        filename = f"camera_settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(os.getcwd(), filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(settings, f, indent=2)
            self.status_message = f"Settings saved to {filename}"
            self.status_time = time.time()
            print(f"\n{self.status_message}")
            return filename
        except Exception as e:
            self.status_message = f"Failed to save: {e}"
            self.status_time = time.time()
            return None
    
    def reset_settings(self, camera_num: int):
        """Reset camera settings to defaults"""
        cap = self.cap1 if camera_num == 1 else self.cap2
        if not cap or not cap.isOpened():
            return
        
        cap.set(self.PROP_BRIGHTNESS, self.prop_ranges['brightness'][2])
        cap.set(self.PROP_CONTRAST, self.prop_ranges['contrast'][2])
        cap.set(self.PROP_SATURATION, self.prop_ranges['saturation'][2])
        cap.set(self.PROP_EXPOSURE, self.prop_ranges['exposure'][2])
        cap.set(self.PROP_GAIN, self.prop_ranges['gain'][2])
        cap.set(self.PROP_FOCUS, self.prop_ranges['focus'][2])
        cap.set(self.PROP_WHITE_BALANCE, self.prop_ranges['white_balance'][2])
        cap.set(self.PROP_SHARPNESS, self.prop_ranges['sharpness'][2])
        cap.set(self.PROP_GAMMA, self.prop_ranges['gamma'][2])
        
        self.status_message = f"Camera {camera_num} settings reset"
        self.status_time = time.time()
    
    def start_analysis(self):
        """Start analysis of recorded videos in background thread"""
        if self.is_analyzing:
            return
        
        if not self.recording_files or len(self.recording_files) != 2:
            self.status_message = "No videos to analyze"
            self.status_time = time.time()
            return
        
        # Check if files exist
        if not os.path.exists(self.recording_files[0]) or not os.path.exists(self.recording_files[1]):
            self.status_message = "Video files not found"
            self.status_time = time.time()
            return
        
        self.is_analyzing = True
        self.analysis_progress = "Starting analysis..."
        self.analysis_start_time = time.time()
        self.analysis_camera1 = None
        self.analysis_camera2 = None
        
        # Start analysis in background thread
        analysis_thread = threading.Thread(target=self._analyze_videos, daemon=True)
        analysis_thread.start()
    
    def _analyze_videos(self):
        """Analyze both videos in background thread"""
        try:
            video1_path = self.recording_files[0]
            video2_path = self.recording_files[1]
            
            # Wait a moment to ensure video files are fully written and accessible
            time.sleep(1.0)  # Give files time to be fully written
            
            # Verify files exist before attempting analysis
            if not os.path.exists(video1_path):
                raise FileNotFoundError(f"Video file not found: {video1_path}")
            if not os.path.exists(video2_path):
                raise FileNotFoundError(f"Video file not found: {video2_path}")
            
            # Get video dimensions for frame_width
            cap1 = cv2.VideoCapture(video1_path)
            if cap1.isOpened():
                frame_width1 = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
                cap1.release()
            else:
                frame_width1 = 1280  # Default
            
            cap2 = cv2.VideoCapture(video2_path)
            if cap2.isOpened():
                frame_width2 = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
                cap2.release()
            else:
                frame_width2 = 1280  # Default
            
            # Process Camera 1 (face-on view)
            self.analysis_progress = "Processing Camera 1 (face-on)..."
            processor1 = PoseProcessor(model_complexity=2)
            landmarks_seq1, annotated_frames1 = processor1.process_video(video1_path)
            processor1.release()
            
            # Calculate sway metrics for camera 1
            calc1 = SwayCalculator()
            analysis1 = calc1.analyze_sequence(landmarks_seq1, frame_width1)
            
            # Calculate detection rate
            detected1 = sum(1 for lm in landmarks_seq1 if lm is not None)
            detection_rate1 = (detected1 / len(landmarks_seq1) * 100) if landmarks_seq1 else 0
            
            analysis1['detection_rate'] = detection_rate1
            self.analysis_camera1 = analysis1
            
            # Process Camera 2 (down-the-line view)
            self.analysis_progress = "Processing Camera 2 (down-the-line)..."
            processor2 = PoseProcessor(model_complexity=2)
            landmarks_seq2, annotated_frames2 = processor2.process_video(video2_path)
            processor2.release()
            
            # Calculate rotation metrics for camera 2
            calc2 = SwayCalculator()
            analysis2 = calc2.analyze_sequence(landmarks_seq2, frame_width2)
            
            # Calculate detection rate
            detected2 = sum(1 for lm in landmarks_seq2 if lm is not None)
            detection_rate2 = (detected2 / len(landmarks_seq2) * 100) if landmarks_seq2 else 0
            
            analysis2['detection_rate'] = detection_rate2
            self.analysis_camera2 = analysis2
            
            # Analysis complete
            self.is_analyzing = False
            self.analysis_progress = ""
            elapsed = time.time() - self.analysis_start_time if self.analysis_start_time else 0
            self.status_message = f"Analysis complete ({elapsed:.1f}s)"
            self.status_time = time.time()
            
            print(f"\nAnalysis complete in {elapsed:.1f}s")
            print(f"Camera 1 detection rate: {detection_rate1:.1f}%")
            print(f"Camera 2 detection rate: {detection_rate2:.1f}%")
            
        except Exception as e:
            self.is_analyzing = False
            self.analysis_progress = ""
            self.status_message = f"Analysis failed: {str(e)}"
            self.status_time = time.time()
            print(f"\nAnalysis error: {e}")
            import traceback
            traceback.print_exc()
    
    def stop(self):
        """Stop and cleanup"""
        self.running = False
        
        try:
            if self.is_recording:
                try:
                    self.stop_recording()
                except:
                    pass
            
            if self.recorder:
                try:
                    self.recorder.stop_recording()
                    self.recorder.stop_cameras()
                except:
                    pass
            
            if self.cap1:
                try:
                    self.cap1.release()
                except:
                    pass
            if self.cap2:
                try:
                    self.cap2.release()
                except:
                    pass
            
            try:
                cv2.destroyAllWindows()
                cv2.waitKey(1)  # Allow windows to close
            except:
                pass
            print("GUI stopped")
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Camera Setup & Recording GUI')
    # Platform-appropriate defaults: Windows uses 0,2 (skip built-in at 1), Linux uses 0,1
    default_cam1, default_cam2 = (0, 2) if sys.platform == 'win32' else (0, 1)
    parser.add_argument('--camera1', type=int, default=default_cam1, 
                       help=f'Camera 1 ID (default: {default_cam1})')
    parser.add_argument('--camera2', type=int, default=default_cam2, 
                       help=f'Camera 2 ID (default: {default_cam2})')
    parser.add_argument('--width', type=int, default=1280, help='Resolution width (default: 1280)')
    parser.add_argument('--height', type=int, default=720, help='Resolution height (default: 720)')
    parser.add_argument('--fps', type=int, default=60, help='Frame rate (default: 60)')
    
    args = parser.parse_args()
    
    gui = TabbedCameraGUI(
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

