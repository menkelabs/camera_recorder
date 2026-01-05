# Quick Fix Guide for HD USB Cameras

## Current Status
- 2 HD USB Cameras: OK (working) ✅
- 1 HD USB Camera: CM_PROB_PHANTOM (phantom device - can be ignored)

## If Your Cameras Stopped Working

### Step 1: Refresh Camera Drivers (Quick Fix)
1. Open Device Manager (Win+X, then M)
2. Expand "Cameras"
3. Right-click each **HD USB Camera** (the ones with OK status)
4. Select **"Disable device"**
5. Wait 5 seconds
6. Right-click again → Select **"Enable device"**
7. Test cameras

### Step 2: If Still Not Working - Reinstall Drivers
1. Open Device Manager
2. Right-click each **HD USB Camera**
3. Select **"Uninstall device"**
4. Check **"Delete the driver software for this device"**
5. Click **"Uninstall"**
6. Unplug the USB camera
7. Wait 10 seconds
8. Plug the USB camera back in
9. Windows will reinstall the driver automatically
10. Test cameras

### Step 3: Disable USB Power Management
USB Selective Suspend can cause cameras to stop working:
1. Control Panel → Power Options
2. Click "Change plan settings" (for your active plan)
3. Click "Change advanced power settings"
4. Expand "USB settings"
5. Expand "USB selective suspend setting"
6. Set to **"Disabled"** (for both "On battery" and "Plugged in")
7. Click OK
8. Restart computer

### Step 4: Test Cameras
```powershell
python scripts/detect_windows_cameras.py
```

## Optional: Remove Phantom Device
The phantom device won't affect your working cameras, but you can remove it:

```powershell
# Run PowerShell as Administrator
.\windows\remove_phantom_camera.ps1
```

Or manually in Device Manager:
1. Right-click the phantom camera (shows "Unknown" status)
2. Select "Uninstall device"
3. Check "Delete the driver software for this device"
4. Click "Uninstall"

## Common Causes
- **USB power management** suspending the camera
- **Driver corruption** after Windows updates
- **Camera disconnected/reconnected** creating phantom device
- **Another application** using the camera

## Still Not Working?
1. Try different USB ports
2. Try the cameras on another computer
3. Check Windows Privacy Settings:
   - Settings → Privacy & Security → Camera
   - Turn ON "Camera access"
   - Turn ON "Let desktop apps access your camera"
4. Check for Windows Updates
5. Restart computer



