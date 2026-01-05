# Platform Configuration Guide

## Overview

The camera_recorder project supports both **Windows** and **Linux** with platform-specific camera configuration. Camera indexing and initialization differ significantly between platforms due to differences in how operating systems enumerate USB devices.

## Platform Differences

### Camera Backend

| Platform | Backend | API |
|----------|---------|-----|
| **Windows** | DirectShow | `cv2.CAP_DSHOW` |
| **Linux** | Video4Linux2 | `cv2.CAP_V4L2` (default) |

### Why Camera Indexes Differ

#### Windows
- Camera indexes are assigned by DirectShow based on device enumeration order
- Built-in webcams often take index 0 or 1
- USB cameras can have non-sequential indexes (e.g., 0, 2, 4)
- Indexes may change when cameras are unplugged/replugged or USB ports change
- **Solution**: Use `config_windows.json` to store detected camera configuration

#### Linux
- Cameras are assigned `/dev/video*` devices
- Each physical camera may create multiple device nodes (video capture + metadata)
- USB cameras are typically sequential (0, 1, 2...) but can vary by USB port order
- Device nodes can change on reboot or when cameras are reconnected
- **Solution**: Need `config_linux.json` (TODO - see roadmap below)

## Current Implementation

### Windows (Implemented ✓)

1. **Auto-detection script**: `scripts/detect_windows_cameras.py`
   - Enumerates all cameras using DirectShow
   - Tests each camera for HD capability and frame rate
   - Saves configuration to `config_windows.json`

2. **Configuration file**: `config_windows.json`
   ```json
   {
     "platform": "windows",
     "camera1_id": 0,
     "camera2_id": 2,
     "detected_cameras": [
       {"id": 0, "is_hd_usb": true, "measured_fps": 90.5},
       {"id": 1, "is_hd_usb": false, "measured_fps": 13.9},
       {"id": 2, "is_hd_usb": true, "measured_fps": 83.9}
     ]
   }
   ```

3. **GUI startup**: Reads `config_windows.json` for camera IDs

### Linux (Partial - Needs Enhancement)

Currently uses hardcoded defaults:
- Camera 1: Index 0
- Camera 2: Index 1

**Limitations**:
- No auto-detection script for Linux
- No configuration file persistence
- Assumes sequential camera indexes

## Roadmap: Linux Support Enhancement

### Phase 1: Linux Camera Detection Script

Create `scripts/detect_linux_cameras.py`:

```python
# Planned functionality:
# 1. List all /dev/video* devices
# 2. Filter to actual capture devices (not metadata nodes)
# 3. Test each camera for resolution/fps capability
# 4. Identify USB cameras by vendor/product ID
# 5. Save to config_linux.json
```

**Key Linux APIs to use**:
- `v4l2-ctl` for device enumeration
- `/sys/class/video4linux/` for device info
- `udevadm` for USB device identification

### Phase 2: Configuration File for Linux

Create `config_linux.json`:
```json
{
  "platform": "linux",
  "camera1_id": 0,
  "camera2_id": 2,
  "camera1_device": "/dev/video0",
  "camera2_device": "/dev/video2",
  "detected_cameras": [
    {
      "id": 0,
      "device": "/dev/video0",
      "usb_path": "1-2.1",
      "vendor": "HD USB Camera",
      "supports_720p_60fps": true
    }
  ]
}
```

### Phase 3: USB Port-Based Identification

For consistent camera assignment regardless of boot order:

```python
# Use USB port path for stable identification
# e.g., "usb-0000:00:14.0-2" always refers to same physical port

def get_camera_by_usb_port(port_path):
    """Find camera device by USB port path (stable across reboots)"""
    # Implementation using udev rules or sysfs
    pass
```

### Phase 4: Unified Configuration Loader

```python
def load_camera_config():
    """Load platform-appropriate configuration"""
    if sys.platform == 'win32':
        config_file = 'config_windows.json'
    else:
        config_file = 'config_linux.json'
    
    if os.path.exists(config_file):
        return json.load(open(config_file))
    else:
        # Run auto-detection
        return auto_detect_cameras()
```

## Usage

### Windows

```bash
# First time: Detect and configure cameras
python scripts/detect_windows_cameras.py

# Run GUI (uses config_windows.json automatically)
python scripts/camera_setup_recorder_gui.py
```

### Linux (Current)

```bash
# List available cameras
ls /dev/video*
v4l2-ctl --list-devices

# Run GUI with explicit camera IDs
python scripts/camera_setup_recorder_gui.py --camera1 0 --camera2 2
```

### Linux (Planned)

```bash
# First time: Detect and configure cameras
python scripts/detect_linux_cameras.py

# Run GUI (will use config_linux.json automatically)
python scripts/camera_setup_recorder_gui.py
```

## Manual Camera Override

On any platform, you can override auto-detected cameras:

```bash
python scripts/camera_setup_recorder_gui.py --camera1 0 --camera2 1
```

## Troubleshooting

### Windows: Cameras Not Detected

1. Run detection script: `python scripts/detect_windows_cameras.py`
2. Check Device Manager for camera availability
3. Ensure cameras aren't in use by other apps (OBS, Zoom, etc.)
4. Try different USB ports

### Linux: Cameras Not Found

1. List devices: `ls -la /dev/video*`
2. Check permissions: `groups` (should include `video`)
3. Add user to video group: `sudo usermod -a -G video $USER`
4. Check USB connection: `lsusb`
5. View kernel messages: `dmesg | grep -i camera`

### Camera Index Changed

- **Windows**: Re-run `python scripts/detect_windows_cameras.py`
- **Linux**: Use `--camera1` and `--camera2` arguments, or wait for `detect_linux_cameras.py`

## Technical Notes

### OpenCV Camera Backends

```python
# Windows - DirectShow provides better USB camera support
cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)

# Linux - V4L2 is the native Linux video API  
cap = cv2.VideoCapture(camera_id, cv2.CAP_V4L2)
# or use default (usually V4L2 on Linux)
cap = cv2.VideoCapture(camera_id)
```

### Buffer Settings

Both platforms benefit from minimal buffering for low latency:
```python
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize frame buffer
```

### Frame Rate Control

```python
cap.set(cv2.CAP_PROP_FPS, 60)  # Request 60 FPS
# Note: Actual FPS depends on camera capability and lighting conditions
```
