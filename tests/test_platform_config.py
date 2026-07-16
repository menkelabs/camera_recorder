"""
Unit tests for cross-platform camera configuration.

These tests mock sys.platform so the same suite validates Windows and Linux
behaviour without needing cameras or the other OS.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'tests'))

from camera_utils import (
    create_camera_capture,
    describe_platform_setup,
    get_camera_ids,
    get_config_filename,
    get_config_path,
    get_default_camera_ids,
    get_opencv_backend,
    get_platform_info,
    load_camera_config,
    save_camera_config,
)
import test_utils


class TestConfigFilenames(unittest.TestCase):
    def test_windows_aliases(self):
        self.assertEqual(get_config_filename('win32'), 'config_windows.json')
        self.assertEqual(get_config_filename('windows'), 'config_windows.json')

    def test_linux_aliases(self):
        self.assertEqual(get_config_filename('linux'), 'config_linux.json')
        self.assertEqual(get_config_filename('linux2'), 'config_linux.json')

    def test_macos_alias(self):
        self.assertEqual(get_config_filename('darwin'), 'config_macos.json')


class TestDefaultCameraIds(unittest.TestCase):
    def test_windows_defaults_skip_builtin(self):
        self.assertEqual(get_default_camera_ids('win32'), (0, 2))
        self.assertEqual(get_default_camera_ids('windows'), (0, 2))

    def test_linux_defaults_sequential(self):
        self.assertEqual(get_default_camera_ids('linux'), (0, 1))


class TestLoadCameraConfigBothPlatforms(unittest.TestCase):
    """Prove one API loads either platform's JSON."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, filename, payload):
        path = os.path.join(self.root, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f)
        return path

    def test_load_windows_config_from_root(self):
        self._write('config_windows.json', {
            'platform': 'windows', 'camera1_id': 4, 'camera2_id': 7,
        })
        cfg = load_camera_config(platform='windows', root=self.root)
        self.assertEqual(cfg['camera1_id'], 4)
        self.assertEqual(cfg['camera2_id'], 7)

    def test_load_linux_config_from_root(self):
        self._write('config_linux.json', {
            'platform': 'linux', 'camera1_id': 2, 'camera2_id': 5,
        })
        cfg = load_camera_config(platform='linux', root=self.root)
        self.assertEqual(cfg['camera1_id'], 2)
        self.assertEqual(cfg['camera2_id'], 5)

    def test_missing_config_returns_none(self):
        self.assertIsNone(load_camera_config(platform='linux', root=self.root))

    def test_get_camera_ids_prefers_config(self):
        self._write('config_linux.json', {
            'platform': 'linux', 'camera1_id': 3, 'camera2_id': 8,
        })
        self.assertEqual(
            get_camera_ids(platform='linux', root=self.root),
            (3, 8),
        )

    def test_get_camera_ids_falls_back_to_defaults(self):
        self.assertEqual(
            get_camera_ids(platform='windows', root=self.root),
            (0, 2),
        )
        self.assertEqual(
            get_camera_ids(platform='linux', root=self.root),
            (0, 1),
        )

    def test_save_roundtrip(self):
        path = save_camera_config(
            {'platform': 'linux', 'camera1_id': 1, 'camera2_id': 2},
            platform='linux',
            root=self.root,
        )
        self.assertTrue(os.path.exists(path))
        loaded = load_camera_config(config_path=path)
        self.assertEqual(loaded['camera1_id'], 1)


class TestPlatformPatching(unittest.TestCase):
    """Same test code path works when sys.platform is forced either way."""

    def test_describe_setup_windows(self):
        with patch('camera_utils.sys.platform', 'win32'):
            setup = describe_platform_setup(root=project_root)
            self.assertTrue(setup['is_windows'])
            self.assertEqual(setup['opencv_backend'], 'CAP_DSHOW')
            self.assertTrue(setup['config_path'].endswith('config_windows.json'))

    def test_describe_setup_linux(self):
        with patch('camera_utils.sys.platform', 'linux'):
            setup = describe_platform_setup(root=project_root)
            self.assertTrue(setup['is_linux'])
            self.assertEqual(setup['opencv_backend'], 'default')
            self.assertTrue(setup['config_path'].endswith('config_linux.json'))

    def test_test_utils_get_camera_ids_follows_platform(self):
        with patch('camera_utils.sys.platform', 'win32'), \
             patch('test_utils.sys.platform', 'win32'):
            # Host may or may not have config_windows.json; defaults or file both OK
            cam1, cam2 = test_utils.get_camera_ids(platform='windows')
            self.assertIsInstance(cam1, int)
            self.assertIsInstance(cam2, int)

        with patch('camera_utils.sys.platform', 'linux'), \
             patch('test_utils.sys.platform', 'linux'):
            cam1, cam2 = test_utils.get_camera_ids(platform='linux')
            self.assertIsInstance(cam1, int)
            self.assertIsInstance(cam2, int)


class TestOpenCVBackendSelection(unittest.TestCase):
    def test_windows_uses_dshow(self):
        import cv2
        self.assertEqual(get_opencv_backend('win32'), cv2.CAP_DSHOW)

    def test_linux_uses_default(self):
        self.assertIsNone(get_opencv_backend('linux'))

    @patch('camera_utils.cv2.VideoCapture')
    def test_create_capture_windows_passes_dshow(self, mock_vc):
        import cv2
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_vc.return_value = mock_cap

        create_camera_capture(0, backend=cv2.CAP_DSHOW)
        mock_vc.assert_called_with(0, cv2.CAP_DSHOW)

    @patch('camera_utils.cv2.VideoCapture')
    def test_create_capture_linux_default(self, mock_vc):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_vc.return_value = mock_cap

        with patch('camera_utils.sys.platform', 'linux'):
            create_camera_capture(1)
        mock_vc.assert_called_with(1)

    @patch('camera_utils.cv2.VideoCapture')
    def test_create_capture_raises_when_closed(self, mock_vc):
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False
        mock_vc.return_value = mock_cap
        with self.assertRaises(ValueError):
            create_camera_capture(99)


class TestRepoConfigFilesExist(unittest.TestCase):
    """Both platform config files should ship in the repo."""

    def test_windows_config_present(self):
        path = get_config_path(platform='windows', root=project_root)
        self.assertTrue(os.path.exists(path), path)

    def test_linux_config_present(self):
        path = get_config_path(platform='linux', root=project_root)
        self.assertTrue(os.path.exists(path), path)
        cfg = load_camera_config(config_path=path)
        self.assertEqual(cfg.get('platform'), 'linux')
        self.assertIn('camera1_id', cfg)
        self.assertIn('camera2_id', cfg)


class TestLegacyTestUtilsWrappers(unittest.TestCase):
    def test_load_windows_helper_none_on_linux_host(self):
        if sys.platform == 'win32':
            self.skipTest('Only meaningful on non-Windows hosts')
        # Legacy behaviour: without an explicit path, return None off Windows
        self.assertIsNone(test_utils.load_windows_camera_config())

    def test_load_linux_helper(self):
        cfg = test_utils.load_linux_camera_config()
        # Template ships in repo — should load on any host
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg['platform'], 'linux')


if __name__ == '__main__':
    unittest.main()
