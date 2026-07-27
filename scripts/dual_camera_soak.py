#!/usr/bin/env python3
"""
Dual-camera soak runner.

Mock (default, CI-safe):
    python scripts/dual_camera_soak.py
    python scripts/dual_camera_soak.py --mock --seconds 2

Hardware (real USB cameras — operator soak):
    python scripts/dual_camera_soak.py --hardware --seconds 30
    python scripts/dual_camera_soak.py --hardware --camera1 0 --camera2 2
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'scripts'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'tests'))


def run_mock() -> int:
    """Run the automated mock soak unittest module."""
    return subprocess.call(
        [sys.executable, '-m', 'unittest', 'tests.test_dual_camera_soak', '-v'],
        cwd=_PROJECT_ROOT,
    )


def run_hardware(camera1: int, camera2: int, seconds: float, width: int, height: int, fps: int) -> int:
    """Open both cameras and verify sustained frame delivery."""
    import cv2
    from camera_utils import create_camera_capture

    print(f'Opening cameras {camera1} + {camera2} for {seconds:.1f}s soak…')
    cap1 = create_camera_capture(camera1)
    cap2 = create_camera_capture(camera2)
    if not cap1 or not cap1.isOpened():
        print(f'FAIL: camera1 index {camera1} did not open', file=sys.stderr)
        return 1
    if not cap2 or not cap2.isOpened():
        print(f'FAIL: camera2 index {camera2} did not open', file=sys.stderr)
        return 1

    for cap in (cap1, cap2):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    counts = [0, 0]
    fails = [0, 0]
    t0 = time.time()
    while time.time() - t0 < seconds:
        for i, cap in enumerate((cap1, cap2)):
            ok, frame = cap.read()
            if ok and frame is not None:
                counts[i] += 1
            else:
                fails[i] += 1
        time.sleep(0.005)

    for cap in (cap1, cap2):
        cap.release()

    elapsed = max(time.time() - t0, 1e-6)
    print(
        f'Cam1 frames={counts[0]} ({counts[0] / elapsed:.1f} fps) fails={fails[0]}\n'
        f'Cam2 frames={counts[1]} ({counts[1] / elapsed:.1f} fps) fails={fails[1]}'
    )
    # Require some sustained delivery on both streams
    min_frames = max(10, int(seconds * 5))
    if counts[0] < min_frames or counts[1] < min_frames:
        print('FAIL: insufficient frames from one or both cameras', file=sys.stderr)
        return 1
    if fails[0] > counts[0] or fails[1] > counts[1]:
        print('FAIL: failure rate too high', file=sys.stderr)
        return 1
    print('PASS: dual-camera hardware soak')
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='Dual-camera soak (mock or hardware)')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--mock', action='store_true', default=True, help='CI-safe mock soak (default)')
    mode.add_argument('--hardware', action='store_true', help='Real USB cameras')
    p.add_argument('--seconds', type=float, default=10.0, help='Hardware soak duration')
    p.add_argument('--camera1', type=int, default=0)
    p.add_argument('--camera2', type=int, default=1)
    p.add_argument('--width', type=int, default=1280)
    p.add_argument('--height', type=int, default=720)
    p.add_argument('--fps', type=int, default=120)
    args = p.parse_args(argv)

    if args.hardware:
        return run_hardware(
            args.camera1, args.camera2, args.seconds, args.width, args.height, args.fps,
        )
    return run_mock()


if __name__ == '__main__':
    raise SystemExit(main())
