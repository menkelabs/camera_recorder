# Dual USB Camera Recorder with Golf Swing Analysis

A Python application for capturing synchronized video from two USB cameras with integrated biomechanical analysis for golf swing evaluation. Features a Flask web-based GUI for camera configuration, recording control, analysis, and recording management.

## Features

- **Dual Camera Capture**: Simultaneously capture from 2 USB cameras with synchronized recording
- **Web-Based GUI**: Flask-powered browser interface with tabbed layout — no desktop GUI dependencies needed
  - Live MJPEG camera preview streams
  - Camera property sliders (brightness, contrast, exposure, etc.)
  - One-click recording with real-time duration display
  - Auto-detection and re-initialization of cameras from the browser
- **Golf Swing Analysis**: Integrated MediaPipe pose detection with 11 biomechanical metrics
  - **Rotation**: Shoulder turn, hip turn, X-factor, tempo ratio
  - **Position**: Lateral sway, head sway, spine angle, spine tilt
  - **Body**: Lead arm angle, knee flex, weight shift
  - Automatic swing phase detection (Address, Backswing, Top, Downswing, Impact, Follow-through)
  - Color-coded metric cards with good/ok/needs-work ratings
  - Interactive time-series chart with metric toggles and phase overlay
  - Frame-by-frame navigation with phase badge
  - Error details displayed in the GUI when analysis fails
- **Video Playback in Analysis**: Side-by-side annotated video panels (face-on + DTL) synced to the frame slider
  - Pose skeleton overlaid on each frame
  - Play/pause with configurable speed (0.25x, 0.5x, 1x, 2x, 4x)
  - Frames stored as compressed JPEG bytes (~15 MB vs ~500 MB raw) for low memory usage
- **Auto Swing Detection**: Hands-free recording via real-time shoulder-turn monitoring
  - Lightweight MediaPipe model (complexity=0) processes every 4th frame (~15 fps)
  - State machine: Idle → Motion Detected → Recording → Cooldown → Idle
  - Configurable thresholds (motion degree, confirmation frames, cooldown timer)
  - Toggle on/off from the Recording tab; hides manual start/stop when active
  - Real-time shoulder-turn gauge and state badge in the UI
- **Swing Comparison**: Side-by-side comparison of any two recorded swings
  - Delta cards showing value changes between swings with color-coded indicators
  - Overlay chart with normalised timeline (swings of different lengths align on 0-100%)
  - Dashed vs solid lines for easy visual distinction
- **Recording Management**: Browse, inspect, and delete recordings from the GUI
  - View all recordings with date, duration, and file sizes
  - Delete individual recordings or bulk-select and delete
  - Age-based cleanup (delete recordings older than N days)
- **Archive to External Disk**: One-click archiving of recordings to a configured USB drive
  - Configure the archive path once in the Settings tab (e.g. `/media/user/Seagate8TB/golf`)
  - Archives video files, analysis JSON, and camera settings
  - Tracks which recordings have been archived to avoid duplicates
  - Shows external disk space (total/used/free) with a usage bar
  - Connected/disconnected status badge for the archive drive
- **Multiple Recording Sessions**: Configure, record, analyze, and record again without restarting
- **Platform Support**: Windows and Linux with platform-appropriate camera backends and defaults
  - Auto-detection of camera indices with fallback search
  - Separate capture threads per camera for reliable dual-cam streaming on Linux
- **120 FPS Recording Target**: Optimized for high frame-rate capture
  - Threaded per-camera capture
  - Efficient video codecs (H.264, XVID)
  - Minimal buffering to reduce memory overhead

## Installation

1. Install Python 3.7 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Dependencies include: `opencv-python`, `numpy`, `mediapipe`, `Pillow`, `flask`

## Quick Start

Run the Flask GUI:
```bash
python scripts/flask_gui.py
```

Then open **http://localhost:5000** in your browser.

### With explicit camera IDs:
```bash
# Linux (find your camera indices with the Detect button in the GUI)
python scripts/flask_gui.py --camera1 0 --camera2 2

# Windows (auto-detected from config_windows.json, or specify manually)
python scripts/flask_gui.py --camera1 0 --camera2 2
```

### Command Line Options

```bash
python scripts/flask_gui.py [OPTIONS]

Options:
  --camera1 ID            Camera 1 index (default: 0 on Linux, from config on Windows)
  --camera2 ID            Camera 2 index (default: 1 on Linux, from config on Windows)
  --width WIDTH           Resolution width (default: 1280)
  --height HEIGHT         Resolution height (default: 720)
  --fps FPS               Recording FPS target (default: 120)
  --model-complexity {0,1,2}  MediaPipe model for analysis: 0=lite (fast), 1=full, 2=heavy (default: 2)
  --host HOST             Host to bind (default: 0.0.0.0)
  --port PORT             Port (default: 5000)
```

For lower-end hardware (e.g. HP EliteBook 840 G5), use `--model-complexity 0` for faster analysis at the cost of slightly lower accuracy.

## Usage

### GUI Overview

The application provides a tabbed web interface with 7 tabs:

1. **Camera 1 Setup [1]**: Live preview + property sliders (brightness, contrast, exposure, etc.)
2. **Camera 2 Setup [2]**: Same controls for the second camera
3. **Recording [3]**: Dual camera live preview, start/stop recording with Space bar
4. **Recordings [4]**: Browse, manage, and delete saved recordings
5. **Analysis [5]**: View analysis results with frame-by-frame navigation
6. **Compare [6]**: Side-by-side comparison of any two analyzed swings
7. **Settings [7]**: Archive configuration and external disk management

### Workflow

1. **Configure Cameras** (Tabs 1 & 2):
   - Adjust camera properties with sliders in the browser
   - Save settings or reset to defaults with buttons
   - Use **Detect** in the header to find available camera indices
   - Use **Reinit** to re-open cameras after plugging in or changing indices

2. **Record** (Tab 3):
   - Click **Start Recording** or press **Space** to start/stop
   - **Auto Detect** toggle: enable to let the system watch for swing motion and auto-start/stop recording
   - When Auto Detect is on, a shoulder-turn gauge and state badge show real-time detection status
   - Recordings save to the `recordings/` directory automatically

3. **Manage Recordings** (Tab 4):
   - View all recordings with date, duration, and file sizes
   - Delete individual recordings or select multiple for bulk delete
   - Clean up old recordings by age (e.g., delete everything older than 30 days)

4. **Analyze** (Tab 5 - Automatic):
   - Analysis starts automatically after recording completes
   - Results are auto-saved as JSON alongside the video files for later comparison
   - **Video playback panels** show annotated frames (pose skeleton) for both cameras, synced to the slider
   - **Play/pause** button with speed control (0.25x – 4x); press **Space** on the Analysis tab
   - Navigate frames with **A/Left Arrow** (previous) and **D/Right Arrow** (next)
   - If analysis fails, the error reason is displayed in the tab

5. **Compare** (Tab 6):
   - Select any two previously analyzed swings from the dropdowns
   - See delta cards showing which metrics improved or regressed
   - View overlaid time-series with normalised x-axis (swing progress 0-100%)

6. **Archive** (Tab 7 — Settings):
   - Set the archive path to your external USB drive (e.g. `/media/username/Seagate8TB/golf`)
   - Click **Archive All New Recordings** to copy videos, analysis JSON, and settings to the drive
   - The disk usage bar shows total/used/free space; a badge shows connected/disconnected status

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| 1-7 | Switch between tabs |
| Space | Start/stop recording (Recording tab) or play/pause video (Analysis tab) |
| A / Left Arrow | Previous analysis frame (on Analysis tab) |
| D / Right Arrow | Next analysis frame (on Analysis tab) |

### Camera Header Controls

The header bar shows per-camera status and provides:
- **Cam 1 / Cam 2** index inputs — set which indices to open
- **Reinit** — Re-open cameras with the specified indices (no restart needed)
- **Detect** — Scan indices 0-7 to find available cameras, auto-fills the inputs
- **Re-initialize** — Re-open cameras with the current indices

### Output

Recorded videos are saved in the `recordings/` directory:
- `recording_YYYYMMDD_HHMMSS_camera1.mp4`
- `recording_YYYYMMDD_HHMMSS_camera2.mp4`

Analysis results include:
- **Camera 1 (face-on)**: Lateral sway, head sway, spine tilt, knee flex, weight shift
- **Camera 2 (down-the-line)**: Shoulder turn, hip turn, X-factor, spine angle, lead arm angle
- Swing phase detection (Address, Backswing, Top, Downswing, Impact, Follow-through)
- Tempo ratio (backswing / downswing frames, pros average ~3:1)
- Detection rates for each camera
- Per-frame values for navigation + time-series chart
- JSON results auto-saved for later comparison

### Analysis Dashboard

The Analysis tab displays a rich dashboard with 5 sections:

```
+----------------------------+  +----------------------------+
| Camera 1 — Face-On         |  | Camera 2 — Down-the-Line   |
|                            |  |                            |
|   [annotated frame with    |  |   [annotated frame with    |
|    pose skeleton overlay]  |  |    pose skeleton overlay]  |
|                            |  |                            |
+----------------------------+  +----------------------------+

+----------------------------------------------------------+
| ▶ 1x  < Prev  Frame: 42/180  [======|====]  Next >  TOP |  <- play/pause + speed
+----------------------------------------------------------+

+---------------+  +---------------+  +---------------+  +---------------+
| SHOULDER TURN |  | HIP TURN      |  | X-FACTOR      |  | TEMPO         |
|    +45.2°     |  |    +22.1°     |  |    23.1°      |  |    3.1:1      |
| [=======  ]   |  | [=====    ]   |  | [======   ]   |  | [======   ]   |
| Max: +92.1°   |  | Max: +38.5°   |  | Max: 53.6°    |  | Ratio: 3.1:1  |
+---------------+  +---------------+  +---------------+  +---------------+
+---------------+  +---------------+  +---------------+  +---------------+
| LATERAL SWAY  |  | HEAD SWAY     |  | SPINE ANGLE   |  | SPINE TILT    |
|    +12px      |  |    -3px       |  |    32.1°      |  |    +5.2°      |
| [=======  ]   |  | [========]    |  | [======   ]   |  | [======   ]   |
| Max R: 34px   |  | Max R: 8px    |  | Addr: 30.5°   |  | Max: +12.3°   |
+---------------+  +---------------+  +---------------+  +---------------+
+---------------+  +---------------+  +---------------+
| LEAD ARM      |  | KNEE FLEX     |  | WEIGHT SHIFT  |
|    172.3°     |  |    165.1°     |  |    62%        |
| [=========]   |  | [========]    |  | [======   ]   |
| Min: 168.5°   |  | Addr: 168.0°  |  | Max Fwd: 72%  |
+---------------+  +---------------+  +---------------+

+----------------------------------------------------------+
| Time-Series Chart                    [Shoulder] [Sway] ..|
|                                                          |
|   ~~~/\~~~~                                              |
|  /        \___           |  <- current frame indicator   |
| /             \~~~~~/    |                                |
+----------------------------------------------------------+

Camera 1 (Face-On)              Camera 2 (Down-the-Line)
  Detection: 98.5%                Detection: 97.2%
  Max Sway Left: 28px            Max Shoulder: +92.1°
  Max Head Sway R: 8px           Max Hip: +38.5°
  ...                             ...
```

Each metric card is color-coded:
- **Green bar**: Good range (e.g., X-factor 30-55°)
- **Yellow bar**: Acceptable range
- **Red bar**: Needs improvement

### Swing Comparison Display

The Compare tab lets you pick any two analyzed swings and see the differences:

```
  Swing A: 2026-02-15 14:30:22        vs        Swing B: 2026-02-15 14:35:10

+------------------+  +------------------+  +------------------+  +------------------+
| SHOULDER TURN    |  | HIP TURN         |  | X-FACTOR         |  | TEMPO            |
| +85.2°  → +92.1° |  | +35.0° → +38.5° |  | 50.2°  → 53.6°  |  | 2.8:1  → 3.1:1  |
|          +6.9    |  |          +3.5    |  |          +3.4    |  |          +0.3    |
+------------------+  +------------------+  +------------------+  +------------------+
  ...

+----------------------------------------------------------+
| Overlay Chart               [Shoulder] [Sway] [X-Factor] |
|                                                          |
|  --- Swing A (dashed)                                    |
|  ___ Swing B (solid)                                     |
|                                                          |
|  ~~~/\~~~~                                               |
| /        \___                                            |
+----------------------------------------------------------+
```

Delta indicators:
- **Green (+)**: Metric improved from A to B
- **Red (-)**: Metric regressed
- **Gray**: No significant change

## API Endpoints

The Flask GUI exposes a REST API (used by the browser UI):

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve the web UI |
| GET | `/video_feed/<cam>` | MJPEG live stream |
| GET | `/api/status` | System status (cameras, recording, analysis) |
| GET | `/api/camera/<cam>/properties` | Camera property values and ranges |
| POST | `/api/camera/<cam>/property` | Set a camera property |
| POST | `/api/camera/<cam>/reset` | Reset camera properties to defaults |
| POST | `/api/settings/save` | Save camera settings to JSON |
| POST | `/api/cameras/reinit` | Re-initialize cameras (optional new IDs) |
| POST | `/api/cameras/detect` | Detect available camera indices |
| POST | `/api/recording/start` | Start recording |
| POST | `/api/recording/stop` | Stop recording + trigger analysis |
| GET | `/api/recordings` | List all recordings with metadata |
| GET | `/api/recordings/stats` | Recording count, disk usage, oldest/newest |
| DELETE | `/api/recordings/<timestamp>` | Delete a recording pair |
| DELETE | `/api/recordings` | Bulk delete recordings |
| POST | `/api/recordings/cleanup` | Delete recordings older than N days |
| GET | `/api/analysis/results` | Get analysis results and frame data |
| POST | `/api/analysis/frame` | Set the current analysis frame index |
| GET | `/api/analysis/frame/<cam>?index=N` | Get annotated JPEG frame for camera at index |
| POST | `/api/auto-detect/toggle` | Enable/disable auto swing detection |
| GET | `/api/auto-detect/status` | Get auto-detect state and shoulder-turn values |
| GET | `/api/analyses` | List all saved analysis results |
| GET | `/api/compare?a=TS&b=TS` | Compare two swings by timestamp |
| GET | `/api/archive/config` | Get archive path and disk status |
| POST | `/api/archive/config` | Set the archive path |
| GET | `/api/archive/status` | Archived recordings count and disk info |
| POST | `/api/archive/run` | Archive all new (or specified) recordings |

## Performance Tips

1. **Resolution**: 720p (1280x720) provides a good balance between quality and performance
2. **Frame Rate**: 120 FPS is the default target; reduce if CPU usage is high
3. **USB Bandwidth**: Two identical USB cameras **must be on different USB buses** (different physical controllers/hubs) to stream simultaneously. If camera 2 opens but shows no frames, move it to a different USB port.
4. **Hardware Acceleration**: The app automatically tries hardware-accelerated codecs when available
5. **Close Other Applications**: Free up CPU and USB bandwidth for camera capture
6. **Model Complexity**: Use `--model-complexity 0` (lite) on laptops like the HP EliteBook 840 G5 for ~3x faster analysis. Use `2` (heavy) on workstations for best accuracy.
7. **Memory**: Annotated frames are stored as compressed JPEG (~50 KB each) instead of raw BGR (~2.7 MB each), keeping analysis memory under 20 MB for a typical 300-frame recording.
8. **Auto-Detect**: The swing detector uses model complexity 0 and only processes every 4th capture frame, adding minimal CPU overhead during preview.

## Platform Differences

### Windows
- Uses DirectShow backend (`cv2.CAP_DSHOW`) for better camera compatibility
- Camera configuration stored in `config_windows.json` (auto-detected)
- To regenerate camera config: `python scripts/detect_windows_cameras.py`
- Default cameras: From `config_windows.json` if available, otherwise 0 and 2

### Linux
- Uses default OpenCV backend (V4L2)
- Separate capture thread per camera for reliable dual-cam streaming
- 1.5s delay between opening cameras + warmup reads (required for V4L2 with identical USB cams)
- Auto-fallback: if the requested camera 2 index fails, tries other indices automatically
- Default cameras: 0 and 1

See [docs/PLATFORM_CONFIG.md](docs/PLATFORM_CONFIG.md) for detailed platform configuration information.

## Troubleshooting

### Camera Not Found
- Use the **Detect** button in the GUI header to find available indices
- **Windows**: Run `python scripts/detect_windows_cameras.py` to detect cameras
- Ensure cameras are not being used by other applications
- Run `python tests/test_cameras.py` to find available cameras

### Camera 2 Opens But No Video
- **Most likely cause**: Both cameras are on the same USB bus (bandwidth conflict)
- **Fix**: Move one camera to a different USB hub/controller (check with `lsusb -t`)
- The GUI will show "Camera 2 not available" in the video feed even if `isOpened()` returns true

### High CPU Usage
- Reduce resolution (try 640x480)
- Reduce FPS target (try 30 or 60)
- Close other applications

### Recording Not Working
- Check if `recordings/` directory exists and is writable
- Verify cameras are providing frames (check console output)

### Analysis Errors
- Errors now display directly in the Analysis tab with the specific error message
- Ensure MediaPipe is installed: `pip install mediapipe`
- Analysis runs even if no poses are detected (detection rate will be 0%)

## Testing

```bash
# Flask GUI tests (routes, template, recording, analysis, video playback, auto-detect)
python -m pytest tests/test_flask_gui.py -v

# Swing detector state machine (idle, motion, recording, cooldown, full cycle)
python -m pytest tests/test_swing_detector.py -v

# Swing metrics (all 11 metrics, phases, tempo, analyze_sequence)
python -m pytest tests/test_sway_calculator.py -v

# Swing comparison (save/load JSON, compare API)
python -m pytest tests/test_swing_comparison.py -v

# Recording management (list, delete, bulk delete, cleanup)
python -m pytest tests/test_recording_management.py -v

# Archive to external disk (config, copy, manifest, API)
python -m pytest tests/test_archive.py -v

# Analysis navigation and workflow
python -m pytest tests/test_analysis_navigation.py -v
python -m pytest tests/test_analysis_workflow.py -v

# GUI unit tests (OpenCV-based, legacy)
python -m pytest tests/test_gui.py -v

# Workflow tests
python -m pytest tests/test_config_to_record_workflow.py -v

# Camera detection
python tests/test_cameras.py

# Run all tests
python run_all_tests.py
```

## Technical Details

- **Architecture**: Flask web server with MJPEG streaming, REST API, and single-page HTML/JS frontend
- **Threading**: Separate capture thread per camera to avoid V4L2 contention
- **Buffering**: Minimal buffering (buffer size 1) to reduce latency
- **Codecs**: Automatically selects best available codec (H.264 > XVID > mp4v)
- **Analysis**: MediaPipe Pose Detection (configurable model complexity 0/1/2) with 15 landmark extraction and 11 biomechanical metrics
- **Video Playback**: Annotated frames stored as compressed JPEG bytes for low-memory playback (~15 MB for 300 frames)
- **Auto-Detect**: SwingDetector state machine using lightweight MediaPipe model (complexity=0) with frame subsampling
- **Swing Comparison**: JSON-serialized analysis results with normalised overlay charting
- **Resource Management**: Automatic camera release/reacquisition between recording sessions
- **Recording Management**: File-based storage with timestamp grouping and safe deletion
- **Archive**: Configurable external disk path with manifest-based deduplication and disk usage reporting

## Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed project organization.

## License

Free to use and modify for your projects.
