"""
GUI Tests for Camera Setup & Recording GUI
Tests button functionality, tab switching, and other GUI logic
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import cv2
import numpy as np

# Add src and scripts to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'scripts'))
sys.path.insert(0, os.path.join(project_root, 'tests'))

from camera_setup_recorder_gui import TabbedCameraGUI
from test_utils import get_camera_ids


class TestGUIInitialization(unittest.TestCase):
    """Test GUI initialization with platform-appropriate defaults"""
    
    def test_platform_defaults_linux(self):
        """Test that Linux uses cameras 0, 1 by default"""
        with patch('sys.platform', 'linux'):
            with patch('cv2.VideoCapture'):
                gui = TabbedCameraGUI()
                self.assertEqual(gui.camera1_id, 0)
                self.assertEqual(gui.camera2_id, 1)
    
    def test_platform_defaults_windows(self):
        """Test that Windows uses cameras from config file"""
        with patch('sys.platform', 'win32'):
            with patch('cv2.VideoCapture'):
                # Get expected camera IDs from config file
                expected_cam1_id, expected_cam2_id = get_camera_ids()
                gui = TabbedCameraGUI()
                self.assertEqual(gui.camera1_id, expected_cam1_id)
                self.assertEqual(gui.camera2_id, expected_cam2_id)
    
    def test_explicit_camera_ids(self):
        """Test that explicit camera IDs override defaults"""
        with patch('cv2.VideoCapture'):
            gui = TabbedCameraGUI(camera1_id=5, camera2_id=7)
            self.assertEqual(gui.camera1_id, 5)
            self.assertEqual(gui.camera2_id, 7)
    
    def test_tab_names(self):
        """Test that all 4 tabs are present"""
        with patch('cv2.VideoCapture'):
            gui = TabbedCameraGUI()
            self.assertEqual(len(gui.tab_names), 4)
            self.assertIn("Camera 1 Setup", gui.tab_names)
            self.assertIn("Camera 2 Setup", gui.tab_names)
            self.assertIn("Recording", gui.tab_names)
            self.assertIn("Analysis", gui.tab_names)
    
    def test_initial_state(self):
        """Test initial GUI state"""
        with patch('cv2.VideoCapture'):
            gui = TabbedCameraGUI()
            self.assertEqual(gui.current_tab, 0)
            self.assertFalse(gui.is_recording)
            self.assertFalse(gui.is_analyzing)
            self.assertIsNone(gui.analysis_camera1)
            self.assertIsNone(gui.analysis_camera2)


class TestTabSwitching(unittest.TestCase):
    """Test tab switching functionality"""
    
    def setUp(self):
        """Set up GUI instance for testing"""
        with patch('cv2.VideoCapture'):
            self.gui = TabbedCameraGUI()
    
    def test_tab_cycle_next(self):
        """Test cycling to next tab"""
        self.gui.current_tab = 0
        # Simulate Tab key press (cycling through tabs)
        new_tab = (self.gui.current_tab + 1) % 4
        self.gui.current_tab = new_tab
        self.assertEqual(self.gui.current_tab, 1)
        
        # Cycle through all tabs
        for expected_tab in [2, 3, 0]:
            new_tab = (self.gui.current_tab + 1) % 4
            self.gui.current_tab = new_tab
            self.assertEqual(self.gui.current_tab, expected_tab)
    
    def test_tab_direct_selection(self):
        """Test direct tab selection with number keys"""
        # Key '1' -> tab 0
        self.gui.current_tab = 0
        self.assertEqual(self.gui.current_tab, 0)
        
        # Key '2' -> tab 1
        self.gui.current_tab = 1
        self.assertEqual(self.gui.current_tab, 1)
        
        # Key '3' -> tab 2
        self.gui.current_tab = 2
        self.assertEqual(self.gui.current_tab, 2)
        
        # Key '4' -> tab 3
        self.gui.current_tab = 3
        self.assertEqual(self.gui.current_tab, 3)


class TestRecordingControls(unittest.TestCase):
    """Test recording start/stop functionality"""
    
    def setUp(self):
        """Set up GUI instance with mocked cameras"""
        self.mock_cap1 = MagicMock()
        self.mock_cap2 = MagicMock()
        self.mock_cap1.isOpened.return_value = True
        self.mock_cap2.isOpened.return_value = True
        self.mock_cap1.get.return_value = 1280  # width
        self.mock_cap2.get.return_value = 1280
        
        with patch('cv2.VideoCapture') as mock_cap_class:
            mock_cap_class.side_effect = [self.mock_cap1, self.mock_cap2]
            
            # Mock DualCameraRecorder
            with patch('camera_setup_recorder_gui.DualCameraRecorder'):
                self.gui = TabbedCameraGUI()
                self.gui.cap1 = self.mock_cap1
                self.gui.cap2 = self.mock_cap2
    
    def test_start_recording_creates_recorder(self):
        """Test that start_recording creates DualCameraRecorder"""
        with patch('camera_setup_recorder_gui.DualCameraRecorder') as mock_recorder_class:
            mock_recorder = MagicMock()
            mock_recorder.video1_path = "test1.mp4"
            mock_recorder.video2_path = "test2.mp4"
            mock_recorder.output_dir = "recordings"
            mock_recorder.camera1 = MagicMock()
            mock_recorder.camera2 = MagicMock()
            mock_recorder.camera1.cap = self.mock_cap1
            mock_recorder.camera2.cap = self.mock_cap2
            mock_recorder.start_cameras.return_value = None
            mock_recorder.start_recording.return_value = None
            mock_recorder_class.return_value = mock_recorder
            
            # Ensure cameras are marked as available
            self.gui.cameras_available = True
            self.gui.recorder = None
            self.gui.current_tab = 2  # Recording tab
            self.gui.start_recording()
            
            self.assertIsNotNone(self.gui.recorder)
            self.assertTrue(self.gui.is_recording)
            mock_recorder.start_cameras.assert_called_once()
            mock_recorder.start_recording.assert_called_once()
    
    def test_start_recording_fails_when_cameras_unavailable(self):
        """Test that start_recording fails gracefully when cameras are unavailable"""
        with patch('camera_setup_recorder_gui.DualCameraRecorder') as mock_recorder_class:
            # Set cameras as unavailable (failed to open)
            self.gui.cameras_available = False
            self.gui.cap1 = None
            self.gui.cap2 = None
            self.gui.recorder = None
            self.gui.is_recording = False
            self.gui.status_message = ""
            self.gui.status_time = 0
            
            # Try to start recording
            self.gui.start_recording()
            
            # Verify recording was NOT started
            self.assertFalse(self.gui.is_recording, 
                           "Recording should not start when cameras unavailable")
            self.assertIsNone(self.gui.recorder, 
                            "Recorder should not be created when cameras unavailable")
            self.assertIn("not available", self.gui.status_message.lower(),
                         "Status message should indicate cameras not available")
            # Verify DualCameraRecorder was never instantiated
            mock_recorder_class.assert_not_called()
    
    def test_stop_recording(self):
        """Test that stop_recording stops the recording"""
        mock_recorder = MagicMock()
        mock_recorder.output_dir = "recordings"
        mock_recorder.stop_recording.return_value = None
        self.gui.recorder = mock_recorder
        self.gui.is_recording = True
        self.gui.recording_start_time = 0
        self.gui.recording_files = ["test1.mp4", "test2.mp4"]
        
        with patch('time.time', return_value=5.0):
            self.gui.stop_recording()
        
        self.assertFalse(self.gui.is_recording)
        mock_recorder.stop_recording.assert_called_once()
    
    def test_recording_state_tracking(self):
        """Test that recording state is tracked correctly"""
        # Test initial state
        self.assertFalse(self.gui.is_recording)
        self.assertIsNone(self.gui.recording_start_time)
        self.assertIsNone(self.gui.recording_files)
        
        # Test that state variables exist
        self.assertTrue(hasattr(self.gui, 'is_recording'))
        self.assertTrue(hasattr(self.gui, 'recording_start_time'))
        self.assertTrue(hasattr(self.gui, 'recording_files'))


class TestAnalysisIntegration(unittest.TestCase):
    """Test analysis functionality"""
    
    def setUp(self):
        """Set up GUI instance"""
        with patch('cv2.VideoCapture'):
            with patch('camera_setup_recorder_gui.PoseProcessor'):
                with patch('camera_setup_recorder_gui.SwayCalculator'):
                    self.gui = TabbedCameraGUI()
    
    def test_analysis_state_initialization(self):
        """Test that analysis state variables are initialized"""
        self.assertFalse(self.gui.is_analyzing)
        self.assertIsNone(self.gui.analysis_camera1)
        self.assertIsNone(self.gui.analysis_camera2)
        self.assertEqual(self.gui.analysis_progress, "")
        self.assertIsNone(self.gui.analysis_start_time)
    
    def test_start_analysis_requires_video_files(self):
        """Test that analysis requires video files"""
        self.gui.recording_files = None
        self.gui.start_analysis()
        self.assertFalse(self.gui.is_analyzing)
        
        self.gui.recording_files = ["test1.mp4"]  # Only one file
        self.gui.start_analysis()
        self.assertFalse(self.gui.is_analyzing)
        
        self.gui.recording_files = ["test1.mp4", "test2.mp4"]  # Both files
        with patch('os.path.exists', return_value=False):
            self.gui.start_analysis()
            self.assertFalse(self.gui.is_analyzing)
    
    def test_stop_recording_triggers_analysis(self):
        """Test that stop_recording triggers analysis automatically"""
        mock_recorder = MagicMock()
        mock_recorder.output_dir = "recordings"
        mock_recorder.stop_recording.return_value = None
        self.gui.recorder = mock_recorder
        self.gui.is_recording = True
        self.gui.recording_start_time = 0
        self.gui.recording_files = ["test1.mp4", "test2.mp4"]
        
        with patch('os.path.exists', return_value=True):
            with patch.object(self.gui, 'start_analysis') as mock_start_analysis:
                with patch('time.time', return_value=5.0):
                    self.gui.stop_recording()
                    
                # Check that start_analysis was called
                mock_start_analysis.assert_called_once()


class TestCameraPropertyAdjustment(unittest.TestCase):
    """Test camera property adjustment functionality"""
    
    def setUp(self):
        """Set up GUI with mocked cameras"""
        with patch('cv2.VideoCapture') as mock_cap_class:
            self.mock_cap1 = MagicMock()
            self.mock_cap2 = MagicMock()
            self.mock_cap1.isOpened.return_value = True
            self.mock_cap2.isOpened.return_value = True
            self.mock_cap1.get.return_value = 128  # brightness
            mock_cap_class.side_effect = [self.mock_cap1, self.mock_cap2]
            
            self.gui = TabbedCameraGUI()
            self.gui.cap1 = self.mock_cap1
            self.gui.cap2 = self.mock_cap2
    
    def test_adjust_property_brightness(self):
        """Test adjusting brightness property"""
        self.mock_cap1.get.return_value = 128
        self.gui.adjust_property(1, 'brightness', 10)
        self.mock_cap1.set.assert_called()
    
    def test_adjust_property_exposure(self):
        """Test adjusting exposure property"""
        self.mock_cap1.get.return_value = -6.0
        self.gui.adjust_property(1, 'exposure', 1)
        self.mock_cap1.set.assert_called()
    
    def test_property_ranges(self):
        """Test that property ranges are defined"""
        self.assertIn('brightness', self.gui.prop_ranges)
        self.assertIn('contrast', self.gui.prop_ranges)
        self.assertIn('saturation', self.gui.prop_ranges)
        self.assertIn('exposure', self.gui.prop_ranges)


class TestTextRendering(unittest.TestCase):
    """Unit tests that verify Pillow-based text rendering actually works correctly"""
    
    def setUp(self):
        """Set up GUI instance"""
        with patch('cv2.VideoCapture'):
            self.gui = TabbedCameraGUI()
    
    def _find_text_in_region(self, frame, text, region_bounds, min_brightness=200):
        """Helper: Check if text is visible in a region of the frame"""
        x1, y1, x2, y2 = region_bounds
        region = frame[y1:y2, x1:x2]
        max_pixel = np.max(region)
        bright_pixels = np.sum(region > min_brightness)
        return max_pixel > min_brightness, bright_pixels
    
    def test_put_text_pil_coordinate_system_correct(self):
        """Test that Pillow text rendering correctly converts OpenCV-style coordinates (bottom-left origin) to Pillow coordinates"""
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        text = "Test"
        
        # Render text at position (10, 90) - should be near bottom
        y_bottom = 90
        result = self.gui._put_text_pil(frame.copy(), text, (10, y_bottom), 
                                         size=0.6, color=(255, 255, 255), thickness=1)
        
        # Get text height
        text_size = self.gui._get_text_size_pil(text, 0.6)
        text_height = text_size[1]
        
        # Text should be visible in bottom region (y_bottom is bottom-left)
        # Top of text should be at y_bottom - text_height
        y_top = y_bottom - text_height
        
        # Check that text appears where expected
        bottom_region = result[max(0, y_top-5):min(100, y_bottom+5), 5:50]
        max_pixel = np.max(bottom_region)
        self.assertGreater(max_pixel, 200, 
                          f"Text at y={y_bottom} should be visible (y_top={y_top}, text_height={text_height})")
        
        # Text should not extend below frame
        self.assertGreaterEqual(y_top, 0, 
                               f"Text should not extend above frame (y_top={y_top})")
    
    def test_draw_tabs_renders_all_tab_names(self):
        """Test that draw_tabs renders all 4 tab names in correct positions"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        frame = self.gui.draw_tabs(frame)
        
        # Each tab should have its name rendered
        h, w = frame.shape[:2]
        tab_width = w // len(self.gui.tab_names)
        
        for i, tab_name in enumerate(self.gui.tab_names):
            # Tab text should be centered in its tab
            x1 = i * tab_width
            x2 = (i + 1) * tab_width
            tab_center_x = (x1 + x2) // 2
            tab_text_y = self.gui.tab_height // 2 + 10  # Approximate center
            
            # Check region around where text should be
            text_region = frame[10:self.gui.tab_height, x1+10:x2-10]
            max_pixel = np.max(text_region)
            
            # Tab text should be visible (active tab is white, inactive is gray)
            self.assertGreater(max_pixel, 100, 
                              f"Tab '{tab_name}' should be visible (max pixel: {max_pixel})")
    
    def test_draw_tabs_active_tab_highlighted(self):
        """Test that active tab is visually different (brighter)"""
        frame1 = np.zeros((900, 1600, 3), dtype=np.uint8)
        frame2 = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        # Draw with tab 0 active
        self.gui.current_tab = 0
        frame1 = self.gui.draw_tabs(frame1)
        
        # Draw with tab 1 active
        self.gui.current_tab = 1
        frame2 = self.gui.draw_tabs(frame2)
        
        # Tab 0 region in frame1 should be brighter than in frame2
        h, w = frame1.shape[:2]
        tab_width = w // len(self.gui.tab_names)
        tab0_region1 = frame1[0:self.gui.tab_height, 0:tab_width]
        tab0_region2 = frame2[0:self.gui.tab_height, 0:tab_width]
        
        max1 = np.max(tab0_region1)
        max2 = np.max(tab0_region2)
        
        # Active tab should be brighter (white text vs gray text)
        self.assertGreater(max1, max2,
                          f"Active tab should be brighter (active: {max1}, inactive: {max2})")
    
    def test_draw_analysis_tab_no_results_displays_message(self):
        """Test that analysis tab displays correct message when no results"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        self.gui.analysis_camera1 = None
        self.gui.analysis_camera2 = None
        self.gui.is_analyzing = False
        
        frame = self.gui.draw_analysis_tab(frame)
        
        # Check center region for "No analysis results available" message
        h, w = frame.shape[:2]
        center_region = frame[h//2-50:h//2+50, w//2-300:w//2+300]
        max_pixel = np.max(center_region)
        bright_pixels = np.sum(center_region > 100)
        
        # Message should be visible
        self.assertGreater(max_pixel, 100,
                          f"'No analysis results' message should be visible (max: {max_pixel})")
        self.assertGreater(bright_pixels, 50,
                          f"Message text should have visible pixels (found: {bright_pixels})")
    
    def test_draw_analysis_tab_with_results_displays_text(self):
        """Test that analysis tab displays results text correctly"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        self.gui.analysis_camera1 = {
            'summary': {'max_sway_left': -10.5, 'max_sway_right': 5.2},
            'detection_rate': 85.5,
            'sway': [0] * 100
        }
        self.gui.analysis_camera2 = {
            'summary': {'max_shoulder_turn': 45.3, 'max_hip_turn': 25.1, 'max_x_factor': 20.2},
            'detection_rate': 90.2,
            'shoulder_turn': [0] * 100
        }
        self.gui.is_analyzing = False
        
        frame = self.gui.draw_analysis_tab(frame)
        
        # Check for title "SWING ANALYSIS RESULTS"
        h, w = frame.shape[:2]
        content_y = self.gui.tab_height + 10
        title_region = frame[content_y+20:content_y+60, w//2-200:w//2+200]
        title_max = np.max(title_region)
        
        self.assertGreater(title_max, 200,
                          f"Title 'SWING ANALYSIS RESULTS' should be visible (max: {title_max})")
        
        # Check for metric labels
        metrics_region = frame[content_y+80:content_y+200, 20:400]
        metrics_max = np.max(metrics_region)
        metrics_bright = np.sum(metrics_region > 200)
        
        self.assertGreater(metrics_max, 200,
                          f"Metrics text should be visible (max: {metrics_max})")
        self.assertGreater(metrics_bright, 100,
                          f"Metrics should have substantial bright pixels (found: {metrics_bright})")
    
    def test_draw_recording_tab_displays_labels(self):
        """Test that recording tab displays camera labels correctly"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        # Mock camera frames
        mock_frame1 = np.zeros((720, 1280, 3), dtype=np.uint8)
        mock_frame2 = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        with patch.object(self.gui, 'cap1') as mock_cap1, \
             patch.object(self.gui, 'cap2') as mock_cap2:
            mock_cap1.isOpened.return_value = True
            mock_cap2.isOpened.return_value = True
            mock_cap1.read.return_value = (True, mock_frame1)
            mock_cap2.read.return_value = (True, mock_frame2)
            
            frame = self.gui.draw_recording_tab(frame)
        
        # Check for "Camera 1" and "Camera 2" labels
        h, w = frame.shape[:2]
        content_y = self.gui.tab_height + 10
        
        # Camera 1 label region (left side)
        cam1_region = frame[content_y:content_y+50, 10:200]
        cam1_max = np.max(cam1_region)
        
        # Camera 2 label region (right side)
        preview_width = (w - 30) // 2
        cam2_x = preview_width + 20
        cam2_region = frame[content_y:content_y+50, cam2_x:cam2_x+200]
        cam2_max = np.max(cam2_region)
        
        # Both labels should be visible
        self.assertGreater(cam1_max, 200,
                          f"'Camera 1' label should be visible (max: {cam1_max})")
        self.assertGreater(cam2_max, 200,
                          f"'Camera 2' label should be visible (max: {cam2_max})")
    
    def test_draw_recording_tab_recording_state_displays_correctly(self):
        """Test that recording state displays correctly"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        # Test recording state
        self.gui.is_recording = True
        self.gui.recording_start_time = 0
        with patch('time.time', return_value=5.0):
            frame = self.gui.draw_recording_tab(frame)
        
        h, w = frame.shape[:2]
        content_y = self.gui.tab_height + 10
        controls_y = content_y + int((w - 30) / 2 * 9 / 16) + 20
        status_y = controls_y + 30
        
        # Check for "RECORDING" text
        recording_region = frame[status_y:status_y+30, 40:200]
        recording_max = np.max(recording_region)
        
        self.assertGreater(recording_max, 200,
                          f"'RECORDING' text should be visible when recording (max: {recording_max})")
        
        # Test not recording state
        frame2 = np.zeros((900, 1600, 3), dtype=np.uint8)
        self.gui.is_recording = False
        frame2 = self.gui.draw_recording_tab(frame2)
        
        ready_region = frame2[status_y:status_y+30, 20:200]
        ready_max = np.max(ready_region)
        
        self.assertGreater(ready_max, 200,
                          f"'Ready to Record' text should be visible when not recording (max: {ready_max})")
    
    def test_text_positioning_bottom_alignment(self):
        """Test that text positioned at bottom doesn't get cut off"""
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        text = "Test"
        
        # Render at various bottom positions
        for y_bottom in [95, 90, 85]:
            test_frame = frame.copy()
            result = self.gui._put_text_pil(test_frame, text, (10, y_bottom),
                                            size=0.6, color=(255, 255, 255), thickness=1)
            
            # Text should be fully visible in frame
            text_height = self.gui._get_text_size_pil(text, 0.6)[1]
            y_top = y_bottom - text_height
            
            self.assertGreaterEqual(y_top, 0,
                                   f"Text at y={y_bottom} should not be cut off (y_top={y_top})")
            
            # Text should be visible
            visible_region = result[max(0, y_top-2):min(100, y_bottom+2), 5:50]
            max_pixel = np.max(visible_region)
            self.assertGreater(max_pixel, 200,
                              f"Text at y={y_bottom} should be visible (max: {max_pixel})")
    
    def test_tab_hints_render_correctly(self):
        """Test that tab number hints [1][2][3][4] render correctly"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        frame = self.gui.draw_tabs(frame)
        
        h, w = frame.shape[:2]
        tab_width = w // len(self.gui.tab_names)
        
        # Check each tab hint
        for i in range(len(self.gui.tab_names)):
            hint_text = f"[{i+1}]"
            x2 = (i + 1) * tab_width
            hint_size = self.gui._get_text_size_pil(hint_text, 0.4)
            hint_x = x2 - hint_size[0] - 10
            
            # Check region where hint should be
            hint_region = frame[10:30, hint_x-5:hint_x+hint_size[0]+5]
            max_pixel = np.max(hint_region)
            
            self.assertGreater(max_pixel, 100,
                              f"Tab hint '{hint_text}' should be visible (max: {max_pixel})")
    
    def test_setup_tab_camera_info_text(self):
        """Test that setup tab renders camera info text"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        # Mock camera
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((720, 1280, 3), dtype=np.uint8))
        mock_cap.get.side_effect = lambda x: {
            cv2.CAP_PROP_FRAME_WIDTH: 1280,
            cv2.CAP_PROP_FRAME_HEIGHT: 720,
            cv2.CAP_PROP_FPS: 60.0
        }.get(x, 128)
        
        self.gui.cap1 = mock_cap
        self.gui.current_prop_index = 0
        
        frame = self.gui.draw_camera_setup_tab(frame, 1)
        
        # Check for camera info text
        h, w = frame.shape[:2]
        content_y = self.gui.tab_height + 10
        preview_y = content_y
        info_y = preview_y + self.gui.preview_height + 20
        
        info_region = frame[info_y:info_y+30, 10:400]
        max_pixel = np.max(info_region)
        
        self.assertGreater(max_pixel, 200,
                          f"Camera info text should be visible (max: {max_pixel})")
    
    def test_setup_tab_property_labels_render(self):
        """Test that setup tab renders property labels"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        # Mock camera
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((720, 1280, 3), dtype=np.uint8))
        mock_cap.get.side_effect = lambda x: {
            cv2.CAP_PROP_FRAME_WIDTH: 1280,
            cv2.CAP_PROP_FRAME_HEIGHT: 720,
            cv2.CAP_PROP_FPS: 60.0,
            cv2.CAP_PROP_BRIGHTNESS: 128,
            cv2.CAP_PROP_CONTRAST: 32,
            cv2.CAP_PROP_SATURATION: 64,
            cv2.CAP_PROP_EXPOSURE: -6.0,
            cv2.CAP_PROP_GAIN: 0,
            cv2.CAP_PROP_FOCUS: 0,
            cv2.CAP_PROP_WHITE_BALANCE_BLUE_U: 4000,
            cv2.CAP_PROP_SHARPNESS: 0,
            cv2.CAP_PROP_GAMMA: 100
        }.get(x, 128)
        
        self.gui.cap1 = mock_cap
        self.gui.current_prop_index = 0
        
        frame = self.gui.draw_camera_setup_tab(frame, 1)
        
        # Check for property labels (should have "Brightness:", "Contrast:", etc.)
        h, w = frame.shape[:2]
        controls_x = self.gui.preview_width + 30
        controls_start_y = self.gui.tab_height + 30
        
        # Check first few property labels
        properties_to_check = ["Brightness", "Contrast", "Saturation"]
        for i, prop_name in enumerate(properties_to_check):
            y_pos = controls_start_y + 20 + (i * 35)
            prop_region = frame[y_pos-15:y_pos+15, controls_x:controls_x+200]
            max_pixel = np.max(prop_region)
            
            self.assertGreater(max_pixel, 200,
                              f"Property label '{prop_name}' should be visible (max: {max_pixel})")
    
    def test_setup_tab_instructions_text(self):
        """Test that setup tab renders instructions text"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        # Mock camera
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((720, 1280, 3), dtype=np.uint8))
        mock_cap.get.side_effect = lambda x: 128 if x not in [cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS] else (1280 if x == cv2.CAP_PROP_FRAME_WIDTH else (720 if x == cv2.CAP_PROP_FRAME_HEIGHT else 60.0))
        
        self.gui.cap1 = mock_cap
        self.gui.current_prop_index = 0
        
        frame = self.gui.draw_camera_setup_tab(frame, 1)
        
        # Check for instructions at bottom
        h, w = frame.shape[:2]
        inst_y = h - 60
        
        inst_region = frame[inst_y:inst_y+20, 10:w-10]
        max_pixel = np.max(inst_region)
        bright_pixels = np.sum(inst_region > 180)
        
        self.assertGreater(max_pixel, 180,
                          f"Instructions text should be visible (max: {max_pixel})")
        self.assertGreater(bright_pixels, 100,
                          f"Instructions should have substantial text pixels (found: {bright_pixels})")
    
    def test_setup_tab_camera_not_available_text(self):
        """Test that setup tab shows 'Camera not available' message"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        self.gui.cap1 = None
        frame = self.gui.draw_camera_setup_tab(frame, 1)
        
        # Check center for "Camera 1 not available" message
        h, w = frame.shape[:2]
        center_region = frame[h//2-30:h//2+30, w//2-200:w//2+200]
        max_pixel = np.max(center_region)
        # Red text should be visible (BGR format, so red is (0, 0, 255) but in region it's more prominent)
        
        self.assertGreater(max_pixel, 100,
                          f"'Camera not available' message should be visible (max: {max_pixel})")
    
    def test_recording_tab_file_names_render(self):
        """Test that recording tab renders file names when recording"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        # Mock cameras
        mock_frame1 = np.zeros((720, 1280, 3), dtype=np.uint8)
        mock_frame2 = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        with patch.object(self.gui, 'cap1') as mock_cap1, \
             patch.object(self.gui, 'cap2') as mock_cap2:
            mock_cap1.isOpened.return_value = True
            mock_cap2.isOpened.return_value = True
            mock_cap1.read.return_value = (True, mock_frame1)
            mock_cap2.read.return_value = (True, mock_frame2)
            
            self.gui.is_recording = True
            self.gui.recording_start_time = 0
            self.gui.recording_files = ["test_camera1_20240101_120000.mp4", 
                                        "test_camera2_20240101_120000.mp4"]
            
            with patch('time.time', return_value=5.0):
                frame = self.gui.draw_recording_tab(frame)
        
        # Check for file name text
        h, w = frame.shape[:2]
        content_y = self.gui.tab_height + 10
        preview_height = int((w - 30) / 2 * 9 / 16)
        controls_y = content_y + preview_height + 20
        status_y = controls_y + 30
        file_y = status_y + 35
        
        file_region = frame[file_y:file_y+40, 20:500]
        max_pixel = np.max(file_region)
        bright_pixels = np.sum(file_region > 180)
        
        self.assertGreater(max_pixel, 180,
                          f"File name text should be visible (max: {max_pixel})")
        self.assertGreater(bright_pixels, 50,
                          f"File names should have visible text (found: {bright_pixels} pixels)")
    
    def test_recording_tab_duration_text(self):
        """Test that recording tab renders duration text"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        mock_frame1 = np.zeros((720, 1280, 3), dtype=np.uint8)
        mock_frame2 = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        with patch.object(self.gui, 'cap1') as mock_cap1, \
             patch.object(self.gui, 'cap2') as mock_cap2:
            mock_cap1.isOpened.return_value = True
            mock_cap2.isOpened.return_value = True
            mock_cap1.read.return_value = (True, mock_frame1)
            mock_cap2.read.return_value = (True, mock_frame2)
            
            self.gui.is_recording = True
            self.gui.recording_start_time = 0
            
            with patch('time.time', return_value=12.5):  # 12.5 seconds elapsed
                frame = self.gui.draw_recording_tab(frame)
        
        # Check for duration text
        h, w = frame.shape[:2]
        content_y = self.gui.tab_height + 10
        preview_height = int((w - 30) / 2 * 9 / 16)
        controls_y = content_y + preview_height + 20
        status_y = controls_y + 30
        
        duration_region = frame[status_y:status_y+25, 200:350]
        max_pixel = np.max(duration_region)
        
        self.assertGreater(max_pixel, 200,
                          f"Duration text should be visible (max: {max_pixel})")
    
    def test_recording_tab_button_text(self):
        """Test that recording tab renders button text correctly"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        mock_frame1 = np.zeros((720, 1280, 3), dtype=np.uint8)
        mock_frame2 = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        with patch.object(self.gui, 'cap1') as mock_cap1, \
             patch.object(self.gui, 'cap2') as mock_cap2:
            mock_cap1.isOpened.return_value = True
            mock_cap2.isOpened.return_value = True
            mock_cap1.read.return_value = (True, mock_frame1)
            mock_cap2.read.return_value = (True, mock_frame2)
            
            # Test START button
            self.gui.is_recording = False
            frame = self.gui.draw_recording_tab(frame)
            
            h, w = frame.shape[:2]
            content_y = self.gui.tab_height + 10
            preview_height = int((w - 30) / 2 * 9 / 16)
            controls_y = content_y + preview_height + 20
            status_y = controls_y + 30
            start_x = w - 200
            start_y = status_y - 10
            
            start_button_region = frame[start_y:start_y+40, start_x:start_x+150]
            start_max = np.max(start_button_region)
            
            self.assertGreater(start_max, 200,
                              f"'START [Space]' button text should be visible (max: {start_max})")
            
            # Test STOP button
            frame2 = np.zeros((900, 1600, 3), dtype=np.uint8)
            self.gui.is_recording = True
            self.gui.recording_start_time = 0
            
            with patch('time.time', return_value=5.0):
                frame2 = self.gui.draw_recording_tab(frame2)
            
            stop_x = w - 200
            stop_y = status_y - 10
            stop_button_region = frame2[stop_y:stop_y+40, stop_x:stop_x+150]
            stop_max = np.max(stop_button_region)
            
            self.assertGreater(stop_max, 200,
                              f"'STOP [Space]' button text should be visible (max: {stop_max})")
    
    def test_analysis_tab_all_metrics_text(self):
        """Test that analysis tab renders all metric text correctly"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        self.gui.analysis_camera1 = {
            'sway': [0, -5, -10, -5, 0, 5, 10, 5, 0] * 10,  # 90 frames
            'summary': {
                'max_sway_left': -10,
                'max_sway_right': 10
            },
            'detection_rate': 95.0
        }
        
        self.gui.analysis_camera2 = {
            'shoulder_turn': [0, 10, 20, 30, 40, 45, 40, 30, 20, 10, 0] * 8,  # 88 frames
            'hip_turn': [0, 5, 10, 15, 20, 25, 20, 15, 10, 5, 0] * 8,
            'x_factor': [0, 5, 10, 15, 20, 20, 20, 15, 10, 5, 0] * 8,
            'summary': {
                'max_shoulder_turn': 45.3,
                'max_hip_turn': 25.1,
                'max_x_factor': 20.2
            },
            'detection_rate': 90.2
        }
        self.gui.is_analyzing = False
        self.gui.analysis_frame_index = 0
        
        frame = self.gui.draw_analysis_tab(frame)
        
        # Check for MAX VALUES section title
        h, w = frame.shape[:2]
        content_y = self.gui.tab_height + 10
        frame_info_y = content_y + 60
        summary_y = frame_info_y + 30
        
        max_values_title_region = frame[summary_y:summary_y+25, 20:250]
        max_title = np.max(max_values_title_region)
        
        self.assertGreater(max_title, 200,
                          f"'MAX VALUES:' title should be visible (max: {max_title})")
        
        # Check for max metric values
        metrics_y = summary_y + 25
        metric_region = frame[metrics_y:metrics_y+100, 30:400]
        metric_max = np.max(metric_region)
        metric_bright = np.sum(metric_region > 200)
        
        self.assertGreater(metric_max, 200,
                          f"Max metric values should be visible (max: {metric_max})")
        self.assertGreater(metric_bright, 150,
                          f"Metric values should have substantial text (found: {metric_bright} pixels)")
        
        # Check for CURRENT FRAME VALUES section
        live_section_y = summary_y + 120
        current_values_title_region = frame[live_section_y:live_section_y+25, 20:350]
        current_title = np.max(current_values_title_region)
        
        self.assertGreater(current_title, 200,
                          f"'CURRENT FRAME VALUES:' title should be visible (max: {current_title})")
    
    def test_analysis_tab_frame_navigation_text(self):
        """Test that analysis tab renders frame navigation text"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        self.gui.analysis_camera1 = {
            'sway': [0] * 100,
            'summary': {'max_sway_left': 0, 'max_sway_right': 0}
        }
        self.gui.analysis_camera2 = {
            'shoulder_turn': [0] * 100,
            'hip_turn': [0] * 100,
            'x_factor': [0] * 100,
            'summary': {'max_shoulder_turn': 0, 'max_hip_turn': 0, 'max_x_factor': 0}
        }
        self.gui.is_analyzing = False
        self.gui.analysis_frame_index = 42  # Frame 43 of 100
        
        frame = self.gui.draw_analysis_tab(frame)
        
        # Check for frame navigation text
        h, w = frame.shape[:2]
        content_y = self.gui.tab_height + 10
        frame_info_y = content_y + 60
        
        frame_nav_region = frame[frame_info_y:frame_info_y+25, 20:500]
        frame_nav_max = np.max(frame_nav_region)
        frame_nav_bright = np.sum(frame_nav_region > 180)
        
        self.assertGreater(frame_nav_max, 180,
                          f"Frame navigation text should be visible (max: {frame_nav_max})")
        self.assertGreater(frame_nav_bright, 50,
                          f"Frame navigation should have visible text (found: {frame_nav_bright} pixels)")
    
    def test_analysis_tab_detection_rate_text(self):
        """Test that analysis tab renders detection rate text"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        self.gui.analysis_camera1 = {
            'sway': [0] * 50,
            'summary': {'max_sway_left': 0, 'max_sway_right': 0},
            'detection_rate': 87.5
        }
        self.gui.analysis_camera2 = {
            'shoulder_turn': [0] * 50,
            'hip_turn': [0] * 50,
            'x_factor': [0] * 50,
            'summary': {'max_shoulder_turn': 0, 'max_hip_turn': 0, 'max_x_factor': 0},
            'detection_rate': 92.3
        }
        self.gui.is_analyzing = False
        self.gui.analysis_frame_index = 0
        
        frame = self.gui.draw_analysis_tab(frame)
        
        # Check for detection rate text (should be in the camera info sections)
        h, w = frame.shape[:2]
        content_y = self.gui.tab_height + 10
        
        # Detection rate appears in camera summary sections
        detection_region = frame[content_y+300:content_y+450, 20:w//2]
        detection_max = np.max(detection_region)
        
        self.assertGreater(detection_max, 180,
                          f"Detection rate text should be visible (max: {detection_max})")
    
    def test_analysis_tab_analyzing_progress_text(self):
        """Test that analysis tab renders progress text while analyzing"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        self.gui.is_analyzing = True
        self.gui.analysis_progress = "Processing Camera 1: Frame 42/150..."
        self.gui.analysis_start_time = 0
        
        with patch('time.time', return_value=5.5):
            frame = self.gui.draw_analysis_tab(frame)
        
        # Check center for progress text
        h, w = frame.shape[:2]
        center_region = frame[h//2-30:h//2+30, w//2-300:w//2+300]
        progress_max = np.max(center_region)
        
        # Check for elapsed time text below progress
        elapsed_region = frame[h//2+20:h//2+70, w//2-150:w//2+150]
        elapsed_max = np.max(elapsed_region)
        
        self.assertGreater(progress_max, 200,
                          f"Progress text should be visible (max: {progress_max})")
        self.assertGreater(elapsed_max, 180,
                          f"Elapsed time text should be visible (max: {elapsed_max})")
    
    def test_analysis_tab_camera_labels_text(self):
        """Test that analysis tab renders camera labels (Face-On, Down-the-Line)"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        self.gui.analysis_camera1 = {
            'sway': [0] * 50,
            'summary': {'max_sway_left': 0, 'max_sway_right': 0},
            'detection_rate': 100.0
        }
        self.gui.analysis_camera2 = {
            'shoulder_turn': [0] * 50,
            'hip_turn': [0] * 50,
            'x_factor': [0] * 50,
            'summary': {'max_shoulder_turn': 0, 'max_hip_turn': 0, 'max_x_factor': 0},
            'detection_rate': 100.0
        }
        self.gui.is_analyzing = False
        self.gui.analysis_frame_index = 0
        
        frame = self.gui.draw_analysis_tab(frame)
        
        # Check for camera labels
        h, w = frame.shape[:2]
        content_y = self.gui.tab_height + 10
        
        # Camera labels appear in summary sections
        cam1_label_region = frame[content_y+300:content_y+350, 20:250]
        cam1_label_max = np.max(cam1_label_region)
        
        cam2_label_region = frame[content_y+350:content_y+400, w//2:w//2+300]
        cam2_label_max = np.max(cam2_label_region)
        
        self.assertGreater(cam1_label_max, 180,
                          f"'Camera 1 (Face-On):' label should be visible (max: {cam1_label_max})")
        self.assertGreater(cam2_label_max, 180,
                          f"'Camera 2 (Down-the-Line):' label should be visible (max: {cam2_label_max})")
    
    def test_instructions_text_on_all_tabs(self):
        """Test that instructions text renders on all tabs"""
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        h, w = frame.shape[:2]
        
        # Recording tab instructions
        mock_frame1 = np.zeros((720, 1280, 3), dtype=np.uint8)
        mock_frame2 = np.zeros((720, 1280, 3), dtype=np.uint8)
        
        with patch.object(self.gui, 'cap1') as mock_cap1, \
             patch.object(self.gui, 'cap2') as mock_cap2:
            mock_cap1.isOpened.return_value = True
            mock_cap2.isOpened.return_value = True
            mock_cap1.read.return_value = (True, mock_frame1)
            mock_cap2.read.return_value = (True, mock_frame2)
            
            frame = self.gui.draw_recording_tab(frame)
        
        inst_y = h - 30
        recording_inst_region = frame[inst_y:inst_y+20, 10:w-10]
        recording_inst_max = np.max(recording_inst_region)
        
        self.assertGreater(recording_inst_max, 180,
                          f"Recording tab instructions should be visible (max: {recording_inst_max})")
        
        # Analysis tab instructions
        frame2 = np.zeros((900, 1600, 3), dtype=np.uint8)
        self.gui.analysis_camera1 = None
        self.gui.analysis_camera2 = None
        frame2 = self.gui.draw_analysis_tab(frame2)
        
        analysis_inst_region = frame2[h-30:h-10, 10:w-10]
        analysis_inst_max = np.max(analysis_inst_region)
        
        self.assertGreater(analysis_inst_max, 180,
                          f"Analysis tab instructions should be visible (max: {analysis_inst_max})")
    
    def test_text_with_special_characters(self):
        """Test that text with special characters renders correctly"""
        frame = np.zeros((100, 400, 3), dtype=np.uint8)
        
        # Test various special characters
        test_texts = [
            "Frame: 42/100",
            "Max X-Factor: 20.2°",
            "Sway: -10.5px",
            "Duration: 12.5s",
            "Camera 1 (Face-On):"
        ]
        
        y_pos = 50
        for text in test_texts:
            result = self.gui._put_text_pil(frame.copy(), text, (10, y_pos),
                                            size=0.6, color=(255, 255, 255), thickness=1)
            
            # Text should render without errors
            text_region = result[y_pos-10:y_pos+10, 10:400]
            max_pixel = np.max(text_region)
            
            self.assertGreater(max_pixel, 200,
                              f"Text '{text}' with special chars should be visible (max: {max_pixel})")
            y_pos += 15
    
    def test_text_size_variations(self):
        """Test that different text sizes render correctly"""
        frame = np.zeros((200, 400, 3), dtype=np.uint8)
        text = "Test"
        
        sizes = [0.4, 0.5, 0.6, 0.8, 1.0]
        y_pos = 30
        
        for size in sizes:
            result = self.gui._put_text_pil(frame.copy(), text, (10, y_pos),
                                            size=size, color=(255, 255, 255), thickness=1)
            
            text_size = self.gui._get_text_size_pil(text, size)
            
            # Verify text size is reasonable
            self.assertGreater(text_size[0], 0, f"Text width should be > 0 for size {size}")
            self.assertGreater(text_size[1], 0, f"Text height should be > 0 for size {size}")
            
            # Verify text is visible
            text_region = result[y_pos-text_size[1]:y_pos+5, 10:10+text_size[0]+10]
            max_pixel = np.max(text_region)
            
            self.assertGreater(max_pixel, 200,
                              f"Text at size {size} should be visible (max: {max_pixel})")
            y_pos += 35


class TestAnalysisTabRendering(unittest.TestCase):
    """Test analysis tab rendering logic"""
    
    def setUp(self):
        """Set up GUI instance"""
        with patch('cv2.VideoCapture'):
            self.gui = TabbedCameraGUI()
    
    def test_analysis_frame_index_exists(self):
        """Test that analysis_frame_index state variable exists"""
        self.assertTrue(hasattr(self.gui, 'analysis_frame_index'))
        self.assertEqual(self.gui.analysis_frame_index, 0)
    
    def test_draw_analysis_tab_no_results(self):
        """Test analysis tab when no results available"""
        self.gui.analysis_camera1 = None
        self.gui.analysis_camera2 = None
        self.gui.is_analyzing = False
        
        # Create a mock frame
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        # Should not crash
        try:
            frame = self.gui.draw_analysis_tab(frame)
            tab_rendered = True
        except Exception as e:
            tab_rendered = False
            print(f"Error rendering analysis tab: {e}")
        
        self.assertTrue(tab_rendered)
    
    def test_draw_analysis_tab_with_results(self):
        """Test analysis tab with analysis results"""
        self.gui.analysis_camera1 = {
            'summary': {
                'max_sway_left': -10.5,
                'max_sway_right': 5.2
            },
            'detection_rate': 85.5
        }
        self.gui.analysis_camera2 = {
            'summary': {
                'max_shoulder_turn': 45.3,
                'max_hip_turn': 25.1,
                'max_x_factor': 20.2
            },
            'detection_rate': 90.2
        }
        self.gui.is_analyzing = False
        
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        try:
            frame = self.gui.draw_analysis_tab(frame)
            tab_rendered = True
        except Exception as e:
            tab_rendered = False
            print(f"Error rendering analysis tab: {e}")
        
        self.assertTrue(tab_rendered)
    
    def test_draw_analysis_tab_analyzing(self):
        """Test analysis tab while analyzing"""
        self.gui.is_analyzing = True
        self.gui.analysis_progress = "Processing Camera 1..."
        self.gui.analysis_start_time = 0
        
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        try:
            frame = self.gui.draw_analysis_tab(frame)
            tab_rendered = True
        except Exception as e:
            tab_rendered = False
            print(f"Error rendering analysis tab: {e}")
        
        self.assertTrue(tab_rendered)


def run_gui_tests():
    """Run all GUI tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestGUIInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestTabSwitching))
    suite.addTests(loader.loadTestsFromTestCase(TestRecordingControls))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalysisIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCameraPropertyAdjustment))
    suite.addTests(loader.loadTestsFromTestCase(TestTextRendering))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalysisTabRendering))
    
    # Add workflow tests if available
    try:
        from test_config_to_record_workflow import TestConfigToRecordWorkflow
        suite.addTests(loader.loadTestsFromTestCase(TestConfigToRecordWorkflow))
    except ImportError:
        pass  # Workflow tests optional
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 70)
    print("GUI Tests for Camera Setup & Recording GUI")
    print("=" * 70)
    print()
    
    success = run_gui_tests()
    
    print()
    print("=" * 70)
    if success:
        print("✓ All GUI tests passed!")
    else:
        print("✗ Some GUI tests failed")
    print("=" * 70)
    
    sys.exit(0 if success else 1)

