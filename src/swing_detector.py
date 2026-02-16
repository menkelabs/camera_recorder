"""
Automatic swing detection module.

Monitors a live camera feed for shoulder rotation changes and fires
start/stop events when a golf swing is detected.  Uses a lightweight
MediaPipe pose model (complexity=0) so it can run in real-time alongside
the preview capture loop.

State machine:
    IDLE -> MOTION_DETECTED -> RECORDING -> COOLDOWN -> IDLE
"""

import time
import numpy as np
from collections import deque
from typing import Optional

from pose_processor import PoseProcessor


class SwingDetector:
    """Detects golf swings from a live camera feed using shoulder-turn velocity."""

    # States
    IDLE = 'idle'
    MOTION_DETECTED = 'motion_detected'
    RECORDING = 'recording'
    COOLDOWN = 'cooldown'

    def __init__(
        self,
        motion_threshold: float = 15.0,
        confirmation_frames: int = 5,
        cooldown_seconds: float = 2.0,
        window_size: int = 10,
        model_complexity: int = 0,
    ):
        """
        Args:
            motion_threshold: Shoulder-turn delta (degrees) from baseline
                              that triggers motion detection.
            confirmation_frames: Number of consecutive frames above
                                 threshold needed before recording starts.
            cooldown_seconds: Seconds of sub-threshold readings before
                              recording stops.
            window_size: Number of recent shoulder-turn values to keep.
            model_complexity: MediaPipe model complexity (0=lite for speed).
        """
        self.motion_threshold = motion_threshold
        self.confirmation_frames = confirmation_frames
        self.cooldown_seconds = cooldown_seconds
        self.window_size = window_size
        self.model_complexity = model_complexity

        # State
        self.state = self.IDLE
        self._confirm_count = 0
        self._cooldown_start: Optional[float] = None

        # Shoulder-turn tracking
        self._baseline: Optional[float] = None
        self._history: deque = deque(maxlen=window_size)
        self._current_turn: Optional[float] = None

        # Pose processor (lazy-init on first frame)
        self._processor: Optional[PoseProcessor] = None
        self._model_complexity = model_complexity

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_frame(self, frame) -> Optional[str]:
        """
        Analyse a single BGR frame.

        Returns:
            None   -- no event
            "start" -- swing detected, start recording
            "stop"  -- swing ended, stop recording
        """
        turn = self._get_shoulder_turn(frame)
        if turn is None:
            return None

        self._current_turn = turn
        self._history.append(turn)

        # Establish baseline from first few stable readings
        if self._baseline is None:
            if len(self._history) >= 3:
                self._baseline = float(np.median(list(self._history)))
            return None

        delta = abs(turn - self._baseline)

        # ---- State machine ----
        if self.state == self.IDLE:
            if delta > self.motion_threshold:
                self._confirm_count += 1
                if self._confirm_count >= self.confirmation_frames:
                    self.state = self.RECORDING
                    self._confirm_count = 0
                    return 'start'
                else:
                    self.state = self.MOTION_DETECTED
            else:
                self._confirm_count = 0
            return None

        elif self.state == self.MOTION_DETECTED:
            if delta > self.motion_threshold:
                self._confirm_count += 1
                if self._confirm_count >= self.confirmation_frames:
                    self.state = self.RECORDING
                    self._confirm_count = 0
                    return 'start'
            else:
                # False alarm — motion dropped before confirmation
                self.state = self.IDLE
                self._confirm_count = 0
            return None

        elif self.state == self.RECORDING:
            if delta <= self.motion_threshold:
                # Motion ended — start cooldown
                self.state = self.COOLDOWN
                self._cooldown_start = time.time()
            return None

        elif self.state == self.COOLDOWN:
            if delta > self.motion_threshold:
                # Motion resumed during cooldown — back to recording
                self.state = self.RECORDING
                self._cooldown_start = None
                return None
            elapsed = time.time() - self._cooldown_start
            if elapsed >= self.cooldown_seconds:
                self.state = self.IDLE
                self._cooldown_start = None
                # Re-baseline after the swing settles
                self._baseline = float(np.median(list(self._history)))
                return 'stop'
            return None

        return None

    def reset(self):
        """Reset the detector to its initial state."""
        self.state = self.IDLE
        self._confirm_count = 0
        self._cooldown_start = None
        self._baseline = None
        self._history.clear()
        self._current_turn = None

    def release(self):
        """Release the MediaPipe resources."""
        if self._processor is not None:
            self._processor.release()
            self._processor = None

    def get_status(self) -> dict:
        """Return a JSON-serialisable status dict for the API."""
        return {
            'state': self.state,
            'baseline': round(self._baseline, 1) if self._baseline is not None else None,
            'current_turn': round(self._current_turn, 1) if self._current_turn is not None else None,
            'delta': round(abs(self._current_turn - self._baseline), 1)
                     if self._current_turn is not None and self._baseline is not None
                     else None,
            'motion_threshold': self.motion_threshold,
            'confirmation_frames': self.confirmation_frames,
            'cooldown_seconds': self.cooldown_seconds,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_shoulder_turn(self, frame) -> Optional[float]:
        """Run lightweight pose detection and compute shoulder turn angle."""
        if self._processor is None:
            self._processor = PoseProcessor(model_complexity=self._model_complexity)

        results, _ = self._processor.process_frame(frame)

        if results.pose_landmarks is None:
            return None

        landmarks = self._processor._extract_landmarks(results.pose_landmarks)
        if landmarks is None:
            return None

        ls = landmarks.get('left_shoulder')
        rs = landmarks.get('right_shoulder')
        if ls is None or rs is None:
            return None

        shoulder_width = abs(rs['x'] - ls['x'])
        if shoulder_width < 1e-9:
            return None
        z_diff = rs['z'] - ls['z']
        return float(np.degrees(np.arctan2(z_diff, shoulder_width)))
