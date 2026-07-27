"""
Tests for live MJPEG preview while DualCameraRecorder owns the cameras.

GUI v2 must-hit: browsers should see moving frames during recording, not a
static placeholder.
"""

from __future__ import annotations

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'scripts'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'tests'))

from dual_camera_recorder import CameraCapture, DualCameraRecorder  # noqa: E402
from flask_gui import (  # noqa: E402
    CameraManager,
    _encode_preview_jpeg,
    _frontend_dist_ready,
    app,
    generate_frames,
)
import flask_gui  # noqa: E402


class TestCameraCapturePreviewSnapshot(unittest.TestCase):
    def test_preview_frame_does_not_consume_queue(self):
        cam = CameraCapture(0, buffer_size=2)
        frame = np.full((60, 80, 3), 40, dtype=np.uint8)
        with cam._preview_lock:
            cam._latest_preview_frame = frame.copy()
            cam._latest_preview_ts = time.time()
        # Put a distinct frame in the write queue
        queued = np.full((60, 80, 3), 200, dtype=np.uint8)
        cam.frame_queue.put((queued, time.time()))

        preview = cam.get_preview_frame()
        self.assertIsNotNone(preview)
        self.assertEqual(int(preview[0, 0, 0]), 40)
        # Queue still has the write frame
        got = cam.get_frame(timeout=0.2)
        self.assertIsNotNone(got)
        self.assertEqual(int(got[0][0, 0, 0]), 200)

    def test_preview_none_when_empty(self):
        cam = CameraCapture(0)
        self.assertIsNone(cam.get_preview_frame())


class TestDualRecorderPreview(unittest.TestCase):
    def test_get_preview_frame_routes_cameras(self):
        rec = DualCameraRecorder.__new__(DualCameraRecorder)
        c1 = CameraCapture(0)
        c2 = CameraCapture(1)
        with c1._preview_lock:
            c1._latest_preview_frame = np.full((10, 10, 3), 11, dtype=np.uint8)
        with c2._preview_lock:
            c2._latest_preview_frame = np.full((10, 10, 3), 22, dtype=np.uint8)
        rec.camera1 = c1
        rec.camera2 = c2

        p1 = rec.get_preview_frame(1)
        p2 = rec.get_preview_frame(2)
        self.assertEqual(int(p1[0, 0, 0]), 11)
        self.assertEqual(int(p2[0, 0, 0]), 22)
        self.assertIsNone(rec.get_preview_frame(3))


class TestCameraManagerRecordingPreview(unittest.TestCase):
    def test_get_frame_uses_recorder_while_recording(self):
        mgr = CameraManager()
        mgr.is_recording = True
        mock_rec = MagicMock()
        mock_rec.get_preview_frame.return_value = np.full((48, 64, 3), 90, dtype=np.uint8)
        mgr.recorder = mock_rec
        # Idle buffers would otherwise win if logic were wrong
        mgr.latest_frame1 = np.zeros((48, 64, 3), dtype=np.uint8)

        frame = mgr.get_frame(1)
        self.assertIsNotNone(frame)
        self.assertEqual(int(frame[0, 0, 0]), 90)
        mock_rec.get_preview_frame.assert_called_with(1)

    def test_get_frame_idle_uses_preview_buffer(self):
        mgr = CameraManager()
        mgr.is_recording = False
        mgr.latest_frame2 = np.full((20, 20, 3), 55, dtype=np.uint8)
        frame = mgr.get_frame(2)
        self.assertEqual(int(frame[0, 0, 0]), 55)


class TestEncodePreviewJpeg(unittest.TestCase):
    def test_recording_path_downscales_wide_frames(self):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[:] = (30, 60, 90)
        raw = _encode_preview_jpeg(frame, recording=True)
        idle = _encode_preview_jpeg(frame, recording=False)
        self.assertTrue(raw.startswith(b'\xff\xd8'))
        self.assertTrue(idle.startswith(b'\xff\xd8'))
        # Recording encode should typically be smaller (downscale + lower quality)
        self.assertLess(len(raw), len(idle))

        arr = np.frombuffer(raw, dtype=np.uint8)
        decoded = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        self.assertIsNotNone(decoded)
        self.assertLessEqual(decoded.shape[1], 640)


class TestMjpegWhileRecording(unittest.TestCase):
    def test_generate_frames_yields_live_jpeg_when_recording(self):
        mgr = CameraManager()
        mgr.is_recording = True
        mock_rec = MagicMock()
        mock_rec.get_preview_frame.return_value = np.full((40, 60, 3), 120, dtype=np.uint8)
        mgr.recorder = mock_rec
        flask_gui.camera_manager = mgr
        try:
            gen = generate_frames(1)
            chunk = next(gen)
            self.assertIn(b'--frame', chunk)
            self.assertIn(b'\xff\xd8', chunk)
            self.assertNotIn(b'Recording in progress', chunk)
        finally:
            flask_gui.camera_manager = None


class TestFrontendRouting(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_legacy_route_serves_v1_template(self):
        resp = self.client.get('/legacy')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Camera Setup', resp.data)

    def test_index_falls_back_to_template_without_dist(self):
        with patch('flask_gui._frontend_dist_ready', return_value=False):
            resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Camera Setup', resp.data)

    def test_dist_ready_helper(self):
        # Default checkout has no built assets
        self.assertIsInstance(_frontend_dist_ready(), bool)


if __name__ == '__main__':
    unittest.main()
