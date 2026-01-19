import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json
import tempfile

# Add scripts folder to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import configure_cameras

class TestConfigureCameras(unittest.TestCase):
    
    @patch('cv2.VideoCapture')
    def test_test_camera_working(self, mock_capture):
        # Setup mock camera
        mock_cap = MagicMock()
        mock_capture.return_value = mock_cap
        
        # Configure mock behavior
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, MagicMock()) # Success, frame
        
        # Mock properties
        def get_prop(prop_id):
            if prop_id == configure_cameras.cv2.CAP_PROP_FRAME_WIDTH: return 1280
            if prop_id == configure_cameras.cv2.CAP_PROP_FRAME_HEIGHT: return 720
            if prop_id == configure_cameras.cv2.CAP_PROP_FPS: return 30.0
            return 0
        mock_cap.get.side_effect = get_prop
        
        # Run test
        result = configure_cameras.test_camera(0, configure_cameras.cv2.CAP_ANY)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result['status'], 'working')
        self.assertEqual(result['resolution'], '1280x720')
        self.assertTrue(result['is_hd'])
        
        mock_cap.release.assert_called()

    @patch('cv2.VideoCapture')
    def test_test_camera_failed_open(self, mock_capture):
        mock_cap = MagicMock()
        mock_capture.return_value = mock_cap
        mock_cap.isOpened.return_value = False
        
        result = configure_cameras.test_camera(0, configure_cameras.cv2.CAP_ANY)
        self.assertIsNone(result)

    @patch('configure_cameras.scan_cameras')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_interactive_configure(self, mock_print, mock_input, mock_scan):
        # Mock finding two cameras
        mock_scan.return_value = [
            {'id': 0, 'status': 'working', 'description': 'Cam 1', 'is_hd': True},
            {'id': 1, 'status': 'working', 'description': 'Cam 2', 'is_hd': True}
        ]
        
        # User selects 1 then 2
        mock_input.side_effect = ['1', '2']
        
        # Use temporary file for config
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            configure_cameras.config_path = tmp.name
        
        try:
            ret = configure_cameras.interactive_configure()
            
            self.assertEqual(ret, 0)
            
            # Verify file content
            with open(configure_cameras.config_path, 'r') as f:
                config = json.load(f)
                self.assertEqual(config['camera1_id'], 0)
                self.assertEqual(config['camera2_id'], 1)
                
        finally:
            if os.path.exists(configure_cameras.config_path):
                os.remove(configure_cameras.config_path)

if __name__ == '__main__':
    unittest.main()
