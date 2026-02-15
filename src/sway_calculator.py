"""
Sway calculator module
Calculates lateral sway, rotation, and biomechanical metrics from pose landmarks
"""

import math
import numpy as np
from typing import List, Dict, Optional, Tuple


def _angle_between(a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]) -> Optional[float]:
    """
    Calculate the angle at point b formed by points a-b-c (in degrees).
    Uses 2D (x, y) coordinates.
    """
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.sqrt(ba[0] ** 2 + ba[1] ** 2)
    mag_bc = math.sqrt(bc[0] ** 2 + bc[1] ** 2)
    if mag_ba < 1e-9 or mag_bc < 1e-9:
        return None
    cos_angle = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))


class SwayCalculator:
    """Calculate golf swing biomechanics from pose landmarks"""

    def __init__(self):
        self.address_landmarks = None  # Reference position (first frame or manual set)

    def set_address_position(self, landmarks: Dict):
        """Set the address position as reference for all measurements"""
        self.address_landmarks = landmarks

    # ------------------------------------------------------------------
    # Center-point helpers
    # ------------------------------------------------------------------

    def calculate_hip_center(self, landmarks: Dict) -> Optional[Tuple[float, float]]:
        """Calculate center point between hips. Returns (x, y) normalised."""
        if landmarks is None:
            return None
        left_hip = landmarks.get('left_hip')
        right_hip = landmarks.get('right_hip')
        if left_hip is None or right_hip is None:
            return None
        return ((left_hip['x'] + right_hip['x']) / 2,
                (left_hip['y'] + right_hip['y']) / 2)

    def calculate_shoulder_center(self, landmarks: Dict) -> Optional[Tuple[float, float]]:
        """Calculate center point between shoulders. Returns (x, y) normalised."""
        if landmarks is None:
            return None
        ls = landmarks.get('left_shoulder')
        rs = landmarks.get('right_shoulder')
        if ls is None or rs is None:
            return None
        return ((ls['x'] + rs['x']) / 2,
                (ls['y'] + rs['y']) / 2)

    # ------------------------------------------------------------------
    # Existing metrics
    # ------------------------------------------------------------------

    def calculate_lateral_sway(self, landmarks: Dict, frame_width: int = 1) -> Optional[float]:
        """
        Lateral hip sway from address position (face-on view).
        Positive = toward target, Negative = away from target.
        Returns pixels (or normalised if frame_width=1).
        """
        if self.address_landmarks is None or landmarks is None:
            return None
        current_hip = self.calculate_hip_center(landmarks)
        address_hip = self.calculate_hip_center(self.address_landmarks)
        if current_hip is None or address_hip is None:
            return None
        return (current_hip[0] - address_hip[0]) * frame_width

    def calculate_shoulder_turn(self, landmarks: Dict) -> Optional[float]:
        """
        Shoulder rotation angle in degrees.
        Uses depth (z) difference between left/right shoulders.
        0 = address, positive = backswing rotation.
        """
        if landmarks is None:
            return None
        ls = landmarks.get('left_shoulder')
        rs = landmarks.get('right_shoulder')
        if ls is None or rs is None:
            return None
        shoulder_width = abs(rs['x'] - ls['x'])
        z_diff = rs['z'] - ls['z']
        return np.degrees(np.arctan2(z_diff, shoulder_width))

    def calculate_hip_turn(self, landmarks: Dict) -> Optional[float]:
        """Hip rotation angle in degrees (same method as shoulder turn)."""
        if landmarks is None:
            return None
        lh = landmarks.get('left_hip')
        rh = landmarks.get('right_hip')
        if lh is None or rh is None:
            return None
        hip_width = abs(rh['x'] - lh['x'])
        z_diff = rh['z'] - lh['z']
        return np.degrees(np.arctan2(z_diff, hip_width))

    def calculate_x_factor(self, landmarks: Dict) -> Optional[float]:
        """X-Factor = |shoulder_turn - hip_turn| (degrees)."""
        st = self.calculate_shoulder_turn(landmarks)
        ht = self.calculate_hip_turn(landmarks)
        if st is None or ht is None:
            return None
        return abs(st - ht)

    # ------------------------------------------------------------------
    # NEW metrics - Face-On Camera (Camera 1)
    # ------------------------------------------------------------------

    def calculate_head_sway(self, landmarks: Dict, frame_width: int = 1) -> Optional[float]:
        """
        Head lateral movement from address position (face-on).
        Tracks the nose landmark. Positive = toward target.
        Returns pixels.
        """
        if self.address_landmarks is None or landmarks is None:
            return None
        nose = landmarks.get('nose')
        addr_nose = self.address_landmarks.get('nose')
        if nose is None or addr_nose is None:
            return None
        return (nose['x'] - addr_nose['x']) * frame_width

    def calculate_spine_tilt(self, landmarks: Dict) -> Optional[float]:
        """
        Spine tilt in the frontal plane (face-on view).
        Angle of the shoulder-center → hip-center line relative to vertical.
        Positive = tilting toward target (left for right-handed).
        Returns degrees.
        """
        sc = self.calculate_shoulder_center(landmarks)
        hc = self.calculate_hip_center(landmarks)
        if sc is None or hc is None:
            return None
        dx = sc[0] - hc[0]
        dy = sc[1] - hc[1]  # y increases downward in image
        # Angle from vertical (straight up would be dx=0, dy<0)
        # atan2(dx, -dy) gives angle from vertical; positive = leaning right in image
        return math.degrees(math.atan2(dx, -dy))

    def calculate_knee_flex(self, landmarks: Dict) -> Optional[float]:
        """
        Lead (left) knee flexion angle (face-on view).
        Angle at the knee formed by hip-knee-ankle.
        180 = fully straight, smaller = more bent.
        """
        if landmarks is None:
            return None
        lh = landmarks.get('left_hip')
        lk = landmarks.get('left_knee')
        la = landmarks.get('left_ankle')
        if lh is None or lk is None or la is None:
            return None
        return _angle_between(
            (lh['x'], lh['y']),
            (lk['x'], lk['y']),
            (la['x'], la['y']),
        )

    def calculate_weight_shift(self, landmarks: Dict) -> Optional[float]:
        """
        Weight shift as percentage (face-on view).
        Horizontal position of hip center between the ankles.
        0% = fully over trail foot, 50% = centered, 100% = fully over lead foot.
        """
        if landmarks is None:
            return None
        hc = self.calculate_hip_center(landmarks)
        la = landmarks.get('left_ankle')
        ra = landmarks.get('right_ankle')
        if hc is None or la is None or ra is None:
            return None
        ankle_span = la['x'] - ra['x']
        if abs(ankle_span) < 1e-6:
            return 50.0
        pct = (hc[0] - ra['x']) / ankle_span * 100.0
        return max(0.0, min(100.0, pct))

    # ------------------------------------------------------------------
    # NEW metrics - Down-the-Line Camera (Camera 2)
    # ------------------------------------------------------------------

    def calculate_spine_angle(self, landmarks: Dict) -> Optional[float]:
        """
        Spine angle in the sagittal plane (down-the-line view).
        Forward bend from hip center to shoulder center vs vertical.
        Larger = more bent over. Should stay constant during the swing.
        Returns degrees (0 = upright, 90 = horizontal).
        """
        sc = self.calculate_shoulder_center(landmarks)
        hc = self.calculate_hip_center(landmarks)
        if sc is None or hc is None:
            return None
        dx = sc[0] - hc[0]
        dy = sc[1] - hc[1]
        # In DTL view the forward bend shows as x displacement
        # Angle from vertical
        return math.degrees(math.atan2(abs(dx), abs(dy)))

    def calculate_lead_arm_angle(self, landmarks: Dict) -> Optional[float]:
        """
        Lead (left) arm angle at the elbow (DTL view).
        Angle at left_elbow formed by left_shoulder - left_elbow - left_wrist.
        180 = straight arm (desired at top), less = bent.
        """
        if landmarks is None:
            return None
        ls = landmarks.get('left_shoulder')
        le = landmarks.get('left_elbow')
        lw = landmarks.get('left_wrist')
        if ls is None or le is None or lw is None:
            return None
        return _angle_between(
            (ls['x'], ls['y']),
            (le['x'], le['y']),
            (lw['x'], lw['y']),
        )

    # ------------------------------------------------------------------
    # Swing phase detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_swing_phases(shoulder_turn: List[Optional[float]],
                            sway: List[Optional[float]]) -> List[str]:
        """
        Label each frame with a swing phase.
        Phases: Address, Backswing, Top, Downswing, Impact, Follow-through.
        Heuristic based on shoulder turn profile.
        """
        n = len(shoulder_turn)
        phases = ['Address'] * n

        # Find valid shoulder turn values (replace None with 0)
        st = [v if v is not None else 0.0 for v in shoulder_turn]

        if n < 5:
            return phases

        # Smooth with a small window
        kernel = 3
        smoothed = []
        for i in range(n):
            lo = max(0, i - kernel // 2)
            hi = min(n, i + kernel // 2 + 1)
            smoothed.append(sum(st[lo:hi]) / (hi - lo))

        # Find peak shoulder turn (top of backswing)
        top_idx = int(np.argmax(smoothed))

        # Find minimum shoulder turn after top (closest to impact)
        post_top = smoothed[top_idx:]
        if len(post_top) > 2:
            impact_offset = int(np.argmin(post_top))
            impact_idx = top_idx + impact_offset
        else:
            impact_idx = min(top_idx + 1, n - 1)

        # Address = first ~10% of frames before significant movement
        threshold = max(smoothed) * 0.1 if max(smoothed) > 0 else 1.0
        address_end = 0
        for i in range(min(top_idx, n)):
            if abs(smoothed[i] - smoothed[0]) > threshold:
                address_end = i
                break

        # Label phases
        for i in range(n):
            if i <= address_end:
                phases[i] = 'Address'
            elif i < top_idx:
                phases[i] = 'Backswing'
            elif i == top_idx:
                phases[i] = 'Top'
            elif i < impact_idx:
                phases[i] = 'Downswing'
            elif i == impact_idx:
                phases[i] = 'Impact'
            else:
                phases[i] = 'Follow-through'

        return phases

    @staticmethod
    def calculate_tempo(phases: List[str]) -> Optional[float]:
        """
        Tempo ratio = backswing frames / downswing frames.
        Pros average ~3:1.
        Returns None if either phase has 0 frames.
        """
        backswing = sum(1 for p in phases if p == 'Backswing')
        downswing = sum(1 for p in phases if p == 'Downswing')
        if downswing == 0:
            return None
        return round(backswing / downswing, 2)

    # ------------------------------------------------------------------
    # Full sequence analysis
    # ------------------------------------------------------------------

    def analyze_sequence(self, landmarks_sequence: List[Dict], frame_width: int = 1) -> Dict:
        """
        Analyze a full swing sequence.

        Args:
            landmarks_sequence: List of landmarks for each frame
            frame_width: Frame width for scaling sway/head_sway to pixels

        Returns:
            Dictionary with per-frame arrays and summary statistics
        """
        # Set first valid frame as address position
        for landmarks in landmarks_sequence:
            if landmarks is not None:
                self.set_address_position(landmarks)
                break

        results = {
            # Existing
            'sway': [],
            'shoulder_turn': [],
            'hip_turn': [],
            'x_factor': [],
            'shoulder_center': [],
            'hip_center': [],
            # New
            'head_sway': [],
            'spine_tilt': [],
            'knee_flex': [],
            'weight_shift': [],
            'spine_angle': [],
            'lead_arm_angle': [],
        }

        for landmarks in landmarks_sequence:
            results['sway'].append(self.calculate_lateral_sway(landmarks, frame_width))
            results['shoulder_turn'].append(self.calculate_shoulder_turn(landmarks))
            results['hip_turn'].append(self.calculate_hip_turn(landmarks))
            results['x_factor'].append(self.calculate_x_factor(landmarks))
            results['shoulder_center'].append(self.calculate_shoulder_center(landmarks))
            results['hip_center'].append(self.calculate_hip_center(landmarks))
            # New
            results['head_sway'].append(self.calculate_head_sway(landmarks, frame_width))
            results['spine_tilt'].append(self.calculate_spine_tilt(landmarks))
            results['knee_flex'].append(self.calculate_knee_flex(landmarks))
            results['weight_shift'].append(self.calculate_weight_shift(landmarks))
            results['spine_angle'].append(self.calculate_spine_angle(landmarks))
            results['lead_arm_angle'].append(self.calculate_lead_arm_angle(landmarks))

        # --- Swing phases and tempo ---
        results['phases'] = self.detect_swing_phases(results['shoulder_turn'], results['sway'])
        results['tempo'] = self.calculate_tempo(results['phases'])

        # --- Summary statistics ---
        def _valid(arr):
            return [v for v in arr if v is not None]

        valid_sway = _valid(results['sway'])
        valid_shoulder = _valid(results['shoulder_turn'])
        valid_hip = _valid(results['hip_turn'])
        valid_xfactor = _valid(results['x_factor'])
        valid_head = _valid(results['head_sway'])
        valid_tilt = _valid(results['spine_tilt'])
        valid_knee = _valid(results['knee_flex'])
        valid_weight = _valid(results['weight_shift'])
        valid_spine_a = _valid(results['spine_angle'])
        valid_arm = _valid(results['lead_arm_angle'])

        # Address values for "change" metrics
        addr_spine_angle = valid_spine_a[0] if valid_spine_a else None
        addr_knee_flex = valid_knee[0] if valid_knee else None

        results['summary'] = {
            # Existing
            'max_sway_left': min(valid_sway) if valid_sway else None,
            'max_sway_right': max(valid_sway) if valid_sway else None,
            'max_shoulder_turn': max(valid_shoulder) if valid_shoulder else None,
            'max_hip_turn': max(valid_hip) if valid_hip else None,
            'max_x_factor': max(valid_xfactor) if valid_xfactor else None,
            # Head sway
            'max_head_sway_left': min(valid_head) if valid_head else None,
            'max_head_sway_right': max(valid_head) if valid_head else None,
            # Spine tilt (frontal)
            'min_spine_tilt': min(valid_tilt) if valid_tilt else None,
            'max_spine_tilt': max(valid_tilt) if valid_tilt else None,
            # Spine angle (sagittal / posture)
            'address_spine_angle': addr_spine_angle,
            'max_spine_angle_change': (max(abs(v - addr_spine_angle) for v in valid_spine_a)
                                       if valid_spine_a and addr_spine_angle is not None else None),
            # Lead arm
            'min_lead_arm_angle': min(valid_arm) if valid_arm else None,
            # Knee flex
            'address_knee_flex': addr_knee_flex,
            'max_knee_flex_change': (max(abs(v - addr_knee_flex) for v in valid_knee)
                                     if valid_knee and addr_knee_flex is not None else None),
            # Weight shift
            'max_weight_shift_forward': max(valid_weight) if valid_weight else None,
            # Tempo
            'tempo_ratio': results['tempo'],
        }

        return results


# Legacy function interface for backwards compatibility
def calculate_lateral_sway(landmarks_sequence):
    """Calculate lateral sway from face-on view"""
    calc = SwayCalculator()
    results = calc.analyze_sequence(landmarks_sequence)
    return results['sway']

def calculate_rotation(landmarks_sequence):
    """Calculate rotation from DTL view"""
    calc = SwayCalculator()
    results = calc.analyze_sequence(landmarks_sequence)
    return results['shoulder_turn']
