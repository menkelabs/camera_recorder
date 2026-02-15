"""
Tests for SwayCalculator — covers all metrics including new ones
(head sway, spine tilt, spine angle, knee flex, weight shift,
 lead arm angle, swing phase detection, tempo).
"""

import math
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from sway_calculator import SwayCalculator, _angle_between


# ---------------------------------------------------------------------------
# Helpers — build fake landmark dictionaries
# ---------------------------------------------------------------------------

def _make_landmarks(overrides=None):
    """Return a full landmarks dict with sensible defaults.  Override specific ones."""
    base = {
        'nose':            {'x': 0.50, 'y': 0.25, 'z': 0.0, 'visibility': 1.0},
        'left_shoulder':   {'x': 0.40, 'y': 0.40, 'z': -0.05, 'visibility': 1.0},
        'right_shoulder':  {'x': 0.60, 'y': 0.40, 'z':  0.05, 'visibility': 1.0},
        'left_hip':        {'x': 0.45, 'y': 0.60, 'z': -0.02, 'visibility': 1.0},
        'right_hip':       {'x': 0.55, 'y': 0.60, 'z':  0.02, 'visibility': 1.0},
        'left_elbow':      {'x': 0.35, 'y': 0.50, 'z':  0.0, 'visibility': 1.0},
        'right_elbow':     {'x': 0.65, 'y': 0.50, 'z':  0.0, 'visibility': 1.0},
        'left_wrist':      {'x': 0.30, 'y': 0.55, 'z':  0.0, 'visibility': 1.0},
        'right_wrist':     {'x': 0.70, 'y': 0.55, 'z':  0.0, 'visibility': 1.0},
        'left_knee':       {'x': 0.45, 'y': 0.75, 'z':  0.0, 'visibility': 1.0},
        'right_knee':      {'x': 0.55, 'y': 0.75, 'z':  0.0, 'visibility': 1.0},
        'left_ankle':      {'x': 0.45, 'y': 0.90, 'z':  0.0, 'visibility': 1.0},
        'right_ankle':     {'x': 0.55, 'y': 0.90, 'z':  0.0, 'visibility': 1.0},
    }
    if overrides:
        for k, v in overrides.items():
            if isinstance(v, dict):
                base[k] = {**base.get(k, {}), **v}
            else:
                base[k] = v
    return base


def _make_sequence(n=10, nose_drift=0.01, shoulder_z_drift=0.05):
    """Build an N-frame landmark sequence simulating a simple backswing."""
    frames = []
    for i in range(n):
        frames.append(_make_landmarks({
            'nose': {'x': 0.50 + i * nose_drift, 'y': 0.25, 'z': 0.0, 'visibility': 1.0},
            'left_shoulder': {'x': 0.40, 'y': 0.40, 'z': -0.05 + i * shoulder_z_drift, 'visibility': 1.0},
            'right_shoulder': {'x': 0.60, 'y': 0.40, 'z': 0.05 - i * shoulder_z_drift, 'visibility': 1.0},
        }))
    return frames


# ===========================================================================
# Tests
# ===========================================================================

class TestAngleBetween(unittest.TestCase):
    """Test the _angle_between helper function."""

    def test_right_angle(self):
        angle = _angle_between((1, 0), (0, 0), (0, 1))
        self.assertAlmostEqual(angle, 90.0, places=3)

    def test_straight_line(self):
        angle = _angle_between((0, 0), (1, 0), (2, 0))
        self.assertAlmostEqual(angle, 180.0, places=3)

    def test_zero_length_returns_none(self):
        result = _angle_between((0, 0), (0, 0), (1, 1))
        self.assertIsNone(result)

    def test_acute_angle(self):
        angle = _angle_between((1, 0), (0, 0), (1, 1))
        self.assertAlmostEqual(angle, 45.0, places=3)


class TestHipAndShoulderCenters(unittest.TestCase):
    def setUp(self):
        self.calc = SwayCalculator()
        self.landmarks = _make_landmarks()

    def test_hip_center(self):
        hc = self.calc.calculate_hip_center(self.landmarks)
        self.assertIsNotNone(hc)
        self.assertAlmostEqual(hc[0], 0.50, places=3)
        self.assertAlmostEqual(hc[1], 0.60, places=3)

    def test_shoulder_center(self):
        sc = self.calc.calculate_shoulder_center(self.landmarks)
        self.assertIsNotNone(sc)
        self.assertAlmostEqual(sc[0], 0.50, places=3)
        self.assertAlmostEqual(sc[1], 0.40, places=3)

    def test_hip_center_none_input(self):
        self.assertIsNone(self.calc.calculate_hip_center(None))

    def test_hip_center_missing_landmarks(self):
        self.assertIsNone(self.calc.calculate_hip_center({'left_hip': {'x': 0, 'y': 0, 'z': 0}}))

    def test_shoulder_center_none_input(self):
        self.assertIsNone(self.calc.calculate_shoulder_center(None))


class TestLateralSway(unittest.TestCase):
    def setUp(self):
        self.calc = SwayCalculator()
        self.address = _make_landmarks()
        self.calc.set_address_position(self.address)

    def test_zero_at_address(self):
        sway = self.calc.calculate_lateral_sway(self.address, 640)
        self.assertAlmostEqual(sway, 0.0, places=3)

    def test_positive_sway(self):
        moved = _make_landmarks({
            'left_hip': {'x': 0.50, 'y': 0.60, 'z': -0.02, 'visibility': 1.0},
            'right_hip': {'x': 0.60, 'y': 0.60, 'z': 0.02, 'visibility': 1.0},
        })
        sway = self.calc.calculate_lateral_sway(moved, 640)
        self.assertGreater(sway, 0)

    def test_none_without_address(self):
        calc2 = SwayCalculator()
        self.assertIsNone(calc2.calculate_lateral_sway(self.address, 640))

    def test_none_with_none_landmarks(self):
        self.assertIsNone(self.calc.calculate_lateral_sway(None, 640))


class TestShoulderTurn(unittest.TestCase):
    def setUp(self):
        self.calc = SwayCalculator()

    def test_zero_at_symmetric(self):
        lm = _make_landmarks({
            'left_shoulder': {'x': 0.4, 'y': 0.4, 'z': 0.0, 'visibility': 1.0},
            'right_shoulder': {'x': 0.6, 'y': 0.4, 'z': 0.0, 'visibility': 1.0},
        })
        turn = self.calc.calculate_shoulder_turn(lm)
        self.assertAlmostEqual(turn, 0.0, places=3)

    def test_positive_with_z_diff(self):
        lm = _make_landmarks({
            'left_shoulder': {'x': 0.4, 'y': 0.4, 'z': -0.2, 'visibility': 1.0},
            'right_shoulder': {'x': 0.6, 'y': 0.4, 'z': 0.2, 'visibility': 1.0},
        })
        turn = self.calc.calculate_shoulder_turn(lm)
        self.assertGreater(turn, 0)

    def test_none_input(self):
        self.assertIsNone(self.calc.calculate_shoulder_turn(None))

    def test_missing_landmarks(self):
        self.assertIsNone(self.calc.calculate_shoulder_turn({'left_shoulder': {'x': 0, 'y': 0, 'z': 0}}))


class TestHipTurn(unittest.TestCase):
    def setUp(self):
        self.calc = SwayCalculator()

    def test_returns_float(self):
        lm = _make_landmarks()
        result = self.calc.calculate_hip_turn(lm)
        self.assertIsInstance(result, float)

    def test_none_input(self):
        self.assertIsNone(self.calc.calculate_hip_turn(None))


class TestXFactor(unittest.TestCase):
    def setUp(self):
        self.calc = SwayCalculator()

    def test_x_factor_is_non_negative(self):
        lm = _make_landmarks()
        xf = self.calc.calculate_x_factor(lm)
        self.assertIsNotNone(xf)
        self.assertGreaterEqual(xf, 0)

    def test_none_when_missing(self):
        self.assertIsNone(self.calc.calculate_x_factor(None))


class TestHeadSway(unittest.TestCase):
    def setUp(self):
        self.calc = SwayCalculator()
        self.address = _make_landmarks()
        self.calc.set_address_position(self.address)

    def test_zero_at_address(self):
        sway = self.calc.calculate_head_sway(self.address, 640)
        self.assertAlmostEqual(sway, 0.0, places=3)

    def test_positive_drift(self):
        moved = _make_landmarks({'nose': {'x': 0.55, 'y': 0.25, 'z': 0.0, 'visibility': 1.0}})
        sway = self.calc.calculate_head_sway(moved, 640)
        self.assertGreater(sway, 0)

    def test_negative_drift(self):
        moved = _make_landmarks({'nose': {'x': 0.45, 'y': 0.25, 'z': 0.0, 'visibility': 1.0}})
        sway = self.calc.calculate_head_sway(moved, 640)
        self.assertLess(sway, 0)

    def test_none_without_address(self):
        calc2 = SwayCalculator()
        self.assertIsNone(calc2.calculate_head_sway(self.address, 640))

    def test_none_with_none_landmarks(self):
        self.assertIsNone(self.calc.calculate_head_sway(None, 640))

    def test_none_missing_nose(self):
        lm = _make_landmarks()
        del lm['nose']
        self.assertIsNone(self.calc.calculate_head_sway(lm, 640))


class TestSpineTilt(unittest.TestCase):
    def setUp(self):
        self.calc = SwayCalculator()

    def test_vertical_spine_is_zero(self):
        """Shoulder center directly above hip center => 0 tilt."""
        lm = _make_landmarks({
            'left_shoulder':  {'x': 0.45, 'y': 0.40, 'z': 0.0, 'visibility': 1.0},
            'right_shoulder': {'x': 0.55, 'y': 0.40, 'z': 0.0, 'visibility': 1.0},
            'left_hip':       {'x': 0.45, 'y': 0.60, 'z': 0.0, 'visibility': 1.0},
            'right_hip':      {'x': 0.55, 'y': 0.60, 'z': 0.0, 'visibility': 1.0},
        })
        tilt = self.calc.calculate_spine_tilt(lm)
        self.assertAlmostEqual(tilt, 0.0, places=3)

    def test_positive_tilt(self):
        """Shoulder center shifted right from hip center => positive tilt."""
        lm = _make_landmarks({
            'left_shoulder':  {'x': 0.50, 'y': 0.40, 'z': 0.0, 'visibility': 1.0},
            'right_shoulder': {'x': 0.70, 'y': 0.40, 'z': 0.0, 'visibility': 1.0},
        })
        tilt = self.calc.calculate_spine_tilt(lm)
        self.assertGreater(tilt, 0)

    def test_none_with_missing_data(self):
        self.assertIsNone(self.calc.calculate_spine_tilt({'left_shoulder': {'x': 0, 'y': 0, 'z': 0}}))


class TestKneeFlex(unittest.TestCase):
    def setUp(self):
        self.calc = SwayCalculator()

    def test_straight_leg_180(self):
        """Straight line hip-knee-ankle => 180 degrees."""
        lm = _make_landmarks({
            'left_hip':   {'x': 0.5, 'y': 0.5, 'z': 0, 'visibility': 1.0},
            'left_knee':  {'x': 0.5, 'y': 0.7, 'z': 0, 'visibility': 1.0},
            'left_ankle': {'x': 0.5, 'y': 0.9, 'z': 0, 'visibility': 1.0},
        })
        flex = self.calc.calculate_knee_flex(lm)
        self.assertAlmostEqual(flex, 180.0, places=1)

    def test_bent_leg_less_than_180(self):
        """Knee offset from straight line => angle < 180."""
        lm = _make_landmarks({
            'left_hip':   {'x': 0.5, 'y': 0.5, 'z': 0, 'visibility': 1.0},
            'left_knee':  {'x': 0.55, 'y': 0.7, 'z': 0, 'visibility': 1.0},
            'left_ankle': {'x': 0.5, 'y': 0.9, 'z': 0, 'visibility': 1.0},
        })
        flex = self.calc.calculate_knee_flex(lm)
        self.assertLess(flex, 180.0)
        self.assertGreater(flex, 90.0)

    def test_none_with_none_landmarks(self):
        self.assertIsNone(self.calc.calculate_knee_flex(None))

    def test_none_missing_ankle(self):
        lm = _make_landmarks()
        del lm['left_ankle']
        self.assertIsNone(self.calc.calculate_knee_flex(lm))


class TestWeightShift(unittest.TestCase):
    def setUp(self):
        self.calc = SwayCalculator()

    def test_centered_is_50(self):
        lm = _make_landmarks()
        ws = self.calc.calculate_weight_shift(lm)
        self.assertAlmostEqual(ws, 50.0, places=0)

    def test_shift_toward_lead(self):
        """Hip center shifted toward lead foot (left ankle) => >50%."""
        lm = _make_landmarks({
            'left_hip':  {'x': 0.42, 'y': 0.60, 'z': 0, 'visibility': 1.0},
            'right_hip': {'x': 0.50, 'y': 0.60, 'z': 0, 'visibility': 1.0},
            # ankles at 0.45 (left) and 0.55 (right)
            # hip center = 0.46 => pct = (0.46 - 0.55) / (0.45 - 0.55) * 100 = 90%
        })
        ws = self.calc.calculate_weight_shift(lm)
        self.assertGreater(ws, 50.0)

    def test_clamped_to_0_100(self):
        # Hips way outside ankle range
        lm = _make_landmarks({
            'left_hip':  {'x': 0.90, 'y': 0.60, 'z': 0, 'visibility': 1.0},
            'right_hip': {'x': 0.95, 'y': 0.60, 'z': 0, 'visibility': 1.0},
        })
        ws = self.calc.calculate_weight_shift(lm)
        self.assertLessEqual(ws, 100.0)
        self.assertGreaterEqual(ws, 0.0)

    def test_none_with_none(self):
        self.assertIsNone(self.calc.calculate_weight_shift(None))

    def test_none_missing_ankle(self):
        lm = _make_landmarks()
        del lm['left_ankle']
        self.assertIsNone(self.calc.calculate_weight_shift(lm))


class TestSpineAngle(unittest.TestCase):
    def setUp(self):
        self.calc = SwayCalculator()

    def test_upright_is_near_zero(self):
        lm = _make_landmarks({
            'left_shoulder':  {'x': 0.45, 'y': 0.30, 'z': 0, 'visibility': 1.0},
            'right_shoulder': {'x': 0.55, 'y': 0.30, 'z': 0, 'visibility': 1.0},
            'left_hip':       {'x': 0.45, 'y': 0.60, 'z': 0, 'visibility': 1.0},
            'right_hip':      {'x': 0.55, 'y': 0.60, 'z': 0, 'visibility': 1.0},
        })
        angle = self.calc.calculate_spine_angle(lm)
        self.assertAlmostEqual(angle, 0.0, places=1)

    def test_forward_bend(self):
        lm = _make_landmarks({
            'left_shoulder':  {'x': 0.30, 'y': 0.45, 'z': 0, 'visibility': 1.0},
            'right_shoulder': {'x': 0.40, 'y': 0.45, 'z': 0, 'visibility': 1.0},
        })
        angle = self.calc.calculate_spine_angle(lm)
        self.assertGreater(angle, 0)

    def test_none_with_missing(self):
        self.assertIsNone(self.calc.calculate_spine_angle({'left_shoulder': {'x': 0, 'y': 0, 'z': 0}}))


class TestLeadArmAngle(unittest.TestCase):
    def setUp(self):
        self.calc = SwayCalculator()

    def test_straight_arm_180(self):
        lm = _make_landmarks({
            'left_shoulder': {'x': 0.5, 'y': 0.3, 'z': 0, 'visibility': 1.0},
            'left_elbow':    {'x': 0.5, 'y': 0.5, 'z': 0, 'visibility': 1.0},
            'left_wrist':    {'x': 0.5, 'y': 0.7, 'z': 0, 'visibility': 1.0},
        })
        angle = self.calc.calculate_lead_arm_angle(lm)
        self.assertAlmostEqual(angle, 180.0, places=1)

    def test_bent_arm(self):
        lm = _make_landmarks({
            'left_shoulder': {'x': 0.5, 'y': 0.3, 'z': 0, 'visibility': 1.0},
            'left_elbow':    {'x': 0.5, 'y': 0.5, 'z': 0, 'visibility': 1.0},
            'left_wrist':    {'x': 0.6, 'y': 0.4, 'z': 0, 'visibility': 1.0},
        })
        angle = self.calc.calculate_lead_arm_angle(lm)
        self.assertLess(angle, 180.0)
        self.assertGreater(angle, 0)

    def test_none_with_none(self):
        self.assertIsNone(self.calc.calculate_lead_arm_angle(None))

    def test_none_missing_elbow(self):
        lm = _make_landmarks()
        del lm['left_elbow']
        self.assertIsNone(self.calc.calculate_lead_arm_angle(lm))


class TestSwingPhaseDetection(unittest.TestCase):
    def test_basic_phase_labels(self):
        # Simulate shoulder turn: 0, 10, 20, 30, 40, 30, 20, 10, 0, -5
        st = [0, 10, 20, 30, 40, 30, 20, 10, 0, -5]
        sway = [0] * 10
        phases = SwayCalculator.detect_swing_phases(st, sway)
        self.assertEqual(len(phases), 10)
        # Must contain at least Address and some other phases
        self.assertIn('Address', phases)
        # Peak is at index 4, so that should be 'Top'
        self.assertEqual(phases[4], 'Top')
        # After peak should be Downswing or Impact
        self.assertIn(phases[5], ['Downswing', 'Impact', 'Follow-through'])

    def test_all_same_returns_address(self):
        st = [0.0] * 5
        sway = [0.0] * 5
        phases = SwayCalculator.detect_swing_phases(st, sway)
        # All zeros, first frame should be Address
        self.assertEqual(phases[0], 'Address')

    def test_short_sequence(self):
        st = [0, 10, 0]
        sway = [0, 0, 0]
        phases = SwayCalculator.detect_swing_phases(st, sway)
        self.assertEqual(len(phases), 3)

    def test_handles_none_values(self):
        st = [None, 10, 20, 30, None]
        sway = [0, 0, 0, 0, 0]
        phases = SwayCalculator.detect_swing_phases(st, sway)
        self.assertEqual(len(phases), 5)

    def test_very_short_sequence(self):
        st = [10, 20]
        sway = [0, 0]
        phases = SwayCalculator.detect_swing_phases(st, sway)
        self.assertEqual(len(phases), 2)


class TestTempo(unittest.TestCase):
    def test_typical_tempo(self):
        phases = ['Address', 'Backswing', 'Backswing', 'Backswing',
                  'Top', 'Downswing', 'Impact', 'Follow-through']
        tempo = SwayCalculator.calculate_tempo(phases)
        self.assertAlmostEqual(tempo, 3.0)

    def test_no_downswing(self):
        phases = ['Address', 'Backswing', 'Backswing', 'Top']
        tempo = SwayCalculator.calculate_tempo(phases)
        self.assertIsNone(tempo)

    def test_no_backswing(self):
        phases = ['Address', 'Top', 'Downswing', 'Impact']
        tempo = SwayCalculator.calculate_tempo(phases)
        self.assertAlmostEqual(tempo, 0.0)


class TestAnalyzeSequence(unittest.TestCase):
    """Integration test for the full analyze_sequence method."""

    def test_returns_all_keys(self):
        calc = SwayCalculator()
        seq = _make_sequence(10)
        results = calc.analyze_sequence(seq, frame_width=640)
        expected_keys = [
            'sway', 'shoulder_turn', 'hip_turn', 'x_factor',
            'shoulder_center', 'hip_center',
            'head_sway', 'spine_tilt', 'knee_flex', 'weight_shift',
            'spine_angle', 'lead_arm_angle',
            'phases', 'tempo', 'summary',
        ]
        for k in expected_keys:
            self.assertIn(k, results, f"Missing key: {k}")

    def test_per_frame_arrays_correct_length(self):
        calc = SwayCalculator()
        seq = _make_sequence(15)
        results = calc.analyze_sequence(seq, frame_width=640)
        for k in ['sway', 'shoulder_turn', 'hip_turn', 'x_factor',
                   'head_sway', 'spine_tilt', 'knee_flex', 'weight_shift',
                   'spine_angle', 'lead_arm_angle', 'phases']:
            self.assertEqual(len(results[k]), 15, f"Wrong length for {k}")

    def test_summary_has_all_keys(self):
        calc = SwayCalculator()
        seq = _make_sequence(10)
        results = calc.analyze_sequence(seq, frame_width=640)
        summary = results['summary']
        expected_summary_keys = [
            'max_sway_left', 'max_sway_right',
            'max_shoulder_turn', 'max_hip_turn', 'max_x_factor',
            'max_head_sway_left', 'max_head_sway_right',
            'min_spine_tilt', 'max_spine_tilt',
            'address_spine_angle', 'max_spine_angle_change',
            'min_lead_arm_angle',
            'address_knee_flex', 'max_knee_flex_change',
            'max_weight_shift_forward',
            'tempo_ratio',
        ]
        for k in expected_summary_keys:
            self.assertIn(k, summary, f"Missing summary key: {k}")

    def test_summary_values_are_numeric_or_none(self):
        calc = SwayCalculator()
        seq = _make_sequence(10)
        results = calc.analyze_sequence(seq, frame_width=640)
        for k, v in results['summary'].items():
            self.assertTrue(v is None or isinstance(v, (int, float)),
                            f"Summary {k} is {type(v)}, expected numeric or None")

    def test_handles_none_frames(self):
        calc = SwayCalculator()
        seq = [_make_landmarks(), None, _make_landmarks(), None, _make_landmarks()]
        results = calc.analyze_sequence(seq, frame_width=640)
        self.assertEqual(len(results['sway']), 5)
        self.assertIsNone(results['sway'][1])
        self.assertIsNone(results['sway'][3])

    def test_empty_sequence(self):
        calc = SwayCalculator()
        results = calc.analyze_sequence([], frame_width=640)
        self.assertEqual(len(results['sway']), 0)
        self.assertEqual(len(results['phases']), 0)

    def test_single_frame_sequence(self):
        calc = SwayCalculator()
        results = calc.analyze_sequence([_make_landmarks()], frame_width=640)
        self.assertEqual(len(results['sway']), 1)
        self.assertEqual(len(results['phases']), 1)

    def test_address_position_set_to_first_valid(self):
        calc = SwayCalculator()
        seq = [None, None, _make_landmarks(), _make_landmarks()]
        results = calc.analyze_sequence(seq, frame_width=640)
        # Frame 2 is the address, so sway at frame 2 should be 0
        self.assertAlmostEqual(results['sway'][2], 0.0, places=3)

    def test_phases_are_valid_strings(self):
        calc = SwayCalculator()
        seq = _make_sequence(20, shoulder_z_drift=0.02)
        results = calc.analyze_sequence(seq, frame_width=640)
        valid_phases = {'Address', 'Backswing', 'Top', 'Downswing', 'Impact', 'Follow-through'}
        for p in results['phases']:
            self.assertIn(p, valid_phases, f"Invalid phase: {p}")

    def test_tempo_is_numeric_or_none(self):
        calc = SwayCalculator()
        seq = _make_sequence(10)
        results = calc.analyze_sequence(seq, frame_width=640)
        self.assertTrue(results['tempo'] is None or isinstance(results['tempo'], (int, float)))


class TestLegacyInterface(unittest.TestCase):
    """Test backwards-compatible legacy functions."""

    def test_calculate_lateral_sway(self):
        from sway_calculator import calculate_lateral_sway
        seq = _make_sequence(5)
        result = calculate_lateral_sway(seq)
        self.assertEqual(len(result), 5)

    def test_calculate_rotation(self):
        from sway_calculator import calculate_rotation
        seq = _make_sequence(5)
        result = calculate_rotation(seq)
        self.assertEqual(len(result), 5)


if __name__ == '__main__':
    unittest.main()
