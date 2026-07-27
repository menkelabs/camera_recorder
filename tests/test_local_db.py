"""
Edge-case tests for the local SQLite stats DB.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'scripts'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'tests'))

from local_db import LocalDB, get_db, reset_db_cache  # noqa: E402
from practice_reports import build_progress_from_stats  # noqa: E402
from practice_settings import (  # noqa: E402
    load_practice_settings,
    set_reference_timestamp,
    update_practice_settings,
)
from recording_meta import (  # noqa: E402
    attach_meta_to_pairs,
    delete_recording_meta,
    get_recording_meta,
    list_favorites,
    update_recording_meta,
)


def _sample_analysis(ts='20260715_120000', score=80.0, shoulder=45.0):
    return {
        'timestamp': ts,
        'camera1': {
            'summary': {'tempo_ratio': 3.0, 'max_sway_right': 2.0, 'max_head_sway_right': 1.0},
            'detection_rate': 95.0,
        },
        'camera2': {
            'summary': {
                'max_shoulder_turn': shoulder,
                'max_hip_turn': 20.0,
                'max_x_factor': 25.0,
            },
            'detection_rate': 90.0,
        },
        'score': {'score': score, 'grade': 'B'},
    }


class TestLocalDBCore(unittest.TestCase):
    def setUp(self):
        reset_db_cache()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        reset_db_cache()
        self.tmp.cleanup()

    def test_creates_db_file(self):
        db = get_db(self.dir)
        self.assertTrue(os.path.isfile(db.path))
        self.assertEqual(db.integrity_check(), 'ok')

    def test_migrate_recording_meta_json(self):
        with open(os.path.join(self.dir, 'recording_meta.json'), 'w') as f:
            json.dump({
                'version': 1,
                'recordings': {
                    '20260715_120000': {
                        'favorite': True,
                        'notes': 'from json',
                        'tags': ['legacy'],
                    },
                    'bad-ts': {'favorite': True},
                },
            }, f)
        reset_db_cache()
        meta = get_recording_meta(self.dir, '20260715_120000')
        self.assertTrue(meta['favorite'])
        self.assertEqual(meta['notes'], 'from json')
        self.assertEqual(meta['tags'], ['legacy'])
        # Invalid legacy keys skipped
        with self.assertRaises(ValueError):
            get_recording_meta(self.dir, 'bad-ts')

    def test_migrate_practice_settings_json(self):
        with open(os.path.join(self.dir, 'practice_settings.json'), 'w') as f:
            json.dump({
                'version': 1,
                'reference_timestamp': '20260715_120000',
                'metronome': {'enabled': True, 'bpm': 72},
            }, f)
        reset_db_cache()
        settings = load_practice_settings(self.dir)
        self.assertEqual(settings['reference_timestamp'], '20260715_120000')
        self.assertTrue(settings['metronome']['enabled'])
        self.assertEqual(settings['metronome']['bpm'], 72)
        # Defaults filled for missing sections
        self.assertIn('camera_roles', settings)

    def test_corrupt_json_does_not_block_db(self):
        with open(os.path.join(self.dir, 'recording_meta.json'), 'w') as f:
            f.write('{not-json')
        with open(os.path.join(self.dir, 'practice_settings.json'), 'w') as f:
            f.write('[]')
        reset_db_cache()
        db = get_db(self.dir)
        self.assertEqual(db.integrity_check(), 'ok')
        meta = get_recording_meta(self.dir, '20260715_120000')
        self.assertFalse(meta['favorite'])

    def test_import_analysis_json_into_swing_stats(self):
        path = os.path.join(self.dir, 'analysis_20260715_120000.json')
        with open(path, 'w') as f:
            json.dump(_sample_analysis(), f)
        reset_db_cache()
        rows = get_db(self.dir).list_swing_stats()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['score'], 80.0)
        self.assertEqual(rows[0]['metrics']['max_shoulder_turn'], 45.0)

    def test_upsert_replaces_stats_for_same_timestamp(self):
        db = get_db(self.dir)
        db.upsert_swing_stats(_sample_analysis(score=70, shoulder=30))
        db.upsert_swing_stats(_sample_analysis(score=90, shoulder=50))
        rows = db.list_swing_stats()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['score'], 90.0)
        self.assertEqual(rows[0]['metrics']['max_shoulder_turn'], 50.0)

    def test_delete_recording_clears_meta_and_stats(self):
        update_recording_meta(self.dir, '20260715_120000', favorite=True, notes='x')
        get_db(self.dir).upsert_swing_stats(_sample_analysis())
        delete_recording_meta(self.dir, '20260715_120000')
        self.assertEqual(list_favorites(self.dir), [])
        self.assertEqual(get_db(self.dir).list_swing_stats(), [])

    def test_notes_and_tags_limits(self):
        long_notes = 'n' * 5000
        tags = [f'tag{i}' for i in range(50)] + ['', '  ', 'dup', 'dup']
        meta = update_recording_meta(
            self.dir, '20260715_120000', notes=long_notes, tags=tags,
        )
        self.assertEqual(len(meta['notes']), 2000)
        self.assertLessEqual(len(meta['tags']), 20)
        self.assertNotIn('', meta['tags'])

    def test_invalid_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            update_recording_meta(self.dir, 'nope', favorite=True)
        with self.assertRaises(ValueError):
            get_db(self.dir).upsert_swing_stats({'timestamp': 'x'})

    def test_json_mirror_written(self):
        update_recording_meta(self.dir, '20260715_120000', favorite=True, notes='mirrored')
        path = os.path.join(self.dir, 'recording_meta.json')
        self.assertTrue(os.path.isfile(path))
        with open(path) as f:
            data = json.load(f)
        self.assertTrue(data['recordings']['20260715_120000']['favorite'])

    def test_reference_and_roles_roundtrip(self):
        update_practice_settings(self.dir, {
            'camera_roles': {'camera1': 'dtl', 'camera2': 'dtl'},  # invalid same → fixed
            'metronome': {'bpm': 80},
        })
        settings = load_practice_settings(self.dir)
        self.assertNotEqual(settings['camera_roles']['camera1'], settings['camera_roles']['camera2'])
        set_reference_timestamp(self.dir, '20260715_120000')
        self.assertEqual(load_practice_settings(self.dir)['reference_timestamp'], '20260715_120000')
        set_reference_timestamp(self.dir, None)
        self.assertIsNone(load_practice_settings(self.dir)['reference_timestamp'])

    def test_progress_from_stats_empty_and_delta(self):
        empty = build_progress_from_stats([])
        self.assertEqual(empty['count'], 0)
        self.assertIsNone(empty['score_delta'])

        db = get_db(self.dir)
        db.upsert_swing_stats(_sample_analysis('20260715_120000', score=70))
        db.upsert_swing_stats(_sample_analysis('20260716_120000', score=85))
        progress = build_progress_from_stats(db.list_swing_stats())
        self.assertEqual(progress['count'], 2)
        self.assertEqual(progress['score_delta'], 15.0)
        self.assertEqual(progress['latest_score'], 85.0)

    def test_concurrent_meta_updates(self):
        errors = []

        def worker(i):
            try:
                update_recording_meta(
                    self.dir, '20260715_120000',
                    notes=f'n{i}', favorite=(i % 2 == 0),
                )
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        meta = get_recording_meta(self.dir, '20260715_120000')
        self.assertTrue(meta['notes'].startswith('n'))

    def test_attach_meta_to_pairs(self):
        update_recording_meta(self.dir, '20260715_120000', favorite=True, notes='x')
        out = attach_meta_to_pairs(self.dir, [{'timestamp': '20260715_120000'}])
        self.assertTrue(out[0]['favorite'])

    def test_practice_events(self):
        db = get_db(self.dir)
        eid = db.add_event('session_start', payload={'count': 0})
        self.assertGreater(eid, 0)
        events = db.list_events()
        self.assertEqual(events[0]['event_type'], 'session_start')

    def test_env_db_path_override(self):
        custom = os.path.join(self.dir, 'custom', 'stats.db')
        os.environ['SWINGLAB_DB_PATH'] = custom
        try:
            reset_db_cache()
            db = get_db(self.dir)
            self.assertEqual(db.path, custom)
            self.assertTrue(os.path.isfile(custom))
        finally:
            del os.environ['SWINGLAB_DB_PATH']
            reset_db_cache()

    def test_stats_summary(self):
        update_recording_meta(self.dir, '20260715_120000', favorite=True)
        get_db(self.dir).upsert_swing_stats(_sample_analysis())
        summary = get_db(self.dir).stats_summary()
        self.assertEqual(summary['swing_count'], 1)
        self.assertEqual(summary['favorite_count'], 1)
        self.assertEqual(summary['integrity'], 'ok')

    def test_reopen_is_idempotent_migration(self):
        update_recording_meta(self.dir, '20260715_120000', favorite=True)
        reset_db_cache()
        get_db(self.dir)
        reset_db_cache()
        get_db(self.dir)
        self.assertEqual(list_favorites(self.dir), ['20260715_120000'])


class TestLocalDBFlaskProgress(unittest.TestCase):
    def setUp(self):
        reset_db_cache()
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        import flask_gui
        self.fg = flask_gui
        self._orig = flask_gui._get_recordings_dir
        flask_gui._get_recordings_dir = lambda: self.dir
        self.client = flask_gui.app.test_client()

    def tearDown(self):
        self.fg._get_recordings_dir = self._orig
        reset_db_cache()
        self.tmp.cleanup()

    def test_progress_api_reads_sqlite(self):
        get_db(self.dir).upsert_swing_stats(_sample_analysis('20260715_120000', score=70))
        get_db(self.dir).upsert_swing_stats(_sample_analysis('20260716_120000', score=90))
        resp = self.client.get('/api/progress')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['latest_score'], 90.0)
        self.assertEqual(data['score_delta'], 20.0)


if __name__ == '__main__':
    unittest.main()
