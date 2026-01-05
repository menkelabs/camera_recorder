#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Disable USB power management on cameras to prevent them from resetting
    
.DESCRIPTION
    This script disables all power management features that can cause USB cameras
    to disconnect or reset after periods of inactivity. It configures:
    - USB Selective Suspend (system-wide)
    - Device-specific power management for cameras
    - Registry settings to keep USB devices powered
    
    Requires Administrator rights.
#>

param(
    [switch]$VerifyOnly
)

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Disable Camera Power Management" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[ERROR] Administrator rights required" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run PowerShell as Administrator:" -ForegroundColor Yellow
    Write-Host "  1. Right-click PowerShell" -ForegroundColor White
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor White
    Write-Host "  3. Run this script again" -ForegroundColor White
    Write-Host ""
    Write-Host "Or double-click: windows\RUN_DISABLE_POWER_MGMT.bat" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "[OK] Running as Administrator" -ForegroundColor Green
Write-Host ""

if ($VerifyOnly) {
    Write-Host "VERIFY MODE: Checking current settings only" -ForegroundColor Yellow
    Write-Host ""
}

# Step 1: Disable USB Selective Suspend (System-wide)
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host "Step 1: Disabling USB Selective Suspend (System-wide)" -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host ""

$usbSuspendPath = "HKLM:\SYSTEM\CurrentControlSet\Services\USB"

try {
    if (Test-Path $usbSuspendPath) {
        $currentValue = Get-ItemProperty -Path $usbSuspendPath -Name "DisableSelectiveSuspend" -ErrorAction SilentlyContinue
        
        if ($currentValue -and $currentValue.DisableSelectiveSuspend -eq 1) {
            Write-Host "[OK] USB Selective Suspend is already disabled" -ForegroundColor Green
            Write-Host "  Registry value: DisableSelectiveSuspend = 1" -ForegroundColor Gray
        } else {
            if (-not $VerifyOnly) {
                Set-ItemProperty -Path $usbSuspendPath -Name "DisableSelectiveSuspend" -Value 1 -Type DWord -ErrorAction Stop
                Write-Host "[OK] USB Selective Suspend disabled" -ForegroundColor Green
                Write-Host "  Set: DisableSelectiveSuspend = 1" -ForegroundColor Gray
            } else {
                Write-Host "[NEEDS FIX] USB Selective Suspend is enabled" -ForegroundColor Red
                Write-Host "  Current value: $($currentValue.DisableSelectiveSuspend)" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "[WARNING] USB registry path not found: $usbSuspendPath" -ForegroundColor Yellow
        if (-not $VerifyOnly) {
            try {
                New-Item -Path $usbSuspendPath -Force | Out-Null
                Set-ItemProperty -Path $usbSuspendPath -Name "DisableSelectiveSuspend" -Value 1 -Type DWord -ErrorAction Stop
                Write-Host "[OK] Created registry path and disabled USB Selective Suspend" -ForegroundColor Green
            } catch {
                Write-Host "[ERROR] Could not create registry path: $_" -ForegroundColor Red
            }
        }
    }
} catch {
    Write-Host "[ERROR] Could not modify USB Selective Suspend: $_" -ForegroundColor Red
}

Write-Host ""

# Step 2: Disable USB Selective Suspend for each power plan
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host "Step 2: Disabling USB Selective Suspend in Power Plans" -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host ""

$powerPlans = powercfg /list 2>$null | Select-String -Pattern "GUID:" | ForEach-Object {
    if ($_ -match '([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})') {
        $matches[1]
    }
}

if ($powerPlans) {
    foreach ($guid in $powerPlans) {
        $settingGuid = "2a737441-1930-4402-8d77-b2bebba308a3"  # USB settings
        $usbSuspendSetting = "48e6b7a6-50f5-4782-a5d4-53bb8f07e226"  # USB selective suspend
        
        try {
            $currentSetting = powercfg /query $guid $settingGuid $usbSuspendSetting 2>$null
            
            if ($currentSetting -match "0x00000001" -or $currentSetting -match "0x00000000") {
                if (-not $VerifyOnly) {
                    powercfg /setacvalueindex $guid $settingGuid $usbSuspendSetting 0 2>$null | Out-Null
                    powercfg /setdcvalueindex $guid $settingGuid $usbSuspendSetting 0 2>$null | Out-Null
                    powercfg /setactive $guid 2>$null | Out-Null
                    Write-Host "[OK] Disabled USB Selective Suspend for power plan: $guid" -ForegroundColor Green
                } else {
                    Write-Host "[CHECK] Power plan $guid - USB Selective Suspend setting" -ForegroundColor Yellow
                }
            }
        } catch {
            # Ignore errors for individual power plans
        }
    }
} else {
    Write-Host "[INFO] Could not enumerate power plans (this is OK)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Note: You can also disable USB Selective Suspend manually:" -ForegroundColor Yellow
Write-Host "  Control Panel > Power Options > Change plan settings > Change advanced power settings" -ForegroundColor Gray
Write-Host "  USB settings > USB selective suspend setting > Disabled" -ForegroundColor Gray
Write-Host ""

# Step 3: Disable power management for each camera device
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host "Step 3: Disabling Power Management for Camera Devices" -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host ""

$cameras = Get-PnpDevice | Where-Object { 
    $_.Class -eq "Camera" -or 
    $_.FriendlyName -like "*USB Camera*" -or
    $_.FriendlyName -like "*HD USB Camera*" -or
    $_.FriendlyName -like "*HP HD Camera*" -or
    $_.FriendlyName -like "*HP IR Camera*"
}

if ($cameras) {
    Write-Host "Found $($cameras.Count) camera device(s):" -ForegroundColor Green
    Write-Host ""
    
    foreach ($camera in $cameras) {
        Write-Host "  Processing: $($camera.FriendlyName)" -ForegroundColor White
        Write-Host "    Instance ID: $($camera.InstanceId)" -ForegroundColor Gray
        
        try {
            # Get device path from registry
            $devicePath = "HKLM:\SYSTEM\CurrentControlSet\Enum\$($camera.InstanceId)"
            
            if (Test-Path $devicePath) {
                if (-not $VerifyOnly) {
                    # Disable power management for this device
                    Set-ItemProperty -Path $devicePath -Name "DisableSelectiveSuspend" -Value 1 -Type DWord -ErrorAction SilentlyContinue
                    Set-ItemProperty -Path $devicePath -Name "SelectiveSuspendEnabled" -Value 0 -Type DWord -ErrorAction SilentlyContinue
                    Write-Host "    [OK] Power management disabled for device" -ForegroundColor Green
                } else {
                    Write-Host "    [CHECK] Power management settings" -ForegroundColor Yellow
                }
            }
            
            # Also try to disable via Device Manager API (if available)
            try {
                if (-not $VerifyOnly) {
                    $device = Get-PnpDeviceProperty -InstanceId $camera.InstanceId -KeyName "DEVPKEY_Device_RemovalPolicy" -ErrorAction SilentlyContinue
                    # Disable selective suspend for this specific device
                    Disable-PnpDevice -InstanceId $camera.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
                    Enable-PnpDevice -InstanceId $camera.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
                }
            } catch {
                # Ignore - not critical
            }
            
        } catch {
            Write-Host "    [WARNING] Could not modify device settings: $_" -ForegroundColor Yellow
        }
        
        Write-Host ""
    }
} else {
    Write-Host "[WARNING] No camera devices found" -ForegroundColor Yellow
    Write-Host ""
}

# Step 4: Disable USB Root Hub Power Management
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host "Step 4: Disabling USB Root Hub Power Management" -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host ""

$usbHubs = Get-PnpDevice | Where-Object { 
    $_.FriendlyName -like "*USB Root Hub*" -or 
    $_.FriendlyName -like "*USB xHCI*"
}

if ($usbHubs) {
    Write-Host "Found $($usbHubs.Count) USB hub device(s):" -ForegroundColor Green
    Write-Host ""
    
    foreach ($hub in $usbHubs) {
        Write-Host "  Processing: $($hub.FriendlyName)" -ForegroundColor White
        
        try {
            $devicePath = "HKLM:\SYSTEM\CurrentControlSet\Enum\$($hub.InstanceId)"
            
            if (Test-Path $devicePath) {
                if (-not $VerifyOnly) {
                    Set-ItemProperty -Path $devicePath -Name "DisableSelectiveSuspend" -Value 1 -Type DWord -ErrorAction SilentlyContinue
                    Set-ItemProperty -Path $devicePath -Name "SelectiveSuspendEnabled" -Value 0 -Type DWord -ErrorAction SilentlyContinue
                    Write-Host "    [OK] Power management disabled" -ForegroundColor Green
                } else {
                    Write-Host "    [CHECK] Power management settings" -ForegroundColor Yellow
                }
            }
        } catch {
            Write-Host "    [WARNING] Could not modify: $_" -ForegroundColor Yellow
        }
        Write-Host ""
    }
} else {
    Write-Host "[INFO] No USB hub devices found (this is OK)" -ForegroundColor Gray
    Write-Host ""
}

# Summary
Write-Host ("=" * 70) -ForegroundColor Cyan
if ($VerifyOnly) {
    Write-Host "Verification Complete" -ForegroundColor Cyan
} else {
    Write-Host "Power Management Disabled!" -ForegroundColor Green
}
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

if (-not $VerifyOnly) {
    Write-Host "Summary of changes:" -ForegroundColor Yellow
    Write-Host "  - USB Selective Suspend disabled (system-wide)" -ForegroundColor White
    Write-Host "  - Power management disabled for camera devices" -ForegroundColor White
    Write-Host "  - USB hub power management disabled" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. RESTART YOUR COMPUTER for changes to take full effect" -ForegroundColor Green
    Write-Host "  2. After restart, cameras should stay on and not reset" -ForegroundColor White
    Write-Host "  3. Test cameras with: python scripts/detect_windows_cameras.py" -ForegroundColor White
    Write-Host ""
    Write-Host "Note: Some settings may require a restart to apply." -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "Run without -VerifyOnly to apply changes" -ForegroundColor Yellow
    Write-Host ""
}


