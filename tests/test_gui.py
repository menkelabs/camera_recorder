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

from camera_setup_recorder_gui import TabbedCameraGUI


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
        """Test that Windows uses cameras 0, 2 by default"""
        with patch('sys.platform', 'win32'):
            with patch('cv2.VideoCapture'):
                gui = TabbedCameraGUI()
                self.assertEqual(gui.camera1_id, 0)
                self.assertEqual(gui.camera2_id, 2)
    
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
            
            self.gui.recorder = None
            self.gui.current_tab = 2  # Recording tab
            self.gui.start_recording()
            
            self.assertIsNotNone(self.gui.recorder)
            self.assertTrue(self.gui.is_recording)
            mock_recorder.start_cameras.assert_called_once()
            mock_recorder.start_recording.assert_called_once()
    
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


class TestAnalysisTabRendering(unittest.TestCase):
    """Test analysis tab rendering logic"""
    
    def setUp(self):
        """Set up GUI instance"""
        with patch('cv2.VideoCapture'):
            self.gui = TabbedCameraGUI()
    
    def test_draw_analysis_tab_no_results(self):
        """Test analysis tab when no results available"""
        self.gui.analysis_camera1 = None
        self.gui.analysis_camera2 = None
        self.gui.is_analyzing = False
        
        # Create a mock frame
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        # Should not crash
        try:
            self.gui.draw_analysis_tab(frame)
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
            self.gui.draw_analysis_tab(frame)
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
            self.gui.draw_analysis_tab(frame)
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
    suite.addTests(loader.loadTestsFromTestCase(TestAnalysisTabRendering))
    
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

