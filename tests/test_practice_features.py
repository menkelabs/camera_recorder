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
        r = self.client.get('/')
        html = r.data.decode('utf-8')
        self.assertIn('data-tab="progress"', html)
        self.assertIn('score-header', html)
        self.assertIn('Export HTML', html)
        self.assertIn('fav-btn', html)


if __name__ == '__main__':
    unittest.main()
