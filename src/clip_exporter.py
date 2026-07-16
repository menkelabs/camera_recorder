"""
Export annotated analysis frames as a short MP4 clip.
"""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

import cv2
import numpy as np


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

    # Decode first frame for dimensions
    arr = np.frombuffer(jpeg_frames[0], dtype=np.uint8)
    first = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if first is None:
        raise ValueError('Failed to decode first JPEG frame')

    h, w = first.shape[:2]
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    fourcc = None
    for codec in ('mp4v', 'XVID', 'MJPG'):
        test = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(output_path, test, float(fps), (w, h))
        if writer.isOpened():
            fourcc = test
            break
        writer.release()
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except OSError:
            pass

    if fourcc is None:
        raise ValueError('Could not open VideoWriter for clip export')

    writer = cv2.VideoWriter(output_path, fourcc, float(fps), (w, h))
    if not writer.isOpened():
        raise ValueError('Could not open VideoWriter for clip export')

    written = 0
    try:
        for raw in jpeg_frames:
            buf = np.frombuffer(raw, dtype=np.uint8)
            frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if frame is None:
                continue
            if frame.shape[0] != h or frame.shape[1] != w:
                frame = cv2.resize(frame, (w, h))
            writer.write(frame)
            written += 1
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


def resolve_clip_output(
    recordings_dir: str,
    timestamp: str,
    camera_num: int,
) -> str:
    """Standard path for an exported annotated clip."""
    name = f'clip_{timestamp}_camera{camera_num}.mp4'
    return os.path.join(recordings_dir, name)
