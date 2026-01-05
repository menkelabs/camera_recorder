# Disable Camera Power Management

## Problem
USB cameras reset or disconnect after periods of inactivity due to Windows USB power management.

## Solution
Disable USB power management features that cause cameras to disconnect.

## Quick Start

**Easiest method:**
1. Double-click: `windows\RUN_DISABLE_POWER_MGMT.bat`
2. Click "Yes" when Windows asks for Administrator permission
3. **Restart your computer** when the script completes

**Alternative method:**
1. Right-click PowerShell → "Run as Administrator"
2. Run: `.\windows\disable_camera_power_management.ps1`
3. **Restart your computer**

## What the Script Does

The script disables power management in multiple places:

1. **USB Selective Suspend (System-wide)**
   - Disables Windows feature that puts USB devices to sleep
   - Registry: `HKLM:\SYSTEM\CurrentControlSet\Services\USB\DisableSelectiveSuspend = 1`

2. **Power Plan Settings**
   - Disables USB selective suspend in all power plans
   - Prevents USB devices from sleeping on battery or AC power

3. **Camera Device Power Management**
   - Disables power management for each camera device
   - Prevents individual cameras from going to sleep

4. **USB Hub Power Management**
   - Disables power management on USB root hubs
   - Ensures USB ports stay powered

## After Running the Script

**IMPORTANT:** Restart your computer for all changes to take effect!

After restart:
- Cameras should stay connected and powered on
- Cameras should not reset or disconnect after inactivity
- Camera streams should remain stable

## Verify Settings Were Applied

To check current settings without making changes:

```powershell
.\windows\disable_camera_power_management.ps1 -VerifyOnly
```

## Manual Alternative

If you prefer to do it manually:

1. **Control Panel → Power Options**
2. Click "Change plan settings" (for your active plan)
3. Click "Change advanced power settings"
4. Expand "USB settings"
5. Expand "USB selective suspend setting"
6. Set both "On battery" and "Plugged in" to **"Disabled"**
7. Click OK
8. **Restart computer**

## Troubleshooting

**If cameras still reset after running the script:**
1. Make sure you restarted your computer
2. Verify settings were applied: Run script with `-VerifyOnly` parameter
3. Check if another application is managing USB power
4. Try unplugging and replugging cameras
5. Check Device Manager for camera driver issues

**If script fails:**
- Make sure you're running as Administrator
- Some antivirus software may block registry changes
- Try running the script again

## Re-enable Power Management

If you want to re-enable power management later:

1. Control Panel → Power Options → Change plan settings → Change advanced power settings
2. USB settings → USB selective suspend setting → Enabled
3. Or delete the registry value:
   ```powershell
   Remove-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\USB" -Name "DisableSelectiveSuspend"
   ```
4. Restart computer

## Notes

- Disabling USB power management may slightly increase power consumption
- For laptops, this may reduce battery life slightly
- Most modern systems handle this well, impact is usually minimal
- This is recommended for systems used primarily with AC power (desktops)


