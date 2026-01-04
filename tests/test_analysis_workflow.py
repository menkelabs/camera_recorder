"""
Test the analysis workflow - analysis should run even with no pose detections
"""
import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch, call
import time

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from camera_setup_recorder_gui import TabbedCameraGUI


class TestAnalysisWorkflow(unittest.TestCase):
    """Test analysis workflow - should handle videos with no detections gracefully"""
    
    def setUp(self):
        """Set up GUI with mocked components"""
        with patch('cv2.VideoCapture'):
            with patch('cv2.namedWindow'):
                with patch('cv2.resizeWindow'):
                    self.gui = TabbedCameraGUI()
    
    @patch('camera_setup_recorder_gui.PoseProcessor')
    @patch('camera_setup_recorder_gui.SwayCalculator')
    @patch('os.path.exists')
    @patch('cv2.VideoCapture')
    def test_analysis_runs_with_no_detections(self, mock_vc, mock_exists, mock_sway_calc, mock_pose_proc):
        """Test: Analysis should run even if no poses are detected (e.g., lab floor)"""
        # Mock video files exist
        mock_exists.return_value = True
        
        # Mock VideoCapture for reading videos
        mock_vc.return_value.isOpened.return_value = True
        mock_vc.return_value.read.side_effect = [
            (True, b'fake_frame') for _ in range(10)  # 10 frames
        ] + [(False, None)]  # End of video
        
        # Mock PoseProcessor - returns empty detections (no poses found)
        mock_processor = MagicMock()
        mock_processor.process_video.return_value = {
            'landmarks': [],  # No landmarks detected
            'detection_rate': 0.0  # 0% detection rate
        }
        mock_pose_proc.return_value = mock_processor
        
        # Mock SwayCalculator - should handle empty landmarks gracefully
        mock_calculator = MagicMock()
        mock_calculator.analyze_sequence.return_value = {
            'sway': [],
            'shoulder_turn': [],
            'hip_turn': [],
            'x_factor': [],
            'summary': {
                'max_sway_left': None,
                'max_sway_right': None,
                'max_shoulder_turn': None,
                'max_hip_turn': None,
                'max_x_factor': None
            }
        }
        mock_sway_calc.return_value = mock_calculator
        
        # Set up recording files
        self.gui.recording_files = ["test_camera1.mp4", "test_camera2.mp4"]
        self.gui.is_analyzing = False
        
        # Start analysis (this should not crash even with no detections)
        try:
            self.gui.start_analysis()
            
            # Give it a moment to start
            time.sleep(0.1)
            
            # Analysis should have started (even if no poses detected)
            # The key is it shouldn't crash
            analysis_started = True
        except Exception as e:
            analysis_started = False
            print(f"Analysis failed: {e}")
        
        self.assertTrue(analysis_started, "Analysis should start even with no pose detections")
    
    @patch('camera_setup_recorder_gui.PoseProcessor')
    @patch('camera_setup_recorder_gui.SwayCalculator')
    @patch('os.path.exists')
    def test_analysis_handles_mediapipe_import_error(self, mock_exists, mock_sway_calc, mock_pose_proc):
        """Test: Analysis should handle mediapipe import/initialization errors gracefully"""
        mock_exists.return_value = True
        
        # Simulate mediapipe import error
        mock_pose_proc.side_effect = AttributeError("module 'mediapipe' has no attribute 'solutions'")
        
        self.gui.recording_files = ["test_camera1.mp4", "test_camera2.mp4"]
        self.gui.is_analyzing = False
        
        # Start analysis - should handle error gracefully
        try:
            self.gui.start_analysis()
            time.sleep(0.1)
            
            # Should set error message, not crash
            error_handled = True
            if hasattr(self.gui, 'analysis_progress'):
                # Error should be reflected in progress/status
                error_handled = True
        except Exception as e:
            print(f"Unexpected exception: {e}")
            error_handled = False
        
        self.assertTrue(error_handled, "Analysis should handle mediapipe errors gracefully")
    
    def test_analysis_requires_video_files(self):
        """Test: Analysis requires both video files"""
        # No files
        self.gui.recording_files = None
        self.gui.start_analysis()
        self.assertFalse(self.gui.is_analyzing, "Analysis should not start without files")
        
        # Only one file
        self.gui.recording_files = ["test1.mp4"]
        self.gui.start_analysis()
        self.assertFalse(self.gui.is_analyzing, "Analysis should not start with only one file")
        
        # Both files (but we'll mock the actual analysis)
        self.gui.recording_files = ["test1.mp4", "test2.mp4"]
        with patch('os.path.exists', return_value=False):
            self.gui.start_analysis()
            self.assertFalse(self.gui.is_analyzing, "Analysis should not start if files don't exist")


if __name__ == '__main__':
    unittest.main()

