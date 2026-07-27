"""
GUI stability tests for the Flask CameraManager + analysis pipeline.

Focus:
  - Analysis against real synthetic (mock) dual-camera captures
  - API / state stability under concurrent polling
  - MJPEG preview generator resilience
  - Frame memory lifecycle and clip export
  - Session / reinit guards that protect the UI from racey actions
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'scripts'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'tests'))

from helpers import (
    count_video_frames,
    landmarks_and_frames_from_video,
    make_annotated_jpeg_frames,
    make_swing_sequence,
    write_mock_swing_pair,
    write_mock_video,
)
import flask_gui
from flask_gui import CameraManager, app, generate_frames
from sway_calculator import SwayCalculator


def _analysis_from_video(path, peak_turn=45.0):
    """Decode mock video + run SwayCalculator (real analysis path, no MediaPipe)."""
    n = count_video_frames(path)
    seq = make_swing_sequence(n, peak_turn=peak_turn)
    landmarks, frames = landmarks_and_frames_from_video(path, seq)
    analysis = SwayCalculator().analyze_sequence(landmarks, frame_width=frames[0].shape[1])
    detected = sum(1 for lm in landmarks if lm is not None)
    analysis['detection_rate'] = (detected / len(landmarks) * 100) if landmarks else 0
    return landmarks, frames, analysis


def _patch_pose_processor_to_read_video():
    """
    Return a context-manager stack that swaps PoseProcessor for a reader that
    returns landmarks + annotated frames from the real mock MP4 (no MediaPipe).
    """
    class _FakeProc:
        def __init__(self, *args, **kwargs):
            self._peak = 50.0 if kwargs.get('model_complexity', 2) else 30.0

        def process_video(self, path):
            landmarks, frames, _ = _analysis_from_video(path, peak_turn=self._peak)
            return landmarks, frames

        def release(self):
            pass

    return patch('flask_gui.PoseProcessor', _FakeProc)


# ======================================================================
# Analysis pipeline with mock captures
# ======================================================================

class TestAnalysisPipelineMockVideos(unittest.TestCase):
    """CameraManager._analyze_videos against synthetic dual captures."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='gui_anal_')
        self.mgr = CameraManager()
        self.cam1, self.cam2 = write_mock_swing_pair(
            self.tmp,
            timestamp='20260727_181500',
            n_frames_cam1=20,
            n_frames_cam2=16,
            pattern='swing',
        )
        self.mgr.recording_files = [self.cam1, self.cam2]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_analyze(self):
        with _patch_pose_processor_to_read_video(), \
             patch('flask_gui.time.sleep'), \
             patch('flask_gui._get_recordings_dir', return_value=self.tmp):
            self.mgr._analyze_videos()

    def test_full_analysis_populates_both_cameras(self):
        self._run_analyze()
        self.assertFalse(self.mgr.is_analyzing)
        self.assertEqual(self.mgr.analysis_error, '')
        self.assertIsNotNone(self.mgr.analysis_camera1)
        self.assertIsNotNone(self.mgr.analysis_camera2)
        self.assertEqual(len(self.mgr.analysis_frames_cam1), 20)
        self.assertEqual(len(self.mgr.analysis_frames_cam2), 16)
        # JPEG compression should shrink vs raw BGR
        self.assertIsInstance(self.mgr.analysis_frames_cam1[0], (bytes, bytearray))
        self.assertGreater(len(self.mgr.analysis_frames_cam1[0]), 100)

    def test_analysis_results_api_shape_after_mock_run(self):
        self._run_analyze()
        results = self.mgr.get_analysis_results()
        self.assertTrue(results['has_frames'])
        self.assertEqual(results['max_frames'], 20)  # longer of the two
        self.assertIn('timeseries', results['camera1'])
        self.assertIn('sway', results['camera1']['current'])
        self.assertIn('shoulder_turn', results['camera2']['current'])
        self.assertGreater(results['camera1']['detection_rate'], 0)

    def test_analysis_json_persisted(self):
        self._run_analyze()
        json_path = os.path.join(self.tmp, 'analysis_20260727_181500.json')
        self.assertTrue(os.path.isfile(json_path), f'Missing {json_path}')
        with open(json_path) as f:
            payload = json.load(f)
        self.assertEqual(payload['timestamp'], '20260727_181500')
        self.assertIn('camera1', payload)
        self.assertIn('camera2', payload)
        self.assertIn('score', payload)

    def test_blank_videos_complete_without_crash(self):
        blank1 = write_mock_video(
            os.path.join(self.tmp, 'recording_20260727_190000_camera1.mp4'),
            n_frames=8, pattern='blank',
        )
        blank2 = write_mock_video(
            os.path.join(self.tmp, 'recording_20260727_190000_camera2.mp4'),
            n_frames=8, pattern='blank',
        )
        self.mgr.recording_files = [blank1, blank2]

        class _EmptyProc:
            def __init__(self, *a, **k):
                pass

            def process_video(self, path):
                landmarks, frames = landmarks_and_frames_from_video(path, None)
                return landmarks, frames

            def release(self):
                pass

        with patch('flask_gui.PoseProcessor', _EmptyProc), \
             patch('flask_gui.time.sleep'), \
             patch('flask_gui._get_recordings_dir', return_value=self.tmp):
            self.mgr._analyze_videos()

        self.assertFalse(self.mgr.is_analyzing)
        self.assertEqual(self.mgr.analysis_error, '')
        self.assertEqual(self.mgr.analysis_camera1['detection_rate'], 0)
        results = self.mgr.get_analysis_results()
        self.assertTrue(results['has_frames'])
        self.assertEqual(results['max_frames'], 8)

    def test_missing_video_sets_analysis_error(self):
        self.mgr.recording_files = [
            os.path.join(self.tmp, 'missing_camera1.mp4'),
            os.path.join(self.tmp, 'missing_camera2.mp4'),
        ]
        # start_analysis gates on exists(); call _analyze_videos directly
        with patch('flask_gui.time.sleep'):
            # Pretend files existed when the thread started, then vanished
            self.mgr.is_analyzing = True
            self.mgr._analyze_videos()
        self.assertFalse(self.mgr.is_analyzing)
        self.assertTrue(self.mgr.analysis_error)


# ======================================================================
# State / concurrency stability
# ======================================================================

class TestGuiStateStability(unittest.TestCase):
    def setUp(self):
        self.mgr = CameraManager()

    def test_double_start_analysis_ignored(self):
        self.mgr.is_analyzing = True
        self.mgr.recording_files = ['a.mp4', 'b.mp4']
        with patch('os.path.exists', return_value=True), \
             patch('threading.Thread') as mock_thread:
            self.mgr.start_analysis()
            mock_thread.assert_not_called()

    def test_start_analysis_sets_analyzing_flag(self):
        tmp = tempfile.mkdtemp(prefix='start_anal_')
        try:
            cam1, cam2 = write_mock_swing_pair(tmp, n_frames_cam1=4, n_frames_cam2=4)
            self.mgr.recording_files = [cam1, cam2]
            # Prevent background thread from doing real work
            with patch.object(self.mgr, '_analyze_videos'):
                self.mgr.start_analysis()
            self.assertTrue(self.mgr.is_analyzing)
            self.assertEqual(self.mgr.analysis_error, '')
            self.assertEqual(self.mgr.analysis_frame_index, 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_reinit_blocked_while_recording(self):
        self.mgr.is_recording = True
        result = self.mgr.reinit_cameras()
        self.assertIn('error', result)

    def test_clear_analysis_frames_frees_buffers(self):
        self.mgr.analysis_frames_cam1 = make_annotated_jpeg_frames(5, label='a')
        self.mgr.analysis_frames_cam2 = make_annotated_jpeg_frames(5, label='b')
        self.mgr._clear_analysis_frames()
        self.assertEqual(self.mgr.analysis_frames_cam1, [])
        self.assertEqual(self.mgr.analysis_frames_cam2, [])

    def test_second_analysis_replaces_frames(self):
        tmp = tempfile.mkdtemp(prefix='reanal_')
        try:
            cam1, cam2 = write_mock_swing_pair(
                tmp, timestamp='20260727_200000',
                n_frames_cam1=10, n_frames_cam2=10,
            )
            self.mgr.recording_files = [cam1, cam2]
            self.mgr.analysis_frames_cam1 = make_annotated_jpeg_frames(3, label='old')
            with _patch_pose_processor_to_read_video(), \
                 patch('flask_gui.time.sleep'), \
                 patch('flask_gui._get_recordings_dir', return_value=tmp):
                self.mgr._analyze_videos()
            self.assertEqual(len(self.mgr.analysis_frames_cam1), 10)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_session_phase_review_after_analysis(self):
        tmp = tempfile.mkdtemp(prefix='session_')
        try:
            cam1, cam2 = write_mock_swing_pair(
                tmp, timestamp='20260727_201000',
                n_frames_cam1=6, n_frames_cam2=6,
            )
            self.mgr.recording_files = [cam1, cam2]
            self.mgr.session_enabled = True
            self.mgr.session_phase = 'analyzing'
            with _patch_pose_processor_to_read_video(), \
                 patch('flask_gui.time.sleep'), \
                 patch('flask_gui._get_recordings_dir', return_value=tmp):
                self.mgr._analyze_videos()
            self.assertEqual(self.mgr.session_phase, 'review')
            self.assertEqual(self.mgr.session_count, 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_concurrent_results_polling_during_analysis(self):
        """Simulate the browser polling /api/analysis/results while analyzing."""
        self.mgr.is_analyzing = True
        self.mgr.analysis_progress = 'Processing Camera 1...'
        errors = []

        def poll():
            try:
                for _ in range(40):
                    r = self.mgr.get_analysis_results()
                    self.assertTrue(r['is_analyzing'])
                    self.assertEqual(r['max_frames'], 0)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=poll) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        self.assertEqual(errors, [])


# ======================================================================
# Flask client stability (routes + MJPEG)
# ======================================================================

class TestFlaskRouteStability(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='flask_stab_')
        self.mgr = CameraManager()
        # Seed preview frames so checklist / streams have something to show
        self.mgr.latest_frame1 = np.zeros((240, 320, 3), dtype=np.uint8)
        self.mgr.latest_frame2 = np.full((240, 320, 3), 40, dtype=np.uint8)
        mock1 = MagicMock()
        mock1.isOpened.return_value = True
        mock1.get.return_value = 1280.0
        mock2 = MagicMock()
        mock2.isOpened.return_value = True
        mock2.get.return_value = 1280.0
        self.mgr.cap1 = mock1
        self.mgr.cap2 = mock2
        self.mgr.cameras_available = True

        flask_gui.camera_manager = self.mgr
        self.client = app.test_client()

    def tearDown(self):
        flask_gui.camera_manager = None
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_status_stable_under_burst(self):
        for _ in range(25):
            resp = self.client.get('/api/status')
            self.assertEqual(resp.status_code, 200)
            data = resp.get_json()
            self.assertIn('is_recording', data)
            self.assertIn('is_analyzing', data)
            self.assertIn('cameras_available', data)

    def test_checklist_ready_when_frames_present(self):
        resp = self.client.get('/api/checklist')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ready'])

    def test_checklist_not_ready_without_frames(self):
        self.mgr.latest_frame1 = None
        self.mgr.latest_frame2 = None
        resp = self.client.get('/api/checklist')
        data = resp.get_json()
        self.assertFalse(data['ready'])

    def test_analysis_frame_endpoint_after_mock_analysis(self):
        cam1, cam2 = write_mock_swing_pair(
            self.tmp, timestamp='20260727_210000',
            n_frames_cam1=8, n_frames_cam2=8,
        )
        self.mgr.recording_files = [cam1, cam2]
        with _patch_pose_processor_to_read_video(), \
             patch('flask_gui.time.sleep'), \
             patch('flask_gui._get_recordings_dir', return_value=self.tmp):
            self.mgr._analyze_videos()

        # Navigate + fetch JPEG for both cameras (API uses "index")
        resp = self.client.post('/api/analysis/frame', json={'index': 3})
        self.assertEqual(resp.status_code, 200)

        for cam in (1, 2):
            img = self.client.get(f'/api/analysis/frame/{cam}?index=3')
            self.assertEqual(img.status_code, 200)
            self.assertIn('image', img.content_type)
            self.assertGreater(len(img.data), 200)
            # Should decode as a real JPEG
            arr = np.frombuffer(img.data, dtype=np.uint8)
            decoded = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            self.assertIsNotNone(decoded)

        results = self.client.get('/api/analysis/results').get_json()
        self.assertTrue(results['has_frames'])
        self.assertEqual(results['frame_index'], 3)

    def test_export_clip_from_analysis_frames(self):
        self.mgr.analysis_frames_cam1 = make_annotated_jpeg_frames(10, label='exp')
        self.mgr.recording_files = [
            os.path.join(self.tmp, 'recording_20260727_211111_camera1.mp4'),
            os.path.join(self.tmp, 'recording_20260727_211111_camera2.mp4'),
        ]
        with patch('flask_gui._get_recordings_dir', return_value=self.tmp):
            resp = self.client.post(
                '/api/analysis/export-clip',
                json={'camera': 1, 'fps': 30},
            )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data['frame_count'], 10)
        self.assertTrue(os.path.isfile(data['path']))
        self.assertEqual(count_video_frames(data['path']), 10)

        # Download route should serve the clip
        filename = data['filename']
        with patch('flask_gui._get_recordings_dir', return_value=self.tmp):
            dl = self.client.get(f'/api/analysis/clip/{filename}')
            try:
                self.assertEqual(dl.status_code, 200)
                self.assertIn('video', dl.content_type)
                self.assertGreater(len(dl.data), 100)
            finally:
                dl.close()

    def test_reinit_api_blocked_during_recording(self):
        self.mgr.is_recording = True
        resp = self.client.post('/api/cameras/reinit')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('error', resp.get_json())

    def test_mjpeg_generator_yields_valid_multipart(self):
        """Consume a few MJPEG chunks; must not hang or raise."""
        gen = generate_frames(1)
        chunks = []
        # generate_frames sleeps ~1/30s per live frame
        deadline = time.time() + 3.0
        while len(chunks) < 3 and time.time() < deadline:
            chunks.append(next(gen))
        self.assertEqual(len(chunks), 3)
        for chunk in chunks:
            self.assertIn(b'--frame', chunk)
            self.assertIn(b'Content-Type: image/jpeg', chunk)
            self.assertIn(b'\xff\xd8', chunk)  # JPEG SOI

    def test_mjpeg_placeholder_while_recording(self):
        self.mgr.is_recording = True
        gen = generate_frames(1)
        chunk = next(gen)
        self.assertIn(b'--frame', chunk)
        self.assertIn(b'\xff\xd8', chunk)

    def test_frame_nav_clamps_across_unequal_mock_lengths(self):
        cam1, cam2 = write_mock_swing_pair(
            self.tmp, timestamp='20260727_220000',
            n_frames_cam1=18, n_frames_cam2=9,
        )
        self.mgr.recording_files = [cam1, cam2]
        with _patch_pose_processor_to_read_video(), \
             patch('flask_gui.time.sleep'), \
             patch('flask_gui._get_recordings_dir', return_value=self.tmp):
            self.mgr._analyze_videos()

        resp = self.client.post('/api/analysis/frame', json={'index': 999})
        self.assertEqual(resp.status_code, 200)
        results = self.client.get('/api/analysis/results').get_json()
        self.assertEqual(results['max_frames'], 18)
        self.assertEqual(results['frame_index'], 17)

        resp = self.client.post('/api/analysis/frame', json={'index': -5})
        results = self.client.get('/api/analysis/results').get_json()
        self.assertEqual(results['frame_index'], 0)


# ======================================================================
# Preview get_frame thread-safety smoke
# ======================================================================

class TestPreviewFrameStability(unittest.TestCase):
    def test_get_frame_copies_under_contention(self):
        mgr = CameraManager()
        mgr.latest_frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
        errors = []

        def reader():
            try:
                for _ in range(50):
                    f = mgr.get_frame(1)
                    self.assertIsNotNone(f)
                    f[0, 0] = (1, 2, 3)  # mutate copy — must not corrupt buffer
            except Exception as exc:
                errors.append(exc)

        def writer():
            try:
                for i in range(50):
                    with mgr.frame_lock:
                        mgr.latest_frame1 = np.full((100, 100, 3), i % 255, dtype=np.uint8)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(3)]
        threads.append(threading.Thread(target=writer))
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        self.assertEqual(errors, [])


if __name__ == '__main__':
    unittest.main()
