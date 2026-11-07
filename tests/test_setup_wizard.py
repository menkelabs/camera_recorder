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
    app_home,
    flask_argv_from_config,
    is_frozen,
    load_install_config,
    resolve_recordings_dir,
    save_install_config,
    should_run_setup,
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

    def test_save_refuses_camera_id_that_is_not_a_non_negative_integer(self):
        """A saved camera id must be a non-negative integer before the profile is written."""
        config_path = os.path.join(self.root, 'swinglab.local.json')
        for label, bad in (
            ('camera1_id', -1),
            ('camera1_id', True),
            ('camera1_id', '2'),
            ('camera1_id', 1.5),
            ('camera2_id', -1),
            ('camera2_id', False),
        ):
            with self.assertRaises(ValueError) as ctx:
                save_install_config(self.root, {label: bad})
            self.assertIn(label, str(ctx.exception))
            self.assertFalse(os.path.exists(config_path))
        save_install_config(self.root, {'camera1_id': 0, 'camera2_id': 4})
        loaded = load_install_config(self.root)
        self.assertEqual(loaded['camera1_id'], 0)
        self.assertEqual(loaded['camera2_id'], 4)

    def test_save_refuses_model_complexity_other_than_0_1_or_2(self):
        """A saved model complexity must be 0, 1, or 2 before the profile is written."""
        config_path = os.path.join(self.root, 'swinglab.local.json')
        for bad in (-1, 3, 9, True, '2'):
            with self.assertRaises(ValueError) as ctx:
                save_install_config(self.root, {'model_complexity': bad})
            self.assertIn('model complexity', str(ctx.exception))
            self.assertFalse(os.path.exists(config_path))
        save_install_config(self.root, {'model_complexity': 0})
        self.assertEqual(load_install_config(self.root)['model_complexity'], 0)
        save_install_config(self.root, {'model_complexity': 1})
        self.assertEqual(load_install_config(self.root)['model_complexity'], 1)

    def test_save_refuses_listen_port_outside_tcp_range(self):
        """A listen port must be an integer from 1 to 65535 before the profile is written."""
        config_path = os.path.join(self.root, 'swinglab.local.json')
        for bad in (0, 65536, -1, True, '5000', 1.5):
            with self.assertRaises(ValueError) as ctx:
                save_install_config(self.root, {'port': bad})
            self.assertIn('listen port', str(ctx.exception))
            self.assertFalse(os.path.exists(config_path))
        save_install_config(self.root, {'port': 1})
        self.assertEqual(load_install_config(self.root)['port'], 1)
        save_install_config(self.root, {'port': 65535})
        self.assertEqual(load_install_config(self.root)['port'], 65535)

    def test_save_refuses_listen_host_that_is_not_a_hostname_or_ip(self):
        """A bind host must not be written when it is a URL, a newline, or not text."""
        config_path = os.path.join(self.root, 'swinglab.local.json')
        for bad in ('0.0.0.0\n', '127.0.0.1 extra', 'http://evil', '../x', '', True, None):
            with self.assertRaises(ValueError) as ctx:
                save_install_config(self.root, {'host': bad})
            self.assertIn('listen host', str(ctx.exception))
            self.assertFalse(os.path.exists(config_path))
        save_install_config(self.root, {'host': '127.0.0.1'})
        self.assertEqual(load_install_config(self.root)['host'], '127.0.0.1')
        save_install_config(self.root, {'host': 'localhost'})
        self.assertEqual(load_install_config(self.root)['host'], 'localhost')

    def test_save_refuses_camera_role_other_than_face_on_or_dtl(self):
        """camera1 and camera2 must be face_on or dtl before the profile is written."""
        config_path = os.path.join(self.root, 'swinglab.local.json')
        for bad in ('side', '', 'Face_On', True, None, 1):
            with self.assertRaises(ValueError) as ctx:
                save_install_config(self.root, {
                    'camera_roles': {'camera1': bad, 'camera2': 'dtl'},
                })
            self.assertIn('camera role', str(ctx.exception))
            self.assertFalse(os.path.exists(config_path))
        with self.assertRaises(ValueError) as ctx:
            save_install_config(self.root, {
                'camera_roles': {'camera1': 'face_on', 'camera2': 'rear'},
            })
        self.assertIn('camera role', str(ctx.exception))
        self.assertFalse(os.path.exists(config_path))
        save_install_config(self.root, {
            'camera_roles': {'camera1': 'face_on', 'camera2': 'face_on'},
        })
        loaded = load_install_config(self.root)
        self.assertEqual(loaded['camera_roles']['camera1'], 'face_on')
        self.assertEqual(loaded['camera_roles']['camera2'], 'face_on')
        save_install_config(self.root, {
            'camera_roles': {'camera1': 'dtl', 'camera2': 'face_on'},
        })
        loaded = load_install_config(self.root)
        self.assertEqual(loaded['camera_roles']['camera1'], 'dtl')
        self.assertEqual(loaded['camera_roles']['camera2'], 'face_on')

    def test_save_refuses_symlink_config(self):
        """swinglab.local.json must not be a symlink that truncates another file."""
        outside = os.path.join(self.root, 'outside')
        os.makedirs(outside)
        secret = os.path.join(outside, 'secret.json')
        with open(secret, 'w', encoding='utf-8') as handle:
            handle.write('secret-bytes')
        link = os.path.join(self.root, 'swinglab.local.json')
        os.symlink(secret, link)
        with self.assertRaises(ValueError) as ctx:
            save_install_config(self.root, {'player_name': 'Pat'})
        self.assertIn('symlink', str(ctx.exception))
        with open(secret, encoding='utf-8') as handle:
            self.assertEqual(handle.read(), 'secret-bytes')
        self.assertTrue(os.path.islink(link))

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

    def test_recordings_dir_refuses_path_that_leaves_project(self):
        """A configured recordings folder must stay inside the project."""
        project = os.path.join(self.root, 'project')
        outside = os.path.join(self.root, 'outside')
        os.makedirs(project)
        os.makedirs(outside)
        secret = os.path.join(outside, 'secret.txt')
        with open(secret, 'w', encoding='utf-8') as handle:
            handle.write('secret-bytes')
        os.symlink(outside, os.path.join(project, 'linked'))
        absolute = os.path.join(self.root, 'absolute-escape')
        for raw in ('../outside', absolute, 'linked', 'takes/../../outside'):
            with self.assertRaises(ValueError) as ctx:
                resolve_recordings_dir(
                    project, env={}, config={'recordings_dir': raw},
                )
            self.assertIn('project', str(ctx.exception))
        with open(secret, encoding='utf-8') as handle:
            self.assertEqual(handle.read(), 'secret-bytes')
        self.assertFalse(os.path.isdir(absolute))

    def test_save_refuses_recordings_dir_that_leaves_project(self):
        """A recordings folder that leaves the project is refused before the profile is written."""
        config_path = os.path.join(self.root, 'swinglab.local.json')
        absolute = os.path.join(os.path.dirname(self.root), 'outside-recordings')
        for bad in ('../outside', absolute, 'takes/../../outside', 12):
            with self.assertRaises(ValueError) as ctx:
                save_install_config(self.root, {'recordings_dir': bad})
            self.assertIn('recordings folder', str(ctx.exception))
            self.assertFalse(os.path.exists(config_path))
        self.assertFalse(os.path.exists(absolute))
        save_install_config(self.root, {'recordings_dir': 'takes'})
        self.assertEqual(load_install_config(self.root)['recordings_dir'], 'takes')

    def test_save_refuses_player_name_a_user_profile_would_refuse(self):
        """A player name must be usable as a local user before the profile is written."""
        config_path = os.path.join(self.root, 'swinglab.local.json')
        for bad in ('', '   ', 'x' * 41, None):
            with self.assertRaises(ValueError) as ctx:
                save_install_config(self.root, {'player_name': bad})
            self.assertIn('player name', str(ctx.exception))
            self.assertFalse(os.path.exists(config_path))
        save_install_config(self.root, {'player_name': 'A' * 40})
        self.assertEqual(load_install_config(self.root)['player_name'], 'A' * 40)

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

    def test_not_frozen_in_source(self):
        self.assertFalse(is_frozen())

    def test_app_home_env_override(self):
        self.assertEqual(app_home({'SWINGLAB_HOME': self.root}), os.path.abspath(self.root))

    def test_app_home_frozen_windows(self):
        with patch('install_config.is_frozen', return_value=True), \
             patch('install_config.os.name', 'nt'):
            home = app_home({'LOCALAPPDATA': self.root})
        self.assertEqual(home, os.path.join(self.root, 'SwingLab'))

    def test_should_run_setup(self):
        self.assertTrue(should_run_setup(config=None))
        self.assertTrue(should_run_setup(setup=True, config={'completed_at': 'x'}))
        self.assertFalse(should_run_setup(skip_setup=True, config=None))
        self.assertFalse(should_run_setup(config={'completed_at': '2026-01-01'}))


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

    def test_merge_refuses_symlink_config(self):
        """The wizard camera config must not be a symlink that truncates another file."""
        with tempfile.TemporaryDirectory() as tmp:
            outside = os.path.join(tmp, 'outside')
            os.makedirs(outside)
            secret = os.path.join(outside, 'secret.json')
            with open(secret, 'w', encoding='utf-8') as handle:
                handle.write('secret-bytes')
            name = 'config_windows.json' if os.name == 'nt' else 'config_linux.json'
            link = os.path.join(tmp, name)
            os.symlink(secret, link)
            with self.assertRaises(ValueError) as ctx:
                merge_platform_camera_config(tmp, 1, 2)
            self.assertIn('symlink', str(ctx.exception))
            with open(secret, encoding='utf-8') as handle:
                self.assertEqual(handle.read(), 'secret-bytes')
            self.assertTrue(os.path.islink(link))


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

    def test_finish_refuses_recordings_dir_that_leaves_project(self):
        """A recordings folder must not escape the project, including via a symlink."""
        project = os.path.join(self.root, 'project')
        outside = os.path.join(self.root, 'outside')
        os.makedirs(project)
        os.makedirs(outside)
        secret = os.path.join(outside, 'secret.txt')
        with open(secret, 'w', encoding='utf-8') as handle:
            handle.write('secret-bytes')
        os.symlink(outside, os.path.join(project, 'linked'))
        absolute = os.path.join(self.root, 'absolute-escape')
        for raw in ('../outside', absolute, 'linked', 'takes/../../outside'):
            result = finish_install(project, {
                'player_name': 'Pat',
                'recordings_dir': raw,
            })
            self.assertFalse(result['ok'], raw)
            self.assertIn('project', result['error'])
            self.assertFalse(
                os.path.isfile(os.path.join(project, 'swinglab.local.json')),
                raw,
            )
            self.assertFalse(
                os.path.isfile(os.path.join(project, 'Start SwingLab.bat')),
                raw,
            )
        with open(secret, encoding='utf-8') as handle:
            self.assertEqual(handle.read(), 'secret-bytes')
        self.assertFalse(os.path.isdir(absolute))

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

    def test_post_finish_refuses_recordings_dir_escape(self):
        status, body, _ = handle_request(
            self.state,
            'POST',
            '/api/finish',
            json.dumps({'recordings_dir': '../outside'}).encode(),
        )
        self.assertEqual(status, 400)
        payload = json.loads(body)
        self.assertFalse(payload['ok'])
        self.assertFalse(os.path.isfile(os.path.join(self.root, 'swinglab.local.json')))

    def test_unknown_route(self):
        status, body, _ = handle_request(self.state, 'GET', '/nope', b'')
        self.assertEqual(status, 404)
        self.assertIn('error', json.loads(body))

    def test_state_includes_frozen_flag(self):
        status, body, _ = handle_request(self.state, 'GET', '/api/state', b'')
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertIn('frozen', payload)
        self.assertFalse(payload['frozen'])


class TestFrozenWizard(unittest.TestCase):
    def test_checks_when_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('setup_wizard.is_frozen', return_value=True), \
                 patch('setup_wizard.resource_path', return_value=os.path.join(tmp, 'missing.html')):
                rows = check_prerequisites(tmp)
        by_id = {row['id']: row for row in rows}
        self.assertTrue(by_id['bundled']['ok'])
        self.assertTrue(by_id['writable']['ok'])
        self.assertNotIn('node', by_id)

    def test_write_launchers_skipped_when_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('setup_wizard.is_frozen', return_value=True):
                self.assertEqual(write_launchers(tmp), [])
            self.assertFalse(os.path.isfile(os.path.join(tmp, 'Start SwingLab.bat')))


class TestLauncherAndPackaging(unittest.TestCase):
    def test_parse_launcher_args(self):
        sys.path.insert(0, os.path.join(project_root, 'scripts'))
        from swinglab_app import parse_launcher_args
        args, rest = parse_launcher_args(['--setup', '--camera1', '2'])
        self.assertTrue(args.setup)
        self.assertFalse(args.skip_setup)
        self.assertEqual(rest, ['--camera1', '2'])
        args, rest = parse_launcher_args(['--skip-setup'])
        self.assertTrue(args.skip_setup)

    def test_packaging_files_exist(self):
        self.assertTrue(os.path.isfile(os.path.join(project_root, 'packaging', 'swinglab.spec')))
        self.assertTrue(os.path.isfile(os.path.join(project_root, 'packaging', 'swinglab.iss')))
        self.assertTrue(os.path.isfile(os.path.join(project_root, 'scripts', 'build_installer.py')))
        self.assertTrue(os.path.isfile(os.path.join(project_root, 'scripts', 'swinglab_app.py')))


if __name__ == '__main__':
    unittest.main()
