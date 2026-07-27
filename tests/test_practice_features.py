"""
Unit tests for swing score, recording meta, and practice reports.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'scripts'))

from swing_score import grade_from_score, rate_value, score_analysis
from recording_meta import (
    attach_meta_to_pairs,
    delete_recording_meta,
    get_recording_meta,
    list_favorites,
    update_recording_meta,
)
from practice_reports import analysis_to_csv, analysis_to_html_report, build_progress_series


def _good_analysis():
    """Synthetic analysis with mostly 'good' summary values."""
    return {
        'timestamp': '20260715_120000',
        'camera1': {
            'summary': {
                'tempo_ratio': 3.0,
                'max_sway_left': -5,
                'max_sway_right': 8,
                'max_head_sway_left': -2,
                'max_head_sway_right': 3,
                'max_spine_tilt': 5,
                'address_knee_flex': 160,
                'max_weight_shift_forward': 65,
            }
        },
        'camera2': {
            'summary': {
                'max_shoulder_turn': 80,
                'max_hip_turn': 40,
                'max_x_factor': 40,
                'address_spine_angle': 30,
                'min_lead_arm_angle': 170,
            }
        },
    }


def _poor_analysis():
    return {
        'timestamp': '20260715_130000',
        'camera1': {
            'summary': {
                'tempo_ratio': 1.0,
                'max_sway_left': -80,
                'max_sway_right': 90,
                'max_head_sway_left': -40,
                'max_head_sway_right': 50,
                'max_spine_tilt': 40,
                'address_knee_flex': 100,
                'max_weight_shift_forward': 10,
            }
        },
        'camera2': {
            'summary': {
                'max_shoulder_turn': 20,
                'max_hip_turn': 5,
                'max_x_factor': 5,
                'address_spine_angle': 5,
                'min_lead_arm_angle': 100,
            }
        },
    }


class TestRateAndGrade(unittest.TestCase):
    def test_rate_good_ok_needs_work(self):
        self.assertEqual(rate_value(70, (60, 100), (40, 60)), 'good')
        self.assertEqual(rate_value(50, (60, 100), (40, 60)), 'ok')
        self.assertEqual(rate_value(10, (60, 100), (40, 60)), 'needs_work')
        self.assertIsNone(rate_value(None, (60, 100), (40, 60)))

    def test_grade_bands(self):
        self.assertEqual(grade_from_score(95), 'A')
        self.assertEqual(grade_from_score(85), 'B')
        self.assertEqual(grade_from_score(75), 'C')
        self.assertEqual(grade_from_score(65), 'D')
        self.assertEqual(grade_from_score(40), 'F')
        self.assertIsNone(grade_from_score(None))


class TestScoreAnalysis(unittest.TestCase):
    def test_good_swing_high_score(self):
        result = score_analysis(_good_analysis())
        self.assertIsNotNone(result['score'])
        self.assertGreaterEqual(result['score'], 80)
        self.assertIn(result['grade'], ('A', 'B'))
        self.assertEqual(result['rated_count'], result['metric_count'])
        self.assertTrue(result['strengths'])

    def test_poor_swing_low_score(self):
        result = score_analysis(_poor_analysis())
        self.assertIsNotNone(result['score'])
        self.assertLessEqual(result['score'], 40)
        self.assertEqual(result['grade'], 'F')
        self.assertTrue(result['focus_areas'])

    def test_empty_analysis(self):
        result = score_analysis({'camera1': None, 'camera2': None})
        self.assertIsNone(result['score'])
        self.assertEqual(result['rated_count'], 0)

    def test_breakdown_has_all_metrics(self):
        result = score_analysis(_good_analysis())
        self.assertEqual(len(result['breakdown']), 11)


class TestRecordingMeta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_meta(self):
        meta = get_recording_meta(self.dir, '20260715_120000')
        self.assertFalse(meta['favorite'])
        self.assertEqual(meta['notes'], '')
        self.assertEqual(meta['tags'], [])

    def test_update_favorite_and_notes(self):
        meta = update_recording_meta(
            self.dir, '20260715_120000',
            favorite=True, notes='Good tempo', tags=['tempo', 'keep'],
        )
        self.assertTrue(meta['favorite'])
        self.assertEqual(meta['notes'], 'Good tempo')
        self.assertEqual(meta['tags'], ['tempo', 'keep'])

        again = get_recording_meta(self.dir, '20260715_120000')
        self.assertTrue(again['favorite'])

    def test_invalid_timestamp(self):
        with self.assertRaises(ValueError):
            get_recording_meta(self.dir, 'not-a-ts')

    def test_list_favorites_and_delete(self):
        update_recording_meta(self.dir, '20260715_120000', favorite=True)
        update_recording_meta(self.dir, '20260715_130000', favorite=False)
        self.assertEqual(list_favorites(self.dir), ['20260715_120000'])
        delete_recording_meta(self.dir, '20260715_120000')
        self.assertEqual(list_favorites(self.dir), [])

    def test_attach_meta_to_pairs(self):
        update_recording_meta(self.dir, '20260715_120000', favorite=True, notes='x')
        pairs = [{'timestamp': '20260715_120000', 'total_size': 1}]
        out = attach_meta_to_pairs(self.dir, pairs)
        self.assertTrue(out[0]['favorite'])
        self.assertEqual(out[0]['notes'], 'x')


class TestPracticeReports(unittest.TestCase):
    def test_progress_series(self):
        analyses = [_good_analysis(), _poor_analysis()]
        # Ensure chronological order uses timestamps
        progress = build_progress_series(analyses)
        self.assertEqual(progress['count'], 2)
        self.assertEqual(len(progress['points']), 2)
        self.assertIn('score', progress['series'])
        self.assertIsNotNone(progress['latest_score'])
        self.assertIsNotNone(progress['score_delta'])

    def test_csv_export(self):
        csv_text = analysis_to_csv(_good_analysis())
        self.assertIn('Swing Score', csv_text)
        self.assertIn('Shoulder Turn', csv_text)

    def test_html_export(self):
        html = analysis_to_html_report(_good_analysis())
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('Golf Swing Analysis Report', html)
        self.assertIn('Metric breakdown', html)


class TestPracticeAPIEndpoints(unittest.TestCase):
    """Flask API smoke tests for the new practice features."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        import flask_gui
        self.fg = flask_gui
        self._orig_dir = flask_gui._get_recordings_dir
        flask_gui._get_recordings_dir = lambda: self.tmp.name
        os.makedirs(self.tmp.name, exist_ok=True)

        # Seed one analysis file
        path = os.path.join(self.tmp.name, 'analysis_20260715_120000.json')
        with open(path, 'w') as f:
            json.dump(_good_analysis(), f)

        # Dummy video pair so list_recordings finds something
        open(os.path.join(self.tmp.name, 'recording_20260715_120000_camera1.mp4'), 'wb').close()
        open(os.path.join(self.tmp.name, 'recording_20260715_120000_camera2.mp4'), 'wb').close()

        self.client = flask_gui.app.test_client()

    def tearDown(self):
        self.fg._get_recordings_dir = self._orig_dir
        self.tmp.cleanup()

    def test_meta_roundtrip(self):
        r = self.client.post(
            '/api/recordings/20260715_120000/meta',
            json={'favorite': True, 'notes': 'nice', 'tags': ['a']},
        )
        self.assertEqual(r.status_code, 200)
        body = r.get_json()
        self.assertTrue(body['favorite'])
        self.assertEqual(body['notes'], 'nice')

        r2 = self.client.get('/api/recordings/20260715_120000/meta')
        self.assertTrue(r2.get_json()['favorite'])

    def test_list_recordings_includes_meta(self):
        self.client.post('/api/recordings/20260715_120000/meta', json={'favorite': True})
        r = self.client.get('/api/recordings')
        data = r.get_json()
        self.assertGreaterEqual(data['favorite_count'], 1)
        self.assertTrue(data['recordings'][0]['favorite'])

    def test_progress_endpoint(self):
        r = self.client.get('/api/progress')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertGreaterEqual(data['count'], 1)
        self.assertIn('points', data)

    def test_score_endpoint_saved(self):
        r = self.client.get('/api/analysis/score?timestamp=20260715_120000')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('grade', data)
        self.assertIsNotNone(data['score'])

    def test_export_html(self):
        r = self.client.get('/api/analysis/export?format=html&timestamp=20260715_120000')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'<!DOCTYPE html>', r.data)

    def test_export_csv(self):
        r = self.client.get('/api/analysis/export?format=csv&timestamp=20260715_120000')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Swing Score', r.data)

    def test_template_has_progress_and_score(self):
        # v1 markup lives at /legacy once frontend/dist is built
        r = self.client.get('/legacy')
        html = r.data.decode('utf-8')
        self.assertIn('data-tab="progress"', html)
        self.assertIn('score-header', html)
        self.assertIn('Export HTML', html)
        self.assertIn('fav-btn', html)
        self.assertIn('checklist-panel', html)
        self.assertIn('drills-panel', html)
        self.assertIn('ref-btn', html)
        self.assertIn('Clip Cam1', html)
        self.assertIn('Pre-Record Checklist', html)
        self.assertIn('session-cb', html)
        self.assertIn('metro-cb', html)
        self.assertIn('usb-warn', html)
        self.assertIn('cam1-role', html)
        self.assertIn('practice-tools', html)
        self.assertIn('Session mode', html)
        self.assertIn('Tempo metronome', html)


class TestDrillsAndReference(unittest.TestCase):
    def test_poor_swing_includes_drills(self):
        result = score_analysis(_poor_analysis())
        self.assertTrue(result['drills'])
        self.assertTrue(all('tip' in d for d in result['drills']))

    def test_good_swing_few_or_no_drills(self):
        result = score_analysis(_good_analysis())
        # Good swing should have few needs_work → few drills
        self.assertLessEqual(len(result['drills']), 2)

    def test_reference_roundtrip(self):
        from practice_settings import get_reference_timestamp, set_reference_timestamp
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(get_reference_timestamp(tmp))
            set_reference_timestamp(tmp, '20260715_120000')
            self.assertEqual(get_reference_timestamp(tmp), '20260715_120000')
            set_reference_timestamp(tmp, None)
            self.assertIsNone(get_reference_timestamp(tmp))


class TestClipExporter(unittest.TestCase):
    def test_jpeg_frames_to_mp4(self):
        import cv2
        import numpy as np
        from clip_exporter import jpeg_frames_to_mp4

        frames = []
        for i in range(5):
            img = np.zeros((60, 80, 3), dtype=np.uint8)
            img[:] = (i * 40, 80, 120)
            ok, buf = cv2.imencode('.jpg', img)
            self.assertTrue(ok)
            frames.append(buf.tobytes())

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'clip_test.mp4')
            result = jpeg_frames_to_mp4(frames, out, fps=10.0)
            self.assertTrue(os.path.isfile(out))
            self.assertEqual(result['frame_count'], 5)
            self.assertGreater(os.path.getsize(out), 0)

    def test_empty_frames_raises(self):
        from clip_exporter import jpeg_frames_to_mp4
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                jpeg_frames_to_mp4([], os.path.join(tmp, 'x.mp4'))


class TestChecklistAndReferenceAPI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        import flask_gui
        self.fg = flask_gui
        self._orig_dir = flask_gui._get_recordings_dir
        flask_gui._get_recordings_dir = lambda: self.tmp.name
        os.makedirs(self.tmp.name, exist_ok=True)
        path = os.path.join(self.tmp.name, 'analysis_20260715_120000.json')
        with open(path, 'w') as f:
            json.dump(_good_analysis(), f)
        self.client = flask_gui.app.test_client()
        # Install a manager so checklist works
        self.mgr = flask_gui.CameraManager(camera1_id=0, camera2_id=1)
        flask_gui.camera_manager = self.mgr

    def tearDown(self):
        self.fg._get_recordings_dir = self._orig_dir
        self.fg.camera_manager = None
        self.tmp.cleanup()

    def test_checklist_endpoint(self):
        r = self.client.get('/api/checklist')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('ready', data)
        self.assertIn('items', data)
        self.assertFalse(data['ready'])  # no real cameras in test env
        ids = {i['id'] for i in data['items']}
        self.assertIn('camera1', ids)
        self.assertIn('disk', ids)
        self.assertIn('usb', ids)
        self.assertIn('camera_labels', data)

    def test_reference_api(self):
        r = self.client.post('/api/reference', json={'timestamp': '20260715_120000'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['reference_timestamp'], '20260715_120000')

        r2 = self.client.get('/api/reference')
        self.assertEqual(r2.get_json()['reference_timestamp'], '20260715_120000')
        self.assertTrue(r2.get_json()['has_analysis'])

        r3 = self.client.get('/api/analyses')
        self.assertEqual(r3.get_json()['reference_timestamp'], '20260715_120000')
        self.assertTrue(r3.get_json()['analyses'][0]['is_reference'])

        self.client.post('/api/reference', json={'timestamp': None})
        self.assertIsNone(self.client.get('/api/reference').get_json()['reference_timestamp'])

    def test_export_clip_without_frames(self):
        r = self.client.post('/api/analysis/export-clip', json={'camera': 1})
        self.assertEqual(r.status_code, 400)
        self.assertIn('error', r.get_json())


class TestUsbHealth(unittest.TestCase):
    def test_usb_bus_root(self):
        from usb_health import _usb_bus_root
        self.assertEqual(_usb_bus_root('1-2.3.4:1.0'), '1-2')
        self.assertEqual(_usb_bus_root('3-1'), '3-1')
        self.assertEqual(_usb_bus_root('2-4.1'), '2-4')

    def test_frame_starvation_warning(self):
        from usb_health import frame_starvation_warning
        self.assertIsNone(frame_starvation_warning(True, True))
        self.assertIsNone(frame_starvation_warning(False, False))
        w2 = frame_starvation_warning(True, False)
        self.assertIsNotNone(w2)
        self.assertIn('Camera 2', w2)
        w1 = frame_starvation_warning(False, True)
        self.assertIsNotNone(w1)
        self.assertIn('Camera 1', w1)

    def test_detect_shared_without_v4l(self):
        from usb_health import detect_shared_usb_bus
        result = detect_shared_usb_bus(0, 1)
        self.assertIn('platform_supported', result)
        self.assertIn('shared_bus', result)


class TestPracticeSettingsRoles(unittest.TestCase):
    def test_roles_and_labels(self):
        from practice_settings import (
            camera_labels,
            load_practice_settings,
            update_practice_settings,
        )
        with tempfile.TemporaryDirectory() as tmp:
            data = load_practice_settings(tmp)
            self.assertEqual(data['camera_roles']['camera1'], 'face_on')
            labels = camera_labels(data)
            self.assertEqual(labels['camera1'], 'Face-On')
            self.assertEqual(labels['camera2'], 'Down-the-Line')

            updated = update_practice_settings(tmp, {
                'camera_roles': {'camera1': 'dtl', 'camera2': 'face_on'},
                'metronome': {'enabled': True, 'bpm': 72},
            })
            self.assertEqual(updated['camera_roles']['camera1'], 'dtl')
            self.assertEqual(updated['metronome']['bpm'], 72)
            labels2 = camera_labels(updated)
            self.assertEqual(labels2['camera1'], 'Down-the-Line')

            # Same role on both → auto-correct camera2
            fixed = update_practice_settings(tmp, {
                'camera_roles': {'camera1': 'face_on', 'camera2': 'face_on'},
            })
            self.assertEqual(fixed['camera_roles']['camera1'], 'face_on')
            self.assertEqual(fixed['camera_roles']['camera2'], 'dtl')


class TestSessionAndPracticeSettingsAPI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        import flask_gui
        self.fg = flask_gui
        self._orig_dir = flask_gui._get_recordings_dir
        flask_gui._get_recordings_dir = lambda: self.tmp.name
        os.makedirs(self.tmp.name, exist_ok=True)
        self.client = flask_gui.app.test_client()
        self.mgr = flask_gui.CameraManager(camera1_id=0, camera2_id=1)
        flask_gui.camera_manager = self.mgr

    def tearDown(self):
        self.fg._get_recordings_dir = self._orig_dir
        self.fg.camera_manager = None
        self.tmp.cleanup()

    def test_practice_settings_get_post(self):
        r = self.client.get('/api/practice/settings')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('camera_roles', data)
        self.assertIn('metronome', data)
        self.assertIn('camera_labels', data)

        r2 = self.client.post('/api/practice/settings', json={
            'camera_roles': {'camera1': 'dtl', 'camera2': 'face_on'},
            'metronome': {'enabled': True, 'bpm': 66},
        })
        self.assertEqual(r2.status_code, 200)
        body = r2.get_json()
        self.assertEqual(body['camera_roles']['camera1'], 'dtl')
        self.assertEqual(body['metronome']['bpm'], 66)
        self.assertEqual(body['camera_labels']['camera1'], 'Down-the-Line')

    def test_session_api_requires_checklist(self):
        r = self.client.post('/api/session', json={'enabled': True})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        # No cameras → checklist fails → session stays off
        self.assertFalse(data.get('enabled'))
        self.assertIn('error', data)

    def test_session_next_when_disabled(self):
        r = self.client.post('/api/session/next')
        self.assertEqual(r.status_code, 200)
        self.assertIn('error', r.get_json())

    def test_status_includes_session_and_labels(self):
        r = self.client.get('/api/status')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('session', data)
        self.assertIn('camera_labels', data)
        self.assertIn('practice', data)


if __name__ == '__main__':
    unittest.main()
