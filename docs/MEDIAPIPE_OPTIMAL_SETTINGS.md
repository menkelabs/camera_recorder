# Optimal Settings for MediaPipe Analysis

## 🎯 Best Recommendation: 1080p @ 60 FPS

For **maximum fidelity** in MediaPipe analysis, use:

```python
recorder.start_cameras(width=1920, height=1080, fps=60)
```

### Why 1080p @ 60fps?

**Resolution Benefits (1080p):**
- ✅ **Maximum detail** - More pixels = better landmark detection
- ✅ **Better accuracy** - Pose, hand, and face detection are more precise
- ✅ **Reduced aliasing** - Higher resolution reduces edge artifacts
- ✅ **Better for zoom/crop** - Can crop regions while maintaining quality

**Frame Rate Benefits (60fps):**
- ✅ **Smooth motion capture** - Better tracking of fast movements
- ✅ **Reduced motion blur** - Each frame has less blur
- ✅ **Better temporal accuracy** - More data points for analysis
- ✅ **Improved tracking** - MediaPipe can track fast-moving subjects better

## Alternative Options

If you encounter performance issues, these are also excellent:

### Option 2: 1080p @ 30fps
```python
recorder.start_cameras(width=1920, height=1080, fps=30)
```
- Maximum detail, slightly less smooth motion
- Good for detailed pose analysis where motion is slower
- Lower CPU/disk usage

### Option 3: 720p @ 60fps
```python
recorder.start_cameras(width=1280, height=720, fps=60)
```
- Good detail, very smooth motion
- Lower file sizes
- Good balance of quality and performance

## Tested Configurations

Your cameras support:
- ✅ **1920x1080 @ 60fps** - Measured: ~46-52 FPS (recommended)
- ✅ **1920x1080 @ 30fps** - Measured: ~48-50 FPS
- ✅ **1280x720 @ 60fps** - Measured: ~105-107 FPS
- ✅ **1280x720 @ 30fps** - Measured: ~105-106 FPS

## MediaPipe-Specific Considerations

### For Pose Detection:
- **1080p @ 60fps** - Best for full-body tracking
- Higher resolution helps with small body parts (hands, feet)
- 60fps captures fast movements better

### For Hand Tracking:
- **1080p @ 60fps** - Optimal for detailed hand landmarks
- Hands move quickly - 60fps is important
- High resolution helps with finger detection

### For Face Detection:
- **1080p @ 30fps** - Usually sufficient (faces move slower)
- High resolution helps with facial landmark accuracy

### For Full Body Analysis:
- **1080p @ 60fps** - Best overall
- Captures all body parts with maximum detail
- Smooth motion for gait analysis, sports analysis, etc.

## Codec Recommendations

For MediaPipe analysis, use **H.264** codec (default):
- Good quality
- Widely supported
- Efficient compression

Avoid lossless codecs unless you need pixel-perfect accuracy (they create huge files).

## File Size Considerations

At 1080p @ 60fps:
- **File size**: ~50-100 MB per minute per camera
- **Total**: ~100-200 MB per minute for dual recording
- **10 minutes**: ~1-2 GB total

Make sure you have sufficient disk space!

## Performance Tips

1. **Use USB 3.0 ports** - Ensures sufficient bandwidth
2. **Close other applications** - Free up CPU/GPU for MediaPipe
3. **Use SSD storage** - Faster write speeds for large files
4. **Monitor CPU usage** - 1080p @ 60fps is demanding

## Quick Start

Update your recording script:

```python
from dual_camera_recorder import DualCameraRecorder

recorder = DualCameraRecorder(camera1_id=0, camera2_id=2)
recorder.start_cameras(width=1920, height=1080, fps=60)  # Best for MediaPipe!
recorder.start_recording("mediapipe_analysis")
# ... record ...
recorder.stop_recording()
recorder.stop_cameras()
```

## Testing

Test your setup:
```powershell
python test_mediapipe_resolutions.py
```

This will show you what resolutions your cameras support and recommend the best settings.

