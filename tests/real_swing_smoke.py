"""
Opt-in MediaPipe smoke on real Face-On / Down-the-Line golf swings.

Default unit tests stay on synthetic stick-figure MP4s. This module is for
checking that the real pose model can see a person and that SwayCalculator
still produces a summary — not for training or score calibration.

Clip resolution (first match wins per view):
  1. fixtures/real_swings/face_on.* and dtl.* (drop your own recordings)
  2. recordings/recording_*_camera1.mp4 + camera2.mp4 pairs
  3. A small public GolfDB demo clip (downloaded on demand, not committed)

Enable the live model with SWINGLAB_REAL_SWING_SMOKE=1 or:
    python run_all_tests.py --smoke
    python scripts/smoke_real_swings.py
"""

from __future__ import annotations

import os
import re
import urllib.request
from typing import Dict, List, Optional

import cv2

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE_DIR = os.path.join(_PROJECT_ROOT, 'fixtures', 'real_swings')
RECORDINGS_DIR = os.path.join(_PROJECT_ROOT, 'recordings')

# Author-provided demo swing from the GolfDB repo (~440 KB). Research/demo use;
# cite McNally et al., CVPRW 2019. Not redistributed in this repository.
GOLFDB_DEMO = {
    'name': 'golfdb_test_video.mp4',
    'url': 'https://raw.githubusercontent.com/wmcnally/golfdb/master/test_video.mp4',
    'view': 'dtl',
    'license': 'GolfDB demo clip (McNally et al., CVPRW 2019)',
}

_RECORDING_PAIR = re.compile(r'^recording_(\d{8}_\d{6})_camera1\.mp4$')
_VIDEO_EXTS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')


def fixture_dir() -> str:
    override = os.environ.get('SWINGLAB_REAL_SWING_DIR')
    return override if override else FIXTURE_DIR


def labeled_local_clips(root: Optional[str] = None) -> List[Dict]:
    """Return face_on.* / dtl.* files dropped into the fixture directory."""
    root = root or fixture_dir()
    if not os.path.isdir(root):
        return []
    found = []
    for view in ('face_on', 'dtl'):
        for ext in _VIDEO_EXTS:
            path = os.path.join(root, f'{view}{ext}')
            if os.path.isfile(path):
                found.append({
                    'path': path,
                    'view': view,
                    'source': 'local-fixture',
                })
                break
    return found


def recording_pair_clips(root: Optional[str] = None) -> List[Dict]:
    """Newest dual-camera pair under recordings/, if both files exist."""
    root = root or RECORDINGS_DIR
    if not os.path.isdir(root):
        return []
    pairs = []
    for name in os.listdir(root):
        match = _RECORDING_PAIR.match(name)
        if not match:
            continue
        ts = match.group(1)
        cam1 = os.path.join(root, f'recording_{ts}_camera1.mp4')
        cam2 = os.path.join(root, f'recording_{ts}_camera2.mp4')
        if os.path.isfile(cam1) and os.path.isfile(cam2):
            pairs.append((ts, cam1, cam2))
    if not pairs:
        return []
    pairs.sort(reverse=True)
    _, cam1, cam2 = pairs[0]
    return [
        {'path': cam1, 'view': 'face_on', 'source': 'recordings'},
        {'path': cam2, 'view': 'dtl', 'source': 'recordings'},
    ]


def download_golfdb_demo(dest_dir: Optional[str] = None) -> Dict:
    """Fetch the small GolfDB demo clip into the fixture cache."""
    dest_dir = dest_dir or fixture_dir()
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, GOLFDB_DEMO['name'])
    if os.path.isfile(path) and os.path.getsize(path) > 10_000:
        return {
            'path': path,
            'view': GOLFDB_DEMO['view'],
            'source': 'golfdb-cache',
            'license': GOLFDB_DEMO['license'],
        }
    req = urllib.request.Request(
        GOLFDB_DEMO['url'],
        headers={'User-Agent': 'camera_recorder-real-swing-smoke'},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    if len(data) < 10_000:
        raise RuntimeError('GolfDB demo download was unexpectedly small')
    tmp = path + '.part'
    with open(tmp, 'wb') as handle:
        handle.write(data)
    os.replace(tmp, path)
    return {
        'path': path,
        'view': GOLFDB_DEMO['view'],
        'source': 'golfdb-download',
        'license': GOLFDB_DEMO['license'],
    }


def resolve_smoke_clips(*, fetch_public: bool = False) -> List[Dict]:
    """Local labeled files, else a recordings pair, else optional public demo."""
    local = labeled_local_clips()
    if local:
        return local
    pairs = recording_pair_clips()
    if pairs:
        return pairs
    if fetch_public:
        return [download_golfdb_demo()]
    return []


def sample_landmarks(path: str, processor, max_frames: int = 36) -> List[Optional[Dict]]:
    """Run MediaPipe on an even sample of frames (smoke, not full analysis)."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f'Failed to open video: {path}')
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        step = max(1, total // max_frames) if total > max_frames else 1
        landmarks: List[Optional[Dict]] = []
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if index % step == 0:
                results, _annotated = processor.process_frame(frame)
                if results.pose_landmarks:
                    landmarks.append(processor._extract_landmarks(results.pose_landmarks))
                else:
                    landmarks.append(None)
                if len(landmarks) >= max_frames:
                    break
            index += 1
        if not landmarks:
            raise RuntimeError(f'No frames decoded from {path}')
        return landmarks
    finally:
        cap.release()


def detection_rate(landmarks: List[Optional[Dict]]) -> float:
    if not landmarks:
        return 0.0
    hits = sum(1 for item in landmarks if item is not None)
    return hits / len(landmarks)


def smoke_clip(path: str, view: str, processor, max_frames: int = 36) -> Dict:
    from sway_calculator import SwayCalculator

    landmarks = sample_landmarks(path, processor, max_frames=max_frames)
    rate = detection_rate(landmarks)
    analysis = SwayCalculator().analyze_sequence(landmarks)
    summary = analysis.get('summary') or {}
    return {
        'path': path,
        'view': view,
        'frames': len(landmarks),
        'detection_rate': round(rate, 3),
        'max_shoulder_turn': summary.get('max_shoulder_turn'),
        'max_sway_right': summary.get('max_sway_right'),
        'address_spine_angle': summary.get('address_spine_angle'),
        'summary': summary,
    }


def run_smoke(*, fetch_public: bool = True, min_detection: float = 0.25) -> List[Dict]:
    """Process resolved clips with the lite MediaPipe model."""
    from pose_processor import PoseProcessor

    clips = resolve_smoke_clips(fetch_public=fetch_public)
    if not clips:
        raise RuntimeError(
            'No real-swing clips found. Drop face_on.mp4 and dtl.mp4 into '
            'fixtures/real_swings/, or re-run with fetch_public=True.'
        )
    try:
        processor = PoseProcessor(model_complexity=0)
    except Exception as exc:
        hint = ''
        if 'libEGL' in str(exc) or 'EGL' in str(exc):
            hint = (
                ' MediaPipe needs a GL/EGL library on Linux '
                '(Debian/Ubuntu: sudo apt install libegl1 libgles2).'
            )
        raise RuntimeError(f'Could not start MediaPipe pose model: {exc}.{hint}') from exc
    try:
        results = []
        for clip in clips:
            result = smoke_clip(clip['path'], clip['view'], processor)
            result['source'] = clip.get('source')
            if result['detection_rate'] < min_detection:
                raise RuntimeError(
                    f"{os.path.basename(clip['path'])} ({clip['view']}): "
                    f"detection_rate {result['detection_rate']:.0%} "
                    f"below smoke floor {min_detection:.0%}"
                )
            results.append(result)
        return results
    finally:
        processor.release()
