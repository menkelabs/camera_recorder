"""
Shared test helpers for the camera_recorder project.

Centralises path bootstrapping, landmark fixtures, and re-exports the
cross-platform camera helpers so tests can do::

    from helpers import ensure_project_paths, get_camera_ids, make_address_pose
"""

import os
import sys

# ---------------------------------------------------------------------------
# Path bootstrap — call ensure_project_paths() at the top of any test module
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def project_root() -> str:
    """Absolute path to the repository root."""
    return _PROJECT_ROOT


def ensure_project_paths():
    """Insert src/ and scripts/ onto sys.path (idempotent)."""
    src = os.path.join(_PROJECT_ROOT, 'src')
    scripts = os.path.join(_PROJECT_ROOT, 'scripts')
    for path in (src, scripts):
        if path not in sys.path:
            sys.path.insert(0, path)


# Always bootstrap when this module is imported
ensure_project_paths()

# Re-export platform helpers so tests have one import surface
from camera_utils import (  # noqa: E402
    create_camera_capture,
    describe_platform_setup,
    fix_console_encoding,
    get_camera_ids,
    get_config_path,
    get_default_camera_ids,
    get_opencv_backend,
    get_platform_info,
    load_camera_config,
)


# ---------------------------------------------------------------------------
# Landmark fixtures
# ---------------------------------------------------------------------------

def make_landmark(x, y, z=0.0, visibility=1.0):
    """Build a single landmark dict."""
    return {'x': float(x), 'y': float(y), 'z': float(z), 'visibility': float(visibility)}


def make_address_pose(
    hip_x=0.5,
    shoulder_x=0.5,
    nose_x=0.5,
    z_offset=0.0,
):
    """
    Build a complete set of golf-relevant landmarks for a neutral address pose.

    Coordinates are normalised (0-1).  The figure faces the camera (face-on)
    with hips/shoulders centred and arms hanging.
    """
    return {
        'nose': make_landmark(nose_x, 0.15, 0.0),
        'left_ear': make_landmark(nose_x + 0.03, 0.14, 0.0),
        'right_ear': make_landmark(nose_x - 0.03, 0.14, 0.0),
        'left_shoulder': make_landmark(shoulder_x + 0.12, 0.30, z_offset),
        'right_shoulder': make_landmark(shoulder_x - 0.12, 0.30, -z_offset),
        'left_elbow': make_landmark(shoulder_x + 0.15, 0.45, 0.0),
        'right_elbow': make_landmark(shoulder_x - 0.15, 0.45, 0.0),
        'left_wrist': make_landmark(shoulder_x + 0.15, 0.60, 0.0),
        'right_wrist': make_landmark(shoulder_x - 0.15, 0.60, 0.0),
        'left_hip': make_landmark(hip_x + 0.08, 0.55, z_offset * 0.5),
        'right_hip': make_landmark(hip_x - 0.08, 0.55, -z_offset * 0.5),
        'left_knee': make_landmark(hip_x + 0.08, 0.75, 0.0),
        'right_knee': make_landmark(hip_x - 0.08, 0.75, 0.0),
        'left_ankle': make_landmark(hip_x + 0.08, 0.95, 0.0),
        'right_ankle': make_landmark(hip_x - 0.08, 0.95, 0.0),
    }


def make_swing_sequence(n_frames=30, peak_turn=45.0):
    """
    Generate a synthetic landmark sequence that mimics a golf swing.

    Shoulder turn rises to *peak_turn* at mid-sequence (top of backswing)
    then falls back toward zero (downswing / impact / follow-through).
    """
    sequence = []
    for i in range(n_frames):
        mid = n_frames // 2
        if i <= mid:
            frac = i / mid if mid else 0
        else:
            frac = 1.0 - (i - mid) / max(n_frames - mid, 1)
        z = (peak_turn / 45.0) * frac * 0.15
        sway = -0.02 * frac
        sequence.append(make_address_pose(
            hip_x=0.5 + sway,
            shoulder_x=0.5 + sway * 0.5,
            z_offset=z,
        ))
    return sequence


class FakeLandmark:
    """Minimal stand-in for a MediaPipe landmark proto."""

    def __init__(self, x=0.0, y=0.0, z=0.0, visibility=1.0):
        self.x = x
        self.y = y
        self.z = z
        self.visibility = visibility


def make_fake_pose_landmarks(count=33, overrides=None):
    """
    Build a list of FakeLandmark objects suitable for PoseProcessor._extract_landmarks.

    *overrides* is an optional dict of {index: (x, y, z)} to set specific joints.
    """
    landmarks = [FakeLandmark() for _ in range(count)]
    if overrides:
        for idx, coords in overrides.items():
            x, y, z = (coords + (0.0,))[:3] if len(coords) < 3 else coords
            landmarks[idx] = FakeLandmark(x, y, z)
    return landmarks
