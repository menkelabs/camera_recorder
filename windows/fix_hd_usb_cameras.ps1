#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Fix HD USB Camera devices that were working but stopped
    
.DESCRIPTION
    This script helps diagnose and fix HD USB Camera devices that were
    working earlier but have stopped functioning. It checks:
    - Device status in Device Manager
    - Driver issues
    - USB power management
    - Device properties
    
.PARAMETER Fix
    Attempt automatic fixes (requires Administrator rights)
#>

param(
    [switch]$Fix
)

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "HD USB Camera Diagnostic and Fix Tool" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Get all HD USB Camera devices
Write-Host "Scanning for HD USB Camera devices..." -ForegroundColor Yellow
Write-Host ""

$hdCameras = Get-PnpDevice | Where-Object { $_.FriendlyName -like "*HD USB Camera*" }

if ($hdCameras) {
    Write-Host "Found $($hdCameras.Count) HD USB Camera device(s):" -ForegroundColor Green
    Write-Host ""
    
    $index = 1
    foreach ($camera in $hdCameras) {
        $status = $camera.Status
        $statusInfo = $camera.StatusInfo
        $instanceId = $camera.InstanceId
        $problem = $camera.Problem
        
        Write-Host "Camera $index : $($camera.FriendlyName)" -ForegroundColor White
        Write-Host "  Instance ID: $instanceId" -ForegroundColor Gray
        Write-Host "  Status: $status" -ForegroundColor $(if ($status -eq "OK") { "Green" } else { "Red" })
        
        if ($problem -and $problem -ne 0) {
            Write-Host "  Problem Code: $problem" -ForegroundColor Red
            
            # Decode common problem codes
            switch ($problem) {
                1 { Write-Host "    Meaning: CM_PROB_NOT_CONFIGURED - Device not configured" -ForegroundColor Yellow }
                10 { Write-Host "    Meaning: CM_PROB_FAILED_START - Device failed to start" -ForegroundColor Yellow }
                14 { Write-Host "    Meaning: CM_PROB_REINSTALL - Driver needs to be reinstalled" -ForegroundColor Yellow }
                22 { Write-Host "    Meaning: CM_PROB_DISABLED - Device is disabled" -ForegroundColor Yellow }
                24 { Write-Host "    Meaning: CM_PROB_PHANTOM - Device is no longer present (phantom)" -ForegroundColor Yellow }
                28 { Write-Host "    Meaning: CM_PROB_FAILED_INSTALL - Driver installation failed" -ForegroundColor Yellow }
                43 { Write-Host "    Meaning: CM_PROB_FAILED_POST_START - Device failed after starting" -ForegroundColor Yellow }
                default { Write-Host "    Unknown problem code" -ForegroundColor Yellow }
            }
        }
        
        # Get more details from Win32_PnPEntity
        try {
            $pnpDevice = Get-WmiObject -Class Win32_PnPEntity -Filter "InstanceId='$instanceId'" -ErrorAction SilentlyContinue
            if ($pnpDevice) {
                if ($pnpDevice.Status -ne $status) {
                    Write-Host "  WMI Status: $($pnpDevice.Status)" -ForegroundColor Gray
                }
            }
        } catch {
            # Ignore WMI errors
        }
        
        Write-Host ""
        $index++
    }
    
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "Recommended Fixes" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Step 1: Check if cameras are physically connected" -ForegroundColor Yellow
    Write-Host "  - Ensure both USB cameras are plugged in" -ForegroundColor White
    Write-Host "  - Try unplugging and reconnecting them" -ForegroundColor White
    Write-Host "  - Try different USB ports" -ForegroundColor White
    Write-Host ""
    
    Write-Host "Step 2: Disable USB Selective Suspend (Power Management)" -ForegroundColor Yellow
    Write-Host "  USB power management can cause cameras to stop working." -ForegroundColor White
    Write-Host "  To disable:" -ForegroundColor White
    Write-Host "  1. Control Panel > Power Options > Change plan settings" -ForegroundColor Gray
    Write-Host "  2. Change advanced power settings" -ForegroundColor Gray
    Write-Host "  3. USB settings > USB selective suspend setting > Disabled" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Step 3: Update/Reinstall Camera Drivers" -ForegroundColor Yellow
    Write-Host "  In Device Manager:" -ForegroundColor White
    Write-Host "  1. Right-click each HD USB Camera" -ForegroundColor Gray
    Write-Host "  2. Select 'Update driver'" -ForegroundColor Gray
    Write-Host "  3. Choose 'Search automatically for drivers'" -ForegroundColor Gray
    Write-Host "  OR" -ForegroundColor Gray
    Write-Host "  1. Right-click > 'Uninstall device'" -ForegroundColor Gray
    Write-Host "  2. Check 'Delete the driver software for this device'" -ForegroundColor Gray
    Write-Host "  3. Unplug and replug the USB camera" -ForegroundColor Gray
    Write-Host "  4. Windows will reinstall the driver" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Step 4: Check for Windows Updates" -ForegroundColor Yellow
    Write-Host "  Sometimes Windows updates can fix camera driver issues." -ForegroundColor White
    Write-Host ""
    
    Write-Host "Step 5: Restart Windows Camera Service (if applicable)" -ForegroundColor Yellow
    Write-Host "  Note: This may not apply to all camera types" -ForegroundColor White
    Write-Host ""
    
    # Check if there are processes using cameras
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "Checking for processes that might be using cameras..." -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host ""
    
    $cameraProcesses = @("Camera", "WindowsCamera", "msedge", "chrome", "firefox", "obs64", "obs32", "zoom", "Teams", "skype", "python")
    $foundProcesses = @()
    
    foreach ($procName in $cameraProcesses) {
        $procs = Get-Process -Name $procName -ErrorAction SilentlyContinue
        if ($procs) {
            foreach ($proc in $procs) {
                $foundProcesses += $proc
                Write-Host "  [FOUND] $($proc.ProcessName) (PID: $($proc.Id))" -ForegroundColor Red
            }
        }
    }
    
    if ($foundProcesses.Count -eq 0) {
        Write-Host "  [OK] No common camera-using processes found" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "  These processes might be using the cameras." -ForegroundColor Yellow
        Write-Host "  Close them before testing cameras." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "Quick Fix Script" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Would you like to try automatic fixes? (This will require Admin rights)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To run as Administrator:" -ForegroundColor White
    Write-Host "  1. Right-click PowerShell" -ForegroundColor Gray
    Write-Host "  2. Select 'Run as Administrator'" -ForegroundColor Gray
    Write-Host "  3. Run: .\windows\fix_hd_usb_cameras.ps1 -Fix" -ForegroundColor Gray
    Write-Host ""
    
} else {
    Write-Host "[WARNING] No HD USB Camera devices found in Device Manager" -ForegroundColor Red
    Write-Host ""
    Write-Host "This could mean:" -ForegroundColor Yellow
    Write-Host "  - Cameras are not connected" -ForegroundColor White
    Write-Host "  - Cameras are not being recognized by Windows" -ForegroundColor White
    Write-Host "  - Drivers are not installed" -ForegroundColor White
    Write-Host ""
    Write-Host "Try:" -ForegroundColor Yellow
    Write-Host "  1. Unplug and replug the USB cameras" -ForegroundColor White
    Write-Host "  2. Check Device Manager for 'Unknown devices'" -ForegroundColor White
    Write-Host "  3. Check USB ports and cables" -ForegroundColor White
}

Write-Host ""

# If -Fix parameter is provided, try to fix issues
if ($Fix) {
    Write-Host "Attempting automatic fixes..." -ForegroundColor Yellow
    Write-Host ""
    
    # Check if running as Administrator
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if (-not $isAdmin) {
        Write-Host "[ERROR] Administrator rights required for automatic fixes" -ForegroundColor Red
        Write-Host "Please run PowerShell as Administrator" -ForegroundColor Yellow
        exit 1
    }
    
    # Disable USB selective suspend via registry (requires admin)
    Write-Host "Disabling USB Selective Suspend..." -ForegroundColor Yellow
    try {
        $usbSuspendPath = "HKLM:\SYSTEM\CurrentControlSet\Services\USB"
        if (Test-Path $usbSuspendPath) {
            Set-ItemProperty -Path $usbSuspendPath -Name "DisableSelectiveSuspend" -Value 1 -ErrorAction SilentlyContinue
            Write-Host "  [OK] USB Selective Suspend disabled" -ForegroundColor Green
        }
    } catch {
        Write-Host "  [WARNING] Could not modify USB settings: $_" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Note: You may need to restart your computer for some changes to take effect." -ForegroundColor Yellow
    Write-Host ""
}

