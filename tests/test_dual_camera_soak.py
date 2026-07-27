"""
Automated dual-camera soak (mock path).

Closes the "manual dual-USB soak" gap for CI by exercising the full operator
loop without USB hardware:

  frames flowing → checklist ready → record with live preview → stop →
  analyze mock pair → export HTML/CSV → export clip

Optional hardware soak remains: ``python scripts/dual_camera_soak.py --hardware``.
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'scripts'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'tests'))

from helpers import write_mock_swing_pair  # noqa: E402
import flask_gui  # noqa: E402
from flask_gui import CameraManager, app, generate_frames  # noqa: E402
from test_gui_stability import _patch_pose_processor_to_read_video  # noqa: E402


def _live_cap(width=1280, height=720, fps=120.0):
    frame = np.full((height, width, 3), 40, dtype=np.uint8)
    cap = MagicMock()
    cap.isOpened.return_value = True

    def _get(prop):
        if prop == cv2.CAP_PROP_FRAME_WIDTH:
            return float(width)
        if prop == cv2.CAP_PROP_FRAME_HEIGHT:
            return float(height)
        if prop == cv2.CAP_PROP_FPS:
            return float(fps)
        return 128.0

    cap.get.side_effect = _get
    cap.read.return_value = (True, frame.copy())
    return cap


class TestDualCameraMockSoak(unittest.TestCase):
    """End-to-end mock soak covering cutover must-hits."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.rec_dir = self.tmp.name
        self._orig_dir = flask_gui._get_recordings_dir
        flask_gui._get_recordings_dir = lambda: self.rec_dir
        os.makedirs(self.rec_dir, exist_ok=True)

        app.config['TESTING'] = True
        self.client = app.test_client()
        self.mgr = CameraManager(camera1_id=0, camera2_id=1)
        self.mgr.cap1 = _live_cap()
        self.mgr.cap2 = _live_cap()
        self.mgr.cameras_available = True
        self.mgr.latest_frame1 = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.mgr.latest_frame2 = np.full((720, 1280, 3), 32, dtype=np.uint8)
        flask_gui.camera_manager = self.mgr

    def tearDown(self):
        self.mgr.running = False
        for t in (self.mgr.capture_thread, self.mgr.capture_thread2):
            if t:
                t.join(timeout=2.0)
        flask_gui.camera_manager = None
        flask_gui._get_recordings_dir = self._orig_dir
        self.tmp.cleanup()

    def test_mock_soak_record_preview_analyze_export(self):
        # 1) Frames flow for a short soak window
        t0 = time.time()
        while time.time() - t0 < 0.4:
            self.mgr.latest_frame1 = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
            self.mgr.latest_frame2 = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
            time.sleep(0.05)

        checklist = self.client.get('/api/checklist').get_json()
        self.assertTrue(checklist['ready'], checklist)

        # 2) Start recording with DualCameraRecorder stub + live preview frames
        preview_hits = {'n': 0}

        with patch('flask_gui.DualCameraRecorder') as MockRec:
            mock_rec = MagicMock()
            mock_rec.output_dir = self.rec_dir
            mock_rec.camera1 = MagicMock()
            mock_rec.camera2 = MagicMock()
            mock_rec.camera1.cap = self.mgr.cap1
            mock_rec.camera2.cap = self.mgr.cap2

            def _preview(cam_num):
                preview_hits['n'] += 1
                return np.full((240, 320, 3), 90 + cam_num, dtype=np.uint8)

            mock_rec.get_preview_frame.side_effect = _preview
            MockRec.return_value = mock_rec

            start = self.client.post('/api/recording/start').get_json()
            self.assertTrue(start.get('success'), start)
            self.assertTrue(self.mgr.is_recording)

            gen = generate_frames(1)
            chunk = next(gen)
            self.assertIn(b'\xff\xd8', chunk)
            self.assertNotIn(b'Recording in progress', chunk)
            self.assertGreater(preview_hits['n'], 0)

            with patch.object(self.mgr, '_reopen_cameras'), \
                 patch.object(self.mgr, 'start_analysis'):
                stop = self.client.post('/api/recording/stop').get_json()
            self.assertTrue(stop.get('success'), stop)

        # 3) Analyze mock swing pair (same path as GUI stability suite)
        cam1, cam2 = write_mock_swing_pair(
            self.rec_dir,
            timestamp='20260727_soak01',
            n_frames_cam1=20,
            n_frames_cam2=16,
        )
        self.mgr.recording_files = [cam1, cam2]
        with _patch_pose_processor_to_read_video(), \
             patch('flask_gui.time.sleep'), \
             patch('flask_gui._get_recordings_dir', return_value=self.rec_dir):
            self.mgr._analyze_videos()

        results = self.client.get('/api/analysis/results').get_json()
        self.assertGreater(results.get('max_frames', 0), 0)
        self.assertTrue(results.get('has_frames'))

        # 4) Export HTML / CSV / clip
        html = self.client.get('/api/analysis/export?format=html')
        self.assertEqual(html.status_code, 200)
        self.assertIn(b'<!DOCTYPE html>', html.data)

        csv = self.client.get('/api/analysis/export?format=csv')
        self.assertEqual(csv.status_code, 200)
        self.assertIn(b'Swing Score', csv.data)

        clip = self.client.post(
            '/api/analysis/export-clip',
            json={'camera': 1, 'fps': 30},
        ).get_json()
        self.assertTrue(clip.get('success'), clip)
        self.assertTrue(clip.get('filename', '').endswith('_camera1.mp4'))

        dl = self.client.get(f"/api/analysis/clip/{clip['filename']}")
        self.assertEqual(dl.status_code, 200)
        self.assertGreater(len(dl.data), 100)


if __name__ == '__main__':
    unittest.main()
