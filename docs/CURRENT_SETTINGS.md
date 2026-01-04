# Current Recording Settings

## 🎯 Recommended Settings for Golf Swings

### **720p @ 120 FPS** ⭐ RECOMMENDED

```python
recorder.start_cameras(width=1280, height=720, fps=120)
```

**Why this is best:**
- ✅ **120fps** - Captures 1 frame every 8.33ms
- ✅ **~10-20 frames during impact zone** - Perfect for golf swing analysis
- ✅ **Good resolution** - 720p is excellent for MediaPipe pose analysis
- ✅ **VideoWriter compatible** - Can write at full 120fps (no limitations)
- ✅ **Best balance** - Speed + detail

## Current Program Setup

### `record_golf_swing.py` - Golf Swing Recorder
- **Default**: 720p @ 120fps (Option 1)
- **Alternative**: 640p @ 120fps (Option 2)
- **Alternative**: 1080p @ 60fps (Option 3)

**Usage:**
```powershell
python record_golf_swing.py
```
Then select option 1 (default) for 720p @ 120fps.

### `dual_camera_recorder.py` - Main Recorder Class
- **Default**: 1080p @ 60fps (for general use)
- **Can be customized**: Pass width, height, fps parameters

**Usage:**
```python
from dual_camera_recorder import DualCameraRecorder

recorder = DualCameraRecorder(camera1_id=0, camera2_id=2)
recorder.start_cameras(width=1280, height=720, fps=120)  # For golf
```

### `run_dual_recording.py` - General Recording Script
- **Current**: 1080p @ 60fps (for MediaPipe analysis)
- **Can be modified** for golf swings

## Quick Reference

| Use Case | Resolution | FPS | Script |
|----------|------------|-----|--------|
| **Golf Swings** | 720p | 120 | `record_golf_swing.py` (Option 1) |
| MediaPipe Analysis | 1080p | 60 | `record_for_mediapipe.py` |
| Maximum Speed | 640p | 120 | `record_golf_swing.py` (Option 2) |
| Maximum Detail | 1080p | 60 | `record_golf_swing.py` (Option 3) |

## Camera Configuration

- **Camera 1**: Index 0 (HD USB Camera)
- **Camera 2**: Index 2 (HD USB Camera)
- **Note**: Index 1 is built-in system camera (not used)

## Verification

To verify your cameras support these settings:
```powershell
python test_golf_swing_settings.py
```

To test frame drops:
```powershell
python test_240fps_no_drops.py
```

## Summary

**For golf swings, use: 720p @ 120fps**

This is:
- ✅ Set as default in `record_golf_swing.py`
- ✅ Fully supported by VideoWriter
- ✅ Optimal for golf swing analysis
- ✅ Good for MediaPipe pose tracking
- ✅ Zero frame drops confirmed

