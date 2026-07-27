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


# ---------------------------------------------------------------------------
# Synthetic / mock video captures
# ---------------------------------------------------------------------------

def _draw_stick_figure(frame, cx, cy, scale=1.0, color=(0, 220, 0), z_shift=0.0):
    """
    Draw a simple stick figure into *frame* (BGR).

    Positions roughly match MediaPipe-normalised golf pose layout so annotated
    frames look intentional when reviewing analysis exports.
    """
    import cv2
    import numpy as np

    h, w = frame.shape[:2]
    # Normalised joints → pixels (x shifted by z_shift for a cheap “rotation” cue)
    joints = {
        'nose': (cx, cy - 0.28 * scale),
        'l_shoulder': (cx + 0.12 * scale + z_shift * 0.05, cy - 0.18 * scale),
        'r_shoulder': (cx - 0.12 * scale - z_shift * 0.05, cy - 0.18 * scale),
        'l_elbow': (cx + 0.18 * scale, cy - 0.02 * scale),
        'r_elbow': (cx - 0.18 * scale, cy - 0.02 * scale),
        'l_wrist': (cx + 0.16 * scale, cy + 0.12 * scale),
        'r_wrist': (cx - 0.16 * scale, cy + 0.12 * scale),
        'l_hip': (cx + 0.08 * scale + z_shift * 0.02, cy + 0.05 * scale),
        'r_hip': (cx - 0.08 * scale - z_shift * 0.02, cy + 0.05 * scale),
        'l_knee': (cx + 0.08 * scale, cy + 0.22 * scale),
        'r_knee': (cx - 0.08 * scale, cy + 0.22 * scale),
        'l_ankle': (cx + 0.08 * scale, cy + 0.38 * scale),
        'r_ankle': (cx - 0.08 * scale, cy + 0.38 * scale),
    }

    def px(name):
        x, y = joints[name]
        return int(np.clip(x, 0, 1) * (w - 1)), int(np.clip(y, 0, 1) * (h - 1))

    bones = [
        ('l_shoulder', 'r_shoulder'),
        ('l_shoulder', 'l_elbow'), ('l_elbow', 'l_wrist'),
        ('r_shoulder', 'r_elbow'), ('r_elbow', 'r_wrist'),
        ('l_shoulder', 'l_hip'), ('r_shoulder', 'r_hip'),
        ('l_hip', 'r_hip'),
        ('l_hip', 'l_knee'), ('l_knee', 'l_ankle'),
        ('r_hip', 'r_knee'), ('r_knee', 'r_ankle'),
        ('l_shoulder', 'nose'), ('r_shoulder', 'nose'),
    ]
    for a, b in bones:
        cv2.line(frame, px(a), px(b), color, 2, cv2.LINE_AA)
    for name in joints:
        cv2.circle(frame, px(name), 4, color, -1, cv2.LINE_AA)


def write_mock_video(
    path,
    n_frames=30,
    width=320,
    height=240,
    fps=30.0,
    pattern='swing',
    codec='mp4v',
):
    """
    Write a synthetic video file that OpenCV can reopen via VideoCapture.

    Patterns:
      - ``solid``: flat colour frames (no figure)
      - ``swing``: stick figure with sway + turn over the sequence
      - ``static_pose``: stick figure frozen at address
      - ``blank``: near-black frames (simulates “no detection” lab floor)

    Returns absolute path. Prefer ``.mp4``; falls back across codecs if needed.
    """
    import cv2
    import numpy as np

    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)

    writer = None
    used_codec = None
    for candidate in (codec, 'mp4v', 'MJPG', 'XVID'):
        fourcc = cv2.VideoWriter_fourcc(*candidate)
        # MJPG is more reliable in .avi containers on some OpenCV builds
        out_path = path
        if candidate == 'MJPG' and path.lower().endswith('.mp4'):
            out_path = os.path.splitext(path)[0] + '.avi'
        w = cv2.VideoWriter(out_path, fourcc, float(fps), (width, height))
        if w.isOpened():
            writer = w
            used_codec = candidate
            path = out_path
            break
        w.release()
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except OSError:
            pass

    if writer is None:
        raise RuntimeError(f'Could not open VideoWriter for {path}')

    mid = max(n_frames // 2, 1)
    try:
        for i in range(n_frames):
            if pattern == 'blank':
                frame = np.zeros((height, width, 3), dtype=np.uint8)
            elif pattern == 'solid':
                frame = np.full((height, width, 3), (40, 90, 140), dtype=np.uint8)
            else:
                # Subtle gradient background so frames are visually distinct
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                frame[:, :] = (30 + (i % 20), 45, 70)

            if pattern in ('swing', 'static_pose'):
                if pattern == 'swing':
                    frac = (i / mid) if i <= mid else (1.0 - (i - mid) / max(n_frames - mid, 1))
                    sway = -0.04 * frac
                    z_shift = 0.8 * frac
                else:
                    sway = 0.0
                    z_shift = 0.0
                _draw_stick_figure(
                    frame,
                    cx=0.5 + sway,
                    cy=0.48,
                    scale=0.9,
                    color=(40, 220, 80) if pattern == 'swing' else (80, 180, 255),
                    z_shift=z_shift,
                )
                # Frame index badge for debugging playback
                cv2.putText(
                    frame, f'{i:03d}', (8, height - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1, cv2.LINE_AA,
                )

            writer.write(frame)
    finally:
        writer.release()

    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise RuntimeError(f'Mock video was not written: {path} (codec={used_codec})')
    return os.path.abspath(path)


def write_mock_swing_pair(
    directory,
    timestamp='20260727_120000',
    n_frames_cam1=24,
    n_frames_cam2=20,
    width=320,
    height=240,
    fps=30.0,
    pattern='swing',
):
    """
    Write a dual-camera recording pair with production-like filenames.

    Returns ``(cam1_path, cam2_path)`` suitable for ``CameraManager.recording_files``.
    Frame counts may differ (common in real captures) so navigation code is exercised.
    """
    os.makedirs(directory, exist_ok=True)
    cam1 = os.path.join(directory, f'recording_{timestamp}_camera1.mp4')
    cam2 = os.path.join(directory, f'recording_{timestamp}_camera2.mp4')
    cam1 = write_mock_video(
        cam1, n_frames=n_frames_cam1, width=width, height=height,
        fps=fps, pattern=pattern,
    )
    cam2 = write_mock_video(
        cam2, n_frames=n_frames_cam2, width=width, height=height,
        fps=fps, pattern=pattern,
    )
    return cam1, cam2


def count_video_frames(path):
    """Read every frame from *path* and return how many were decoded."""
    import cv2

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f'Failed to open video: {path}')
    n = 0
    try:
        while True:
            ret, _ = cap.read()
            if not ret:
                break
            n += 1
    finally:
        cap.release()
    return n


def video_probe(path):
    """Return basic properties for a video file."""
    import cv2

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f'Failed to open video: {path}')
    try:
        info = {
            'path': path,
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
            'fps': float(cap.get(cv2.CAP_PROP_FPS) or 0),
            'reported_frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
        }
    finally:
        cap.release()
    info['readable_frames'] = count_video_frames(path)
    return info


def make_annotated_jpeg_frames(n_frames=12, width=160, height=120, label='cam'):
    """Build JPEG byte-strings like CameraManager.analysis_frames_cam*."""
    import cv2
    import numpy as np

    frames = []
    for i in range(n_frames):
        img = np.zeros((height, width, 3), dtype=np.uint8)
        img[:, :] = (20 + i * 3, 60, 100)
        _draw_stick_figure(img, cx=0.5, cy=0.5, scale=0.8, z_shift=i * 0.05)
        cv2.putText(
            img, f'{label}:{i}', (6, 18),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA,
        )
        ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ok:
            raise RuntimeError('JPEG encode failed')
        frames.append(buf.tobytes())
    return frames


def landmarks_and_frames_from_video(path, landmark_sequence=None):
    """
    Read a mock video and pair each frame with a landmark dict (or None).

    Useful when patching ``PoseProcessor.process_video`` while still exercising
    real OpenCV decode + annotated-frame compression in CameraManager.
    """
    import cv2

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f'Failed to open video: {path}')
    landmarks = []
    frames = []
    idx = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            if landmark_sequence is None:
                landmarks.append(None)
            elif idx < len(landmark_sequence):
                landmarks.append(landmark_sequence[idx])
            else:
                landmarks.append(None)
            idx += 1
    finally:
        cap.release()
    return landmarks, frames
