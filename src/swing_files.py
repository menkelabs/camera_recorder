"""Recording and pose-overlay files stored beside each take."""

from __future__ import annotations

import os
import re
import shutil
from typing import Dict, List, Optional

from clip_exporter import jpeg_frames_to_mp4, overlay_video_path, read_video_frame_jpeg

_STAMP_OK = re.compile(r'^\d{8}_\d{6}$')
OVERLAY_FPS = 30.0


def _stamp_ok(timestamp: str) -> bool:
    return isinstance(timestamp, str) and _STAMP_OK.fullmatch(timestamp) is not None


def _inside(recordings_dir: str, path: str) -> Optional[str]:
    root = os.path.realpath(recordings_dir)
    real = os.path.realpath(path)
    if real == root or not real.startswith(root + os.sep):
        return None
    return real


def write_overlay_videos(
    recordings_dir: str,
    timestamp: str,
    frames_by_camera: Dict[int, List[bytes]],
    fps: float = OVERLAY_FPS,
) -> List[str]:
    """Write pose-overlay MP4s. Returns the paths that were written."""
    written = []
    for camera_num in (1, 2):
        frames = frames_by_camera.get(camera_num) or []
        if not frames:
            continue
        path = overlay_video_path(recordings_dir, timestamp, camera_num)
        jpeg_frames_to_mp4(frames, path, fps=fps)
        written.append(path)
    return written


def overlay_is_available(recordings_dir: str, timestamp: str) -> bool:
    if not _stamp_ok(timestamp):
        return False
    for camera_num in (1, 2):
        path = overlay_video_path(recordings_dir, timestamp, camera_num)
        if os.path.isfile(path):
            return True
    return False


def read_overlay_jpeg(
    recordings_dir: str,
    timestamp: str,
    camera_num: int,
    index: int,
) -> Optional[bytes]:
    if not _stamp_ok(timestamp) or camera_num not in (1, 2):
        return None
    path = overlay_video_path(recordings_dir, timestamp, camera_num)
    real = _inside(recordings_dir, path)
    if real is None or not os.path.isfile(real):
        return None
    return read_video_frame_jpeg(real, index)


def recording_video_file(
    recordings_dir: str,
    timestamp: str,
    camera_num: int,
) -> Optional[str]:
    """Absolute path of a source recording, or None when it is missing or unsafe."""
    if not _stamp_ok(timestamp) or camera_num not in (1, 2):
        return None
    path = os.path.join(recordings_dir, f'recording_{timestamp}_camera{camera_num}.mp4')
    real = _inside(recordings_dir, path)
    if real is None or not os.path.isfile(real):
        return None
    return real


def recording_video_flags(recordings_dir: str, timestamp: str) -> Dict[str, bool]:
    return {
        'camera1': recording_video_file(recordings_dir, timestamp, 1) is not None,
        'camera2': recording_video_file(recordings_dir, timestamp, 2) is not None,
    }


def copy_overlay_files(recordings_dir: str, timestamp: str, archive_dir: str) -> Dict[str, List[str]]:
    """Copy overlay MP4s into an archive directory."""
    copied: List[str] = []
    errors: List[str] = []
    if not _stamp_ok(timestamp):
        return {'copied': copied, 'errors': errors}
    os.makedirs(archive_dir, exist_ok=True)
    for camera_num in (1, 2):
        src = overlay_video_path(recordings_dir, timestamp, camera_num)
        if not os.path.isfile(src):
            continue
        name = os.path.basename(src)
        try:
            shutil.copy2(src, os.path.join(archive_dir, name))
            copied.append(name)
        except OSError as exc:
            errors.append(f'{name}: {exc}')
    return {'copied': copied, 'errors': errors}


def remove_overlay_files(recordings_dir: str, timestamp: str) -> List[str]:
    """Delete overlay MP4s that live inside the recordings directory."""
    removed = []
    if not _stamp_ok(timestamp):
        return removed
    for camera_num in (1, 2):
        path = overlay_video_path(recordings_dir, timestamp, camera_num)
        real = _inside(recordings_dir, path)
        if real is None or not os.path.isfile(real) or os.path.islink(path):
            continue
        os.remove(real)
        removed.append(os.path.basename(real))
    return removed
