# Dual USB Camera Recorder with Golf Swing Analysis

A Python application for capturing synchronized video from two USB cameras with integrated biomechanical analysis for golf swing evaluation. Features a GUI for camera configuration, recording control, and automated analysis.

## Features

- **Dual Camera Capture**: Simultaneously capture from 2 USB cameras with synchronized recording
- **GUI Interface**: Tabbed interface for camera setup, recording control, and analysis visualization
- **Golf Swing Analysis**: Integrated MediaPipe pose detection and biomechanical analysis
  - Lateral sway tracking (face-on view)
  - Shoulder turn, hip turn, and X-factor measurement (down-the-line view)
  - Frame-by-frame navigation through analysis results
  - Maximum metrics tracking and display
- **Multiple Recording Sessions**: Support for sequential recording sessions (configure → record → analyze → record again)
- **Platform Support**: Windows and Linux with platform-appropriate camera backends and defaults
- **Low CPU Usage**: 
  - Threaded capture to prevent blocking
  - Efficient video codecs (H.264, XVID)
  - Minimal buffering to reduce memory overhead

## Installation

1. Install Python 3.7 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

Run the GUI application:
```bash
python scripts/camera_setup_recorder_gui.py
```

On Windows (default cameras 0 and 2):
```bash
python scripts/camera_setup_recorder_gui.py --camera1 0 --camera2 2
```

On Linux (default cameras 0 and 1):
```bash
python scripts/camera_setup_recorder_gui.py --camera1 0 --camera2 1
```

## Usage

### GUI Overview

The application provides a tabbed interface with 4 tabs:

1. **Camera 1 Setup**: Configure camera properties (brightness, contrast, exposure, etc.)
2. **Camera 2 Setup**: Configure camera properties for the second camera
3. **Recording**: Start/stop recording with live preview
4. **Analysis**: View analysis results with frame navigation

### Workflow

The typical workflow supports multiple recording sessions:

1. **Configure Cameras** (Tabs 1 & 2):
   - Adjust camera properties using W/X to select, +/- to adjust
   - Save settings with 'S' key
   - Reset to defaults with 'R' key

2. **Record** (Tab 3):
   - Press **Space** to start/stop recording
   - Recordings are automatically saved to the `recordings/` directory

3. **Analyze** (Tab 4 - Automatic):
   - Analysis starts automatically after recording completes
   - View biomechanical metrics and pose detection results
   - Navigate frames with **A/Left Arrow** (previous) and **D/Right Arrow** (next)

4. **Record Again**:
   - Return to Tab 3 and press **Space** to start a new recording session
   - Camera resources are automatically managed between sessions

### Controls

#### Tab Navigation
- **Tab/1/2/3/4**: Switch between tabs
- **Q/ESC**: Quit application

#### Camera Setup Tabs (1 & 2)
- **W/X**: Select property (previous/next)
- **+/-**: Adjust current property (increase/decrease)
- **S**: Save camera settings
- **R**: Reset camera settings to defaults

#### Recording Tab (3)
- **Space**: Start/Stop recording

#### Analysis Tab (4)
- **A/Left Arrow**: Navigate to previous frame
- **D/Right Arrow**: Navigate to next frame

### Command Line Options

```bash
python scripts/camera_setup_recorder_gui.py [OPTIONS]

Options:
  --camera1 ID    Camera 1 ID (default: 0 on Linux, 0 on Windows)
  --camera2 ID    Camera 2 ID (default: 1 on Linux, 2 on Windows)
  --width WIDTH   Resolution width (default: 1280)
  --height HEIGHT Resolution height (default: 720)
  --fps FPS       Frame rate (default: 60)
```

### Output

Recorded videos are saved in the `recordings/` directory with filenames:
- `recording_YYYYMMDD_HHMMSS_camera1.mp4`
- `recording_YYYYMMDD_HHMMSS_camera2.mp4`

Analysis results include:
- **Camera 1 (face-on)**: Lateral sway metrics (left/right displacement)
- **Camera 2 (down-the-line)**: Rotation metrics (shoulder turn, hip turn, X-factor)
- Detection rates for each camera
- Maximum values for all metrics
- Frame-by-frame values for navigation

## Performance Tips

1. **Resolution**: 720p (1280x720) provides a good balance between quality and performance
2. **Frame Rate**: 60 FPS is recommended; reduce to 30 FPS if CPU usage is high
3. **Hardware Acceleration**: The app automatically tries to use hardware-accelerated codecs when available
4. **Close Other Applications**: Free up CPU resources for camera capture and analysis

## Platform Differences

### Windows
- Uses DirectShow backend (`cv2.CAP_DSHOW`) for better camera compatibility
- Default cameras: 0 and 2 (skips built-in camera typically at index 1)

### Linux
- Uses V4L2 backend (default)
- Default cameras: 0 and 1
- Cameras cannot be opened simultaneously by multiple processes (GUI automatically manages this)

See [docs/PLATFORM_CONFIG.md](docs/PLATFORM_CONFIG.md) for detailed platform configuration information.

## Troubleshooting

### Camera Not Found
- Check camera IDs: Try 0, 1, 2, etc.
- Ensure cameras are not being used by other applications (OBS, Zoom, etc.)
- On Windows, check Device Manager for camera availability
- Run `python tests/test_cameras.py` to find available cameras

### High CPU Usage
- Reduce resolution (try 640x480)
- Reduce FPS (try 30)
- Close other applications
- Check if hardware acceleration is working (see codec selection in console output)

### Recording Not Working
- Check if `recordings/` directory exists and is writable
- Verify cameras are providing frames (check console output)
- Ensure cameras are not locked by another process (especially on Linux)

### Analysis Errors
- Ensure MediaPipe is installed correctly: `pip install "mediapipe>=0.10.0,<0.10.30"`
- Analysis runs even if no poses are detected (detection rate will be 0%)
- Check that video files are fully written before analysis starts (automatic delay included)

### Multiple Recording Sessions Fail
- The application automatically manages camera resources between sessions
- If issues persist, ensure no other applications are using the cameras
- Check console output for camera lock warnings

## Testing

The project includes comprehensive test suites:

### GUI Tests
```bash
python -m pytest tests/test_gui.py -v
```

### Analysis Tests
```bash
python -m pytest tests/test_analysis_navigation.py -v
python -m pytest tests/test_analysis_workflow.py -v
```

### Workflow Tests
```bash
python -m pytest tests/test_config_to_record_workflow.py -v
```

### Camera Tests
```bash
python tests/test_cameras.py
```

See test README files for detailed information:
- [tests/README_GUI_TESTS.md](tests/README_GUI_TESTS.md)
- [tests/README_ANALYSIS_TESTS.md](tests/README_ANALYSIS_TESTS.md)

## Technical Details

- **Synchronization**: Timestamp-based frame matching with configurable tolerance
- **Threading**: Each camera runs in its own thread to prevent blocking
- **Buffering**: Minimal buffering (buffer size 2) to reduce latency and memory usage
- **Codecs**: Automatically selects best available codec (H.264 > XVID > mp4v)
- **Analysis**: MediaPipe Pose Detection (model complexity 2) with custom biomechanical calculations
- **Resource Management**: Automatic camera release/reacquisition for multiple recording sessions

## Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed project organization.

## License

Free to use and modify for your projects.
