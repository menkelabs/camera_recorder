# Quick Fix for Black Screen Camera

## Problem
HD USB Camera shows black screen (camera detected but no video output)

## Quick Fix (Try This First - Takes 30 seconds)

**Step 1: Refresh Camera in Device Manager**
1. Press **Win+X**, then press **M** (opens Device Manager)
2. Expand **"Cameras"** folder
3. Find the **HD USB Camera** that shows black screen
4. **Right-click** it → Select **"Disable device"**
5. Wait **10 seconds**
6. **Right-click** it again → Select **"Enable device"**
7. Wait **10 seconds** for camera to reinitialize
8. Test the camera

This fixes black screen issues 80% of the time!

## If That Doesn't Work

**Step 2: Reinstall Camera Driver**
1. Device Manager → Cameras
2. Right-click the HD USB Camera showing black screen
3. Select **"Uninstall device"**
4. Check **"Delete the driver software for this device"**
5. Click **"Uninstall"**
6. **Unplug the USB camera** from computer
7. Wait **10 seconds**
8. **Plug the USB camera back in** (try a different USB port if possible)
9. Windows will reinstall the driver automatically
10. Test the camera

## If Still Not Working

**Step 3: Check Physical Connection**
- Unplug the camera
- Try a different USB port (preferably USB 3.0 if available)
- Check USB cable (try a different cable if possible)
- Make sure USB port isn't loose/damaged

**Step 4: Check USB Power Management**
1. Control Panel → Power Options
2. Click "Change plan settings" (for your active plan)
3. Click "Change advanced power settings"
4. Expand "USB settings"
5. Expand "USB selective suspend setting"
6. Set to **"Disabled"** (for both "On battery" and "Plugged in")
7. Click OK
8. **Restart computer**

## Test Camera

After fixing, test with:
```powershell
python scripts/detect_windows_cameras.py
```

This will show which cameras are actually working.



