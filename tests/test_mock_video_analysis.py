"""
Mock video capture fixtures + analysis-tool verification.

Generates synthetic dual-camera recordings (OpenCV-readable) and runs them
through PoseProcessor / SwayCalculator / clip_exporter without real cameras
or MediaPipe model downloads.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'scripts'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'tests'))

from helpers import (
    count_video_frames,
    landmarks_and_frames_from_video,
    make_address_pose,
    make_annotated_jpeg_frames,
    make_fake_pose_landmarks,
    make_swing_sequence,
    video_probe,
    write_mock_swing_pair,
    write_mock_video,
)
from clip_exporter import jpeg_frames_to_mp4, resolve_clip_output
from pose_processor import PoseProcessor
from sway_calculator import SwayCalculator


# MediaPipe landmark indices used by PoseProcessor._extract_landmarks
_JOINT_INDEX = {
    'nose': 0,
    'left_ear': 7,
    'right_ear': 8,
    'left_shoulder': 11,
    'right_shoulder': 12,
    'left_elbow': 13,
    'right_elbow': 14,
    'left_wrist': 15,
    'right_wrist': 16,
    'left_hip': 23,
    'right_hip': 24,
    'left_knee': 25,
    'right_knee': 26,
    'left_ankle': 27,
    'right_ankle': 28,
}


def _dict_to_pose_landmarks(pose_dict):
    """Convert make_address_pose()-style dict → 33 FakeLandmark list."""
    overrides = {}
    for name, idx in _JOINT_INDEX.items():
        if name in pose_dict:
            lm = pose_dict[name]
            overrides[idx] = (lm['x'], lm['y'], lm['z'])
    return make_fake_pose_landmarks(33, overrides)


class _FakeDetectResult:
    def __init__(self, pose_landmarks):
        self.pose_landmarks = pose_landmarks


class _FakeLandmarker:
    """Stand-in for MediaPipe PoseLandmarker that yields a canned sequence."""

    def __init__(self, sequences=None, always_none=False):
        self._sequences = list(sequences or [])
        self._always_none = always_none
        self._i = 0
        self.closed = False

    def detect(self, _mp_image):
        if self._always_none or self._i >= len(self._sequences):
            self._i += 1
            return _FakeDetectResult([])
        pose = self._sequences[self._i]
        self._i += 1
        # process_frame expects a list-of-poses
        return _FakeDetectResult([pose] if pose is not None else [])

    def close(self):
        self.closed = True


def _build_pose_processor(sequences=None, always_none=False):
    """Construct PoseProcessor without downloading models / native EGL libs."""
    proc = PoseProcessor.__new__(PoseProcessor)
    proc.pose_landmarker = _FakeLandmarker(sequences=sequences, always_none=always_none)
    proc.landmarks_sequence = []

    # Bypass mediapipe.Image (needs libEGL) while still exercising process_video I/O.
    def _process_frame(frame):
        detection_result = proc.pose_landmarker.detect(frame)
        annotated_frame = frame.copy()
        pose_landmarks_list = detection_result.pose_landmarks or []

        class Results:
            def __init__(self, pose_landmarks):
                self.pose_landmarks = pose_landmarks[0] if pose_landmarks else None

        return Results(pose_landmarks_list), annotated_frame

    proc.process_frame = _process_frame
    return proc


# ======================================================================
# Fixture creation
# ======================================================================

class TestMockVideoFixtures(unittest.TestCase):
    """Synthetic videos must be writable and re-readable by OpenCV."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='mockvid_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_write_swing_video_readable(self):
        path = write_mock_video(
            os.path.join(self.tmp, 'swing.mp4'),
            n_frames=18, width=320, height=240, pattern='swing',
        )
        info = video_probe(path)
        self.assertEqual(info['width'], 320)
        self.assertEqual(info['height'], 240)
        self.assertEqual(info['readable_frames'], 18)
        self.assertGreater(os.path.getsize(path), 500)

    def test_blank_and_static_patterns(self):
        blank = write_mock_video(
            os.path.join(self.tmp, 'blank.mp4'), n_frames=8, pattern='blank',
        )
        static = write_mock_video(
            os.path.join(self.tmp, 'static.mp4'), n_frames=8, pattern='static_pose',
        )
        self.assertEqual(count_video_frames(blank), 8)
        self.assertEqual(count_video_frames(static), 8)

    def test_swing_pair_production_filenames(self):
        cam1, cam2 = write_mock_swing_pair(
            self.tmp, timestamp='20260727_153000',
            n_frames_cam1=16, n_frames_cam2=12,
        )
        self.assertTrue(os.path.basename(cam1).startswith('recording_20260727_153000_camera1'))
        self.assertTrue(os.path.basename(cam2).startswith('recording_20260727_153000_camera2'))
        self.assertEqual(count_video_frames(cam1), 16)
        self.assertEqual(count_video_frames(cam2), 12)

    def test_landmarks_and_frames_from_video(self):
        path = write_mock_video(
            os.path.join(self.tmp, 'seq.mp4'), n_frames=10, pattern='swing',
        )
        seq = make_swing_sequence(10, peak_turn=40)
        landmarks, frames = landmarks_and_frames_from_video(path, seq)
        self.assertEqual(len(landmarks), 10)
        self.assertEqual(len(frames), 10)
        self.assertIsNotNone(landmarks[5])
        self.assertEqual(frames[0].shape[2], 3)


# ======================================================================
# PoseProcessor + mock captures
# ======================================================================

class TestPoseProcessorWithMockVideo(unittest.TestCase):
    """PoseProcessor.process_video against synthetic captures (no model download)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='posevid_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_detections_still_returns_all_frames(self):
        path = write_mock_video(
            os.path.join(self.tmp, 'empty_lab.mp4'),
            n_frames=12, pattern='blank',
        )
        proc = _build_pose_processor(always_none=True)
        landmarks, annotated = proc.process_video(path)
        proc.release()
        self.assertEqual(len(landmarks), 12)
        self.assertEqual(len(annotated), 12)
        self.assertTrue(all(lm is None for lm in landmarks))
        self.assertTrue(proc.pose_landmarker.closed)

    def test_detections_extracted_per_frame(self):
        n = 15
        path = write_mock_video(
            os.path.join(self.tmp, 'detected.mp4'),
            n_frames=n, pattern='swing',
        )
        seq = make_swing_sequence(n, peak_turn=50)
        fake_poses = [_dict_to_pose_landmarks(p) for p in seq]
        proc = _build_pose_processor(sequences=fake_poses)
        landmarks, annotated = proc.process_video(path)
        proc.release()

        self.assertEqual(len(landmarks), n)
        self.assertEqual(len(annotated), n)
        detected = [lm for lm in landmarks if lm is not None]
        self.assertEqual(len(detected), n)
        mid = n // 2
        self.assertIn('left_shoulder', detected[0])
        self.assertIn('right_hip', detected[mid])
        # Mid-swing should have larger |z| offset than address
        z0 = abs(detected[0]['left_shoulder']['z'])
        z_mid = abs(detected[mid]['left_shoulder']['z'])
        self.assertGreater(z_mid, z0)

    def test_missing_video_raises(self):
        proc = _build_pose_processor(always_none=True)
        with self.assertRaises(RuntimeError):
            proc.process_video(os.path.join(self.tmp, 'does_not_exist.mp4'))


# ======================================================================
# End-to-end analysis tools on mock captures
# ======================================================================

class TestAnalysisToolsOnMockCaptures(unittest.TestCase):
    """SwayCalculator + clip export fed by mock dual-camera captures."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='analvid_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_sway_metrics_from_mock_swing_pair(self):
        cam1, cam2 = write_mock_swing_pair(
            self.tmp, n_frames_cam1=30, n_frames_cam2=28, pattern='swing',
        )
        seq1 = make_swing_sequence(30, peak_turn=45)
        seq2 = make_swing_sequence(28, peak_turn=55)

        # Simulate PoseProcessor output by decoding the real mock videos
        lm1, frames1 = landmarks_and_frames_from_video(cam1, seq1)
        lm2, frames2 = landmarks_and_frames_from_video(cam2, seq2)

        calc = SwayCalculator()
        a1 = calc.analyze_sequence(lm1, frame_width=320)
        a2 = calc.analyze_sequence(lm2, frame_width=320)

        self.assertIn('summary', a1)
        self.assertIn('summary', a2)
        self.assertEqual(len(a1.get('sway', [])), 30)
        self.assertEqual(len(a2.get('shoulder_turn', [])), 28)
        # At least some numeric metrics should populate from a swing sequence
        self.assertTrue(
            any(v is not None for v in a1.get('sway', [])),
            'Expected non-null sway values from synthetic swing',
        )
        self.assertTrue(
            any(v is not None for v in a2.get('shoulder_turn', [])),
            'Expected non-null shoulder_turn from synthetic swing',
        )
        self.assertEqual(len(frames1), 30)
        self.assertEqual(len(frames2), 28)

    def test_blank_capture_yields_empty_but_stable_analysis(self):
        path = write_mock_video(
            os.path.join(self.tmp, 'blank.mp4'), n_frames=10, pattern='blank',
        )
        landmarks, _ = landmarks_and_frames_from_video(path, None)
        analysis = SwayCalculator().analyze_sequence(landmarks, frame_width=320)
        self.assertEqual(len(analysis.get('sway', [])), 10)
        self.assertTrue(all(v is None for v in analysis.get('sway', [])))

    def test_clip_export_roundtrip_from_annotated_jpegs(self):
        jpegs = make_annotated_jpeg_frames(n_frames=14, width=160, height=120, label='c1')
        out = resolve_clip_output(self.tmp, '20260727_160000', 1)
        result = jpeg_frames_to_mp4(jpegs, out, fps=30.0)
        self.assertTrue(os.path.isfile(result['path']))
        self.assertEqual(result['frame_count'], 14)
        self.assertEqual(count_video_frames(result['path']), 14)
        probe = video_probe(result['path'])
        self.assertEqual(probe['width'], 160)
        self.assertEqual(probe['height'], 120)

    def test_clip_export_rejects_empty(self):
        with self.assertRaises(ValueError):
            jpeg_frames_to_mp4([], os.path.join(self.tmp, 'empty.mp4'))


# ======================================================================
# PoseProcessor._extract_landmarks wiring (dict ↔ FakeLandmark)
# ======================================================================

class TestLandmarkExtraction(unittest.TestCase):
    def test_extract_key_joints(self):
        proc = _build_pose_processor(always_none=True)
        pose = make_address_pose(hip_x=0.52, shoulder_x=0.51, z_offset=0.1)
        fake = _dict_to_pose_landmarks(pose)
        extracted = proc._extract_landmarks(fake)
        self.assertAlmostEqual(extracted['left_hip']['x'], pose['left_hip']['x'])
        self.assertAlmostEqual(extracted['right_shoulder']['z'], pose['right_shoulder']['z'])
        self.assertIn('nose', extracted)


if __name__ == '__main__':
    unittest.main()
