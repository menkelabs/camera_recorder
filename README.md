# Dual USB Camera Recorder

> **Note**: This project has been reorganized! See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for the new structure.
> 
> **Quick Start**: `python scripts/record_golf_swing.py` (for golf swings) or `python scripts/record_for_mediapipe.py` (for MediaPipe)

A Python application for capturing and recording synchronized video from two USB cameras simultaneously with optimized CPU usage. Designed for MediaPipe analysis pipeline.

## Features

- **Dual Camera Capture**: Simultaneously capture from 2 USB cameras
- **Synchronized Recording**: Timestamp-based synchronization ensures frames are aligned
- **Low CPU Usage**: 
  - Threaded capture to prevent blocking
  - Efficient video codecs (H.264, XVID)
  - Minimal buffering to reduce memory overhead
- **Easy Control**: Simple command-line interface for recording control
- **Preview Mode**: Preview both camera feeds before recording

## Installation

1. Install Python 3.7 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the application:
```bash
python dual_camera_recorder.py
```

The application will:
1. Show available cameras
2. Ask for camera IDs (usually 0 and 1)
3. Ask for resolution and FPS settings
4. Allow preview of cameras
5. Provide interactive controls for recording

### Controls

- **'r'** - Start/Stop recording
- **'p'** - Preview cameras
- **'q'** - Quit application

### Output

Recorded videos are saved in the `recordings/` directory with filenames:
- `{output_name}_camera1.mp4`
- `{output_name}_camera2.mp4`

## Performance Tips

1. **Lower Resolution**: Use 720p (1280x720) instead of 1080p for lower CPU usage
2. **Lower FPS**: 30 FPS is usually sufficient; reduce to 24 or 15 if needed
3. **Hardware Acceleration**: The app automatically tries to use hardware-accelerated codecs when available
4. **Close Other Applications**: Free up CPU resources for camera capture

## Integration with MediaPipe

The recorded videos can be processed with MediaPipe:

```python
import cv2
import mediapipe as mp

# Load recorded videos
cap1 = cv2.VideoCapture('recordings/dual_capture_20240101_120000_camera1.mp4')
cap2 = cv2.VideoCapture('recordings/dual_capture_20240101_120000_camera2.mp4')

# Process with MediaPipe
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

while cap1.isOpened() and cap2.isOpened():
    ret1, frame1 = cap1.read()
    ret2, frame2 = cap2.read()
    
    if not (ret1 and ret2):
        break
    
    # Process frames with MediaPipe
    results1 = pose.process(cv2.cvtColor(frame1, cv2.COLOR_BGR2RGB))
    results2 = pose.process(cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB))
    
    # Your analysis code here
```

## Debugging

If you encounter issues, use these debugging tools:

### Step 1: Test Camera Access
```bash
python test_cameras.py
```
This will show which cameras are available and if they can be accessed simultaneously.

### Step 2: Run Debug Mode
```bash
python debug_recorder.py
```
This provides detailed logging and step-by-step testing to identify the issue.

### Step 3: Check Error Messages
The main application now provides detailed error messages. Look for:
- Camera opening errors
- Frame reading failures
- Video writer initialization issues
- Synchronization problems

## Troubleshooting

### Camera Not Found
- Check camera IDs: Try 0, 1, 2, etc.
- Ensure cameras are not being used by other applications (OBS, Zoom, etc.)
- On Windows, check Device Manager for camera availability
- Run `python test_cameras.py` to find available cameras

### High CPU Usage
- Reduce resolution (try 640x480)
- Reduce FPS (try 15 or 24)
- Close other applications
- Check if hardware acceleration is working (see codec selection in console output)

### Synchronization Issues
- Ensure both cameras support the same FPS
- Try reducing the sync threshold in code if frames are being dropped
- Use cameras from the same manufacturer/model for best results

### Codec Issues
- If H.264 doesn't work, the app will fall back to other codecs
- Install codec packs if videos won't play (K-Lite Codec Pack on Windows)
- Check debug output to see which codec is being used

### Recording Not Working
- Check if `recordings/` directory exists and is writable
- Verify video writers are opening (check console output)
- Ensure cameras are providing frames (see frame count in debug output)

## Technical Details

- **Synchronization**: Uses timestamp-based matching with ~33ms tolerance (1 frame at 30fps)
- **Threading**: Each camera runs in its own thread to prevent blocking
- **Buffering**: Minimal buffering (buffer size 2) to reduce latency and memory usage
- **Codecs**: Automatically selects best available codec (H.264 > XVID > mp4v)

## License

Free to use and modify for your projects.

