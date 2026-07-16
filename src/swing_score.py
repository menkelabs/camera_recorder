"""
Swing score / grade from analysis summary metrics.

Uses the same good/ok ranges as the Analysis dashboard so the letter
grade matches the colour coding users already see on metric cards.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


# Mirrors templates/index.html METRIC_DEFS summaryKey + good/ok ranges.
# cam: which camera summary to read (1=face-on, 2=DTL).
SCORE_METRICS: List[Dict[str, Any]] = [
    # Rotation (DTL)
    {'key': 'shoulder_turn', 'label': 'Shoulder Turn', 'cam': 2,
     'summary_key': 'max_shoulder_turn', 'good': (60, 100), 'ok': (40, 60)},
    {'key': 'hip_turn', 'label': 'Hip Turn', 'cam': 2,
     'summary_key': 'max_hip_turn', 'good': (30, 50), 'ok': (20, 30)},
    {'key': 'x_factor', 'label': 'X-Factor', 'cam': 2,
     'summary_key': 'max_x_factor', 'good': (30, 55), 'ok': (20, 30)},
    # Tempo (face-on)
    {'key': 'tempo', 'label': 'Tempo', 'cam': 1,
     'summary_key': 'tempo_ratio', 'good': (2.5, 3.5), 'ok': (2.0, 4.0)},
    # Position
    {'key': 'sway', 'label': 'Lateral Sway', 'cam': 1,
     'summary_key': 'max_sway_right', 'good': (-20, 20), 'ok': (-40, 40)},
    {'key': 'head_sway', 'label': 'Head Sway', 'cam': 1,
     'summary_key': 'max_head_sway_right', 'good': (-10, 10), 'ok': (-25, 25)},
    {'key': 'spine_angle', 'label': 'Spine Angle', 'cam': 2,
     'summary_key': 'address_spine_angle', 'good': (25, 40), 'ok': (15, 50)},
    {'key': 'spine_tilt', 'label': 'Spine Tilt', 'cam': 1,
     'summary_key': 'max_spine_tilt', 'good': (-10, 15), 'ok': (-20, 20)},
    # Body
    {'key': 'lead_arm_angle', 'label': 'Lead Arm', 'cam': 2,
     'summary_key': 'min_lead_arm_angle', 'good': (160, 180), 'ok': (140, 160)},
    {'key': 'knee_flex', 'label': 'Knee Flex', 'cam': 1,
     'summary_key': 'address_knee_flex', 'good': (150, 175), 'ok': (130, 150)},
    {'key': 'weight_shift', 'label': 'Weight Shift', 'cam': 1,
     'summary_key': 'max_weight_shift_forward', 'good': (55, 80), 'ok': (40, 55)},
]

# Points: good=100, ok=60, needs-work=20
_POINTS = {'good': 100.0, 'ok': 60.0, 'needs_work': 20.0}

# Short coaching drills for metrics rated needs_work
DRILL_TIPS = {
    'shoulder_turn': (
        'Make a fuller shoulder turn with a quiet lower body. '
        'Pause at the top and feel your lead shoulder under your chin.'
    ),
    'hip_turn': (
        'Start the downswing with the hips. Feel pressure move into the lead heel '
        'before the arms drop.'
    ),
    'x_factor': (
        'Create separation: turn shoulders more than hips on the backswing, '
        'then lead with the hips on the way down.'
    ),
    'tempo': (
        'Count a smooth 3:1 rhythm — “one-two-three” back, “one” through. '
        'A metronome app at a slow beat helps.'
    ),
    'sway': (
        'Keep the trail hip from sliding away from the target. '
        'Feel like you turn around a stable trail leg.'
    ),
    'head_sway': (
        'Pick a spot behind the ball and keep your head quiet over it '
        'until after impact.'
    ),
    'spine_angle': (
        'Set posture at address and hold it. Practice half-swings focusing on '
        'keeping chest tilt constant.'
    ),
    'spine_tilt': (
        'Avoid early standing up. Feel the trail shoulder stay lower through impact.'
    ),
    'lead_arm_angle': (
        'Widen the swing arc — soft trail elbow, lead arm extended but not locked '
        'at the top.'
    ),
    'knee_flex': (
        'Soft-flex both knees at address and keep that flex into the downswing; '
        'don’t straighten early.'
    ),
    'weight_shift': (
        'Finish with most pressure on the lead foot. Step-through drills: '
        'step toward the target as you swing through.'
    ),
}


def rate_value(value: Optional[float], good: Tuple[float, float],
               ok: Tuple[float, float]) -> Optional[str]:
    """Return 'good', 'ok', 'needs_work', or None if value is missing."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if good[0] <= v <= good[1]:
        return 'good'
    if ok[0] <= v <= ok[1]:
        return 'ok'
    return 'needs_work'


def grade_from_score(score: Optional[float]) -> Optional[str]:
    """Map 0-100 score to a letter grade."""
    if score is None:
        return None
    if score >= 90:
        return 'A'
    if score >= 80:
        return 'B'
    if score >= 70:
        return 'C'
    if score >= 60:
        return 'D'
    return 'F'


def _cam_summary(analysis: Dict, cam: int) -> Dict:
    key = 'camera1' if cam == 1 else 'camera2'
    block = analysis.get(key) or {}
    return block.get('summary') or {}


def score_analysis(analysis: Dict) -> Dict[str, Any]:
    """
    Compute an overall swing score from a saved or live analysis payload.

    ``analysis`` shape matches analysis_*.json / get_analysis_results():
      { camera1: { summary: {...} }, camera2: { summary: {...} } }

    Returns:
        {
          'score': float|None,          # 0-100 average of rated metrics
          'grade': str|None,            # A-F
          'rated_count': int,
          'breakdown': [ {key, label, value, rating, points}, ... ],
          'strengths': [label, ...],    # good ratings
          'focus_areas': [label, ...],  # needs_work ratings
        }
    """
    breakdown = []
    points_list = []

    for metric in SCORE_METRICS:
        summary = _cam_summary(analysis, metric['cam'])
        raw = summary.get(metric['summary_key'])
        # Lateral/head sway: prefer magnitude of worst side when only one key
        if metric['key'] == 'sway' and raw is not None:
            left = summary.get('max_sway_left')
            right = summary.get('max_sway_right')
            candidates = [v for v in (left, right) if v is not None]
            if candidates:
                # Use the value farthest from 0 (worst sway)
                raw = max(candidates, key=lambda x: abs(x))
        if metric['key'] == 'head_sway' and raw is not None:
            left = summary.get('max_head_sway_left')
            right = summary.get('max_head_sway_right')
            candidates = [v for v in (left, right) if v is not None]
            if candidates:
                raw = max(candidates, key=lambda x: abs(x))

        rating = rate_value(raw, metric['good'], metric['ok'])
        pts = _POINTS[rating] if rating else None
        entry = {
            'key': metric['key'],
            'label': metric['label'],
            'cam': metric['cam'],
            'summary_key': metric['summary_key'],
            'value': raw if raw is None else float(raw),
            'rating': rating,
            'points': pts,
        }
        breakdown.append(entry)
        if pts is not None:
            points_list.append(pts)

    score = round(sum(points_list) / len(points_list), 1) if points_list else None
    grade = grade_from_score(score)

    focus_keys = [e['key'] for e in breakdown if e['rating'] == 'needs_work']
    drills = [
        {'key': k, 'label': next(e['label'] for e in breakdown if e['key'] == k),
         'tip': DRILL_TIPS[k]}
        for k in focus_keys if k in DRILL_TIPS
    ]

    return {
        'score': score,
        'grade': grade,
        'rated_count': len(points_list),
        'metric_count': len(SCORE_METRICS),
        'breakdown': breakdown,
        'strengths': [e['label'] for e in breakdown if e['rating'] == 'good'],
        'focus_areas': [e['label'] for e in breakdown if e['rating'] == 'needs_work'],
        'drills': drills,
    }
