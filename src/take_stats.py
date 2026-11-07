"""Capture counters copied off the recorder when a take stops."""

from __future__ import annotations


def _count(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def take_stats(recorder, duration: float) -> dict:
    written = _count(getattr(recorder, 'frames_written', 0))
    dropped = _count(getattr(recorder, 'frames_dropped', 0))
    seconds = float(duration) if duration and duration > 0 else 0.0
    achieved = round(written / seconds, 1) if seconds > 0 else 0.0
    return {
        'frames_written': written,
        'frames_dropped': dropped,
        'achieved_fps': achieved,
        'duration': round(seconds, 1),
    }
