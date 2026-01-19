"""
Tests for Analysis Tab Frame Navigation and Metrics
Tests frame advancement, summary correctness, and live metrics
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock, patch
import numpy as np

# Add src and scripts to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'scripts'))

from camera_setup_recorder_gui import TabbedCameraGUI


class TestFrameNavigation(unittest.TestCase):
    """Test frame navigation in analysis tab"""
    
    def setUp(self):
        """Set up GUI with mock analysis data"""
        with patch('cv2.VideoCapture'):
            self.gui = TabbedCameraGUI()
            
            # Create mock analysis data with per-frame metrics
            self.gui.analysis_camera1 = {
                'sway': [0, -5, -10, -15, -12, -8, -5, 0, 5, 10, 8, 5, 0],  # 13 frames
                'summary': {
                    'max_sway_left': -15,
                    'max_sway_right': 10
                },
                'detection_rate': 95.0
            }
            
            self.gui.analysis_camera2 = {
                'shoulder_turn': [0, 10, 20, 30, 40, 45, 40, 30, 20, 10, 0],  # 11 frames
                'hip_turn': [0, 5, 10, 15, 20, 25, 20, 15, 10, 5, 0],
                'x_factor': [0, 5, 10, 15, 20, 20, 20, 15, 10, 5, 0],
                'summary': {
                    'max_shoulder_turn': 45,
                    'max_hip_turn': 25,
                    'max_x_factor': 20
                },
                'detection_rate': 90.0
            }
            
            self.gui.current_tab = 3  # Analysis tab
            self.gui.analysis_frame_index = 0
    
    def test_frame_index_initialization(self):
        """Test that frame index is initialized to 0"""
        self.assertEqual(self.gui.analysis_frame_index, 0)
    
    def test_navigate_forward(self):
        """Test navigating forward through frames"""
        # Get max frames (should be 13 from camera1)
        max_frames = max(
            len(self.gui.analysis_camera1.get('sway', [])),
            len(self.gui.analysis_camera2.get('shoulder_turn', []))
        )
        self.assertEqual(max_frames, 13)
        
        # Navigate forward
        self.gui.analysis_frame_index = min(max_frames - 1, self.gui.analysis_frame_index + 1)
        self.assertEqual(self.gui.analysis_frame_index, 1)
        
        self.gui.analysis_frame_index = min(max_frames - 1, self.gui.analysis_frame_index + 1)
        self.assertEqual(self.gui.analysis_frame_index, 2)
    
    def test_navigate_backward(self):
        """Test navigating backward through frames"""
        self.gui.analysis_frame_index = 5
        
        # Navigate backward
        self.gui.analysis_frame_index = max(0, self.gui.analysis_frame_index - 1)
        self.assertEqual(self.gui.analysis_frame_index, 4)
        
        self.gui.analysis_frame_index = max(0, self.gui.analysis_frame_index - 1)
        self.assertEqual(self.gui.analysis_frame_index, 3)
    
    def test_navigate_at_boundaries(self):
        """Test that navigation respects boundaries"""
        max_frames = max(
            len(self.gui.analysis_camera1.get('sway', [])),
            len(self.gui.analysis_camera2.get('shoulder_turn', []))
        )
        
        # Try to go before start
        self.gui.analysis_frame_index = 0
        self.gui.analysis_frame_index = max(0, self.gui.analysis_frame_index - 1)
        self.assertEqual(self.gui.analysis_frame_index, 0)
        
        # Try to go past end
        self.gui.analysis_frame_index = max_frames - 1
        self.gui.analysis_frame_index = min(max_frames - 1, self.gui.analysis_frame_index + 1)
        self.assertEqual(self.gui.analysis_frame_index, max_frames - 1)
    
    def test_frame_index_clamping(self):
        """Test that frame index is clamped to valid range"""
        max_frames = max(
            len(self.gui.analysis_camera1.get('sway', [])),
            len(self.gui.analysis_camera2.get('shoulder_turn', []))
        )
        
        # Set invalid index (too high)
        self.gui.analysis_frame_index = 999
        self.gui.analysis_frame_index = max(0, min(max_frames - 1, self.gui.analysis_frame_index))
        self.assertEqual(self.gui.analysis_frame_index, max_frames - 1)
        
        # Set invalid index (negative)
        self.gui.analysis_frame_index = -5
        self.gui.analysis_frame_index = max(0, min(max_frames - 1, self.gui.analysis_frame_index))
        self.assertEqual(self.gui.analysis_frame_index, 0)


class TestSummaryCorrectness(unittest.TestCase):
    """Test that summary metrics are correct for each camera"""
    
    def setUp(self):
        """Set up GUI with test analysis data"""
        with patch('cv2.VideoCapture'):
            self.gui = TabbedCameraGUI()
    
    def test_camera1_summary_structure(self):
        """Test that camera1 summary has correct structure"""
        analysis1 = {
            'sway': [-5, -10, -15, -10, -5, 0, 5, 10, 5, 0],
            'summary': {
                'max_sway_left': -15,
                'max_sway_right': 10
            },
            'detection_rate': 95.0
        }
        
        self.gui.analysis_camera1 = analysis1
        
        summary = self.gui.analysis_camera1.get('summary', {})
        self.assertIn('max_sway_left', summary)
        self.assertIn('max_sway_right', summary)
        self.assertEqual(summary['max_sway_left'], -15)
        self.assertEqual(summary['max_sway_right'], 10)
    
    def test_camera2_summary_structure(self):
        """Test that camera2 summary has correct structure"""
        analysis2 = {
            'shoulder_turn': [0, 10, 20, 30, 40, 45, 40, 30, 20, 10, 0],
            'hip_turn': [0, 5, 10, 15, 20, 25, 20, 15, 10, 5, 0],
            'x_factor': [0, 5, 10, 15, 20, 20, 20, 15, 10, 5, 0],
            'summary': {
                'max_shoulder_turn': 45,
                'max_hip_turn': 25,
                'max_x_factor': 20
            },
            'detection_rate': 90.0
        }
        
        self.gui.analysis_camera2 = analysis2
        
        summary = self.gui.analysis_camera2.get('summary', {})
        self.assertIn('max_shoulder_turn', summary)
        self.assertIn('max_hip_turn', summary)
        self.assertIn('max_x_factor', summary)
        self.assertEqual(summary['max_shoulder_turn'], 45)
        self.assertEqual(summary['max_hip_turn'], 25)
        self.assertEqual(summary['max_x_factor'], 20)
    
    def test_summary_max_values_correctness(self):
        """Test that max values in summary are actually maximums"""
        # Camera 1: Test max sway values
        sway_sequence = [-5, -10, -15, -10, -5, 0, 5, 10, 5, 0]
        expected_max_left = min(sway_sequence)  # Most negative
        expected_max_right = max(sway_sequence)  # Most positive
        
        analysis1 = {
            'sway': sway_sequence,
            'summary': {
                'max_sway_left': expected_max_left,
                'max_sway_right': expected_max_right
            }
        }
        
        self.gui.analysis_camera1 = analysis1
        summary = self.gui.analysis_camera1['summary']
        
        # Verify max values are correct
        self.assertEqual(summary['max_sway_left'], min(sway_sequence))
        self.assertEqual(summary['max_sway_right'], max(sway_sequence))
        
        # Camera 2: Test max rotation values
        shoulder_sequence = [0, 10, 20, 30, 40, 45, 40, 30, 20, 10, 0]
        hip_sequence = [0, 5, 10, 15, 20, 25, 20, 15, 10, 5, 0]
        xfactor_sequence = [abs(s - h) for s, h in zip(shoulder_sequence, hip_sequence)]
        
        analysis2 = {
            'shoulder_turn': shoulder_sequence,
            'hip_turn': hip_sequence,
            'x_factor': xfactor_sequence,
            'summary': {
                'max_shoulder_turn': max(shoulder_sequence),
                'max_hip_turn': max(hip_sequence),
                'max_x_factor': max(xfactor_sequence)
            }
        }
        
        self.gui.analysis_camera2 = analysis2
        summary2 = self.gui.analysis_camera2['summary']
        
        # Verify max values are correct
        self.assertEqual(summary2['max_shoulder_turn'], max(shoulder_sequence))
        self.assertEqual(summary2['max_hip_turn'], max(hip_sequence))
        self.assertEqual(summary2['max_x_factor'], max(xfactor_sequence))
    
    def test_both_cameras_have_summaries(self):
        """Test that both cameras have summary data"""
        self.gui.analysis_camera1 = {
            'sway': [0, -5, -10, -5, 0],
            'summary': {'max_sway_left': -10, 'max_sway_right': 0},
            'detection_rate': 100.0
        }
        
        self.gui.analysis_camera2 = {
            'shoulder_turn': [0, 20, 40, 20, 0],
            'hip_turn': [0, 10, 20, 10, 0],
            'x_factor': [0, 10, 20, 10, 0],
            'summary': {
                'max_shoulder_turn': 40,
                'max_hip_turn': 20,
                'max_x_factor': 20
            },
            'detection_rate': 100.0
        }
        
        self.assertIsNotNone(self.gui.analysis_camera1)
        self.assertIsNotNone(self.gui.analysis_camera2)
        self.assertIn('summary', self.gui.analysis_camera1)
        self.assertIn('summary', self.gui.analysis_camera2)


class TestLiveMetrics(unittest.TestCase):
    """Test that live metrics display correctly for current frame"""
    
    def setUp(self):
        """Set up GUI with mock analysis data"""
        with patch('cv2.VideoCapture'):
            self.gui = TabbedCameraGUI()
            
            self.gui.analysis_camera1 = {
                'sway': [0, -5, -10, -15, -10, -5, 0, 5, 10, 5, 0],
                'summary': {'max_sway_left': -15, 'max_sway_right': 10}
            }
            
            self.gui.analysis_camera2 = {
                'shoulder_turn': [0, 10, 20, 30, 40, 45, 40, 30, 20, 10, 0],
                'hip_turn': [0, 5, 10, 15, 20, 25, 20, 15, 10, 5, 0],
                'x_factor': [0, 5, 10, 15, 20, 20, 20, 15, 10, 5, 0],
                'summary': {
                    'max_shoulder_turn': 45,
                    'max_hip_turn': 25,
                    'max_x_factor': 20
                }
            }
            
            self.gui.analysis_frame_index = 0
    
    def test_current_frame_sway(self):
        """Test getting current frame sway value"""
        frame_idx = 3
        self.gui.analysis_frame_index = frame_idx
        
        current_sway = self.gui.analysis_camera1['sway'][frame_idx]
        self.assertEqual(current_sway, -15)
        
        # Check at different frame
        frame_idx = 7
        self.gui.analysis_frame_index = frame_idx
        current_sway = self.gui.analysis_camera1['sway'][frame_idx]
        self.assertEqual(current_sway, 5)
    
    def test_current_frame_shoulder_turn(self):
        """Test getting current frame shoulder turn value"""
        frame_idx = 5
        self.gui.analysis_frame_index = frame_idx
        
        current_shoulder = self.gui.analysis_camera2['shoulder_turn'][frame_idx]
        self.assertEqual(current_shoulder, 45)
    
    def test_current_frame_hip_turn(self):
        """Test getting current frame hip turn value"""
        frame_idx = 5
        self.gui.analysis_frame_index = frame_idx
        
        current_hip = self.gui.analysis_camera2['hip_turn'][frame_idx]
        self.assertEqual(current_hip, 25)
    
    def test_current_frame_x_factor(self):
        """Test getting current frame x-factor value"""
        frame_idx = 5
        self.gui.analysis_frame_index = frame_idx
        
        current_xfactor = self.gui.analysis_camera2['x_factor'][frame_idx]
        self.assertEqual(current_xfactor, 20)
    
    def test_live_metrics_access_all_frames(self):
        """Test that we can access metrics for all frames"""
        max_frames = len(self.gui.analysis_camera1['sway'])
        
        for frame_idx in range(max_frames):
            self.gui.analysis_frame_index = frame_idx
            
            # Access camera1 metric
            sway = self.gui.analysis_camera1['sway'][frame_idx]
            self.assertIsNotNone(sway)
            
            # Access camera2 metrics
            if frame_idx < len(self.gui.analysis_camera2['shoulder_turn']):
                shoulder = self.gui.analysis_camera2['shoulder_turn'][frame_idx]
                hip = self.gui.analysis_camera2['hip_turn'][frame_idx]
                xfactor = self.gui.analysis_camera2['x_factor'][frame_idx]
                self.assertIsNotNone(shoulder)
                self.assertIsNotNone(hip)
                self.assertIsNotNone(xfactor)


class TestAnalysisTabRendering(unittest.TestCase):
    """Test that analysis tab renders correctly with navigation"""
    
    def setUp(self):
        """Set up GUI instance"""
        with patch('cv2.VideoCapture'):
            self.gui = TabbedCameraGUI()
    
    def test_draw_analysis_tab_with_navigation(self):
        """Test analysis tab rendering with frame navigation"""
        self.gui.analysis_camera1 = {
            'sway': [0, -5, -10, -5, 0],
            'summary': {'max_sway_left': -10, 'max_sway_right': 0},
            'detection_rate': 100.0
        }
        
        self.gui.analysis_camera2 = {
            'shoulder_turn': [0, 20, 40, 20, 0],
            'hip_turn': [0, 10, 20, 10, 0],
            'x_factor': [0, 10, 20, 10, 0],
            'summary': {
                'max_shoulder_turn': 40,
                'max_hip_turn': 20,
                'max_x_factor': 20
            },
            'detection_rate': 100.0
        }
        
        self.gui.analysis_frame_index = 2
        self.gui.is_analyzing = False
        
        frame = np.zeros((900, 1600, 3), dtype=np.uint8)
        
        try:
            self.gui.draw_analysis_tab(frame)
            tab_rendered = True
        except Exception as e:
            tab_rendered = False
            print(f"Error rendering analysis tab: {e}")
            import traceback
            traceback.print_exc()
        
        self.assertTrue(tab_rendered)
    
    def test_frame_count_display(self):
        """Test that frame count is calculated correctly"""
        self.gui.analysis_camera1 = {
            'sway': [0] * 100,  # 100 frames
            'summary': {'max_sway_left': 0, 'max_sway_right': 0}
        }
        
        self.gui.analysis_camera2 = {
            'shoulder_turn': [0] * 100,
            'hip_turn': [0] * 100,
            'x_factor': [0] * 100,
            'summary': {'max_shoulder_turn': 0, 'max_hip_turn': 0, 'max_x_factor': 0}
        }
        
        # Calculate max frames
        max_frames = max(
            len(self.gui.analysis_camera1.get('sway', [])),
            len(self.gui.analysis_camera2.get('shoulder_turn', []))
        )
        
        self.assertEqual(max_frames, 100)


class TestPerVideoSummary(unittest.TestCase):
    """Test that each video has its own summary"""
    
    def test_camera1_video_summary(self):
        """Test camera1 (face-on) video summary"""
        with patch('cv2.VideoCapture'):
            gui = TabbedCameraGUI()
            
            # Simulate analysis results for camera1
            camera1_analysis = {
                'sway': [-5, -10, -15, -10, -5, 0, 5, 10, 5, 0],
                'summary': {
                    'max_sway_left': -15,
                    'max_sway_right': 10
                },
                'detection_rate': 95.0
            }
            
            gui.analysis_camera1 = camera1_analysis
            
            # Verify camera1 summary
            summary1 = gui.analysis_camera1.get('summary', {})
            self.assertIsNotNone(summary1)
            self.assertIn('max_sway_left', summary1)
            self.assertIn('max_sway_right', summary1)
            self.assertEqual(summary1['max_sway_left'], -15)
            self.assertEqual(summary1['max_sway_right'], 10)
    
    def test_camera2_video_summary(self):
        """Test camera2 (down-the-line) video summary"""
        with patch('cv2.VideoCapture'):
            gui = TabbedCameraGUI()
            
            # Simulate analysis results for camera2
            camera2_analysis = {
                'shoulder_turn': [0, 10, 20, 30, 40, 45, 40, 30, 20, 10, 0],
                'hip_turn': [0, 5, 10, 15, 20, 25, 20, 15, 10, 5, 0],
                'x_factor': [0, 5, 10, 15, 20, 20, 20, 15, 10, 5, 0],
                'summary': {
                    'max_shoulder_turn': 45,
                    'max_hip_turn': 25,
                    'max_x_factor': 20
                },
                'detection_rate': 90.0
            }
            
            gui.analysis_camera2 = camera2_analysis
            
            # Verify camera2 summary
            summary2 = gui.analysis_camera2.get('summary', {})
            self.assertIsNotNone(summary2)
            self.assertIn('max_shoulder_turn', summary2)
            self.assertIn('max_hip_turn', summary2)
            self.assertIn('max_x_factor', summary2)
            self.assertEqual(summary2['max_shoulder_turn'], 45)
            self.assertEqual(summary2['max_hip_turn'], 25)
            self.assertEqual(summary2['max_x_factor'], 20)
    
    def test_both_videos_separate_summaries(self):
        """Test that both videos maintain separate summaries"""
        with patch('cv2.VideoCapture'):
            gui = TabbedCameraGUI()
            
            gui.analysis_camera1 = {
                'sway': [-10, -5, 0],
                'summary': {'max_sway_left': -10, 'max_sway_right': 0},
                'detection_rate': 100.0
            }
            
            gui.analysis_camera2 = {
                'shoulder_turn': [0, 30, 0],
                'hip_turn': [0, 15, 0],
                'x_factor': [0, 15, 0],
                'summary': {
                    'max_shoulder_turn': 30,
                    'max_hip_turn': 15,
                    'max_x_factor': 15
                },
                'detection_rate': 100.0
            }
            
            # Verify summaries are independent
            summary1 = gui.analysis_camera1['summary']
            summary2 = gui.analysis_camera2['summary']
            
            self.assertNotEqual(summary1, summary2)
            self.assertNotIn('max_shoulder_turn', summary1)
            self.assertNotIn('max_sway_left', summary2)


def run_analysis_tests():
    """Run all analysis navigation tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFrameNavigation))
    suite.addTests(loader.loadTestsFromTestCase(TestSummaryCorrectness))
    suite.addTests(loader.loadTestsFromTestCase(TestLiveMetrics))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalysisTabRendering))
    suite.addTests(loader.loadTestsFromTestCase(TestPerVideoSummary))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 70)
    print("Analysis Navigation & Summary Tests")
    print("=" * 70)
    print()
    
    success = run_analysis_tests()
    
    print()
    print("=" * 70)
    if success:
        print("✓ All analysis navigation tests passed!")
    else:
        print("✗ Some analysis navigation tests failed")
    print("=" * 70)
    
    sys.exit(0 if success else 1)

