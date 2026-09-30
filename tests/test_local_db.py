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
        self.assertEqual(summary['user_count'], 1)
        self.assertEqual(summary['active_user']['name'], 'Player 1')
        self.assertEqual(summary['schema_version'], 2)

    def test_reopen_is_idempotent_migration(self):
        update_recording_meta(self.dir, '20260715_120000', favorite=True)
        reset_db_cache()
        get_db(self.dir)
        reset_db_cache()
        get_db(self.dir)
        self.assertEqual(list_favorites(self.dir), ['20260715_120000'])

    def test_default_user_created(self):
        db = get_db(self.dir)
        users = db.list_users()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]['name'], 'Player 1')
        self.assertTrue(users[0]['is_active'])

    def test_multi_user_stats_and_settings_isolation(self):
        db = get_db(self.dir)
        p1 = db.get_active_user_id()
        p2 = db.create_user('Player 2')['id']

        db.upsert_swing_stats(_sample_analysis('20260715_120000', score=70))
        update_practice_settings(self.dir, {'metronome': {'bpm': 60}})
        update_recording_meta(self.dir, '20260715_120000', favorite=True)

        db.set_active_user(p2)
        db.upsert_swing_stats(_sample_analysis('20260716_120000', score=90))
        update_practice_settings(self.dir, {'metronome': {'bpm': 80}})
        update_recording_meta(self.dir, '20260716_120000', favorite=True, notes='p2')

        self.assertEqual(len(db.list_swing_stats()), 1)
        self.assertEqual(db.list_swing_stats()[0]['score'], 90.0)
        self.assertEqual(load_practice_settings(self.dir)['metronome']['bpm'], 80)
        self.assertEqual(list_favorites(self.dir), ['20260716_120000'])

        db.set_active_user(p1)
        self.assertEqual(len(db.list_swing_stats()), 1)
        self.assertEqual(db.list_swing_stats()[0]['score'], 70.0)
        self.assertEqual(load_practice_settings(self.dir)['metronome']['bpm'], 60)
        self.assertEqual(list_favorites(self.dir), ['20260715_120000'])

    def test_pin_required_to_switch(self):
        db = get_db(self.dir)
        locked = db.create_user('Locked', pin='1234')
        with self.assertRaises(PermissionError):
            db.set_active_user(locked['id'])
        with self.assertRaises(PermissionError):
            db.set_active_user(locked['id'], pin='9999')
        active = db.set_active_user(locked['id'], pin='1234')
        self.assertEqual(active['id'], locked['id'])

    def test_cannot_delete_last_user(self):
        db = get_db(self.dir)
        uid = db.get_active_user_id()
        with self.assertRaises(ValueError):
            db.delete_user(uid)
        other = db.create_user('Two')['id']
        db.delete_user(uid)
        self.assertEqual([u['id'] for u in db.list_users()], [other])
        self.assertEqual(db.get_active_user_id(), other)

    def test_claim_recording_ownership(self):
        db = get_db(self.dir)
        p1 = db.get_active_user_id()
        p2 = db.create_user('Player 2')['id']
        first = db.claim_recording('20260715_120000')
        self.assertEqual(first['user_id'], p1)
        self.assertEqual(db.get_recording_owner('20260715_120000'), p1)
        again = db.claim_recording('20260715_120000')
        self.assertTrue(again.get('already_owned'))
        db.set_active_user(p2)
        with self.assertRaises(PermissionError):
            db.claim_recording('20260715_120000')
        self.assertEqual(db.get_recording_owner('20260715_120000'), p1)

    def test_upsert_stats_follow_camera_roles(self):
        from practice_settings import update_practice_settings

        raw = _sample_analysis('20260715_120000', score=None, shoulder=80)
        # Physical cameras swapped: DTL metrics live on camera1
        swapped = {
            'timestamp': '20260715_120000',
            'camera1': raw['camera2'],
            'camera2': raw['camera1'],
        }
        update_practice_settings(self.dir, {
            'camera_roles': {'camera1': 'dtl', 'camera2': 'face_on'},
        })
        db = get_db(self.dir)
        db.upsert_swing_stats(swapped)
        row = db.list_swing_stats()[0]
        self.assertEqual(row['metrics']['max_shoulder_turn'], 80)
        self.assertEqual(row['metrics']['tempo_ratio'], 3.0)

    def test_upsert_does_not_steal_ownership(self):
        db = get_db(self.dir)
        p1 = db.get_active_user_id()
        p2 = db.create_user('Player 2')['id']
        db.claim_recording('20260715_120000')
        db.set_active_user(p2)
        db.upsert_swing_stats(_sample_analysis('20260715_120000', score=88))
        self.assertEqual(db.get_recording_owner('20260715_120000'), p1)
        self.assertEqual(db.list_swing_stats()[0]['score'], 88.0)

    def test_v1_schema_migrates_to_multi_user(self):
        """Hand-build a v1 DB, then open via LocalDB and expect Player 1 ownership."""
        import sqlite3

        path = os.path.join(self.dir, 'swinglab.db')
        conn = sqlite3.connect(path)
        conn.executescript(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL
            );
            CREATE TABLE app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE settings (
                key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE recording_meta (
                timestamp TEXT PRIMARY KEY,
                favorite INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT
            );
            CREATE TABLE swing_stats (
                timestamp TEXT PRIMARY KEY,
                date TEXT, score REAL, grade TEXT,
                max_shoulder_turn REAL, max_hip_turn REAL, max_x_factor REAL,
                tempo_ratio REAL, max_sway_right REAL, max_head_sway_right REAL,
                detection_rate_cam1 REAL, detection_rate_cam2 REAL,
                source_path TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE practice_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL, timestamp TEXT, payload TEXT,
                created_at TEXT NOT NULL
            );
            INSERT INTO schema_migrations(version, applied_at) VALUES (1, '2026-01-01');
            INSERT INTO recording_meta(timestamp, favorite, notes, tags, updated_at)
            VALUES ('20260715_120000', 1, 'old', '[]', '2026-01-01');
            INSERT INTO swing_stats(
              timestamp, date, score, grade,
              max_shoulder_turn, max_hip_turn, max_x_factor,
              tempo_ratio, max_sway_right, max_head_sway_right,
              detection_rate_cam1, detection_rate_cam2,
              source_path, created_at, updated_at
            ) VALUES (
              '20260715_120000', '2026-07-15', 77.0, 'B',
              40, 20, 20, 3.0, 1.0, 1.0, 90, 90, NULL, 't', 't'
            );
            INSERT INTO settings(key, value, updated_at)
            VALUES ('practice', '{"version":1,"metronome":{"bpm":66}}', 't');
            """
        )
        conn.commit()
        conn.close()

        reset_db_cache()
        os.environ['SWINGLAB_DB_PATH'] = path
        try:
            db = get_db(self.dir)
            self.assertEqual(db.stats_summary()['schema_version'], 2)
            self.assertEqual(db.get_active_user()['name'], 'Player 1')
            self.assertEqual(db.get_recording_owner('20260715_120000'), db.get_active_user_id())
            self.assertEqual(list_favorites(self.dir), ['20260715_120000'])
            self.assertEqual(db.list_swing_stats()[0]['score'], 77.0)
            self.assertEqual(load_practice_settings(self.dir)['metronome']['bpm'], 66)
        finally:
            del os.environ['SWINGLAB_DB_PATH']
            reset_db_cache()


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

    def test_progress_scoped_to_active_user(self):
        db = get_db(self.dir)
        db.upsert_swing_stats(_sample_analysis('20260715_120000', score=70))
        p2 = db.create_user('Player 2')['id']
        db.set_active_user(p2)
        db.upsert_swing_stats(_sample_analysis('20260716_120000', score=95))
        resp = self.client.get('/api/progress')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['latest_score'], 95.0)

    def test_users_api_create_and_switch(self):
        resp = self.client.get('/api/users')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['active_user']['name'], 'Player 1')

        created = self.client.post('/api/users', json={'name': 'Jordan', 'pin': '4321'})
        self.assertEqual(created.status_code, 201)
        uid = created.get_json()['id']

        denied = self.client.post('/api/users/active', json={'user_id': uid})
        self.assertEqual(denied.status_code, 403)

        ok = self.client.post('/api/users/active', json={'user_id': uid, 'pin': '4321'})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.get_json()['active_user']['name'], 'Jordan')

        status = self.client.get('/api/status')
        # This fixture has no CameraManager — fail closed with 503, not a fake 200.
        self.assertEqual(status.status_code, 503)
        self.assertIn('error', status.get_json())

    def test_claim_api_conflict_when_owned(self):
        db = get_db(self.dir)
        db.claim_recording('20260715_120000')
        p2 = db.create_user('Player 2')['id']
        db.set_active_user(p2)
        resp = self.client.post('/api/recordings/20260715_120000/claim')
        self.assertEqual(resp.status_code, 409)
        self.assertIn('already claimed', resp.get_json()['error'])
        self.assertEqual(db.get_recording_owner('20260715_120000'), db.list_users()[0]['id'])

    def test_claim_api_success_unclaimed(self):
        resp = self.client.post('/api/recordings/20260715_120000/claim')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['timestamp'], '20260715_120000')
        self.assertEqual(data['user_id'], get_db(self.dir).get_active_user_id())

    def test_list_recordings_scope_unclaimed(self):
        db = get_db(self.dir)
        db.claim_recording('20260715_120000')
        rec_dir = self.dir
        for ts, cam in (('20260715_120000', 'camera1'), ('20260716_120000', 'camera1')):
            open(os.path.join(rec_dir, f'recording_{ts}_{cam}.mp4'), 'wb').close()
        mine = self.client.get('/api/recordings?scope=mine')
        self.assertEqual(mine.status_code, 200)
        unclaimed = self.client.get('/api/recordings?scope=unclaimed')
        self.assertEqual(unclaimed.status_code, 200)
        unclaimed_ts = {r['timestamp'] for r in unclaimed.get_json()['recordings']}
        self.assertIn('20260716_120000', unclaimed_ts)
        self.assertNotIn('20260715_120000', unclaimed_ts)

    def test_progress_fallback_skips_other_users_files(self):
        db = get_db(self.dir)
        p1 = db.get_active_user_id()
        p2 = db.create_user('Player 2')['id']
        other = _sample_analysis('20260715_120000', score=55)
        path = os.path.join(self.dir, 'analysis_20260715_120000.json')
        with open(path, 'w') as f:
            json.dump(other, f)
        db.claim_recording('20260715_120000', user_id=p2)
        # Active user is still p1; no swing_stats rows yet → JSON fallback
        resp = self.client.get('/api/progress')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['count'], 0)
        self.assertEqual(db.get_recording_owner('20260715_120000'), p2)

    def test_switch_blocked_while_recording(self):
        import flask_gui

        class _Mgr:
            is_recording = True

        prev = flask_gui.camera_manager
        flask_gui.camera_manager = _Mgr()
        try:
            other = self.client.post('/api/users', json={'name': 'Busy'})
            # create itself also blocked while recording
            self.assertEqual(other.status_code, 409)
        finally:
            flask_gui.camera_manager = prev


if __name__ == '__main__':
    unittest.main()
