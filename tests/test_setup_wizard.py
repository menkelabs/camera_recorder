"""Unit tests for the stdlib setup wizard (no pip/npm/cameras)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from install_config import (  # noqa: E402
    flask_argv_from_config,
    load_install_config,
    resolve_recordings_dir,
    save_install_config,
    venv_python,
)
from setup_wizard import (  # noqa: E402
    WizardState,
    check_prerequisites,
    finish_install,
    handle_request,
    merge_platform_camera_config,
    suggest_cameras,
    write_desktop_shortcut,
    write_launchers,
)


class TestInstallConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_load_round_trip(self):
        path = save_install_config(self.root, {
            'camera1_id': 3,
            'camera2_id': 5,
            'player_name': 'Pat',
            'port': 5010,
            'recordings_dir': 'swings',
        })
        self.assertTrue(os.path.isfile(path))
        loaded = load_install_config(self.root)
        self.assertEqual(loaded['camera1_id'], 3)
        self.assertEqual(loaded['player_name'], 'Pat')
        self.assertEqual(loaded['port'], 5010)
        self.assertTrue(loaded['completed_at'])

    def test_missing_config_is_none(self):
        self.assertIsNone(load_install_config(self.root))

    def test_recordings_dir_env_wins(self):
        custom = os.path.join(self.root, 'custom-rec')
        save_install_config(self.root, {'recordings_dir': 'from-file'})
        resolved = resolve_recordings_dir(
            self.root,
            env={'SWINGLAB_RECORDINGS_DIR': custom},
        )
        self.assertEqual(resolved, os.path.abspath(custom))

    def test_recordings_dir_from_config(self):
        save_install_config(self.root, {'recordings_dir': 'from-file'})
        resolved = resolve_recordings_dir(self.root, env={})
        self.assertEqual(resolved, os.path.abspath(os.path.join(self.root, 'from-file')))

    def test_recordings_dir_default(self):
        resolved = resolve_recordings_dir(self.root, env={}, config=None)
        self.assertEqual(resolved, os.path.abspath(os.path.join(self.root, 'recordings')))

    def test_flask_argv(self):
        args = flask_argv_from_config({
            'camera1_id': 0,
            'camera2_id': 2,
            'port': 5001,
            'model_complexity': 0,
        })
        self.assertIn('--camera2', args)
        self.assertIn('2', args)
        self.assertIn('--port', args)
        self.assertIn('5001', args)

    def test_venv_python_missing(self):
        self.assertIsNone(venv_python(self.root))


class TestPrerequisiteChecks(unittest.TestCase):
    def test_project_root_checks(self):
        rows = check_prerequisites(project_root)
        by_id = {row['id']: row for row in rows}
        self.assertTrue(by_id['python']['ok'])
        self.assertTrue(by_id['requirements']['ok'])
        self.assertTrue(by_id['frontend']['ok'])
        self.assertTrue(by_id['writable']['ok'])

    def test_empty_root_fails_required_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = check_prerequisites(tmp)
        by_id = {row['id']: row for row in rows}
        self.assertFalse(by_id['requirements']['ok'])
        self.assertFalse(by_id['frontend']['ok'])


class TestCameraSuggestAndConfig(unittest.TestCase):
    def test_suggest_two_live(self):
        suggested = suggest_cameras([
            {'id': 0, 'status': 'ok'},
            {'id': 2, 'status': 'ok'},
        ])
        self.assertEqual(suggested, {'camera1_id': 0, 'camera2_id': 2})

    def test_suggest_none_uses_platform_default(self):
        suggested = suggest_cameras([])
        self.assertEqual(suggested['camera1_id'], 0)
        self.assertIn(suggested['camera2_id'], (1, 2))

    def test_merge_platform_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = merge_platform_camera_config(
                tmp, 4, 6, detected=[{'id': 4, 'status': 'ok'}],
            )
            self.assertTrue(os.path.isfile(path))
            with open(path, encoding='utf-8') as fh:
                data = json.load(fh)
            self.assertEqual(data['camera1_id'], 4)
            self.assertEqual(data['camera2_id'], 6)
            self.assertEqual(len(data['detected_cameras']), 1)


class TestFinishAndLaunchers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_finish_writes_profile_and_launchers(self):
        result = finish_install(self.root, {
            'camera1_id': 1,
            'camera2_id': 3,
            'player_name': 'Alex',
            'recordings_dir': 'takes',
            'port': 5055,
            'camera_roles': {'camera1': 'dtl', 'camera2': 'face_on'},
        })
        self.assertTrue(result['ok'])
        self.assertEqual(result['url'], 'http://127.0.0.1:5055')
        self.assertTrue(os.path.isdir(os.path.join(self.root, 'takes')))
        self.assertTrue(os.path.isfile(os.path.join(self.root, 'swinglab.local.json')))
        self.assertTrue(os.path.isfile(os.path.join(self.root, 'Start SwingLab.bat')))
        self.assertTrue(os.path.isfile(os.path.join(self.root, 'start-swinglab.sh')))
        loaded = load_install_config(self.root)
        self.assertEqual(loaded['player_name'], 'Alex')
        self.assertEqual(loaded['camera_roles']['camera1'], 'dtl')

    def test_write_launchers_content(self):
        paths = write_launchers(self.root)
        self.assertEqual(len(paths), 2)
        with open(paths[0], encoding='utf-8') as fh:
            bat = fh.read()
        self.assertIn('start_swinglab.py', bat)

    def test_desktop_shortcut_when_desktop_exists(self):
        home = os.path.join(self.root, 'home')
        desktop = os.path.join(home, 'Desktop')
        os.makedirs(desktop)
        with patch('os.path.expanduser', return_value=home):
            dest = write_desktop_shortcut(self.root)
        self.assertIsNotNone(dest)
        self.assertTrue(os.path.isfile(dest))

    def test_desktop_shortcut_skipped_without_desktop(self):
        home = os.path.join(self.root, 'nodsk')
        os.makedirs(home)
        with patch('os.path.expanduser', return_value=home):
            self.assertIsNone(write_desktop_shortcut(self.root))


class TestWizardHttp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, 'frontend'))
        with open(os.path.join(self.root, 'requirements.txt'), 'w', encoding='utf-8'):
            pass
        with open(os.path.join(self.root, 'frontend', 'package.json'), 'w', encoding='utf-8') as fh:
            fh.write('{}')
        self.state = WizardState(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_get_index(self):
        status, body, ctype = handle_request(self.state, 'GET', '/', b'')
        self.assertEqual(status, 200)
        self.assertIn('text/html', ctype)
        self.assertIn(b'SwingLab', body)

    def test_post_check(self):
        status, body, _ = handle_request(self.state, 'POST', '/api/check', b'{}')
        self.assertEqual(status, 200)
        payload = json.loads(body)
        ids = {row['id'] for row in payload['checks']}
        self.assertIn('python', ids)
        self.assertIn('node', ids)

    def test_post_finish(self):
        status, body, _ = handle_request(
            self.state,
            'POST',
            '/api/finish',
            json.dumps({'player_name': 'Kim', 'port': 5002}).encode(),
        )
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['url'], 'http://127.0.0.1:5002')
        self.assertEqual(load_install_config(self.root)['player_name'], 'Kim')

    def test_unknown_route(self):
        status, body, _ = handle_request(self.state, 'GET', '/nope', b'')
        self.assertEqual(status, 404)
        self.assertIn('error', json.loads(body))


if __name__ == '__main__':
    unittest.main()
