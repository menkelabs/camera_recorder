"""Choose which video frames MediaPipe should see.

Capture stays at the camera rate. Analysis samples near 30 fps so a
120 fps take does not run the pose model on every frame.
"""

from __future__ import annotations


def sample_plan(source_fps: float, sample_fps: float = 30.0) -> tuple:
    """Return ``(source_fps, stride, sample_fps)``.

    A missing or unusable source rate is treated as the sample rate, which
    keeps a 1:1 stride.
    """
    sample = _positive(sample_fps, 30.0)
    source = _positive(source_fps, sample)
    stride = max(1, int(round(source / sample)))
    return source, stride, sample


def keep_frame(index: int, stride: int) -> bool:
    """True when this source frame should be analyzed."""
    step = stride if isinstance(stride, int) and stride > 0 else 1
    return index % step == 0


def _positive(value, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if number < 1:
        return fallback
    return number
