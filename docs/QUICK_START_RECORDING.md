# Quick Start - Dual HD USB Camera Recording at 60 FPS

## Your Cameras
- **Camera 1**: Index 0 (HD USB Camera) - Supports up to 120fps @ 720p
- **Camera 2**: Index 1 (HD USB Camera) - Supports up to 120fps @ 720p

**Recording Settings: 1280x720 @ 60 FPS**

## Quick Start

### Option 1: Simple Recording Script (60 FPS)
```powershell
python run_dual_recording.py
```
This will:
- Use cameras 0 and 1 automatically
- Record at **1280x720 @ 60fps**
- Save to `recordings/` folder

### Option 2: Debug/Test Mode
```powershell
# Test basic capture at 60fps
python debug_recorder.py --test 1 --camera1 0 --camera2 1

# Test recording at 60fps
python debug_recorder.py --test 2 --camera1 0 --camera2 1

# Run both tests
python debug_recorder.py --test 3 --camera1 0 --camera2 1
```

### Option 3: Use Main Recorder Directly
```python
from dual_camera_recorder import DualCameraRecorder

recorder = DualCameraRecorder(camera1_id=0, camera2_id=1)
recorder.start_cameras(width=1280, height=720, fps=60)  # 60 FPS!
recorder.start_recording("my_recording")
# ... record ...
recorder.stop_recording()
recorder.stop_cameras()
```

## FPS Testing

Test if cameras can achieve 60 FPS:
```powershell
python test_60fps.py
```

## Camera Identification

If you need to identify cameras again:
```powershell
python identify_hd_cameras.py
```

## Troubleshooting

### Cameras not achieving 60 FPS?
1. Make sure no other app is using the cameras (Zoom, Teams, OBS, etc.)
2. Check USB connection - use USB 3.0 ports for best performance
3. Try closing other applications to free up system resources
4. Some cameras may need a moment to stabilize at higher FPS

### Low frame rate?
- Check USB connection quality
- Close other applications
- Try unplugging and replugging cameras
- Check if cameras are sharing USB bandwidth (use different USB controllers if possible)

### Recording issues?
- Check `recordings/` folder exists
- Make sure you have disk space (60fps uses more space!)
- Check debug output for codec issues
- 60fps videos will be larger files

## Output

Recordings are saved to `recordings/` folder as:
- `{output_name}_camera1.mp4` (1280x720 @ 60fps)
- `{output_name}_camera2.mp4` (1280x720 @ 60fps)

Both videos are synchronized and ready for MediaPipe processing!

## Performance Notes

- **60 FPS** = smoother motion capture
- **File size**: ~2x larger than 30fps recordings
- **CPU usage**: Slightly higher, but still optimized
- **Sync**: Frames are synchronized within ~16ms (1 frame at 60fps)
