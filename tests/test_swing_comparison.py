"""
Tests for swing comparison feature:
  - Saving analysis results to JSON
  - Listing saved analyses
  - Comparing two swings via API
"""

import sys
import os
import json
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'scripts'))

from flask_gui import app, CameraManager, _list_saved_analyses, _load_analysis


class TestAnalysisSaveLoad(unittest.TestCase):
    """Test _save_analysis_json and _load_analysis."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.mgr = CameraManager()
        self.mgr.recording_files = [
            os.path.join(self.tmpdir, 'recording_20260215_140000_camera1.mp4'),
            os.path.join(self.tmpdir, 'recording_20260215_140000_camera2.mp4'),
        ]
        # Populate analysis data
        self.mgr.analysis_camera1 = {
            'sway': [0, -5, -10],
            'shoulder_turn': [0, 10, 20],
            'hip_turn': [0, 5, 10],
            'x_factor': [0, 5, 10],
            'head_sway': [0, -1, -2],
            'spine_tilt': [0, 1, 2],
            'knee_flex': [170, 165, 160],
            'weight_shift': [50, 55, 60],
            'spine_angle': [30, 30, 31],
            'lead_arm_angle': [175, 170, 165],
            'phases': ['Address', 'Backswing', 'Top'],
            'tempo': 2.0,
            'summary': {'max_sway_right': 0, 'max_sway_left': -10, 'tempo_ratio': 2.0},
            'detection_rate': 100.0,
        }
        self.mgr.analysis_camera2 = {
            'sway': [0, -2, -4],
            'shoulder_turn': [0, 20, 40],
            'hip_turn': [0, 10, 20],
            'x_factor': [0, 10, 20],
            'head_sway': [0, 0, 0],
            'spine_tilt': [0, 0, 0],
            'knee_flex': [170, 170, 170],
            'weight_shift': [50, 50, 50],
            'spine_angle': [30, 32, 34],
            'lead_arm_angle': [180, 175, 170],
            'phases': ['Address', 'Backswing', 'Top'],
            'tempo': 2.0,
            'summary': {'max_shoulder_turn': 40, 'max_hip_turn': 20, 'max_x_factor': 20},
            'detection_rate': 95.0,
        }

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _patch_recordings_dir(self):
        return patch('flask_gui._get_recordings_dir', return_value=self.tmpdir)

    def test_analysis_json_path(self):
        path = self.mgr._analysis_json_path()
        self.assertIsNotNone(path)
        self.assertIn('analysis_20260215_140000.json', path)

    def test_analysis_json_path_no_files(self):
        self.mgr.recording_files = None
        self.assertIsNone(self.mgr._analysis_json_path())

    def test_save_creates_file(self):
        with self._patch_recordings_dir():
            self.mgr._save_analysis_json()
        json_path = os.path.join(self.tmpdir, 'analysis_20260215_140000.json')
        self.assertTrue(os.path.exists(json_path))

    def test_saved_json_is_valid(self):
        with self._patch_recordings_dir():
            self.mgr._save_analysis_json()
        json_path = os.path.join(self.tmpdir, 'analysis_20260215_140000.json')
        with open(json_path) as f:
            data = json.load(f)
        self.assertIn('timestamp', data)
        self.assertEqual(data['timestamp'], '20260215_140000')
        self.assertIn('camera1', data)
        self.assertIn('camera2', data)

    def test_saved_json_has_metrics(self):
        with self._patch_recordings_dir():
            self.mgr._save_analysis_json()
        json_path = os.path.join(self.tmpdir, 'analysis_20260215_140000.json')
        with open(json_path) as f:
            data = json.load(f)
        cam1 = data['camera1']
        self.assertIn('sway', cam1)
        self.assertIn('head_sway', cam1)
        self.assertIn('phases', cam1)
        self.assertIn('tempo', cam1)
        self.assertIn('summary', cam1)
        self.assertIn('detection_rate', cam1)

    def test_load_analysis(self):
        with self._patch_recordings_dir():
            self.mgr._save_analysis_json()
            loaded = _load_analysis('20260215_140000')
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded['timestamp'], '20260215_140000')

    def test_load_nonexistent(self):
        with self._patch_recordings_dir():
            loaded = _load_analysis('99999999_999999')
        self.assertIsNone(loaded)


class TestListSavedAnalyses(unittest.TestCase):
    """Test _list_saved_analyses helper."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_analysis(self, ts, data=None):
        path = os.path.join(self.tmpdir, f'analysis_{ts}.json')
        with open(path, 'w') as f:
            json.dump(data or {'timestamp': ts}, f)

    def test_empty_dir(self):
        with patch('flask_gui._get_recordings_dir', return_value=self.tmpdir):
            result = _list_saved_analyses()
        self.assertEqual(result, [])

    def test_finds_analyses(self):
        self._write_analysis('20260215_140000')
        self._write_analysis('20260215_150000')
        with patch('flask_gui._get_recordings_dir', return_value=self.tmpdir):
            result = _list_saved_analyses()
        self.assertEqual(len(result), 2)

    def test_sorted_newest_first(self):
        self._write_analysis('20260210_100000')
        self._write_analysis('20260215_150000')
        self._write_analysis('20260212_120000')
        with patch('flask_gui._get_recordings_dir', return_value=self.tmpdir):
            result = _list_saved_analyses()
        timestamps = [r['timestamp'] for r in result]
        self.assertEqual(timestamps, ['20260215_150000', '20260212_120000', '20260210_100000'])

    def test_ignores_non_analysis_files(self):
        self._write_analysis('20260215_140000')
        # Write a non-matching file
        with open(os.path.join(self.tmpdir, 'recording_20260215_140000_camera1.mp4'), 'w') as f:
            f.write('fake')
        with patch('flask_gui._get_recordings_dir', return_value=self.tmpdir):
            result = _list_saved_analyses()
        self.assertEqual(len(result), 1)

    def test_nonexistent_dir(self):
        with patch('flask_gui._get_recordings_dir', return_value='/nonexistent/path'):
            result = _list_saved_analyses()
        self.assertEqual(result, [])


class TestCompareAPI(unittest.TestCase):
    """Test the /api/analyses and /api/compare endpoints."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.tmpdir = tempfile.mkdtemp()

        import flask_gui
        self.mgr = CameraManager()
        flask_gui.camera_manager = self.mgr

        # Write two analysis files
        self.analysis_a = {
            'timestamp': '20260215_140000',
            'camera1': {
                'sway': [0, -5, -10],
                'shoulder_turn': [0, 10, 20],
                'hip_turn': [0, 5, 10],
                'x_factor': [0, 5, 10],
                'head_sway': [0, -1, -2],
                'spine_tilt': [0, 1, 2],
                'knee_flex': [170, 165, 160],
                'weight_shift': [50, 55, 60],
                'spine_angle': [30, 30, 31],
                'lead_arm_angle': [175, 170, 165],
                'phases': ['Address', 'Backswing', 'Top'],
                'tempo': 2.0,
                'summary': {'max_sway_right': 0, 'max_sway_left': -10, 'tempo_ratio': 2.0,
                            'max_shoulder_turn': 20, 'max_hip_turn': 10, 'max_x_factor': 10},
                'detection_rate': 100.0,
            },
            'camera2': {
                'sway': [0, -2, -4],
                'shoulder_turn': [0, 20, 40],
                'summary': {'max_shoulder_turn': 40, 'max_hip_turn': 20, 'max_x_factor': 20},
                'detection_rate': 95.0,
            },
        }
        self.analysis_b = {
            'timestamp': '20260215_150000',
            'camera1': {
                'sway': [0, -3, -8],
                'summary': {'max_sway_right': 0, 'max_sway_left': -8, 'tempo_ratio': 3.0,
                            'max_shoulder_turn': 25, 'max_hip_turn': 12, 'max_x_factor': 13},
                'detection_rate': 98.0,
            },
            'camera2': {
                'shoulder_turn': [0, 25, 50],
                'summary': {'max_shoulder_turn': 50, 'max_hip_turn': 25, 'max_x_factor': 25},
                'detection_rate': 97.0,
            },
        }
        for analysis in (self.analysis_a, self.analysis_b):
            path = os.path.join(self.tmpdir, f"analysis_{analysis['timestamp']}.json")
            with open(path, 'w') as f:
                json.dump(analysis, f)

        self._patcher = patch('flask_gui._get_recordings_dir', return_value=self.tmpdir)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        import flask_gui
        flask_gui.camera_manager = None
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_list_analyses(self):
        resp = self.client.get('/api/analyses')
        data = json.loads(resp.data)
        self.assertEqual(data['count'], 2)
        self.assertEqual(len(data['analyses']), 2)
        # Newest first
        self.assertEqual(data['analyses'][0]['timestamp'], '20260215_150000')

    def test_list_analyses_no_path(self):
        """No internal path exposed in response."""
        resp = self.client.get('/api/analyses')
        data = json.loads(resp.data)
        for a in data['analyses']:
            self.assertNotIn('path', a)

    def test_compare_success(self):
        resp = self.client.get('/api/compare?a=20260215_140000&b=20260215_150000')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('swing_a', data)
        self.assertIn('swing_b', data)
        self.assertIn('deltas', data)
        self.assertEqual(data['swing_a']['timestamp'], '20260215_140000')
        self.assertEqual(data['swing_b']['timestamp'], '20260215_150000')

    def test_compare_has_deltas(self):
        resp = self.client.get('/api/compare?a=20260215_140000&b=20260215_150000')
        data = json.loads(resp.data)
        deltas = data['deltas']
        self.assertIn('camera1', deltas)
        self.assertIn('camera2', deltas)
        # Camera 2 should have shoulder turn delta
        c2 = deltas['camera2']
        self.assertIn('max_shoulder_turn', c2)
        self.assertEqual(c2['max_shoulder_turn']['a'], 40)
        self.assertEqual(c2['max_shoulder_turn']['b'], 50)
        self.assertEqual(c2['max_shoulder_turn']['delta'], 10.0)

    def test_compare_missing_params(self):
        resp = self.client.get('/api/compare')
        self.assertEqual(resp.status_code, 400)

    def test_compare_missing_a(self):
        resp = self.client.get('/api/compare?a=20260215_140000')
        self.assertEqual(resp.status_code, 400)

    def test_compare_not_found(self):
        resp = self.client.get('/api/compare?a=20260215_140000&b=99999999_999999')
        self.assertEqual(resp.status_code, 404)

    def test_compare_both_not_found(self):
        resp = self.client.get('/api/compare?a=99999999_111111&b=99999999_222222')
        self.assertEqual(resp.status_code, 404)


if __name__ == '__main__':
    unittest.main()
