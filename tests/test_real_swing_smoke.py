"""
Real Face-On / DTL smoke.

Clip discovery always runs (no MediaPipe). The live pose model is opt-in:
    SWINGLAB_REAL_SWING_SMOKE=1 python -m unittest tests.test_real_swing_smoke
    python run_all_tests.py --smoke
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
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'tests'))

from helpers import write_mock_video
from real_swing_smoke import (
    GOLFDB_DEMO,
    labeled_local_clips,
    recording_pair_clips,
    resolve_smoke_clips,
    run_smoke,
)


class TestRealSwingClipDiscovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='realswing_')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_labeled_local_face_on_and_dtl(self):
        write_mock_video(os.path.join(self.tmp, 'face_on.mp4'), n_frames=6, pattern='swing')
        write_mock_video(os.path.join(self.tmp, 'dtl.mp4'), n_frames=6, pattern='swing')
        clips = labeled_local_clips(self.tmp)
        views = {c['view'] for c in clips}
        self.assertEqual(views, {'face_on', 'dtl'})

    def test_recording_pair_prefers_newest(self):
        write_mock_video(
            os.path.join(self.tmp, 'recording_20260101_120000_camera1.mp4'),
            n_frames=4, pattern='static_pose',
        )
        write_mock_video(
            os.path.join(self.tmp, 'recording_20260101_120000_camera2.mp4'),
            n_frames=4, pattern='static_pose',
        )
        write_mock_video(
            os.path.join(self.tmp, 'recording_20260815_090000_camera1.mp4'),
            n_frames=4, pattern='swing',
        )
        write_mock_video(
            os.path.join(self.tmp, 'recording_20260815_090000_camera2.mp4'),
            n_frames=4, pattern='swing',
        )
        clips = recording_pair_clips(self.tmp)
        self.assertEqual(len(clips), 2)
        self.assertTrue(all('20260815_090000' in c['path'] for c in clips))
        self.assertEqual([c['view'] for c in clips], ['face_on', 'dtl'])

    def test_resolve_does_not_fetch_by_default(self):
        with patch('real_swing_smoke.labeled_local_clips', return_value=[]), \
             patch('real_swing_smoke.recording_pair_clips', return_value=[]), \
             patch('real_swing_smoke.download_golfdb_demo') as fetch:
            self.assertEqual(resolve_smoke_clips(fetch_public=False), [])
            fetch.assert_not_called()

    def test_golfdb_demo_url_is_https(self):
        self.assertTrue(GOLFDB_DEMO['url'].startswith('https://'))
        self.assertIn('golfdb', GOLFDB_DEMO['url'])
        self.assertEqual(GOLFDB_DEMO['view'], 'dtl')

    def test_mediapipe_pose_connections_alias(self):
        try:
            from mediapipe.tasks.python import vision
        except ImportError:
            self.skipTest('mediapipe not installed')
        connections = getattr(
            vision.PoseLandmarksConnections, 'POSE_LANDMARKS', None,
        ) or getattr(
            vision.PoseLandmarksConnections, 'POSE_CONNECTIONS', None,
        )
        self.assertTrue(connections, 'MediaPipe pose skeleton connections missing')


@unittest.skipUnless(
    os.environ.get('SWINGLAB_REAL_SWING_SMOKE') == '1',
    'opt-in real MediaPipe smoke (run_all_tests.py --smoke)',
)
class TestRealMediaPipeSmoke(unittest.TestCase):
    def test_public_or_local_clips_detect_a_person(self):
        results = run_smoke(fetch_public=True, min_detection=0.25)
        self.assertGreaterEqual(len(results), 1)
        for item in results:
            self.assertGreaterEqual(item['detection_rate'], 0.25)
            self.assertGreater(item['frames'], 0)
            self.assertIn(item['view'], ('face_on', 'dtl', 'unknown'))


if __name__ == '__main__':
    unittest.main()
