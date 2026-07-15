"""
Camera utility functions for platform-agnostic camera handling.

Supports Linux (development/testing) and Windows (production) from one
codebase: config loading, default camera IDs, OpenCV backends, and
console encoding for shared test scripts.
"""

from __future__ import annotations

import cv2
import json
import os
import sys
from typing import Any, Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Platform introspection
# ---------------------------------------------------------------------------

def get_platform_info() -> Dict[str, Any]:
    """Return a dict describing the current OS."""
    return {
        'platform': sys.platform,
        'is_windows': sys.platform == 'win32',
        'is_linux': sys.platform.startswith('linux'),
        'is_mac': sys.platform == 'darwin',
    }


def is_windows() -> bool:
    return sys.platform == 'win32'


def is_linux() -> bool:
    return sys.platform.startswith('linux')


# ---------------------------------------------------------------------------
# Console helpers (shared by tests/scripts that print Unicode)
# ---------------------------------------------------------------------------

_CONSOLE_FIXED = False


def fix_console_encoding() -> None:
    """
    Make stdout UTF-8 on Windows so status glyphs (✓ / ✗) do not crash.

    Safe to call multiple times; no-op on Linux/macOS and when stdout is
    not a real TTY buffer (e.g. under unittest capture).
    """
    global _CONSOLE_FIXED
    if _CONSOLE_FIXED or not is_windows():
        return
    try:
        import io
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer, encoding='utf-8', errors='replace'
            )
        _CONSOLE_FIXED = True
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Config paths & loading (Windows + Linux from the same API)
# ---------------------------------------------------------------------------

def project_root() -> str:
    """Absolute path to the repository root (parent of src/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_config_filename(platform: Optional[str] = None) -> str:
    """
    Return the platform-specific config filename.

    Args:
        platform: Override platform key ('windows', 'linux', 'darwin')
                  or a sys.platform value. Defaults to the host OS.
    """
    if platform is None:
        platform = sys.platform

    platform = platform.lower()
    if platform in ('win32', 'windows'):
        return 'config_windows.json'
    if platform.startswith('linux') or platform == 'linux':
        return 'config_linux.json'
    if platform in ('darwin', 'mac', 'macos'):
        return 'config_macos.json'
    # Fallback: treat unknown as linux-style
    return 'config_linux.json'


def get_config_path(platform: Optional[str] = None, root: Optional[str] = None) -> str:
    """Absolute path to the platform config file (may not exist yet)."""
    root = root or project_root()
    return os.path.join(root, get_config_filename(platform))


def load_camera_config(
    config_path: Optional[str] = None,
    platform: Optional[str] = None,
    root: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Load the platform-appropriate camera config JSON.

    Unlike the old Windows-only helper, this works on Linux too when
    ``config_linux.json`` is present.

    Args:
        config_path: Explicit path (skips platform selection).
        platform: Force a platform ('windows'/'linux'/sys.platform).
        root: Project root override (useful in tests).

    Returns:
        Parsed config dict, or None if the file is missing/invalid.
    """
    if config_path is None:
        config_path = get_config_path(platform=platform, root=root)

    if not os.path.exists(config_path):
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: Could not load config from {config_path}: {exc}")
        return None


def save_camera_config(
    config: Dict[str, Any],
    config_path: Optional[str] = None,
    platform: Optional[str] = None,
    root: Optional[str] = None,
) -> str:
    """
    Write a camera config JSON for the current (or forced) platform.

    Returns the path written.
    """
    if config_path is None:
        config_path = get_config_path(platform=platform, root=root)
    os.makedirs(os.path.dirname(config_path) or '.', exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)
        f.write('\n')
    return config_path


def get_default_camera_ids(platform: Optional[str] = None) -> Tuple[int, int]:
    """
    Hardcoded fallback camera indexes when no config file exists.

    Windows production: (0, 2) — skips a common built-in at 1.
    Linux / other: (0, 1).
    """
    if platform is None:
        plat = sys.platform
    else:
        plat = platform.lower()

    if plat in ('win32', 'windows'):
        return (0, 2)
    return (0, 1)


def get_camera_ids(
    config_path: Optional[str] = None,
    platform: Optional[str] = None,
    root: Optional[str] = None,
) -> Tuple[int, int]:
    """
    Resolve camera1/camera2 IDs for the current platform.

    Order of preference:
      1. Values from the platform config file
      2. Platform defaults from get_default_camera_ids()
    """
    config = load_camera_config(
        config_path=config_path, platform=platform, root=root
    )
    defaults = get_default_camera_ids(platform=platform)
    if not config:
        return defaults
    return (
        int(config.get('camera1_id', defaults[0])),
        int(config.get('camera2_id', defaults[1])),
    )


# ---------------------------------------------------------------------------
# OpenCV capture helpers
# ---------------------------------------------------------------------------

def get_opencv_backend(platform: Optional[str] = None):
    """
    Return the preferred OpenCV capture backend constant, or None for default.

    Windows → cv2.CAP_DSHOW
    Linux/macOS → None (V4L2 / AVFoundation via OpenCV default)
    """
    if platform is None:
        plat = sys.platform
    else:
        plat = platform.lower()

    if plat in ('win32', 'windows'):
        return cv2.CAP_DSHOW
    return None


def create_camera_capture(camera_id, backend=None):
    """
    Create a VideoCapture with the platform-appropriate backend.

    Args:
        camera_id: Camera index (int) or device path (str)
        backend: Optional backend override (for tests). Pass None to
                 auto-select; pass an explicit cv2.CAP_* constant to force.

    Returns:
        cv2.VideoCapture object

    Raises:
        ValueError: If the camera cannot be opened
    """
    if backend is None:
        backend = get_opencv_backend()

    if backend is not None and isinstance(camera_id, int):
        cap = cv2.VideoCapture(camera_id, backend)
    else:
        cap = cv2.VideoCapture(camera_id)

    if not cap.isOpened():
        raise ValueError(f"Failed to open camera {camera_id}")

    return cap


def describe_platform_setup(
    config_path: Optional[str] = None,
    platform: Optional[str] = None,
    root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Snapshot of how this host will resolve cameras — handy for test banners.
    """
    info = get_platform_info()
    cfg_path = config_path or get_config_path(platform=platform, root=root)
    config = load_camera_config(config_path=cfg_path, platform=platform, root=root)
    cam1, cam2 = get_camera_ids(config_path=cfg_path, platform=platform, root=root)
    backend = get_opencv_backend(platform=platform)
    return {
        **info,
        'config_path': cfg_path,
        'config_found': config is not None,
        'camera1_id': cam1,
        'camera2_id': cam2,
        'opencv_backend': 'CAP_DSHOW' if backend == cv2.CAP_DSHOW else 'default',
    }
