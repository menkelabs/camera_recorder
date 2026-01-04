# Project Structure

## Reorganized Code Structure

```
camera_recorder/
├── src/                          # Main source code
│   ├── __init__.py              # Package initialization
│   ├── dual_camera_recorder.py  # Main recorder class
│   └── mediapipe_example.py     # MediaPipe example code
│
├── scripts/                      # Recording and utility scripts
│   ├── record_golf_swing.py     # Golf swing recording (720p @ 120fps)
│   ├── record_for_mediapipe.py  # MediaPipe-optimized recording
│   ├── run_dual_recording.py    # General dual recording script
│   └── debug_recorder.py        # Debug/testing recorder
│
├── tests/                        # Test and diagnostic scripts
│   ├── test_cameras.py          # Camera detection test
│   ├── test_frame_drops.py      # Frame drop verification
│   ├── test_240fps_no_drops.py  # 240fps frame drop test
│   ├── test_golf_swing_settings.py
│   ├── test_mediapipe_resolutions.py
│   ├── test_60fps.py
│   ├── test_videowriter_fps.py
│   ├── verify_dual_recording.py
│   ├── find_hd_usb_cameras.py
│   ├── find_camera_index.py
│   ├── identify_hd_cameras.py
│   └── enumerate_dshow_cameras.py
│
├── docs/                         # Documentation
│   ├── README.md                # Main README
│   ├── QUICK_START.md
│   ├── SETUP_GUIDE.md
│   ├── GOLF_SWING_CAPTURE_GUIDE.md
│   ├── MEDIAPIPE_OPTIMAL_SETTINGS.md
│   ├── CAMERA_SETUP.md
│   ├── CURRENT_SETTINGS.md
│   └── ... (other docs)
│
├── recordings/                   # Video output (gitignored)
├── path_fix_archive/            # Archived PATH fix scripts
│
├── requirements.txt             # Python dependencies
├── setup_env.ps1               # Environment setup script
├── setup_env.bat               # Environment setup (batch)
├── .gitignore                  # Git ignore rules
└── PROJECT_STRUCTURE.md        # This file
```

## Usage

### Running Scripts

**From project root:**
```powershell
# Golf swing recording
python scripts/record_golf_swing.py

# MediaPipe recording
python scripts/record_for_mediapipe.py

# General recording
python scripts/run_dual_recording.py
```

### Running Tests

```powershell
# Test cameras
python tests/test_cameras.py

# Test frame drops
python tests/test_frame_drops.py

# Verify dual recording
python tests/verify_dual_recording.py
```

### Using as a Module

```python
import sys
import os
sys.path.insert(0, 'src')

from dual_camera_recorder import DualCameraRecorder

recorder = DualCameraRecorder(camera1_id=0, camera2_id=2)
recorder.start_cameras(width=1280, height=720, fps=120)
```

## Benefits of This Structure

1. **Clear separation** - Code, scripts, tests, and docs are organized
2. **Easy to find** - Know where to look for specific functionality
3. **Scalable** - Easy to add new features
4. **Professional** - Standard Python project structure
5. **Maintainable** - Easier to maintain and update



