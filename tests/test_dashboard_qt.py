import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json
import tempfile
import time

# Mock PyQt6 before importing the dashboard script
# This is necessary because the environment lacks libEGL/libGL for Qt
mock_qt = MagicMock()
sys.modules['PyQt6'] = mock_qt
sys.modules['PyQt6.QtWidgets'] = mock_qt
sys.modules['PyQt6.QtCore'] = mock_qt
sys.modules['PyQt6.QtGui'] = mock_qt

# Define minimal mock classes that the script inherits from
class MockQThread:
    def __init__(self): 
        pass
    def start(self): pass
    def stop(self): pass
    def wait(self): pass
    
    # Mock signals with a connect method
    class Signal:
        def connect(self, func): pass
        def emit(self, *args): pass
    
    frame_ready = Signal()
    progress_update = Signal()
    analysis_complete = Signal()
    error_occurred = Signal()

mock_qt.QThread = MockQThread
mock_qt.pyqtSignal = lambda *args: MockQThread.Signal()
mock_qt.pyqtSlot = lambda *args: lambda fn: fn # Decorator mock

class MockQMainWindow:
    def __init__(self): pass
    def setCentralWidget(self, w): pass
    def setWindowTitle(self, t): pass
    def resize(self, w, h): pass
    def show(self): pass

mock_qt.QMainWindow = MockQMainWindow
mock_qt.QWidget = MagicMock()
mock_qt.QLabel = MagicMock()

# Add scripts folder to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import dashboard_gui_qt
from dashboard_gui_qt import CameraThread, AnalysisThread

class TestDashboardLogic(unittest.TestCase):
    
    def test_load_camera_config(self):
        # Create a temp config file
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            json.dump({'camera1_id': 10, 'camera2_id': 20}, tmp)
            tmp_path = tmp.name
            
        try:
            # Test loading specific path
            config = dashboard_gui_qt.load_camera_config(tmp_path)
            self.assertEqual(config['camera1_id'], 10)
            self.assertEqual(config['camera2_id'], 20)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @patch('cv2.VideoCapture')
    def test_camera_thread(self, mock_capture):
        # Setup mock camera
        mock_cap = MagicMock()
        mock_capture.return_value = mock_cap
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, MagicMock()) # Success, frame
        
        # Instantiate thread (using our MockQThread base)
        thread = CameraThread(camera_id=0, camera_index=1)
        
        # Test property getters
        thread.cap = mock_cap
        thread.get_property(10)
        mock_cap.get.assert_called_with(10)
        
        # Test property setters
        thread.set_property(10, 100)
        mock_cap.set.assert_called_with(10, 100)
        
        # Clean up
        thread.running = False
        thread.cap = None

    @patch('dashboard_gui_qt.PoseProcessor')
    @patch('dashboard_gui_qt.SwayCalculator')
    @patch('cv2.VideoCapture')
    def test_analysis_thread(self, mock_cap, mock_calc, mock_pose):
        # Setup mocks
        mock_pose_instance = MagicMock()
        mock_pose.return_value = mock_pose_instance
        mock_pose_instance.process_video.return_value = ([], []) # landmarks, frames
        
        mock_calc_instance = MagicMock()
        mock_calc.return_value = mock_calc_instance
        mock_calc_instance.analyze_sequence.return_value = {'summary': {}}
        
        # Mock video cap for width detection
        mock_cap_instance = MagicMock()
        mock_cap.return_value = mock_cap_instance
        mock_cap_instance.isOpened.return_value = True
        mock_cap_instance.get.return_value = 1920
        
        # Run thread logic
        thread = AnalysisThread(["vid1.mp4", "vid2.mp4"])
        
        # Connect signals to mocks (using our MockQThread signal mechanism)
        mock_complete = MagicMock()
        thread.analysis_complete.connect(mock_complete)
        
        thread.run()
        
        # Verify calls
        self.assertEqual(mock_pose.call_count, 2) # Once for each video
        self.assertEqual(mock_calc.call_count, 2)
        # Verify signal emission (this depends on how we mocked signal)
        # Since we just mocked Signal class, we can't easily verify 'emit' happened 
        # unless we check the run() logic execution flow, which we did via mock_pose calls.

if __name__ == '__main__':
    unittest.main()
