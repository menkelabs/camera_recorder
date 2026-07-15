"""
Test utilities for cross-platform camera configuration.

Thin wrappers around ``src.camera_utils`` so existing tests that
``from test_utils import get_camera_ids`` keep working on both
Windows and Linux — including loading ``config_linux.json``.
"""

from __future__ import annotations

import os
import sys

# Ensure src/ is importable when tests run this module directly
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_PROJECT_ROOT, 'src')
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from camera_utils import (  # noqa: E402
    create_camera_capture,
    describe_platform_setup,
    fix_console_encoding,
    get_camera_ids as _get_camera_ids,
    get_config_filename,
    get_config_path,
    get_default_camera_ids,
    get_opencv_backend,
    get_platform_info,
    load_camera_config,
    project_root,
    save_camera_config,
)


def load_windows_camera_config(config_path=None):
    """
    Backwards-compatible helper.

    Historically returned None on non-Windows hosts. Prefer
    ``load_camera_config()`` for new code — it works on every platform.
    """
    if sys.platform != 'win32' and config_path is None:
        return None
    if config_path is None:
        config_path = get_config_path(platform='windows')
    return load_camera_config(config_path=config_path)


def load_linux_camera_config(config_path=None):
    """Load Linux camera configuration (``config_linux.json``)."""
    if config_path is None:
        config_path = get_config_path(platform='linux')
    return load_camera_config(config_path=config_path)


def get_camera_ids(config_path=None, platform=None):
    """
    Camera IDs for tests on the current (or forced) platform.

    Uses ``config_windows.json`` / ``config_linux.json`` when present,
    otherwise platform defaults.
    """
    return _get_camera_ids(config_path=config_path, platform=platform)


def print_platform_banner(title: str = "CAMERA RECORDER TESTS"):
    """Print a short cross-platform setup summary (for standalone scripts)."""
    fix_console_encoding()
    setup = describe_platform_setup()
    print("=" * 70)
    print(title)
    print("=" * 70)
    os_name = (
        'Windows' if setup['is_windows']
        else 'Linux' if setup['is_linux']
        else setup['platform']
    )
    print(f"Platform:     {os_name} ({setup['platform']})")
    print(f"Config file:  {os.path.basename(setup['config_path'])} "
          f"({'found' if setup['config_found'] else 'missing — using defaults'})")
    print(f"Camera IDs:   {setup['camera1_id']}, {setup['camera2_id']}")
    print(f"OpenCV backend: {setup['opencv_backend']}")
    print("=" * 70)


__all__ = [
    'create_camera_capture',
    'describe_platform_setup',
    'fix_console_encoding',
    'get_camera_ids',
    'get_config_filename',
    'get_config_path',
    'get_default_camera_ids',
    'get_opencv_backend',
    'get_platform_info',
    'load_camera_config',
    'load_linux_camera_config',
    'load_windows_camera_config',
    'print_platform_banner',
    'project_root',
    'save_camera_config',
]
