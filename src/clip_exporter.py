"""
Export annotated analysis frames as a short MP4 clip.
"""

from __future__ import annotations

import os
import re
from typing import Iterator, List, Optional, Tuple

import cv2
import numpy as np


def _open_writer(output_path: str, fps: float, size: Tuple[int, int]):
    """Open a VideoWriter, trying a few codecs. Caller must release it.

    A symlink is refused before any codec opens, so a failed open cannot
    ``os.remove`` a file that lives outside the recordings directory.
    """
    if os.path.islink(output_path):
        raise ValueError('clip output must not be a symlink')
    w, h = size
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    for codec in ('mp4v', 'XVID', 'MJPG'):
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(output_path, fourcc, float(fps), (w, h))
        if writer.isOpened():
            return writer
        writer.release()
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except OSError:
            pass
    raise ValueError('Could not open VideoWriter for clip export')


def _write_bgr_iter(frames: Iterator[np.ndarray], output_path: str, fps: float) -> dict:
    first = next(frames, None)
    if first is None:
        raise ValueError('No frames to export')
    h, w = first.shape[:2]
    writer = _open_writer(output_path, fps, (w, h))
    written = 0
    try:
        frame = first
        while frame is not None:
            if frame.shape[0] != h or frame.shape[1] != w:
                frame = cv2.resize(frame, (w, h))
            writer.write(frame)
            written += 1
            frame = next(frames, None)
    finally:
        writer.release()
    if written == 0:
        raise ValueError('No frames could be decoded for export')
    return {
        'path': output_path,
        'filename': os.path.basename(output_path),
        'frame_count': written,
        'fps': float(fps),
        'width': w,
        'height': h,
    }


def jpeg_frames_to_mp4(
    jpeg_frames: List[bytes],
    output_path: str,
    fps: float = 30.0,
) -> dict:
    """
    Write a list of JPEG byte-strings to an MP4 file.

    Returns a status dict with path, frame_count, and fps.
    Raises ValueError if there are no frames or VideoWriter fails.
    """
    if not jpeg_frames:
        raise ValueError('No frames to export')

    def _decoded():
        for raw in jpeg_frames:
            buf = np.frombuffer(raw, dtype=np.uint8)
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if frame is not None:
                yield frame

    try:
        return _write_bgr_iter(_decoded(), output_path, fps)
    except ValueError as exc:
        if str(exc) == 'No frames to export':
            raise ValueError('No frames could be decoded for export') from exc
        raise


def video_file_to_mp4(
    video_path: str,
    output_path: str,
    fps: float = 30.0,
) -> dict:
    """
    Re-encode a saved recording to a clip MP4 without loading every frame.

    Raises ValueError if the file cannot be opened or has no readable frames.
    """
    if not os.path.isfile(video_path):
        raise ValueError(f'Video not found: {os.path.basename(video_path)}')

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f'Could not open video: {os.path.basename(video_path)}')

    def _iter():
        try:
            while True:
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                yield frame
        finally:
            cap.release()

    try:
        return _write_bgr_iter(_iter(), output_path, fps)
    except ValueError as exc:
        if str(exc) == 'No frames to export':
            raise ValueError(
                f'No frames decoded from {os.path.basename(video_path)}'
            ) from exc
        raise


_RECORDING_STAMP = re.compile(r'^\d{8}_\d{6}$')


def resolve_clip_output(
    recordings_dir: str,
    timestamp: str,
    camera_num: int,
) -> str:
    """Standard path for an exported annotated clip.

    A timestamp that is not a recording id, or a camera other than 1 or 2,
    is refused before the path is joined. That keeps a caller from writing
    ``clip_../../outside_camera9.mp4``.
    """
    if not isinstance(timestamp, str) or _RECORDING_STAMP.fullmatch(timestamp) is None:
        raise ValueError('Invalid timestamp')
    if type(camera_num) is not int or camera_num not in (1, 2):
        raise ValueError('camera must be 1 or 2')
    name = f'clip_{timestamp}_camera{camera_num}.mp4'
    return os.path.join(recordings_dir, name)


def overlay_video_path(recordings_dir: str, timestamp: str, camera_num: int) -> str:
    """Pose-overlay MP4 stored beside the recording pair."""
    if not isinstance(timestamp, str) or _RECORDING_STAMP.fullmatch(timestamp) is None:
        raise ValueError('Invalid timestamp')
    if type(camera_num) is not int or camera_num not in (1, 2):
        raise ValueError('camera must be 1 or 2')
    name = f'overlay_{timestamp}_camera{camera_num}.mp4'
    return os.path.join(recordings_dir, name)


def read_video_frame_jpeg(video_path: str, index: int, quality: int = 85) -> Optional[bytes]:
    """Decode one frame from an overlay video and return JPEG bytes."""
    if not isinstance(index, int) or index < 0 or not os.path.isfile(video_path):
        return None
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        ok, frame = cap.read()
        if not ok or frame is None:
            return None
        encoded, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
        if not encoded:
            return None
        return buf.tobytes()
    finally:
        cap.release()
