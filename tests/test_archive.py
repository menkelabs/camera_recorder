"""
Tests for the archive-to-external-disk feature.

Tests config persistence, file copy logic, manifest tracking,
and Flask API endpoints.
"""

import sys
import os
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'scripts'))

from flask_gui import (
    app, CameraManager,
    _load_archive_config, _save_archive_config,
    _load_archive_manifest, _save_archive_manifest,
    _archive_recording, _disk_usage,
    _get_recordings_dir, _ARCHIVE_CONFIG_FILE,
)


class TestArchiveConfig(unittest.TestCase):
    """Test archive config load/save helpers."""

    def setUp(self):
        self._orig = _ARCHIVE_CONFIG_FILE
        self._tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self._tmp.close()
        # Monkey-patch the config file path
        import flask_gui
        flask_gui._ARCHIVE_CONFIG_FILE = self._tmp.name

    def tearDown(self):
        import flask_gui
        flask_gui._ARCHIVE_CONFIG_FILE = self._orig
        os.unlink(self._tmp.name)

    def test_load_empty(self):
        """Returns empty dict when file doesn't exist."""
        os.unlink(self._tmp.name)
        import flask_gui
        flask_gui._ARCHIVE_CONFIG_FILE = self._tmp.name + '.nonexistent'
        self.assertEqual(_load_archive_config(), {})
        flask_gui._ARCHIVE_CONFIG_FILE = self._tmp.name
        # recreate for tearDown
        open(self._tmp.name, 'w').close()

    def test_save_and_load(self):
        config = {'archive_path': '/mnt/seagate/golf'}
        _save_archive_config(config)
        loaded = _load_archive_config()
        self.assertEqual(loaded['archive_path'], '/mnt/seagate/golf')


class TestArchiveManifest(unittest.TestCase):
    """Test archive manifest load/save."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tmpdir)

    @patch('flask_gui._get_recordings_dir')
    def test_empty_manifest(self, mock_dir):
        mock_dir.return_value = self._tmpdir
        self.assertEqual(_load_archive_manifest(), {})

    @patch('flask_gui._get_recordings_dir')
    def test_save_and_load_manifest(self, mock_dir):
        mock_dir.return_value = self._tmpdir
        data = {'20260215_140000': {'archived_at': '2026-02-15', 'files': ['a.mp4']}}
        _save_archive_manifest(data)
        loaded = _load_archive_manifest()
        self.assertIn('20260215_140000', loaded)


class TestArchiveRecording(unittest.TestCase):
    """Test _archive_recording file copy logic."""

    def setUp(self):
        self._rec_dir = tempfile.mkdtemp()
        self._archive_dir = tempfile.mkdtemp()

        # Create fake recording files
        ts = '20260215_140000'
        for cam in ['camera1', 'camera2']:
            path = os.path.join(self._rec_dir, f'recording_{ts}_{cam}.mp4')
            with open(path, 'wb') as f:
                f.write(b'fakevideodata_' + cam.encode())

        # Create fake analysis JSON
        analysis_path = os.path.join(self._rec_dir, f'analysis_{ts}.json')
        with open(analysis_path, 'w') as f:
            json.dump({'camera1': {}, 'camera2': {}}, f)

    def tearDown(self):
        shutil.rmtree(self._rec_dir)
        shutil.rmtree(self._archive_dir)

    @patch('flask_gui._get_recordings_dir')
    def test_copies_all_files(self, mock_dir):
        mock_dir.return_value = self._rec_dir
        result = _archive_recording('20260215_140000', self._archive_dir)
        self.assertIn('recording_20260215_140000_camera1.mp4', result['copied'])
        self.assertIn('recording_20260215_140000_camera2.mp4', result['copied'])
        self.assertIn('analysis_20260215_140000.json', result['copied'])
        self.assertFalse(result.get('errors'))
        # Verify files exist in archive
        self.assertTrue(os.path.exists(
            os.path.join(self._archive_dir, 'recording_20260215_140000_camera1.mp4')))

    @patch('flask_gui._get_recordings_dir')
    def test_missing_files_not_error(self, mock_dir):
        mock_dir.return_value = self._rec_dir
        result = _archive_recording('20260215_999999', self._archive_dir)
        self.assertEqual(result['copied'], [])

    @patch('flask_gui._get_recordings_dir')
    def test_creates_archive_dir(self, mock_dir):
        mock_dir.return_value = self._rec_dir
        new_dir = os.path.join(self._archive_dir, 'sub', 'nested')
        result = _archive_recording('20260215_140000', new_dir)
        self.assertTrue(os.path.isdir(new_dir))
        self.assertTrue(len(result['copied']) > 0)


class TestDiskUsage(unittest.TestCase):
    """Test _disk_usage helper."""

    def test_valid_path(self):
        usage = _disk_usage('/')
        self.assertIsNotNone(usage)
        self.assertIn('total', usage)
        self.assertIn('free', usage)
        self.assertGreater(usage['total'], 0)

    def test_invalid_path(self):
        usage = _disk_usage('/nonexistent/path/that/does/not/exist')
        self.assertIsNone(usage)


class TestArchiveAPIEndpoints(unittest.TestCase):
    """Test Flask archive API routes."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        import flask_gui
        self.mgr = CameraManager()
        flask_gui.camera_manager = self.mgr

        # Use temp config file
        self._orig_config = flask_gui._ARCHIVE_CONFIG_FILE
        self._tmp_config = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self._tmp_config.close()
        flask_gui._ARCHIVE_CONFIG_FILE = self._tmp_config.name

    def tearDown(self):
        import flask_gui
        flask_gui.camera_manager = None
        flask_gui._ARCHIVE_CONFIG_FILE = self._orig_config
        os.unlink(self._tmp_config.name)

    def test_get_config_unconfigured(self):
        resp = self.client.get('/api/archive/config')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertFalse(data['configured'])
        self.assertEqual(data['archive_path'], '')

    def test_set_config_requires_path(self):
        resp = self.client.post('/api/archive/config', json={})
        self.assertEqual(resp.status_code, 400)

    def test_set_config_validates_parent(self):
        resp = self.client.post('/api/archive/config',
                                json={'archive_path': '/nonexistent/path/abc'})
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn('error', data)

    def test_set_config_success(self):
        resp = self.client.post('/api/archive/config',
                                json={'archive_path': '/tmp/test_archive_golf'})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data['success'])
        # Verify it persisted
        resp2 = self.client.get('/api/archive/config')
        data2 = json.loads(resp2.data)
        self.assertTrue(data2['configured'])
        self.assertEqual(data2['archive_path'], '/tmp/test_archive_golf')

    def test_archive_status(self):
        resp = self.client.get('/api/archive/status')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('archived_count', data)
        self.assertIn('archived_timestamps', data)

    def test_archive_run_without_config(self):
        resp = self.client.post('/api/archive/run')
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn('error', data)

    def test_archive_run_with_config(self):
        # Set up a temp archive path
        tmpdir = tempfile.mkdtemp()
        try:
            self.client.post('/api/archive/config',
                             json={'archive_path': tmpdir})
            resp = self.client.post('/api/archive/run')
            self.assertEqual(resp.status_code, 200)
            data = json.loads(resp.data)
            self.assertIn('archived_count', data)
            self.assertIn('total_files_copied', data)
        finally:
            shutil.rmtree(tmpdir)


class TestTemplateSettingsTab(unittest.TestCase):
    """Test that the template includes the Settings tab."""

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        import flask_gui
        self.mgr = CameraManager()
        flask_gui.camera_manager = self.mgr

    def tearDown(self):
        import flask_gui
        flask_gui.camera_manager = None

    def test_settings_tab_button(self):
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('Settings', html)
        self.assertIn('[7]', html)
        self.assertIn("switchTab('settings')", html)

    def test_archive_path_input(self):
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('archive-path-input', html)
        self.assertIn('saveArchivePath', html)

    def test_disk_info_section(self):
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('archive-disk-section', html)
        self.assertIn('disk-total', html)
        self.assertIn('disk-free', html)

    def test_archive_actions(self):
        resp = self.client.get('/')
        html = resp.data.decode()
        self.assertIn('archive-all-btn', html)
        self.assertIn('archiveAll', html)
        self.assertIn('archive-count', html)


# ======================================================================
# Runner
# ======================================================================

def run_archive_tests():
    """Run all archive tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestArchiveConfig,
        TestArchiveManifest,
        TestArchiveRecording,
        TestDiskUsage,
        TestArchiveAPIEndpoints,
        TestTemplateSettingsTab,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 70)
    print("Archive Tests")
    print("=" * 70)
    print()
    success = run_archive_tests()
    print()
    print("=" * 70)
    if success:
        print("All Archive tests passed!")
    else:
        print("Some Archive tests failed")
    print("=" * 70)
    sys.exit(0 if success else 1)
