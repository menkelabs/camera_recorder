"""
Tests for the SwingDetector automatic swing detection module.

Tests the state machine transitions and event generation without
requiring real cameras or MediaPipe models.
"""

import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

# Add project paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from swing_detector import SwingDetector


class _MockableSwingDetector(SwingDetector):
    """SwingDetector subclass that skips MediaPipe and lets us inject shoulder turns."""

    def __init__(self, **kwargs):
        # Avoid calling PoseProcessor by not calling super().__init__
        self.motion_threshold = kwargs.get('motion_threshold', 15.0)
        self.confirmation_frames = kwargs.get('confirmation_frames', 5)
        self.cooldown_seconds = kwargs.get('cooldown_seconds', 2.0)
        self.window_size = kwargs.get('window_size', 10)

        self.state = self.IDLE
        self._confirm_count = 0
        self._cooldown_start = None
        self._baseline = None
        from collections import deque
        self._history = deque(maxlen=self.window_size)
        self._current_turn = None
        self._processor = None
        self._model_complexity = 0

        # Queue of turn values to feed
        self._turn_queue = []

    def _get_shoulder_turn(self, frame):
        """Return the next value from the injected queue."""
        if self._turn_queue:
            return self._turn_queue.pop(0)
        return None

    def feed_turns(self, values):
        """Convenience: set the turn queue and process dummy frames."""
        self._turn_queue = list(values)
        events = []
        dummy = np.zeros((10, 10, 3), dtype=np.uint8)
        for _ in values:
            ev = self.process_frame(dummy)
            events.append(ev)
        return events


# ======================================================================
# State machine tests
# ======================================================================

class TestSwingDetectorInit(unittest.TestCase):
    """Test construction and defaults."""

    def test_default_state(self):
        det = _MockableSwingDetector()
        self.assertEqual(det.state, SwingDetector.IDLE)
        self.assertIsNone(det._baseline)
        self.assertEqual(det.motion_threshold, 15.0)
        self.assertEqual(det.confirmation_frames, 5)
        self.assertEqual(det.cooldown_seconds, 2.0)

    def test_custom_params(self):
        det = _MockableSwingDetector(motion_threshold=10,
                                     confirmation_frames=3,
                                     cooldown_seconds=1.0)
        self.assertEqual(det.motion_threshold, 10)
        self.assertEqual(det.confirmation_frames, 3)
        self.assertEqual(det.cooldown_seconds, 1.0)


class TestBaselineEstablishment(unittest.TestCase):
    """Test that the detector establishes a baseline from the first few frames."""

    def test_baseline_from_first_three(self):
        det = _MockableSwingDetector()
        det.feed_turns([5.0, 5.5, 4.5])
        self.assertIsNotNone(det._baseline)
        self.assertAlmostEqual(det._baseline, 5.0, places=1)

    def test_no_baseline_with_fewer_than_three(self):
        det = _MockableSwingDetector()
        det.feed_turns([5.0, 5.5])
        self.assertIsNone(det._baseline)

    def test_none_turns_dont_advance(self):
        det = _MockableSwingDetector()
        det._turn_queue = [None, None, None]
        dummy = np.zeros((10, 10, 3), dtype=np.uint8)
        for _ in range(3):
            det.process_frame(dummy)
        self.assertIsNone(det._baseline)
        self.assertEqual(len(det._history), 0)


class TestIdleToMotionDetected(unittest.TestCase):
    """Test transition from IDLE to MOTION_DETECTED."""

    def test_motion_above_threshold(self):
        det = _MockableSwingDetector(motion_threshold=10, confirmation_frames=3)
        # Establish baseline at ~0
        det.feed_turns([0, 0, 0])
        self.assertEqual(det.state, SwingDetector.IDLE)
        # One frame above threshold -> MOTION_DETECTED
        events = det.feed_turns([25])
        self.assertEqual(det.state, SwingDetector.MOTION_DETECTED)
        self.assertIsNone(events[0])  # no event yet

    def test_stays_idle_below_threshold(self):
        det = _MockableSwingDetector(motion_threshold=10, confirmation_frames=3)
        det.feed_turns([0, 0, 0])
        det.feed_turns([5, 5, 5])  # below threshold
        self.assertEqual(det.state, SwingDetector.IDLE)


class TestMotionConfirmation(unittest.TestCase):
    """Test that confirmation_frames consecutive above-threshold readings trigger start."""

    def test_confirmed_start(self):
        det = _MockableSwingDetector(motion_threshold=10, confirmation_frames=3)
        det.feed_turns([0, 0, 0])  # baseline
        events = det.feed_turns([25, 25, 25])
        self.assertIn('start', events)
        self.assertEqual(det.state, SwingDetector.RECORDING)

    def test_false_trigger_rejected(self):
        """Motion spike that drops before confirmation -> back to IDLE."""
        det = _MockableSwingDetector(motion_threshold=10, confirmation_frames=3)
        det.feed_turns([0, 0, 0])  # baseline
        events = det.feed_turns([25, 25])  # only 2, need 3
        self.assertNotIn('start', events)
        # Now drop below threshold
        events2 = det.feed_turns([2])
        self.assertEqual(det.state, SwingDetector.IDLE)
        self.assertIsNone(events2[0])

    def test_confirm_count_resets_on_drop(self):
        """If motion drops during IDLE (before entering MOTION_DETECTED), counter resets."""
        det = _MockableSwingDetector(motion_threshold=10, confirmation_frames=4)
        det.feed_turns([0, 0, 0])  # baseline
        det.feed_turns([25])  # 1st above
        det.feed_turns([2])   # drop — back to IDLE, count reset
        det.feed_turns([25])  # 1st again
        self.assertEqual(det._confirm_count, 1)


class TestRecordingState(unittest.TestCase):
    """Test behaviour while in RECORDING state."""

    def _start_recording(self, det):
        det.feed_turns([0, 0, 0])
        det.feed_turns([25] * det.confirmation_frames)
        self.assertEqual(det.state, SwingDetector.RECORDING)

    def test_stays_recording_while_motion(self):
        det = _MockableSwingDetector(motion_threshold=10, confirmation_frames=3)
        self._start_recording(det)
        events = det.feed_turns([30, 35, 40])
        self.assertEqual(det.state, SwingDetector.RECORDING)
        self.assertTrue(all(e is None for e in events))

    def test_enters_cooldown_when_motion_drops(self):
        det = _MockableSwingDetector(motion_threshold=10, confirmation_frames=3)
        self._start_recording(det)
        det.feed_turns([2])  # below threshold
        self.assertEqual(det.state, SwingDetector.COOLDOWN)
        self.assertIsNotNone(det._cooldown_start)


class TestCooldownState(unittest.TestCase):
    """Test cooldown timer and transitions."""

    def _into_cooldown(self, det):
        det.feed_turns([0, 0, 0])
        det.feed_turns([25] * det.confirmation_frames)
        det.feed_turns([2])  # enter cooldown
        self.assertEqual(det.state, SwingDetector.COOLDOWN)

    def test_motion_resumes_from_cooldown(self):
        det = _MockableSwingDetector(motion_threshold=10,
                                     confirmation_frames=3,
                                     cooldown_seconds=2.0)
        self._into_cooldown(det)
        events = det.feed_turns([25])  # motion resumes
        self.assertEqual(det.state, SwingDetector.RECORDING)
        self.assertIsNone(events[0])

    def test_cooldown_expires_stop_event(self):
        det = _MockableSwingDetector(motion_threshold=10,
                                     confirmation_frames=3,
                                     cooldown_seconds=0.1)
        self._into_cooldown(det)
        time.sleep(0.15)
        events = det.feed_turns([2])
        self.assertIn('stop', events)
        self.assertEqual(det.state, SwingDetector.IDLE)

    def test_cooldown_not_expired_no_event(self):
        det = _MockableSwingDetector(motion_threshold=10,
                                     confirmation_frames=3,
                                     cooldown_seconds=5.0)
        self._into_cooldown(det)
        events = det.feed_turns([2])  # immediately, well before 5s
        self.assertEqual(det.state, SwingDetector.COOLDOWN)
        self.assertIsNone(events[0])


class TestResetAndRelease(unittest.TestCase):
    """Test reset() and release() methods."""

    def test_reset(self):
        det = _MockableSwingDetector(motion_threshold=10, confirmation_frames=3)
        det.feed_turns([0, 0, 0, 25, 25, 25])
        self.assertEqual(det.state, SwingDetector.RECORDING)
        det.reset()
        self.assertEqual(det.state, SwingDetector.IDLE)
        self.assertIsNone(det._baseline)
        self.assertEqual(len(det._history), 0)

    def test_release_without_processor(self):
        det = _MockableSwingDetector()
        det.release()  # should not raise


class TestGetStatus(unittest.TestCase):
    """Test the get_status() serialisation helper."""

    def test_status_idle_no_baseline(self):
        det = _MockableSwingDetector()
        s = det.get_status()
        self.assertEqual(s['state'], 'idle')
        self.assertIsNone(s['baseline'])
        self.assertIsNone(s['delta'])
        self.assertEqual(s['motion_threshold'], 15.0)

    def test_status_with_baseline(self):
        det = _MockableSwingDetector()
        det.feed_turns([5, 5, 5])
        s = det.get_status()
        self.assertIsNotNone(s['baseline'])
        self.assertIsNotNone(s['current_turn'])

    def test_status_recording(self):
        det = _MockableSwingDetector(motion_threshold=10, confirmation_frames=3)
        det.feed_turns([0, 0, 0, 25, 25, 25])
        s = det.get_status()
        self.assertEqual(s['state'], 'recording')


class TestFullSwingCycle(unittest.TestCase):
    """End-to-end: baseline -> motion -> confirm -> recording -> cooldown -> stop."""

    def test_full_cycle(self):
        det = _MockableSwingDetector(motion_threshold=10,
                                     confirmation_frames=2,
                                     cooldown_seconds=0.05)
        # Baseline
        events = det.feed_turns([0, 0, 0])
        self.assertTrue(all(e is None for e in events))
        self.assertEqual(det.state, SwingDetector.IDLE)

        # Motion detected -> confirmed -> start
        events = det.feed_turns([25, 25])
        self.assertIn('start', events)
        self.assertEqual(det.state, SwingDetector.RECORDING)

        # Stay in recording
        events = det.feed_turns([30, 35])
        self.assertEqual(det.state, SwingDetector.RECORDING)

        # Motion drops -> cooldown
        events = det.feed_turns([2])
        self.assertEqual(det.state, SwingDetector.COOLDOWN)

        # Wait for cooldown
        time.sleep(0.1)

        # Final quiet frame -> stop
        events = det.feed_turns([1])
        self.assertIn('stop', events)
        self.assertEqual(det.state, SwingDetector.IDLE)

    def test_multiple_swings(self):
        """Two full swings in sequence."""
        det = _MockableSwingDetector(motion_threshold=10,
                                     confirmation_frames=2,
                                     cooldown_seconds=0.05)
        # Swing 1
        det.feed_turns([0, 0, 0])
        events1 = det.feed_turns([25, 25])
        self.assertIn('start', events1)
        det.feed_turns([2])  # cooldown
        time.sleep(0.1)
        events_stop1 = det.feed_turns([1])
        self.assertIn('stop', events_stop1)

        # Swing 2 — baseline should have been re-established
        events2 = det.feed_turns([25, 25])
        self.assertIn('start', events2)


# ======================================================================
# Runner
# ======================================================================

def run_swing_detector_tests():
    """Run all SwingDetector tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestSwingDetectorInit,
        TestBaselineEstablishment,
        TestIdleToMotionDetected,
        TestMotionConfirmation,
        TestRecordingState,
        TestCooldownState,
        TestResetAndRelease,
        TestGetStatus,
        TestFullSwingCycle,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    print("=" * 70)
    print("Swing Detector Tests")
    print("=" * 70)
    print()
    success = run_swing_detector_tests()
    print()
    print("=" * 70)
    if success:
        print("All Swing Detector tests passed!")
    else:
        print("Some Swing Detector tests failed")
    print("=" * 70)
    sys.exit(0 if success else 1)
