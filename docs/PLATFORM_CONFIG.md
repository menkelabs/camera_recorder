# Platform Configuration Guide

## Overview

The camera_recorder project supports **Windows** and **Linux** from one codebase.
Camera indexes and OpenCV backends differ by OS; a shared API in
`src/camera_utils.py` hides that so apps and tests call the same functions
everywhere.

## Quick start (either OS)

```bash
# 1. Detect cameras and write the platform config file
# Windows:
python scripts/detect_windows_cameras.py
# Linux:
python scripts/detect_linux_cameras.py

# 2. Run the GUI (reads config_windows.json or config_linux.json automatically)
python scripts/flask_gui.py

# 3. Run unit tests (no cameras needed — same command on both OSes)
python run_all_tests.py --unit

# 4. Run hardware/camera scripts when cameras are plugged in
python run_all_tests.py --hardware
```

## Platform differences

| Concern | Windows | Linux |
|---------|---------|-------|
| Config file | `config_windows.json` | `config_linux.json` |
| OpenCV backend | `cv2.CAP_DSHOW` | default (V4L2) |
| Typical dual-cam IDs | `0, 2` (skip built-in) | `0, 1` |
| Detection script | `scripts/detect_windows_cameras.py` | `scripts/detect_linux_cameras.py` |
| Console Unicode | `fix_console_encoding()` | no-op |

## Shared API (`src/camera_utils.py`)

Use these helpers instead of branching on `sys.platform` in new code:

```python
from camera_utils import (
    get_camera_ids,          # (cam1, cam2) from config or defaults
    load_camera_config,      # dict from config_*.json (any platform)
    create_camera_capture,   # VideoCapture with correct backend
    get_opencv_backend,      # CAP_DSHOW or None
    fix_console_encoding,    # UTF-8 stdout on Windows
    describe_platform_setup, # banner-friendly snapshot
)
```

### Config shape (same on both platforms)

```json
{
  "platform": "linux",
  "camera1_id": 0,
  "camera2_id": 1,
  "recording_settings": { "general": {...}, "golf_swing": {...} },
  "detected_cameras": [ ... ],
  "detection_date": "2026-07-15",
  "notes": "..."
}
```

## Testing from one codebase

### Unit tests (CI / cloud / laptop without cameras)

```bash
python run_all_tests.py --unit
# or a single module:
python -m unittest tests.test_platform_config -v
```

`tests/test_platform_config.py` mocks `sys.platform` so Windows and Linux
config paths, defaults, and backends are verified on whichever host you use.

### Hardware tests

```bash
python run_all_tests.py --hardware
```

Standalone scripts under `tests/` now:

1. Call `fix_console_encoding()` (safe on Linux).
2. Open cameras with `create_camera_capture()` (no hardcoded `CAP_DSHOW`).
3. Resolve indexes with `get_camera_ids()` (reads the local config file).

### Test helpers

```python
# tests/test_utils.py — re-exports camera_utils for existing imports
from test_utils import get_camera_ids, create_camera_capture, print_platform_banner
```

`from test_utils import get_camera_ids` keeps working; it no longer
Windows-only-loads config.

## Flask GUI / recorder

`CameraManager` and `DualCameraRecorder` both call `get_camera_ids()` and
`create_camera_capture()`, so the same binary behaves correctly after you
generate the platform config once.

Override anytime:

```bash
python scripts/flask_gui.py --camera1 0 --camera2 2
```

## Troubleshooting

### Windows: cameras not detected

1. `python scripts/detect_windows_cameras.py`
2. Device Manager → cameras present
3. Close apps that lock the camera (Zoom, OBS, Camera app)

### Linux: cameras not found

1. `ls -la /dev/video*`
2. `groups` should include `video` (`sudo usermod -aG video $USER`)
3. `python scripts/detect_linux_cameras.py`
4. Re-check `config_linux.json` camera IDs

### Index changed after unplug/replug

Re-run the platform detection script; unit tests stay green because they
do not depend on live indexes.

## Why this matters

Previously Linux tests skipped Windows config, and several hardware scripts
hardcoded `CAP_DSHOW` (broken on Linux). The shared helpers + dual config
files + `--unit` / `--hardware` split let you develop on Linux, ship on
Windows, and run the same commands on both.
