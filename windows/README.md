# Windows Camera Diagnostic Tools

This folder contains PowerShell scripts to diagnose Windows camera issues that are outside of the Python application scope.

## Quick Start

Run the comprehensive diagnostic script first:

```powershell
.\windows\diagnose_cameras.ps1
```

This will run all checks and provide a summary of issues.

## Individual Scripts

### 1. `diagnose_cameras.ps1` (Recommended)
**Comprehensive diagnostic tool** - Runs all checks in sequence.

```powershell
.\windows\diagnose_cameras.ps1
```

### 2. `check_camera_privacy.ps1`
**Checks Windows camera privacy settings**

This script checks:
- Camera privacy registry settings
- Whether cameras are allowed for desktop apps
- Privacy settings that might block camera access

```powershell
.\windows\check_camera_privacy.ps1
```

**Common Issues:**
- Camera access is disabled in Windows Settings
- Desktop apps are not allowed to access cameras
- Registry values are set to "Deny"

**Fix:**
1. Open Settings (Windows Key + I)
2. Go to Privacy & Security > Camera
3. Turn ON "Camera access"
4. Turn ON "Let desktop apps access your camera"
5. Restart computer

### 3. `check_usb_cameras.ps1`
**Checks USB camera devices in Device Manager**

This script:
- Enumerates camera devices
- Checks device status (OK, Error, etc.)
- Identifies problem devices
- Shows driver information

```powershell
.\windows\check_usb_cameras.ps1
```

**Common Issues:**
- Camera not recognized (yellow exclamation mark in Device Manager)
- Driver problems
- USB connection issues

**Fix:**
1. Open Device Manager (Win+X, then M)
2. Expand "Cameras" or "Imaging devices"
3. Right-click problematic camera
4. Select "Update driver" or "Uninstall device"
5. If uninstalling, disconnect and reconnect USB camera

### 4. `check_camera_processes.ps1`
**Checks for processes using cameras**

Windows cameras can typically only be accessed by one application at a time. This script finds processes that might be locking cameras.

```powershell
.\windows\check_camera_processes.ps1
```

**Common culprits:**
- Windows Camera app
- Web browsers (Chrome, Edge, Firefox)
- Video conferencing apps (Zoom, Teams, Skype)
- Streaming software (OBS, XSplit)
- Python processes

**Fix:**
- Close the applications using cameras
- Use `Stop-Process -Id <PID>` to force-close if needed

### 5. `enumerate_directshow.ps1`
**Checks DirectShow enumeration**

DirectShow is what OpenCV uses with `CAP_DSHOW` backend on Windows. This script attempts to check DirectShow availability.

```powershell
.\windows\enumerate_directshow.ps1
```

**Note:** For detailed DirectShow enumeration, use the Python script:
```powershell
python tests/enumerate_dshow_cameras.py
```

## Common Issues and Solutions

### Issue: Cameras work in some apps but not others

**Possible causes:**
1. Privacy settings blocking desktop apps
2. Another application is using the camera
3. DirectShow vs. other backend conflicts

**Solution:**
1. Run `check_camera_privacy.ps1` - ensure desktop apps are allowed
2. Run `check_camera_processes.ps1` - close other camera-using apps
3. Restart computer

### Issue: Cameras not detected at all

**Possible causes:**
1. USB connection issues
2. Driver problems
3. Device Manager conflicts

**Solution:**
1. Run `check_usb_cameras.ps1` - check device status
2. Check Device Manager for yellow exclamation marks
3. Disconnect and reconnect USB cameras
4. Update or reinstall camera drivers
5. Try different USB ports

### Issue: Cameras work but show wrong resolution/fps

**This is usually a Python/OpenCV issue, not Windows:**
- Check camera capabilities with: `python tests/find_hd_usb_cameras.py`
- Use the detection script: `python scripts/detect_windows_cameras.py`
- Verify settings in `config_windows.json`

### Issue: Camera access denied errors

**Possible causes:**
1. Privacy settings
2. Another app is using the camera
3. Permission issues

**Solution:**
1. Run `check_camera_privacy.ps1`
2. Run `check_camera_processes.ps1`
3. Run application as Administrator (if needed)
4. Restart computer

## Running Scripts

All scripts are PowerShell scripts. Run them in PowerShell or PowerShell Core:

```powershell
# From project root
.\windows\diagnose_cameras.ps1

# Or change to windows directory
cd windows
.\diagnose_cameras.ps1
```

**Note:** Some scripts may require Administrator privileges for full functionality. If you get permission errors, try running PowerShell as Administrator.

## After Running Diagnostics

1. **Fix any issues found** by the diagnostic scripts
2. **Restart your computer** after changing privacy settings or drivers
3. **Test cameras** with the Python detection script:
   ```powershell
   python scripts/detect_windows_cameras.py
   ```
4. **If cameras still don't work**, check:
   - USB cables and ports
   - Try cameras on another computer
   - Check manufacturer's website for driver updates
   - Verify cameras work in Windows Camera app

## Integration with Python Scripts

After fixing Windows issues, use these Python scripts to verify:

1. **Detect all cameras:**
   ```powershell
   python scripts/detect_windows_cameras.py
   ```

2. **Find HD USB cameras:**
   ```powershell
   python tests/find_hd_usb_cameras.py
   ```

3. **Enumerate DirectShow devices:**
   ```powershell
   python tests/enumerate_dshow_cameras.py
   ```

## Additional Resources

- [Windows Camera Privacy Settings](https://support.microsoft.com/windows/camera-and-privacy-in-windows-b45b35c0-7e12-2c9c-7a16-e16e6e7a58e4)
- [Fix Camera Issues in Windows](https://support.microsoft.com/windows/fix-camera-problems-in-windows-5c6128d5-48e0-c0b1-8d7c-0f5c5e5e5f8e)
- Device Manager help: Win+X, then M (or search "Device Manager")

