# Platform Configuration Guide

## Overview

The camera_recorder project supports both **Linux (development/testing)** and **Windows (production)** with platform-appropriate defaults.

## Platform Differences

### Camera Backend

- **Windows**: Uses DirectShow backend (`CAP_DSHOW`) for better compatibility with USB cameras
- **Linux**: Uses default backend (V4L2) - automatically selected by OpenCV

### Default Camera IDs

- **Windows Production**: 
  - Camera 1: Index 0 (HD USB Camera)
  - Camera 2: Index 2 (HD USB Camera)
  - Note: Index 1 is typically the built-in camera (skipped)
  
- **Linux Development**: 
  - Camera 1: Index 0 (USB Camera)
  - Camera 2: Index 1 (USB Camera)
  - Note: Both USB cameras are typically sequential on Linux

## Usage

### Automatic Platform Detection

The code automatically detects the platform and uses appropriate defaults:

```python
from dual_camera_recorder import DualCameraRecorder

# Uses platform-appropriate defaults automatically
recorder = DualCameraRecorder()  
# Windows: cameras 0, 2
# Linux: cameras 0, 1
```

### Explicit Camera IDs

You can always override the defaults:

```python
# Force specific camera IDs
recorder = DualCameraRecorder(camera1_id=0, camera2_id=1)
```

### GUI Script

The GUI script also uses platform-appropriate defaults:

```bash
# Uses defaults for your platform
python scripts/camera_setup_recorder_gui.py

# Override with specific cameras
python scripts/camera_setup_recorder_gui.py --camera1 0 --camera2 1
```

## Finding Your Cameras

### Windows

Use the camera enumeration tools:
```powershell
python tests/find_hd_usb_cameras.py
python tests/enumerate_dshow_cameras.py
```

### Linux

List available video devices:
```bash
ls /dev/video*
v4l2-ctl --list-devices
```

Test cameras:
```bash
python tests/test_cameras.py
```

## Development Workflow

1. **Develop on Linux**: Test with USB cameras connected
2. **Deploy on Windows**: Use the same code - platform detection handles differences
3. **Configuration**: No config files needed - defaults work for both platforms

## Code Implementation

The platform detection is implemented in:

- `src/dual_camera_recorder.py`: `DualCameraRecorder.__init__()`
- `scripts/camera_setup_recorder_gui.py`: `TabbedCameraGUI.__init__()`
- Both use `sys.platform == 'win32'` to detect Windows

Platform-specific logic:
```python
if sys.platform == 'win32':
    # Windows: Use DirectShow backend, cameras 0, 2
    cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
    default_cameras = (0, 2)
else:
    # Linux/Other: Use default backend, cameras 0, 1
    cap = cv2.VideoCapture(camera_id)
    default_cameras = (0, 1)
```

