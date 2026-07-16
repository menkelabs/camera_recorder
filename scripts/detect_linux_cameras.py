#!/usr/bin/env python3
"""
Detect Linux cameras and write config_linux.json.

Mirrors scripts/detect_windows_cameras.py so Windows and Linux share the
same config shape and the rest of the codebase can call
camera_utils.get_camera_ids() on either OS.

Usage:
    python scripts/detect_linux_cameras.py
    python scripts/detect_linux_cameras.py --max-index 10
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

import cv2

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))

from camera_utils import (  # noqa: E402
    create_camera_capture,
    fix_console_encoding,
    get_config_path,
    save_camera_config,
)


def _list_video_nodes():
    """Return sorted /dev/video* paths that exist."""
    dev = '/dev'
    if not os.path.isdir(dev):
        return []
    nodes = [
        os.path.join(dev, name)
        for name in sorted(os.listdir(dev))
        if name.startswith('video') and name[5:].isdigit()
    ]
    return nodes


def _probe_camera(camera_id):
    """Open a camera index/path and collect capability metadata."""
    try:
        cap = create_camera_capture(camera_id)
    except ValueError:
        return None

    try:
        ret, frame = cap.read()
        if not ret or frame is None:
            return {
                'id': camera_id if isinstance(camera_id, int) else str(camera_id),
                'status': 'opens_but_no_frames',
                'description': 'Opens successfully but cannot read frames',
                'is_hd_usb': False,
            }

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        try:
            backend = cap.getBackendName()
        except Exception:
            backend = 'unknown'

        # Prefer 720p @ 60 as an HD-USB signal (same heuristic as Windows)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_FPS, 60)
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)

        frame_count = 0
        start = time.time()
        while time.time() - start < 0.5:
            ok, _ = cap.read()
            if ok:
                frame_count += 1
            time.sleep(0.001)
        elapsed = max(time.time() - start, 1e-6)
        measured_fps = frame_count / elapsed

        is_hd_usb = (
            actual_width == 1280
            and actual_height == 720
            and actual_fps >= 50
            and measured_fps >= 30
        )

        device = f'/dev/video{camera_id}' if isinstance(camera_id, int) else str(camera_id)
        return {
            'id': camera_id if isinstance(camera_id, int) else str(camera_id),
            'device': device if os.path.exists(device) else None,
            'status': 'working',
            'description': 'Opens and can read frames',
            'resolution': f'{width}x{height}',
            'fps': fps,
            'backend': backend,
            'is_hd_usb': is_hd_usb,
            'supports_720p_60fps': actual_width == 1280 and actual_height == 720 and actual_fps >= 50,
            'measured_fps': measured_fps,
        }
    finally:
        cap.release()


def detect_cameras(max_index: int = 10) -> list:
    """Probe camera indexes 0..max_index-1 and return working entries."""
    results = []
    print(f"Probing camera indexes 0..{max_index - 1}...")
    for idx in range(max_index):
        info = _probe_camera(idx)
        if info is None:
            print(f"  [{idx}] not available")
            continue
        tag = 'HD USB' if info.get('is_hd_usb') else info.get('status', 'ok')
        print(f"  [{idx}] {tag} — {info.get('resolution', '?')} "
              f"(measured {info.get('measured_fps', 0):.1f} fps)")
        results.append(info)

    nodes = _list_video_nodes()
    if nodes:
        print(f"\n/dev video nodes seen: {', '.join(nodes)}")
    return results


def pick_dual_cameras(detected: list) -> tuple:
    """
    Choose face-on / DTL camera IDs.

    Prefer HD USB cameras; fall back to the first two working indexes.
    """
    hd = [c for c in detected if c.get('is_hd_usb') and isinstance(c.get('id'), int)]
    working = [
        c for c in detected
        if c.get('status') == 'working' and isinstance(c.get('id'), int)
    ]

    if len(hd) >= 2:
        return hd[0]['id'], hd[1]['id']
    if len(working) >= 2:
        return working[0]['id'], working[1]['id']
    if len(working) == 1:
        return working[0]['id'], working[0]['id'] + 1
    return 0, 1


def build_config(detected: list) -> dict:
    cam1, cam2 = pick_dual_cameras(detected)
    return {
        'platform': 'linux',
        'camera1_id': cam1,
        'camera2_id': cam2,
        'recording_settings': {
            'general': {
                'width': 1280,
                'height': 720,
                'fps': 60,
                'notes': 'Auto-generated by detect_linux_cameras.py',
            },
            'golf_swing': {
                'width': 1280,
                'height': 720,
                'fps': 120,
                'notes': 'Auto-generated by detect_linux_cameras.py',
            },
        },
        'detected_cameras': detected,
        'detection_date': datetime.now().strftime('%Y-%m-%d'),
        'notes': (
            f'Camera detection completed. {len(detected)} working camera(s) found, '
            f'{sum(1 for c in detected if c.get("is_hd_usb"))} HD USB camera(s).'
        ),
    }


def main():
    fix_console_encoding()
    parser = argparse.ArgumentParser(description='Detect Linux cameras → config_linux.json')
    parser.add_argument('--max-index', type=int, default=10,
                        help='Highest camera index to probe (exclusive)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print config JSON without writing the file')
    args = parser.parse_args()

    print("=" * 70)
    print("Linux Camera Detection")
    print("=" * 70)

    detected = detect_cameras(max_index=args.max_index)
    config = build_config(detected)
    path = get_config_path(platform='linux')

    print()
    print(f"Selected camera1_id={config['camera1_id']}, camera2_id={config['camera2_id']}")
    print(json.dumps(config, indent=2))

    if args.dry_run:
        print("\nDry run — config not written.")
        return 0

    written = save_camera_config(config, config_path=path)
    print(f"\nWrote {written}")
    print("The Flask GUI and tests will pick this up via camera_utils.get_camera_ids().")
    return 0


if __name__ == '__main__':
    sys.exit(main())
