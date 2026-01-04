# Camera Test GUI Guide

## Overview

The Camera Test GUI provides a high-performance, real-time interface for testing and adjusting camera properties. Perfect for:
- **Focus adjustment** - Fine-tune camera focus manually
- **Brightness control** - Adjust for different lighting conditions (sun, shade, etc.)
- **Saturation** - Control color intensity
- **Exposure** - Manual exposure control
- **Other properties** - Gain, white balance, sharpness, gamma, contrast

## Features

- **Dual camera support** - Test both cameras simultaneously
- **Real-time preview** - Low-latency live feed from both cameras
- **Property controls** - Adjustable trackbars for all camera properties
- **Live info overlay** - See current settings on the preview
- **Save/Load settings** - Save your preferred settings for later
- **High performance** - Optimized for smooth 60fps preview

## Quick Start

### Basic Usage
```powershell
# Use default cameras (0 and 2) at 720p @ 60fps
python scripts/camera_test_gui.py

# Custom cameras and resolution
python scripts/camera_test_gui.py --camera1 0 --camera2 2 --width 1920 --height 1080 --fps 60
```

### Command Line Options
```
--camera1 ID    Camera 1 index (default: 0)
--camera2 ID    Camera 2 index (default: 2)
--width WIDTH   Resolution width (default: 1280)
--height HEIGHT Resolution height (default: 720)
--fps FPS       Frame rate (default: 60)
```

## Controls

### Keyboard Shortcuts
- **`q`** - Quit the application
- **`s`** - Save current settings to JSON file
- **`r`** - Reset all settings to defaults
- **`1`** - Show/hide Camera 1 window
- **`2`** - Show/hide Camera 2 window

### Trackbars (Per Camera)

Each camera window has trackbars for:

1. **Brightness** (0-255)
   - Controls overall image brightness
   - Increase for darker scenes, decrease for bright scenes

2. **Contrast** (0-255)
   - Controls difference between light and dark areas
   - Higher values = more dramatic differences

3. **Saturation** (0-255)
   - Controls color intensity
   - 0 = grayscale, 255 = maximum color

4. **Exposure** (0-100, mapped to camera range)
   - Manual exposure control
   - Lower = darker (less light), Higher = brighter (more light)
   - Useful for compensating for sun/shade changes

5. **Gain** (0-100)
   - Amplifies the signal (similar to ISO)
   - Higher gain = brighter but more noise

6. **Focus** (0-255)
   - Manual focus control (if camera supports it)
   - Adjust to get sharp focus on your subject

7. **White Balance** (0-100, mapped to 2000-6500K)
   - Adjusts color temperature
   - Lower = cooler (blue), Higher = warmer (orange)
   - Important for accurate colors in different lighting

8. **Sharpness** (0-255)
   - Edge enhancement
   - Higher = sharper edges (may increase artifacts)

9. **Gamma** (0-200)
   - Controls brightness curve
   - Affects mid-tones more than highlights/shadows

## Usage Tips

### For Outdoor/Sunny Conditions
1. **Lower Exposure** - Prevent overexposure from bright sun
2. **Increase Saturation** - Sunlight can wash out colors
3. **Adjust White Balance** - Sunlight is typically 5500-6500K
4. **Fine-tune Focus** - Ensure subject is sharp

### For Indoor/Low Light
1. **Increase Brightness/Gain** - Boost signal in low light
2. **Lower Exposure** - Prevent motion blur
3. **Adjust White Balance** - Indoor lighting is typically 3000-4000K
4. **Increase Contrast** - Make details more visible

### For Focus Testing
1. Position camera to view your subject
2. Adjust **Focus** trackbar slowly
3. Watch the preview for sharpness
4. Note the focus value when optimal
5. Save settings for later use

### Saving Settings
- Press **`s`** to save current settings
- Settings are saved as JSON: `camera_settings_YYYYMMDD_HHMMSS.json`
- You can load these settings later in your recording scripts

## Example Workflow

1. **Start GUI**
   ```powershell
   python scripts/camera_test_gui.py
   ```

2. **Adjust for lighting**
   - If sunny: Lower exposure, increase saturation
   - If cloudy: Increase brightness, adjust white balance

3. **Fine-tune focus**
   - Adjust focus trackbar while viewing preview
   - Find the value that gives sharpest image

4. **Save settings**
   - Press `s` to save
   - Note the filename for later reference

5. **Test recording**
   - Use saved settings in your recording scripts
   - Or manually adjust during recording setup

## Performance Notes

- **Frame Rate**: GUI runs at specified FPS (default 60fps)
- **Latency**: Minimized by using buffer size of 1
- **CPU Usage**: Low overhead for smooth preview
- **Resolution**: Higher resolutions may reduce frame rate

## Troubleshooting

### Camera not opening
- Check camera IDs with `python tests/test_cameras.py`
- Ensure cameras are not in use by another application
- Try different camera IDs

### Trackbar not working
- Some cameras don't support all properties
- Check camera capabilities with `python tests/enumerate_dshow_cameras.py`
- Property may be read-only on your camera

### Preview is laggy
- Reduce resolution: `--width 640 --height 480`
- Reduce FPS: `--fps 30`
- Close other applications using the cameras

### Settings not saving
- Check file permissions in current directory
- Settings are saved as JSON in the current working directory

## Integration with Recording

After finding optimal settings in the GUI:

1. **Note the values** from the saved JSON file
2. **Apply in recording scripts** by setting camera properties before recording
3. **Or use saved settings** - Load JSON and apply values programmatically

Example:
```python
from dual_camera_recorder import DualCameraRecorder
import json

# Load saved settings
with open('camera_settings_20240103_120000.json') as f:
    settings = json.load(f)

recorder = DualCameraRecorder()
recorder.start_cameras(width=1280, height=720, fps=60)

# Apply settings
cap1 = recorder.camera1.cap
cap1.set(cv2.CAP_PROP_BRIGHTNESS, settings['camera1']['brightness'])
cap1.set(cv2.CAP_PROP_SATURATION, settings['camera1']['saturation'])
# ... etc

recorder.start_recording('output')
```

## Advanced Usage

### Single Camera Mode
Hide one camera window with `1` or `2` key to focus on one camera.

### Custom Property Ranges
Edit `prop_ranges` in the script to adjust trackbar ranges for your specific cameras.

### Auto-Exposure
The GUI disables auto-exposure for manual control. If you want auto-exposure back:
- Set `CAP_PROP_AUTO_EXPOSURE` to 0.75 (auto mode)
- Or modify the script to add an auto/manual toggle



