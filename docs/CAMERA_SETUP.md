# Camera Setup Guide

## Important: Camera IDs

Your system has 3 cameras:
- **Camera 0**: HD USB Camera ✅ (Use this)
- **Camera 1**: Built-in System Camera ❌ (Don't use - doesn't support 60fps)
- **Camera 2**: HD USB Camera ✅ (Use this)

## Correct Configuration

Always use **Camera 0** and **Camera 2** for dual recording:

```python
recorder = DualCameraRecorder(camera1_id=0, camera2_id=2)
```

## Finding Your Cameras

Run this to identify which cameras are HD USB:
```powershell
python find_hd_usb_cameras.py
```

This will show:
- Which cameras support 720p@60fps
- Which cameras are built-in vs USB
- Recommended camera IDs to use

## Default Settings

The default settings have been updated to use cameras 0 and 2:
- `dual_camera_recorder.py` - Default: `camera1_id=0, camera2_id=2`
- `run_dual_recording.py` - Uses cameras 0 and 2

## Testing

Test with the correct cameras:
```powershell
python debug_recorder.py --test 1 --camera1 0 --camera2 2
```

## Why Camera 1 Was Wrong

Camera 1 is the built-in system camera which:
- Doesn't support 60fps at 720p
- Has different hardware capabilities
- Was causing frame rate mismatches

Using cameras 0 and 2 ensures:
- Both cameras are identical HD USB hardware
- Both support 60fps+ at 720p
- Perfect synchronization
- Zero frame drops

