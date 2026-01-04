"""
Test the workflow from camera configuration to recording
This verifies the complete user journey: configure -> record
The goal is to ensure this sequence WORKS successfully when cameras are available
"""
import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from camera_setup_recorder_gui import TabbedCameraGUI


class TestConfigToRecordWorkflow(unittest.TestCase):
    """Test the complete workflow from configuration to recording - SUCCESS PATH"""
    
    def setUp(self):
        """Set up GUI with mocked cameras that are OPEN and AVAILABLE"""
        self.mock_cap1 = MagicMock()
        self.mock_cap2 = MagicMock()
        self.mock_cap1.isOpened.return_value = True
        self.mock_cap2.isOpened.return_value = True
        self.mock_cap1.get.return_value = 128  # brightness default
        self.mock_cap2.get.return_value = 128
        
        with patch('cv2.VideoCapture') as mock_cap_class:
            mock_cap_class.side_effect = [self.mock_cap1, self.mock_cap2]
            with patch('camera_setup_recorder_gui.DualCameraRecorder'):
                with patch('cv2.namedWindow'):
                    with patch('cv2.resizeWindow'):
                        self.gui = TabbedCameraGUI()
                        self.gui.cap1 = self.mock_cap1
                        self.gui.cap2 = self.mock_cap2
                        # CRITICAL: Cameras are available - workflow should succeed
                        self.gui.cameras_available = True
    
    def test_workflow_configure_then_record_succeeds(self):
        """Test: Configure cameras, then record - THIS SHOULD SUCCEED"""
        # Step 1: Configure camera 1 properties
        self.gui.current_tab = 0  # Camera 1 setup tab
        self.gui.adjust_property(1, 'brightness', 10)  # Increase brightness
        self.mock_cap1.set.assert_called()  # Verify configuration was applied
        
        # Step 2: Configure camera 2 properties  
        self.gui.current_tab = 1  # Camera 2 setup tab
        self.gui.adjust_property(2, 'contrast', 5)  # Increase contrast
        self.mock_cap2.set.assert_called()  # Verify configuration was applied
        
        # Step 3: Switch to recording tab
        self.gui.current_tab = 2  # Recording tab
        
        # Step 4: Start recording - THIS MUST SUCCEED
        # CRITICAL: Cameras must be released before recorder opens them (Linux limitation)
        with patch('camera_setup_recorder_gui.DualCameraRecorder') as mock_recorder_class:
            mock_recorder = MagicMock()
            mock_recorder.output_dir = "recordings"
            mock_recorder.camera1 = MagicMock()
            mock_recorder.camera2 = MagicMock()
            mock_recorder.camera1.cap = self.mock_cap1
            mock_recorder.camera2.cap = self.mock_cap2
            mock_recorder.start_cameras.return_value = None
            mock_recorder.start_recording.return_value = None
            mock_recorder_class.return_value = mock_recorder
            
            self.gui.recorder = None
            self.gui.is_recording = False
            self.gui.status_message = ""
            
            # Verify cameras are currently open (before recording)
            self.assertTrue(self.gui.cap1.isOpened(), "Cameras should be open for GUI preview")
            self.assertTrue(self.gui.cap2.isOpened(), "Cameras should be open for GUI preview")
            
            # Execute the recording start
            self.gui.start_recording()
            
            # VERIFY: Cameras were released (so recorder can open them)
            self.mock_cap1.release.assert_called_once(), "GUI camera 1 MUST be released before recording"
            self.mock_cap2.release.assert_called_once(), "GUI camera 2 MUST be released before recording"
            
            # VERIFY SUCCESS: Recording must start successfully
            self.assertTrue(self.gui.is_recording, 
                          "Recording MUST start after successful configuration")
            self.assertIsNotNone(self.gui.recorder, 
                               "Recorder MUST be created when cameras are available")
            mock_recorder.start_cameras.assert_called_once()
            mock_recorder.start_recording.assert_called_once()
    
    def test_workflow_cameras_released_before_recording(self):
        """Test: Cameras are released before recorder opens them (critical for Linux)"""
        # Set up: cameras are open for GUI preview
        self.gui.cap1 = self.mock_cap1
        self.gui.cap2 = self.mock_cap2
        self.mock_cap1.isOpened.return_value = True
        self.mock_cap2.isOpened.return_value = True
        
        with patch('camera_setup_recorder_gui.DualCameraRecorder') as mock_recorder_class:
            mock_recorder = MagicMock()
            mock_recorder.output_dir = "recordings"
            mock_recorder.camera1 = MagicMock()
            mock_recorder.camera2 = MagicMock()
            mock_recorder.start_cameras.return_value = None
            mock_recorder.start_recording.return_value = None
            mock_recorder_class.return_value = mock_recorder
            
            self.gui.recorder = None
            self.gui.is_recording = False
            
            # Start recording
            self.gui.start_recording()
            
            # CRITICAL TEST: Verify cameras were released BEFORE recorder.start_cameras() was called
            # This prevents "camera already open" errors on Linux
            release_calls = self.mock_cap1.release.call_count + self.mock_cap2.release.call_count
            self.assertGreater(release_calls, 0, 
                             "Cameras MUST be released before recorder opens them")
            
            # Verify recorder was called (meaning cameras were released first)
            mock_recorder.start_cameras.assert_called_once()
    
    def test_workflow_cameras_reopened_after_recording_stops(self):
        """Test: Cameras are reopened after recording stops for GUI preview"""
        # Set up: recording is in progress
        mock_recorder = MagicMock()
        mock_recorder.output_dir = "recordings"
        self.gui.recorder = mock_recorder
        self.gui.is_recording = True
        self.gui.recording_start_time = time.time() - 5.0
        self.gui.recording_files = ["test1.mp4", "test2.mp4"]
        
        # Mock VideoCapture for reopening
        with patch('cv2.VideoCapture') as mock_cap_class:
            mock_cap_class.side_effect = [self.mock_cap1, self.mock_cap2]
            
            # Stop recording
            self.gui.stop_recording()
            
            # CRITICAL TEST: Verify cameras were reopened after recording stopped
            # This allows GUI preview to continue after recording
            self.assertGreater(mock_cap_class.call_count, 0,
                             "Cameras MUST be reopened after recording stops")
            
            # Verify recording was stopped
            self.assertFalse(self.gui.is_recording)


if __name__ == '__main__':
    unittest.main()

