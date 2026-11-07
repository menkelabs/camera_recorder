"""
USB topology helpers for dual-camera bandwidth warnings (Linux-focused).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


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


def _require_camera_index(value: Any, label: str) -> int:
    """Device indexes are non-negative ints. Booleans are not indexes."""
    if type(value) is not int or value < 0:
        raise ValueError(f'{label} must be a non-negative integer')
    return value


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
    camera1_id = _require_camera_index(camera1_id, 'camera1_id')
    camera2_id = _require_camera_index(camera2_id, 'camera2_id')
    if not result['platform_supported']:
        result['warning'] = None  # Windows: rely on frame-delivery heuristic instead
        return result

    usb1 = _v4l_usb_path(camera1_id)
    usb2 = _v4l_usb_path(camera2_id)
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


_WINDOWS_CACHE: Dict[str, Any] = {'at': 0.0, 'devices': []}
_WINDOWS_CACHE_SECONDS = 30.0

_WINDOWS_CONTROLLER_PS = r'''
$ErrorActionPreference = "SilentlyContinue"
$cams = @(Get-CimInstance Win32_PnPEntity | Where-Object {
  $_.PNPClass -eq "Camera" -or $_.Service -eq "usbvideo"
})
foreach ($cam in $cams) {
  $ctrl = ""
  $cur = $cam.PNPDeviceID
  for ($i = 0; $i -lt 8; $i++) {
    if (-not $cur) { break }
    $prop = Get-PnpDeviceProperty -InstanceId $cur -KeyName "DEVPKEY_Device_Parent" -ErrorAction SilentlyContinue
    $parent = $prop.Data
    if (-not $parent) { break }
    if ($parent -like "PCI\*" -or $parent -like "USB\ROOT_HUB*") { $ctrl = [string]$parent; break }
    $cur = [string]$parent
  }
  if ($cam.Name) { Write-Output ($cam.Name + "`t" + $ctrl) }
}
'''


def query_windows_camera_controllers() -> List[Dict[str, Optional[str]]]:
    """Best-effort camera name → USB controller map. Empty off Windows."""
    if sys.platform != 'win32':
        return []
    now = time.time()
    cached_at = float(_WINDOWS_CACHE.get('at') or 0)
    if now - cached_at < _WINDOWS_CACHE_SECONDS:
        return list(_WINDOWS_CACHE.get('devices') or [])
    devices = _run_windows_controller_query()
    _WINDOWS_CACHE['at'] = now
    _WINDOWS_CACHE['devices'] = devices
    return list(devices)


def _run_windows_controller_query() -> List[Dict[str, Optional[str]]]:
    try:
        completed = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command', _WINDOWS_CONTROLLER_PS],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    devices = []
    for line in (completed.stdout or '').splitlines():
        name, _, controller = line.partition('\t')
        name = name.strip()
        if not name:
            continue
        controller = controller.strip() or None
        devices.append({'name': name, 'controller': controller})
    return devices


def detect_windows_usb_controllers(devices: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Warn when Windows cameras share one USB controller.

    ``devices`` is optional so tests can pass a topology without WMI.
    Each item is ``{'name': str, 'controller': str|None}``.
    """
    supplied = devices is not None
    if not supplied and sys.platform != 'win32':
        return {
            'checked': False,
            'shared_controller': None,
            'controllers': [],
            'warning': None,
            'platform_supported': False,
        }
    if not supplied:
        devices = query_windows_camera_controllers()
    controllers = []
    for device in devices or []:
        controller = (device or {}).get('controller')
        if controller:
            controllers.append(str(controller))
    result = {
        'checked': True,
        'shared_controller': None,
        'controllers': controllers,
        'warning': None,
        'platform_supported': True,
    }
    if len(controllers) >= 2 and len(set(controllers)) == 1:
        result['shared_controller'] = True
        result['warning'] = (
            f'Both cameras appear on USB controller {controllers[0]}. '
            'High-FPS dual capture often fails on one controller — '
            'plug one camera into a different USB controller.'
        )
    elif len(controllers) >= 2:
        result['shared_controller'] = False
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
