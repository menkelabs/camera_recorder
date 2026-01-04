# Quick Reference Guide

## 🚀 Quick Start

### Golf Swing Recording (Recommended: 720p @ 120fps)
```powershell
python scripts/record_golf_swing.py
```

### MediaPipe Recording (1080p @ 60fps)
```powershell
python scripts/record_for_mediapipe.py
```

### General Recording
```powershell
python scripts/run_dual_recording.py
```

### Camera Test GUI (Focus, Brightness, Saturation, etc.)
```powershell
python scripts/camera_test_gui.py
```
**Controls:**
- Adjust trackbars for brightness, saturation, exposure, focus, etc.
- Press `s` to save settings, `r` to reset, `q` to quit
- Perfect for adjusting cameras based on sun/lighting conditions

## 📁 Project Structure

- **`src/`** - Main source code
  - `dual_camera_recorder.py` - Core recorder class
  - `mediapipe_example.py` - MediaPipe example

- **`scripts/`** - Ready-to-use recording scripts
  - `record_golf_swing.py` - Golf swing recording
  - `record_for_mediapipe.py` - MediaPipe-optimized
  - `run_dual_recording.py` - General recording
  - `camera_test_gui.py` - **Camera test GUI** (focus, brightness, saturation, etc.)
  - `debug_recorder.py` - Debug/testing

- **`tests/`** - Test and diagnostic tools
  - `test_cameras.py` - Find available cameras
  - `test_frame_drops.py` - Verify no frame drops
  - `verify_dual_recording.py` - Test dual recording

- **`docs/`** - Documentation
  - `GOLF_SWING_CAPTURE_GUIDE.md` - Golf swing guide
  - `MEDIAPIPE_OPTIMAL_SETTINGS.md` - MediaPipe settings
  - `CAMERA_SETUP.md` - Camera configuration
  - `CAMERA_TEST_GUI.md` - Camera test GUI guide

## 🎥 Camera Configuration

- **Camera 1**: Index 0 (HD USB Camera)
- **Camera 2**: Index 2 (HD USB Camera)
- **Note**: Index 1 is built-in (not used)

## ⚙️ Recommended Settings

### Golf Swings
- **720p @ 120fps** - Best balance
- Code: `recorder.start_cameras(width=1280, height=720, fps=120)`

### MediaPipe Analysis
- **1080p @ 60fps** - Maximum detail
- Code: `recorder.start_cameras(width=1920, height=1080, fps=60)`

## 🧪 Testing

```powershell
# Find your cameras
python tests/test_cameras.py

# Test frame drops
python tests/test_frame_drops.py

# Verify dual recording
python tests/verify_dual_recording.py
```

## 📝 Using as a Module

```python
import sys
sys.path.insert(0, 'src')
from dual_camera_recorder import DualCameraRecorder

recorder = DualCameraRecorder(camera1_id=0, camera2_id=2)
recorder.start_cameras(width=1280, height=720, fps=120)
recorder.start_recording("my_recording")
# ... record ...
recorder.stop_recording()
recorder.stop_cameras()
```

