"""
USB topology helpers for dual-camera bandwidth warnings (Linux-focused).
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read().strip()
    except OSError:
        return None


def _v4l_usb_path(index: int) -> Optional[str]:
    """
    Resolve /dev/videoN → USB sysfs path fragment when available.
    Example: '1-2.1:1.0' or similar.
    """
    # Prefer sysfs via /sys/class/video4linux/videoN/device
    v4l = f'/sys/class/video4linux/video{index}'
    if not os.path.isdir(v4l):
        return None
    device_link = os.path.join(v4l, 'device')
    try:
        real = os.path.realpath(device_link)
    except OSError:
        return None
    # Walk up looking for an idVendor sibling (USB interface/device)
    cur = real
    for _ in range(8):
        if os.path.exists(os.path.join(cur, 'idVendor')):
            return os.path.basename(cur)
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.basename(real) if real else None


def _usb_bus_root(usb_name: str) -> str:
    """
    Collapse a USB device name to its root port for same-bus detection.
    '1-2.3.4' → '1-2' ; '3-1' → '3-1'
    """
    # Strip interface suffix like ':1.0'
    base = usb_name.split(':')[0]
    m = re.match(r'^(\d+-\d+)', base)
    if m:
        return m.group(1)
    return base


def detect_shared_usb_bus(camera1_id: int, camera2_id: int) -> Dict[str, Any]:
    """
    Best-effort check whether both cameras sit on the same USB root port.

    Returns:
        {
          'checked': bool,
          'shared_bus': bool|None,
          'camera1_usb': str|None,
          'camera2_usb': str|None,
          'warning': str|None,
          'platform_supported': bool,
        }
    """
    result = {
        'checked': False,
        'shared_bus': None,
        'camera1_usb': None,
        'camera2_usb': None,
        'warning': None,
        'platform_supported': os.path.isdir('/sys/class/video4linux'),
    }
    if not result['platform_supported']:
        result['warning'] = None  # Windows: rely on frame-delivery heuristic instead
        return result

    usb1 = _v4l_usb_path(int(camera1_id))
    usb2 = _v4l_usb_path(int(camera2_id))
    result['camera1_usb'] = usb1
    result['camera2_usb'] = usb2
    result['checked'] = True

    if not usb1 or not usb2:
        result['warning'] = (
            'Could not map both cameras to USB ports — if Camera 2 drops frames, '
            'move one camera to another USB controller.'
        )
        return result

    root1 = _usb_bus_root(usb1)
    root2 = _usb_bus_root(usb2)
    if root1 == root2:
        result['shared_bus'] = True
        result['warning'] = (
            f'Both cameras appear on USB port {root1}. High-FPS dual capture often fails '
            'on one bus — plug one camera into a different USB controller/hub.'
        )
    else:
        result['shared_bus'] = False
    return result


def frame_starvation_warning(cam1_has_frames: bool, cam2_has_frames: bool) -> Optional[str]:
    """Heuristic warning when one camera is silent (classic bandwidth symptom)."""
    if cam1_has_frames and not cam2_has_frames:
        return (
            'Camera 2 is open but not delivering frames — often a USB bandwidth conflict. '
            'Move one camera to another USB port/controller.'
        )
    if cam2_has_frames and not cam1_has_frames:
        return (
            'Camera 1 is open but not delivering frames — check cable/USB bandwidth.'
        )
    return None
