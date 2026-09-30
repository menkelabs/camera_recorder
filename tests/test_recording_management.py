"""
Tests for recording management feature:
  - Listing recordings
  - Deleting recordings (single, bulk)
  - Age-based cleanup
"""

import sys
import os
import json
import tempfile
import shutil
import time
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'scripts'))

from flask_gui import (
    app, CameraManager,
    _list_recording_pairs, _delete_recording_pair, _get_recordings_dir,
)


class TestListRecordingPairs(unittest.TestCase):
    """Test _list_recording_pairs helper."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_pair(self, ts):
        for cam in ['camera1', 'camera2']:
            path = os.path.join(self.tmpdir, f'recording_{ts}_{cam}.mp4')
            with open(path, 'wb') as f:
                f.write(b'\x00' * 1024)  # 1KB fake file

    def test_empty_dir(self):
        with patch('flask_gui._get_recordings_dir', return_value=self.tmpdir):
            pairs = _list_recording_pairs()
        self.assertEqual(pairs, [])

    def test_finds_pairs(self):
        self._create_pair('20260215_140000')
        self._create_pair('20260215_150000')
        with patch('flask_gui._get_recordings_dir', return_value=self.tmpdir):
            pairs = _list_recording_pairs()
        self.assertEqual(len(pairs), 2)

    def test_sorted_newest_first(self):
        self._create_pair('20260210_100000')
        self._create_pair('20260215_150000')
        self._create_pair('20260212_120000')
        with patch('flask_gui._get_recordings_dir', return_value=self.tmpdir):
            pairs = _list_recording_pairs()
        timestamps = [p['timestamp'] for p in pairs]
        self.assertEqual(timestamps, ['20260215_150000', '20260212_120000', '20260210_100000'])

    def test_pair_metadata(self):
        self._create_pair('20260215_140000')
        with patch('flask_gui._get_recordings_dir', return_value=self.tmpdir):
            pairs = _list_recording_pairs()
        p = pairs[0]
        self.assertEqual(p['timestamp'], '20260215_140000')
        self.assertIn('date', p)
        self.assertIn('camera1_size', p)
        self.assertIn('camera2_size', p)
        self.assertIn('total_size', p)
        self.assertEqual(p['camera1_size'], 1024)
        self.assertEqual(p['camera2_size'], 1024)
        self.assertEqual(p['total_size'], 2048)

    def test_nonexistent_dir(self):
        with patch('flask_gui._get_recordings_dir', return_value='/nonexistent/path'):
            pairs = _list_recording_pairs()
        self.assertEqual(pairs, [])

    def test_ignores_non_recording_files(self):
        self._create_pair('20260215_140000')
        with open(os.path.join(self.tmpdir, 'notes.txt'), 'w') as f:
            f.write('notes')
        with patch('flask_gui._get_recordings_dir', return_value=self.tmpdir):
            pairs = _list_recording_pairs()
        self.assertEqual(len(pairs), 1)


class TestDeleteRecordingPair(unittest.TestCase):
    """Test _delete_recording_pair helper."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_pair(self, ts):
        for cam in ['camera1', 'camera2']:
            path = os.path.join(self.tmpdir, f'recording_{ts}_{cam}.mp4')
            with open(path, 'wb') as f:
                f.write(b'\x00' * 512)

    def test_delete_existing(self):
        self._create_pair('20260215_140000')
        with patch('flask_gui._get_recordings_dir', return_value=self.tmpdir):
            result = _delete_recording_pair('20260215_140000')
        self.assertEqual(len(result['deleted']), 2)
        self.assertFalse(os.path.exists(
            os.path.join(self.tmpdir, 'recording_20260215_140000_camera1.mp4')))

    def test_delete_nonexistent(self):
        with patch('flask_gui._get_recordings_dir', return_value=self.tmpdir):
            result = _delete_recording_pair('20260215_140000')
        self.assertEqual(result['deleted'], [])

    def test_invalid_timestamp_format(self):
        result = _delete_recording_pair('invalid')
        self.assertIn('error', result)


class TestRecordingManagementAPI(unittest.TestCase):
    """Test recording management Flask endpoints."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        self.tmpdir = tempfile.mkdtemp()

        import flask_gui
        self.mgr = CameraManager()
        flask_gui.camera_manager = self.mgr

        self._patcher = patch('flask_gui._get_recordings_dir', return_value=self.tmpdir)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        import flask_gui
        flask_gui.camera_manager = None
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _create_pair(self, ts):
        for cam in ['camera1', 'camera2']:
            path = os.path.join(self.tmpdir, f'recording_{ts}_{cam}.mp4')
            with open(path, 'wb') as f:
                f.write(b'\x00' * 1024)

    def test_list_empty(self):
        resp = self.client.get('/api/recordings')
        data = json.loads(resp.data)
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['recordings'], [])

    def test_list_with_recordings(self):
        self._create_pair('20260215_140000')
        self._create_pair('20260215_150000')
        resp = self.client.get('/api/recordings')
        data = json.loads(resp.data)
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['total_size'], 4096)

    def test_delete_single(self):
        self._create_pair('20260215_140000')
        resp = self.client.delete('/api/recordings/20260215_140000')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data['deleted']), 2)

    def test_delete_invalid_timestamp(self):
        resp = self.client.delete('/api/recordings/invalid')
        self.assertEqual(resp.status_code, 400)

    def test_delete_rejects_other_users_recording(self):
        from local_db import get_db, reset_db_cache

        reset_db_cache()
        self._create_pair('20260215_140000')
        db = get_db(self.tmpdir)
        other = db.create_user('Player 2')['id']
        db.claim_recording('20260215_140000', user_id=other)
        resp = self.client.delete('/api/recordings/20260215_140000')
        self.assertEqual(resp.status_code, 403)
        self.assertIn('another player', resp.get_json()['error'])
        self.assertTrue(os.path.exists(
            os.path.join(self.tmpdir, 'recording_20260215_140000_camera1.mp4')
        ))
        reset_db_cache()

    def test_delete_fails_closed_when_owner_lookup_fails(self):
        self._create_pair('20260215_140000')
        with patch('flask_gui.get_db', side_effect=RuntimeError('db down')):
            result = _delete_recording_pair('20260215_140000')
        self.assertIn('error', result)
        self.assertIn('verify recording owner', result['error'])
        self.assertTrue(os.path.exists(
            os.path.join(self.tmpdir, 'recording_20260215_140000_camera1.mp4')
        ))

    def test_bulk_delete(self):
        self._create_pair('20260215_140000')
        self._create_pair('20260215_150000')
        resp = self.client.delete('/api/recordings',
                                  json={'timestamps': ['20260215_140000', '20260215_150000']})
        data = json.loads(resp.data)
        self.assertEqual(data['deleted_count'], 2)

    def test_bulk_delete_empty(self):
        resp = self.client.delete('/api/recordings', json={'timestamps': []})
        self.assertEqual(resp.status_code, 400)

    def test_cleanup_by_age(self):
        # Create old recording (31 days ago timestamp)
        old_dt = datetime.now() - timedelta(days=31)
        old_ts = old_dt.strftime('%Y%m%d_%H%M%S')
        self._create_pair(old_ts)
        # Create recent recording
        self._create_pair(datetime.now().strftime('%Y%m%d_%H%M%S'))

        resp = self.client.post('/api/recordings/cleanup',
                                json={'max_age_days': 30})
        data = json.loads(resp.data)
        self.assertEqual(data['deleted_count'], 1)

    def _old_timestamp(self, days=31):
        return (datetime.now() - timedelta(days=days)).strftime('%Y%m%d_%H%M%S')

    def test_cleanup_skips_other_users_recording(self):
        from local_db import get_db, reset_db_cache

        reset_db_cache()
        old_ts = self._old_timestamp()
        self._create_pair(old_ts)
        db = get_db(self.tmpdir)
        other = db.create_user('Player 2')['id']
        db.claim_recording(old_ts, user_id=other)
        resp = self.client.post('/api/recordings/cleanup', json={'max_age_days': 30})
        data = json.loads(resp.data)
        self.assertEqual(data['deleted_count'], 0)
        self.assertGreaterEqual(data['skipped_count'], 1)
        self.assertTrue(any(item.get('reason') == 'owned' for item in data['skipped']))
        self.assertTrue(os.path.exists(
            os.path.join(self.tmpdir, f'recording_{old_ts}_camera1.mp4')
        ))
        reset_db_cache()

    def test_cleanup_skips_reference_and_favorite(self):
        from local_db import reset_db_cache
        from practice_settings import set_reference_timestamp
        from recording_meta import update_recording_meta

        reset_db_cache()
        ref_ts = self._old_timestamp(32)
        fav_ts = self._old_timestamp(33)
        self._create_pair(ref_ts)
        self._create_pair(fav_ts)
        set_reference_timestamp(self.tmpdir, ref_ts)
        update_recording_meta(self.tmpdir, fav_ts, favorite=True)
        resp = self.client.post('/api/recordings/cleanup', json={'max_age_days': 30})
        data = json.loads(resp.data)
        self.assertEqual(data['deleted_count'], 0)
        reasons = {item['reason'] for item in data['skipped']}
        self.assertIn('reference', reasons)
        self.assertIn('favorite', reasons)
        self.assertTrue(os.path.exists(
            os.path.join(self.tmpdir, f'recording_{ref_ts}_camera1.mp4')
        ))
        self.assertTrue(os.path.exists(
            os.path.join(self.tmpdir, f'recording_{fav_ts}_camera1.mp4')
        ))
        reset_db_cache()

    def test_cleanup_missing_param(self):
        resp = self.client.post('/api/recordings/cleanup', json={})
        self.assertEqual(resp.status_code, 400)

    def test_cleanup_invalid_days(self):
        resp = self.client.post('/api/recordings/cleanup',
                                json={'max_age_days': 0})
        self.assertEqual(resp.status_code, 400)

    def test_stats_endpoint(self):
        self._create_pair('20260215_140000')
        resp = self.client.get('/api/recordings/stats')
        data = json.loads(resp.data)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['total_size'], 2048)


if __name__ == '__main__':
    unittest.main()
