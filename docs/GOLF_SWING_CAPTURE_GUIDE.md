# Golf Swing Capture - Optimal Settings Guide

## 🏌️ Golf Swings Are VERY Fast!

Golf swings require **ultra-high frame rates** to capture:
- Clubhead speed: **100+ mph**
- Swing duration: **~0.5-1.5 seconds**
- Impact moment: **happens in milliseconds**
- Body rotation: **very fast**

## 🎯 BEST Options for Golf Swings

### Option 1: 640p @ 240 FPS ⭐ RECOMMENDED FOR GOLF
```python
recorder.start_cameras(width=640, height=480, fps=240)
```

**Why this is EXCELLENT for golf:**
- ✅ **240fps = 1 frame every 4.17ms** - Captures ultra-fast motion
- ✅ **Perfect for impact analysis** - Can see clubhead position precisely
- ✅ **Captures body rotation** - Every detail of weight transfer and rotation
- ✅ **Good for MediaPipe** - 640p is sufficient for pose detection
- ✅ **Smaller files** - More manageable than 1080p

**Timing Analysis:**
- At 240fps: 1 frame = **4.17ms**
- At 120fps: 1 frame = **8.33ms**
- At 60fps:  1 frame = **16.67ms**
- At 30fps:  1 frame = **33.33ms**

**Impact Zone Capture:**
- Golf impact happens in ~1-2ms
- At 240fps: **~20-40 frames** during impact zone
- At 120fps: **~10-20 frames** during impact zone
- At 60fps:  **~5-10 frames** during impact zone
- At 30fps:  **~2-4 frames** during impact zone (TOO FEW!)

### Option 2: 720p @ 120 FPS
```python
recorder.start_cameras(width=1280, height=720, fps=120)
```

**Why this is good:**
- ✅ **120fps** - Still very fast, captures most details
- ✅ **Higher resolution** - Better for detailed analysis
- ✅ **Good balance** - Speed + detail

### Option 3: 1080p @ 60 FPS
```python
recorder.start_cameras(width=1920, height=1080, fps=60)
```

**When to use:**
- If you need maximum detail for post-swing analysis
- For slow-motion replay (can slow down 60fps footage)
- Less ideal for real-time impact analysis

## 📊 Comparison Table

| Resolution | FPS | Frame Time | Impact Frames | Best For |
|------------|-----|------------|---------------|----------|
| **640p** | **240** | **4.17ms** | **~20-40** | **⭐ Golf swings - BEST** |
| 720p | 120 | 8.33ms | ~10-20 | Golf swings - Good |
| 720p | 60 | 16.67ms | ~5-10 | General motion |
| 1080p | 60 | 16.67ms | ~5-10 | High detail analysis |
| 1080p | 30 | 33.33ms | ~2-4 | ❌ Too slow for golf |

## 🎬 Recommended Setup for Golf

### For Maximum Motion Capture:
```python
from dual_camera_recorder import DualCameraRecorder

recorder = DualCameraRecorder(camera1_id=0, camera2_id=2)
recorder.start_cameras(width=640, height=480, fps=240)  # BEST for golf!
recorder.start_recording("golf_swing")
```

### For MediaPipe Analysis:
```python
# 240fps is excellent for MediaPipe pose tracking during fast motion
recorder.start_cameras(width=640, height=480, fps=240)
```

**Why 640p is fine for MediaPipe:**
- MediaPipe pose detection works well at 640p
- The high frame rate (240fps) is more important than resolution
- You get smooth, detailed motion tracking

## 📁 File Size Considerations

At **640p @ 240fps**:
- **File size**: ~100-200 MB per minute per camera
- **Total**: ~200-400 MB per minute for dual recording
- **A 10-second swing**: ~35-70 MB total
- **A 1-minute session**: ~200-400 MB total

**Storage Tips:**
- Use fast SSD storage
- Record in short clips (10-30 seconds per swing)
- Delete unwanted recordings promptly

## 🎯 Use Cases

### For Impact Analysis:
**Use 640p @ 240fps**
- Maximum frames during impact
- Can analyze clubhead position precisely
- See ball contact in detail

### For Full Swing Analysis:
**Use 720p @ 120fps**
- Good balance of detail and speed
- Captures entire swing smoothly
- Better for full-body pose analysis

### For Slow-Motion Replay:
**Use 1080p @ 60fps**
- High detail for slow-motion playback
- Can slow down to 0.25x speed smoothly
- Good for post-swing review

## 🚀 Quick Start Script

I've created `record_golf_swing.py` for easy golf swing capture:

```powershell
python record_golf_swing.py
```

This uses optimal settings (640p @ 240fps) for golf swings.

## ⚠️ Important Notes

1. **240fps requires fast storage** - Use SSD, not HDD
2. **Large file sizes** - Plan storage accordingly
3. **USB 3.0 ports** - Ensure cameras are on USB 3.0 for bandwidth
4. **Close other apps** - Free up CPU/disk for high-speed recording
5. **Record in short clips** - 10-30 seconds per swing is ideal

## 📈 Performance Tips

1. **Test your setup first** - Record a test swing to verify
2. **Monitor disk space** - 240fps creates large files quickly
3. **Use fast codec** - H.264 is good, avoid lossless
4. **Dual recording** - Both cameras at 240fps is demanding
5. **Post-process** - You can always downscale/convert later

## 🎥 Recording Workflow

1. **Setup**: Position cameras for best angle (side + front recommended)
2. **Test**: Record a practice swing to verify settings
3. **Record**: Capture each swing as a separate file
4. **Review**: Use video player to slow down and analyze
5. **Analyze**: Use MediaPipe on the recordings for pose analysis

## Conclusion

**For golf swings, 240fps @ 640p is the BEST option:**
- Captures ultra-fast motion
- Perfect for impact analysis
- Good enough for MediaPipe
- Manageable file sizes

**The high frame rate is more important than resolution for fast motion!**

