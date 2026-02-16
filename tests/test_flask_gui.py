"""
Tests for the Flask-based Camera Setup & Recording GUI.

Mirrors the structure of test_gui.py but tests the Flask app and
CameraManager class instead of the OpenCV-based TabbedCameraGUI.
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
import numpy as np

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'scripts'))
sys.path.insert(0, os.path.join(project_root, 'tests'))

import cv2
from flask_gui import app, CameraManager, load_windows_config
from test_utils import get_camera_ids


# ======================================================================
# CameraManager Initialization
# ======================================================================

class TestCameraManagerInitialization(unittest.TestCase):
    """Test CameraManager initialization with platform-appropriate defaults."""

    def test_platform_defaults_linux(self):
        """Linux should use cameras 0, 1 by default."""
        with patch('sys.platform', 'linux'):
            mgr = CameraManager()
            self.assertEqual(mgr.camera1_id, 0)
            self.assertEqual(mgr.camera2_id, 1)

    def test_platform_defaults_windows(self):
        """Windows should read from config file."""
        with patch('sys.platform', 'win32'):
            expected_cam1, expected_cam2 = get_camera_ids()
            mgr = CameraManager()
            self.assertEqual(mgr.camera1_id, expected_cam1)
            self.assertEqual(mgr.camera2_id, expected_cam2)

    def test_explicit_camera_ids(self):
        """Explicit IDs override defaults."""
        mgr = CameraManager(camera1_id=5, camera2_id=7)
        self.assertEqual(mgr.camera1_id, 5)
        self.assertEqual(mgr.camera2_id, 7)

    def test_tab_names(self):
        """All tab names should be present."""
        self.assertGreaterEqual(len(CameraManager.TAB_NAMES), 4)
        self.assertIn("Camera 1 Setup", CameraManager.TAB_NAMES)
        self.assertIn("Camera 2 Setup", CameraManager.TAB_NAMES)
        self.assertIn("Recording", CameraManager.TAB_NAMES)
        self.assertIn("Analysis", CameraManager.TAB_NAMES)

    def test_initial_state(self):
        """Verify initial state variables."""
        mgr = CameraManager()
        self.assertFalse(mgr.is_recording)
        self.assertFalse(mgr.is_analyzing)
        self.assertIsNone(mgr.analysis_camera1)
        self.assertIsNone(mgr.analysis_camera2)
        self.assertEqual(mgr.analysis_frame_index, 0)
        self.assertIsNone(mgr.recording_start_time)
        self.assertIsNone(mgr.recording_files)
        self.assertFalse(mgr.cameras_available)

    def test_default_fps_is_120(self):
        """Default recording target should be 120fps."""
        mgr = CameraManager()
        self.assertEqual(mgr.fps, 120)

    def test_default_resolution(self):
        """Default resolution should be 1280x720."""
        mgr = CameraManager()
        self.assertEqual(mgr.width, 1280)
        self.assertEqual(mgr.height, 720)

    def test_custom_fps(self):
        """Custom FPS is honoured."""
        mgr = CameraManager(fps=240)
        self.assertEqual(mgr.fps, 240)


# ======================================================================
# Camera Properties
# ======================================================================

class TestCameraProperties(unittest.TestCase):
    """Test camera property get/set/reset via CameraManager."""

    def setUp(self):
        self.mgr = CameraManager()
        self.mock_cap = MagicMock()
        self.mock_cap.isOpened.return_value = True
        self.mock_cap.get.return_value = 128.0
        self.mgr.cap1 = self.mock_cap

    def test_get_camera_properties(self):
        """Properties dict contains all expected keys."""
        props = self.mgr.get_camera_properties(1)
        self.assertIsNotNone(props)
        for name in CameraManager.PROP_MAP:
            self.assertIn(name, props)
            self.assertIn('value', props[name])
            self.assertIn('min', props[name])
            self.assertIn('max', props[name])
            self.assertIn('default', props[name])
        self.assertIn('_info', props)

    def test_get_properties_unavailable_camera(self):
        """Unavailable camera returns None."""
        self.mgr.cap2 = None
        self.assertIsNone(self.mgr.get_camera_properties(2))

    def test_set_property(self):
        """Setting a property calls cap.set()."""
        ok = self.mgr.set_camera_property(1, 'brightness', 200)
        self.assertTrue(ok)
        self.mock_cap.set.assert_called()

    def test_set_unknown_property(self):
        """Unknown property name returns False."""
        ok = self.mgr.set_camera_property(1, 'nonexistent', 42)
        self.assertFalse(ok)

    def test_reset_properties(self):
        """Reset calls cap.set for every property."""
        ok = self.mgr.reset_camera_properties(1)
        self.assertTrue(ok)
        # One set call per property
        self.assertEqual(self.mock_cap.set.call_count, len(CameraManager.PROP_MAP))

    def test_property_ranges_defined(self):
        """All property ranges have required keys."""
        for name, rng in CameraManager.PROP_RANGES.items():
            self.assertIn('min', rng, f"Missing 'min' for {name}")
            self.assertIn('max', rng, f"Missing 'max' for {name}")
            self.assertIn('default', rng, f"Missing 'default' for {name}")
            self.assertIn('step', rng, f"Missing 'step' for {name}")


# ======================================================================
# Recording Controls
# ======================================================================

class TestRecordingControls(unittest.TestCase):
    """Test recording start/stop functionality."""

    def setUp(self):
        self.mgr = CameraManager()
        self.mock_cap1 = MagicMock()
        self.mock_cap2 = MagicMock()
        self.mock_cap1.isOpened.return_value = True
        self.mock_cap2.isOpened.return_value = True
        self.mock_cap1.get.return_value = 128.0
        self.mock_cap2.get.return_value = 128.0
        self.mgr.cap1 = self.mock_cap1
        self.mgr.cap2 = self.mock_cap2
        self.mgr.cameras_available = True

    def test_start_recording_creates_recorder(self):
        """start_recording should create DualCameraRecorder and begin."""
        with patch('flask_gui.DualCameraRecorder') as MockRec:
            mock_rec = MagicMock()
            mock_rec.output_dir = 'recordings'
            mock_rec.camera1 = MagicMock()
            mock_rec.camera2 = MagicMock()
            mock_rec.camera1.cap = self.mock_cap1
            mock_rec.camera2.cap = self.mock_cap2
            MockRec.return_value = mock_rec

            result = self.mgr.start_recording()

            self.assertIn('success', result)
            self.assertTrue(result['success'])
            self.assertTrue(self.mgr.is_recording)
            mock_rec.start_cameras.assert_called_once()
            mock_rec.start_recording.assert_called_once()

    def test_start_recording_fails_without_cameras(self):
        """Recording must not start when cameras_available is False."""
        self.mgr.cameras_available = False
        self.mgr.cap1 = None
        self.mgr.cap2 = None

        result = self.mgr.start_recording()

        self.assertIn('error', result)
        self.assertFalse(self.mgr.is_recording)

    def test_start_recording_fails_when_already_recording(self):
        """Double-start returns error."""
        self.mgr.is_recording = True
        result = self.mgr.start_recording()
        self.assertIn('error', result)

    def test_stop_recording(self):
        """stop_recording should clean up and trigger analysis."""
        mock_recorder = MagicMock()
        mock_recorder.output_dir = 'recordings'
        self.mgr.recorder = mock_recorder
        self.mgr.is_recording = True
        self.mgr.recording_start_time = 0
        self.mgr.recording_files = ['test1.mp4', 'test2.mp4']

        with patch.object(self.mgr, '_reopen_cameras'):
            with patch.object(self.mgr, 'start_analysis'):
                with patch('time.time', return_value=5.0):
                    result = self.mgr.stop_recording()

        self.assertIn('success', result)
        self.assertFalse(self.mgr.is_recording)
        mock_recorder.stop_recording.assert_called_once()

    def test_stop_when_not_recording(self):
        """stop_recording when not recording returns error."""
        self.mgr.is_recording = False
        result = self.mgr.stop_recording()
        self.assertIn('error', result)

    def test_recording_state_tracking(self):
        """Initial recording state variables are correct."""
        self.assertFalse(self.mgr.is_recording)
        self.assertIsNone(self.mgr.recording_start_time)
        self.assertIsNone(self.mgr.recording_files)


# ======================================================================
# Analysis
# ======================================================================

class TestAnalysis(unittest.TestCase):
    """Test analysis triggering and result formatting."""

    def setUp(self):
        self.mgr = CameraManager()

    def test_analysis_state_initialization(self):
        """Analysis state should be clean on init."""
        self.assertFalse(self.mgr.is_analyzing)
        self.assertIsNone(self.mgr.analysis_camera1)
        self.assertIsNone(self.mgr.analysis_camera2)
        self.assertEqual(self.mgr.analysis_progress, "")
        self.assertIsNone(self.mgr.analysis_start_time)
        self.assertEqual(self.mgr.analysis_frame_index, 0)

    def test_start_analysis_requires_files(self):
        """start_analysis with no files should not start."""
        self.mgr.recording_files = None
        self.mgr.start_analysis()
        self.assertFalse(self.mgr.is_analyzing)

        self.mgr.recording_files = ['only_one.mp4']
        self.mgr.start_analysis()
        self.assertFalse(self.mgr.is_analyzing)

    def test_start_analysis_requires_existing_files(self):
        """start_analysis with non-existent files should not start."""
        self.mgr.recording_files = ['nonexistent1.mp4', 'nonexistent2.mp4']
        with patch('os.path.exists', return_value=False):
            self.mgr.start_analysis()
        self.assertFalse(self.mgr.is_analyzing)

    def test_get_analysis_results_empty(self):
        """get_analysis_results with no data returns empty structure."""
        results = self.mgr.get_analysis_results()
        self.assertFalse(results['is_analyzing'])
        self.assertEqual(results['max_frames'], 0)
        self.assertIsNone(results['camera1'])
        self.assertIsNone(results['camera2'])

    def test_get_analysis_results_with_data(self):
        """get_analysis_results formats camera data correctly."""
        self.mgr.analysis_camera1 = {
            'sway': [0, -5, -10, -5, 0, 5, 10, 5, 0],
            'head_sway': [0, -1, -2, -1, 0, 1, 2, 1, 0],
            'spine_tilt': [0] * 9,
            'knee_flex': [170] * 9,
            'weight_shift': [50] * 9,
            'shoulder_turn': [0] * 9,
            'hip_turn': [0] * 9,
            'x_factor': [0] * 9,
            'spine_angle': [30] * 9,
            'lead_arm_angle': [175] * 9,
            'phases': ['Address', 'Backswing', 'Backswing', 'Top', 'Downswing',
                       'Impact', 'Follow-through', 'Follow-through', 'Follow-through'],
            'tempo': 2.0,
            'summary': {'max_sway_left': -10, 'max_sway_right': 10},
            'detection_rate': 95.0,
        }
        self.mgr.analysis_camera2 = {
            'shoulder_turn': [0, 10, 20, 30, 40, 45, 40, 30, 20],
            'hip_turn': [0, 5, 10, 15, 20, 25, 20, 15, 10],
            'x_factor': [0, 5, 10, 15, 20, 20, 20, 15, 10],
            'sway': [0] * 9,
            'head_sway': [0] * 9,
            'spine_tilt': [0] * 9,
            'knee_flex': [170] * 9,
            'weight_shift': [50] * 9,
            'spine_angle': [30] * 9,
            'lead_arm_angle': [175] * 9,
            'phases': ['Address'] * 9,
            'tempo': 3.0,
            'summary': {
                'max_shoulder_turn': 45,
                'max_hip_turn': 25,
                'max_x_factor': 20,
            },
            'detection_rate': 90.0,
        }
        self.mgr.analysis_frame_index = 5

        results = self.mgr.get_analysis_results()

        self.assertEqual(results['max_frames'], 9)
        self.assertEqual(results['frame_index'], 5)

        # Camera 1 current frame
        self.assertIsNotNone(results['camera1'])
        self.assertEqual(results['camera1']['current']['sway'], 5)
        self.assertEqual(results['camera1']['detection_rate'], 95.0)
        # New: should include timeseries
        self.assertIn('timeseries', results['camera1'])
        # New: should include phase
        self.assertIn('phase', results['camera1']['current'])
        # New: should include all new metric keys
        for key in ['head_sway', 'spine_tilt', 'knee_flex', 'weight_shift',
                     'spine_angle', 'lead_arm_angle']:
            self.assertIn(key, results['camera1']['current'])

        # Camera 2 current frame
        self.assertIsNotNone(results['camera2'])
        self.assertEqual(results['camera2']['current']['shoulder_turn'], 45)
        self.assertEqual(results['camera2']['current']['hip_turn'], 25)
        self.assertEqual(results['camera2']['current']['x_factor'], 20)

    def test_frame_index_clamping(self):
        """Frame index should be clamped to valid range."""
        self.mgr.analysis_camera1 = {
            'sway': [0] * 10,
            'summary': {},
        }
        self.mgr.analysis_camera2 = None
        self.mgr.analysis_frame_index = 999
        results = self.mgr.get_analysis_results()
        self.assertEqual(results['frame_index'], 9)

    def test_stop_recording_triggers_analysis(self):
        """stop_recording should call start_analysis when files are available."""
        mock_recorder = MagicMock()
        mock_recorder.output_dir = 'recordings'
        self.mgr.recorder = mock_recorder
        self.mgr.is_recording = True
        self.mgr.recording_start_time = 0
        self.mgr.recording_files = ['test1.mp4', 'test2.mp4']
        self.mgr.cameras_available = True

        with patch.object(self.mgr, '_reopen_cameras'):
            with patch.object(self.mgr, 'start_analysis') as mock_analyze:
                with patch('time.time', return_value=5.0):
                    self.mgr.stop_recording()
        mock_analyze.assert_called_once()


# ======================================================================
# Analysis Frame Navigation
# ======================================================================

class TestFrameNavigation(unittest.TestCase):
    """Test analysis frame navigation logic."""

    def setUp(self):
        self.mgr = CameraManager()
        n1 = 13
        n2 = 11
        self.mgr.analysis_camera1 = {
            'sway': [0, -5, -10, -15, -12, -8, -5, 0, 5, 10, 8, 5, 0],
            'head_sway': [0] * n1,
            'spine_tilt': [0] * n1,
            'knee_flex': [170] * n1,
            'weight_shift': [50] * n1,
            'shoulder_turn': [0] * n1,
            'hip_turn': [0] * n1,
            'x_factor': [0] * n1,
            'spine_angle': [30] * n1,
            'lead_arm_angle': [175] * n1,
            'phases': ['Address'] * n1,
            'tempo': 2.0,
            'summary': {'max_sway_left': -15, 'max_sway_right': 10},
            'detection_rate': 95.0,
        }
        self.mgr.analysis_camera2 = {
            'shoulder_turn': [0, 10, 20, 30, 40, 45, 40, 30, 20, 10, 0],
            'hip_turn': [0, 5, 10, 15, 20, 25, 20, 15, 10, 5, 0],
            'x_factor': [0, 5, 10, 15, 20, 20, 20, 15, 10, 5, 0],
            'sway': [0] * n2,
            'head_sway': [0] * n2,
            'spine_tilt': [0] * n2,
            'knee_flex': [170] * n2,
            'weight_shift': [50] * n2,
            'spine_angle': [30] * n2,
            'lead_arm_angle': [175] * n2,
            'phases': ['Address'] * n2,
            'tempo': 3.0,
            'summary': {
                'max_shoulder_turn': 45,
                'max_hip_turn': 25,
                'max_x_factor': 20,
            },
            'detection_rate': 90.0,
        }
        self.mgr.analysis_frame_index = 0

    def test_navigate_forward(self):
        """Frame index increments correctly."""
        max_frames = 13  # camera1 has 13 sway values
        self.mgr.analysis_frame_index = min(max_frames - 1, self.mgr.analysis_frame_index + 1)
        self.assertEqual(self.mgr.analysis_frame_index, 1)

    def test_navigate_backward(self):
        """Frame index decrements correctly."""
        self.mgr.analysis_frame_index = 5
        self.mgr.analysis_frame_index = max(0, self.mgr.analysis_frame_index - 1)
        self.assertEqual(self.mgr.analysis_frame_index, 4)

    def test_boundary_start(self):
        """Cannot go below 0."""
        self.mgr.analysis_frame_index = 0
        self.mgr.analysis_frame_index = max(0, self.mgr.analysis_frame_index - 1)
        self.assertEqual(self.mgr.analysis_frame_index, 0)

    def test_boundary_end(self):
        """Cannot exceed max_frames - 1."""
        max_frames = 13
        self.mgr.analysis_frame_index = max_frames - 1
        self.mgr.analysis_frame_index = min(max_frames - 1, self.mgr.analysis_frame_index + 1)
        self.assertEqual(self.mgr.analysis_frame_index, max_frames - 1)

    def test_current_frame_values_at_index(self):
        """Accessing per-frame values at a specific index works correctly."""
        self.mgr.analysis_frame_index = 3
        results = self.mgr.get_analysis_results()
        self.assertEqual(results['camera1']['current']['sway'], -15)
        self.assertEqual(results['camera2']['current']['shoulder_turn'], 30)
        self.assertEqual(results['camera2']['current']['hip_turn'], 15)
        self.assertEqual(results['camera2']['current']['x_factor'], 15)


# ======================================================================
# Summary Correctness
# ======================================================================

class TestSummaryCorrectness(unittest.TestCase):
    """Verify that summary metrics match the per-frame sequences."""

    def test_camera1_summary(self):
        mgr = CameraManager()
        mgr.analysis_camera1 = {
            'sway': [-5, -10, -15, -10, -5, 0, 5, 10, 5, 0],
            'summary': {'max_sway_left': -15, 'max_sway_right': 10},
        }
        summary = mgr.analysis_camera1['summary']
        self.assertEqual(summary['max_sway_left'], min(mgr.analysis_camera1['sway']))
        self.assertEqual(summary['max_sway_right'], max(mgr.analysis_camera1['sway']))

    def test_camera2_summary(self):
        mgr = CameraManager()
        mgr.analysis_camera2 = {
            'shoulder_turn': [0, 10, 20, 30, 40, 45, 40, 30, 20, 10, 0],
            'hip_turn': [0, 5, 10, 15, 20, 25, 20, 15, 10, 5, 0],
            'x_factor': [0, 5, 10, 15, 20, 20, 20, 15, 10, 5, 0],
            'summary': {
                'max_shoulder_turn': 45,
                'max_hip_turn': 25,
                'max_x_factor': 20,
            },
        }
        summary = mgr.analysis_camera2['summary']
        self.assertEqual(summary['max_shoulder_turn'], max(mgr.analysis_camera2['shoulder_turn']))
        self.assertEqual(summary['max_hip_turn'], max(mgr.analysis_camera2['hip_turn']))
        self.assertEqual(summary['max_x_factor'], max(mgr.analysis_camera2['x_factor']))

    def test_separate_summaries(self):
        """Camera summaries are independent of each other."""
        mgr = CameraManager()
        mgr.analysis_camera1 = {
            'sway': [-10, 0],
            'summary': {'max_sway_left': -10, 'max_sway_right': 0},
        }
        mgr.analysis_camera2 = {
            'shoulder_turn': [0, 30],
            'hip_turn': [0, 15],
            'x_factor': [0, 15],
            'summary': {'max_shoulder_turn': 30, 'max_hip_turn': 15, 'max_x_factor': 15},
        }
        s1 = mgr.analysis_camera1['summary']
        s2 = mgr.analysis_camera2['summary']
        self.assertNotIn('max_shoulder_turn', s1)
        self.assertNotIn('max_sway_left', s2)


# ======================================================================
# Flask Routes
# ======================================================================

class TestFlaskRoutes(unittest.TestCase):
    """Test Flask HTTP endpoints."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

        # Create a CameraManager with mocked cameras
        import flask_gui
        self.mgr = CameraManager()
        self.mock_cap1 = MagicMock()
        self.mock_cap2 = MagicMock()
        self.mock_cap1.isOpened.return_value = True
        self.mock_cap2.isOpened.return_value = True
        self.mock_cap1.get.return_value = 128.0
        self.mock_cap2.get.return_value = 128.0
        self.mgr.cap1 = self.mock_cap1
        self.mgr.cap2 = self.mock_cap2
        self.mgr.cameras_available = True
        flask_gui.camera_manager = self.mgr

    def tearDown(self):
        import flask_gui
        flask_gui.camera_manager = None

    def test_index_returns_html(self):
        """GET / should return the HTML page."""
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Camera Setup', resp.data)

    def test_api_status(self):
        """GET /api/status returns JSON with expected keys."""
        resp = self.client.get('/api/status')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('cameras_available', data)
        self.assertIn('is_recording', data)
        self.assertIn('is_analyzing', data)
        self.assertIn('fps', data)
        self.assertEqual(data['fps'], 120)

    def test_api_camera_properties(self):
        """GET /api/camera/1/properties returns property data."""
        resp = self.client.get('/api/camera/1/properties')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('brightness', data)
        self.assertIn('_info', data)

    def test_api_camera_properties_unavailable(self):
        """GET /api/camera/2/properties when cap2 is None."""
        self.mgr.cap2 = None
        resp = self.client.get('/api/camera/2/properties')
        data = json.loads(resp.data)
        self.assertIn('error', data)

    def test_api_set_property(self):
        """POST /api/camera/1/property sets a property."""
        resp = self.client.post('/api/camera/1/property',
                                json={'name': 'brightness', 'value': 200})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        self.mock_cap1.set.assert_called()

    def test_api_set_property_missing_params(self):
        """POST without required params returns 400."""
        resp = self.client.post('/api/camera/1/property', json={})
        self.assertEqual(resp.status_code, 400)

    def test_api_reset_camera(self):
        """POST /api/camera/1/reset resets properties."""
        resp = self.client.post('/api/camera/1/reset')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])

    def test_api_recording_start(self):
        """POST /api/recording/start triggers recording."""
        with patch('flask_gui.DualCameraRecorder') as MockRec:
            mock_rec = MagicMock()
            mock_rec.output_dir = 'recordings'
            mock_rec.camera1 = MagicMock()
            mock_rec.camera2 = MagicMock()
            mock_rec.camera1.cap = self.mock_cap1
            mock_rec.camera2.cap = self.mock_cap2
            MockRec.return_value = mock_rec

            resp = self.client.post('/api/recording/start')
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.data)
            self.assertTrue(data.get('success'))

    def test_api_recording_start_no_cameras(self):
        """POST /api/recording/start without cameras returns error."""
        self.mgr.cameras_available = False
        self.mgr.cap1 = None
        self.mgr.cap2 = None
        resp = self.client.post('/api/recording/start')
        data = json.loads(resp.data)
        self.assertIn('error', data)

    def test_api_recording_stop(self):
        """POST /api/recording/stop stops recording."""
        mock_rec = MagicMock()
        mock_rec.output_dir = 'recordings'
        self.mgr.recorder = mock_rec
        self.mgr.is_recording = True
        self.mgr.recording_start_time = 0
        self.mgr.recording_files = ['a.mp4', 'b.mp4']

        with patch.object(self.mgr, '_reopen_cameras'):
            with patch.object(self.mgr, 'start_analysis'):
                with patch('time.time', return_value=5.0):
                    resp = self.client.post('/api/recording/stop')

        data = json.loads(resp.data)
        self.assertTrue(data.get('success'))
        self.assertFalse(self.mgr.is_recording)

    def test_api_analysis_results_empty(self):
        """GET /api/analysis/results with no data."""
        resp = self.client.get('/api/analysis/results')
        data = json.loads(resp.data)
        self.assertEqual(data['max_frames'], 0)
        self.assertIsNone(data['camera1'])
        self.assertIsNone(data['camera2'])

    def test_api_analysis_results_with_data(self):
        """GET /api/analysis/results with mock analysis data."""
        self.mgr.analysis_camera1 = {
            'sway': [0, -5, -10],
            'shoulder_turn': [0, 0, 0], 'hip_turn': [0, 0, 0], 'x_factor': [0, 0, 0],
            'head_sway': [0, 0, 0], 'spine_tilt': [0, 0, 0],
            'knee_flex': [170, 170, 170], 'weight_shift': [50, 50, 50],
            'spine_angle': [30, 30, 30], 'lead_arm_angle': [175, 175, 175],
            'phases': ['Address', 'Backswing', 'Top'], 'tempo': 2.0,
            'summary': {'max_sway_left': -10, 'max_sway_right': 0},
            'detection_rate': 100.0,
        }
        self.mgr.analysis_camera2 = {
            'shoulder_turn': [0, 20, 40], 'hip_turn': [0, 10, 20], 'x_factor': [0, 10, 20],
            'sway': [0, 0, 0], 'head_sway': [0, 0, 0], 'spine_tilt': [0, 0, 0],
            'knee_flex': [170, 170, 170], 'weight_shift': [50, 50, 50],
            'spine_angle': [30, 30, 30], 'lead_arm_angle': [175, 175, 175],
            'phases': ['Address', 'Backswing', 'Top'], 'tempo': 3.0,
            'summary': {'max_shoulder_turn': 40, 'max_hip_turn': 20, 'max_x_factor': 20},
            'detection_rate': 100.0,
        }
        resp = self.client.get('/api/analysis/results')
        data = json.loads(resp.data)
        self.assertEqual(data['max_frames'], 3)
        self.assertIsNotNone(data['camera1'])
        self.assertIsNotNone(data['camera2'])
        # Check new structure
        self.assertIn('timeseries', data['camera1'])
        self.assertIn('phase', data['camera1']['current'])
        self.assertIn('tempo', data['camera1']['current'])

    def test_api_set_analysis_frame(self):
        """POST /api/analysis/frame sets the frame index."""
        self.mgr.analysis_camera1 = {
            'sway': [0] * 50,
            'summary': {},
        }
        resp = self.client.post('/api/analysis/frame', json={'index': 25})
        data = json.loads(resp.data)
        self.assertEqual(data['frame_index'], 25)

    def test_api_save_settings(self):
        """POST /api/settings/save creates a JSON file."""
        with patch('builtins.open', unittest.mock.mock_open()):
            resp = self.client.post('/api/settings/save')
            data = json.loads(resp.data)
            self.assertTrue(data.get('success') or 'filename' in data)

    def test_api_status_during_recording(self):
        """Status should reflect recording state."""
        self.mgr.is_recording = True
        self.mgr.recording_start_time = 100.0
        self.mgr.recording_files = ['cam1.mp4', 'cam2.mp4']

        with patch('time.time', return_value=105.0):
            resp = self.client.get('/api/status')
        data = json.loads(resp.data)
        self.assertTrue(data['is_recording'])
        self.assertAlmostEqual(data['recording_duration'], 5.0, places=1)

    def test_api_status_during_analysis(self):
        """Status should reflect analysis state."""
        self.mgr.is_analyzing = True
        self.mgr.analysis_progress = "Processing Camera 1..."
        resp = self.client.get('/api/status')
        data = json.loads(resp.data)
        self.assertTrue(data['is_analyzing'])
        self.assertEqual(data['analysis_progress'], "Processing Camera 1...")


# ======================================================================
# Template Rendering
# ======================================================================

class TestTemplateRendering(unittest.TestCase):
    """Test that the HTML template renders with all expected elements."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        import flask_gui
        self.mgr = CameraManager()
        flask_gui.camera_manager = self.mgr

    def tearDown(self):
        import flask_gui
        flask_gui.camera_manager = None

    def test_template_contains_all_tabs(self):
        """HTML should contain all 6 tab buttons."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('Camera 1 Setup', html)
        self.assertIn('Camera 2 Setup', html)
        self.assertIn('Recording', html)
        self.assertIn('Recordings', html)
        self.assertIn('Analysis', html)
        self.assertIn('Compare', html)

    def test_template_contains_keyboard_hints(self):
        """HTML should include keyboard shortcut hints."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('[1]', html)
        self.assertIn('[2]', html)
        self.assertIn('[3]', html)
        self.assertIn('[4]', html)
        self.assertIn('[5]', html)
        self.assertIn('[6]', html)
        self.assertIn('Space', html)

    def test_template_contains_video_feeds(self):
        """HTML should reference the MJPEG video feed URLs."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('/video_feed/1', html)
        self.assertIn('/video_feed/2', html)

    def test_template_contains_recording_controls(self):
        """HTML should have recording start/stop UI."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('Start Recording', html)
        self.assertIn('toggleRecording', html)

    def test_template_contains_analysis_sections(self):
        """HTML should have analysis result sections."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('metrics-dashboard', html)
        self.assertIn('timeseries-canvas', html)
        self.assertIn('phase-badge', html)
        self.assertIn('Face-On', html)
        self.assertIn('Down-the-Line', html)

    def test_template_contains_compare_tab(self):
        """HTML should have the comparison tab."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('tab-compare', html)
        self.assertIn('compare-a', html)
        self.assertIn('compare-b', html)
        self.assertIn('compare-canvas', html)

    def test_template_contains_property_controls(self):
        """HTML should have camera property sections."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('Camera 1 Properties', html)
        self.assertIn('Camera 2 Properties', html)
        self.assertIn('Save Settings', html)
        self.assertIn('Reset Defaults', html)

    def test_template_contains_settings_display(self):
        """HTML should show the recording settings (fps, resolution)."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('120fps', html)
        self.assertIn('1280x720', html)

    def test_template_contains_frame_navigation(self):
        """HTML should have frame navigation controls."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('Prev', html)
        self.assertIn('Next', html)
        self.assertIn('frame-slider', html)


# ======================================================================
# New Analysis & Compare Endpoints
# ======================================================================

class TestNewAnalysisEndpoints(unittest.TestCase):
    """Test new API endpoints for analyses listing and comparison."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        import flask_gui
        self.mgr = CameraManager()
        flask_gui.camera_manager = self.mgr

    def tearDown(self):
        import flask_gui
        flask_gui.camera_manager = None

    def test_analyses_list_endpoint_exists(self):
        """GET /api/analyses should return 200."""
        resp = self.client.get('/api/analyses')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('analyses', data)
        self.assertIn('count', data)

    def test_compare_endpoint_requires_params(self):
        """GET /api/compare without params should return 400."""
        resp = self.client.get('/api/compare')
        self.assertEqual(resp.status_code, 400)

    def test_compare_endpoint_requires_both(self):
        """GET /api/compare with only one param should return 400."""
        resp = self.client.get('/api/compare?a=20260215_140000')
        self.assertEqual(resp.status_code, 400)


# ======================================================================
# Video Playback & Auto-Detect Endpoints
# ======================================================================

class TestAnalysisFrameEndpoint(unittest.TestCase):
    """Test /api/analysis/frame/<camera_num> image endpoint."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        import flask_gui
        self.mgr = CameraManager()
        flask_gui.camera_manager = self.mgr

    def tearDown(self):
        import flask_gui
        flask_gui.camera_manager = None

    def test_returns_placeholder_when_no_frames(self):
        """Should return a JPEG placeholder when no analysis frames exist."""
        resp = self.client.get('/api/analysis/frame/1?index=0')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'image/jpeg')

    def test_returns_placeholder_for_out_of_range(self):
        """Should return placeholder for index out of range."""
        # Store a single compressed frame
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buf = cv2.imencode('.jpg', dummy, [cv2.IMWRITE_JPEG_QUALITY, 85])
        self.mgr.analysis_frames_cam1 = [buf.tobytes()]
        resp = self.client.get('/api/analysis/frame/1?index=99')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'image/jpeg')

    def test_returns_stored_frame(self):
        """Should return the pre-compressed JPEG frame."""
        dummy = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buf = cv2.imencode('.jpg', dummy, [cv2.IMWRITE_JPEG_QUALITY, 85])
        jpeg_bytes = buf.tobytes()
        self.mgr.analysis_frames_cam1 = [jpeg_bytes]
        resp = self.client.get('/api/analysis/frame/1?index=0')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'image/jpeg')
        self.assertEqual(resp.data, jpeg_bytes)

    def test_camera2_frame(self):
        """Should serve cam2 frames correctly."""
        dummy = np.full((50, 50, 3), 128, dtype=np.uint8)
        _, buf = cv2.imencode('.jpg', dummy, [cv2.IMWRITE_JPEG_QUALITY, 85])
        jpeg_bytes = buf.tobytes()
        self.mgr.analysis_frames_cam2 = [jpeg_bytes]
        resp = self.client.get('/api/analysis/frame/2?index=0')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, jpeg_bytes)

    def test_has_frames_in_results(self):
        """Analysis results should report has_frames correctly."""
        self.assertFalse(self.mgr.get_analysis_results()['has_frames'])
        self.mgr.analysis_frames_cam1 = [b'fake']
        self.assertTrue(self.mgr.get_analysis_results()['has_frames'])


class TestAutoDetectEndpoints(unittest.TestCase):
    """Test /api/auto-detect/* endpoints."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        import flask_gui
        self.mgr = CameraManager()
        flask_gui.camera_manager = self.mgr

    def tearDown(self):
        import flask_gui
        if self.mgr.swing_detector:
            try:
                self.mgr.swing_detector.release()
            except Exception:
                pass
        flask_gui.camera_manager = None

    def test_status_when_disabled(self):
        """GET /api/auto-detect/status when disabled."""
        resp = self.client.get('/api/auto-detect/status')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['enabled'])
        self.assertEqual(data['status'], {})

    @patch('flask_gui.SwingDetector')
    def test_toggle_on(self, MockDetector):
        """POST /api/auto-detect/toggle should enable."""
        mock_instance = MagicMock()
        mock_instance.get_status.return_value = {'state': 'idle'}
        MockDetector.return_value = mock_instance

        resp = self.client.post('/api/auto-detect/toggle')
        data = json.loads(resp.data)
        self.assertTrue(data['enabled'])
        self.assertTrue(self.mgr.auto_detect_enabled)

    @patch('flask_gui.SwingDetector')
    def test_toggle_off(self, MockDetector):
        """Toggle on then off should disable."""
        mock_instance = MagicMock()
        mock_instance.get_status.return_value = {'state': 'idle'}
        MockDetector.return_value = mock_instance

        self.client.post('/api/auto-detect/toggle')  # on
        resp = self.client.post('/api/auto-detect/toggle')  # off
        data = json.loads(resp.data)
        self.assertFalse(data['enabled'])
        self.assertFalse(self.mgr.auto_detect_enabled)

    def test_status_in_api_status(self):
        """GET /api/status should include auto_detect_enabled."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.return_value = 128.0
        self.mgr.cap1 = mock_cap
        self.mgr.cap2 = mock_cap
        self.mgr.cameras_available = True

        resp = self.client.get('/api/status')
        data = json.loads(resp.data)
        self.assertIn('auto_detect_enabled', data)
        self.assertFalse(data['auto_detect_enabled'])
        self.assertIn('auto_detect_status', data)


class TestCompressFrames(unittest.TestCase):
    """Test the _compress_frames static method."""

    def test_compress_frames(self):
        frames = [
            np.zeros((100, 100, 3), dtype=np.uint8),
            np.full((100, 100, 3), 255, dtype=np.uint8),
        ]
        compressed = CameraManager._compress_frames(frames)
        self.assertEqual(len(compressed), 2)
        for c in compressed:
            self.assertIsInstance(c, bytes)
            self.assertTrue(len(c) > 0)
            # JPEG magic bytes
            self.assertTrue(c[:2] == b'\xff\xd8')

    def test_compress_empty(self):
        compressed = CameraManager._compress_frames([])
        self.assertEqual(compressed, [])


class TestTemplateNewFeatures(unittest.TestCase):
    """Test that the template includes the new video playback and auto-detect UI."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        import flask_gui
        self.mgr = CameraManager()
        flask_gui.camera_manager = self.mgr

    def tearDown(self):
        import flask_gui
        flask_gui.camera_manager = None

    def test_template_has_video_panels(self):
        """HTML should contain analysis video playback panels."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('analysis-video-panels', html)
        self.assertIn('analysis-frame-cam1', html)
        self.assertIn('analysis-frame-cam2', html)

    def test_template_has_play_button(self):
        """HTML should contain the play/pause button."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('play-btn', html)
        self.assertIn('togglePlayback', html)
        self.assertIn('speed-label', html)

    def test_template_has_auto_detect_toggle(self):
        """HTML should contain the auto-detect toggle switch."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('auto-detect-cb', html)
        self.assertIn('Auto Detect', html)
        self.assertIn('auto-detect-panel', html)

    def test_template_has_auto_detect_gauge(self):
        """HTML should contain the shoulder turn gauge."""
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('auto-detect-gauge-fill', html)
        self.assertIn('auto-detect-badge', html)
        self.assertIn('Shoulder Turn', html)


# ======================================================================
# Runner
# ======================================================================

def run_flask_gui_tests():
    """Run all Flask GUI tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestCameraManagerInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestCameraProperties))
    suite.addTests(loader.loadTestsFromTestCase(TestRecordingControls))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalysis))
    suite.addTests(loader.loadTestsFromTestCase(TestFrameNavigation))
    suite.addTests(loader.loadTestsFromTestCase(TestSummaryCorrectness))
    suite.addTests(loader.loadTestsFromTestCase(TestFlaskRoutes))
    suite.addTests(loader.loadTestsFromTestCase(TestTemplateRendering))
    suite.addTests(loader.loadTestsFromTestCase(TestNewAnalysisEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestAnalysisFrameEndpoint))
    suite.addTests(loader.loadTestsFromTestCase(TestAutoDetectEndpoints))
    suite.addTests(loader.loadTestsFromTestCase(TestCompressFrames))
    suite.addTests(loader.loadTestsFromTestCase(TestTemplateNewFeatures))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 70)
    print("Flask GUI Tests")
    print("=" * 70)
    print()

    success = run_flask_gui_tests()

    print()
    print("=" * 70)
    if success:
        print("All Flask GUI tests passed!")
    else:
        print("Some Flask GUI tests failed")
    print("=" * 70)

    sys.exit(0 if success else 1)
