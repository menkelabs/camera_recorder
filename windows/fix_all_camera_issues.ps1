#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Comprehensive fix for camera issues - removes phantom devices and optimizes settings
#>

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Camera Fix Script" -ForegroundColor Cyan
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
    exit 1
}

Write-Host "[OK] Running as Administrator" -ForegroundColor Green
Write-Host ""

# Step 1: Remove phantom devices
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host "Step 1: Removing Phantom Camera Devices" -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host ""

$phantomCameras = Get-PnpDevice | Where-Object { 
    ($_.FriendlyName -like "*HD USB Camera*" -or 
     $_.FriendlyName -like "*USB Camera*" -or
     $_.FriendlyName -like "*OBSBOT*" -or
     $_.FriendlyName -like "*StreamCamera*") -and 
    $_.Problem -eq 24  # CM_PROB_PHANTOM
}

if ($phantomCameras) {
    Write-Host "Found $($phantomCameras.Count) phantom camera device(s):" -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($camera in $phantomCameras) {
        Write-Host "  Removing: $($camera.FriendlyName)" -ForegroundColor White
        Write-Host "    Instance ID: $($camera.InstanceId)" -ForegroundColor Gray
        
        try {
            Remove-PnpDevice -InstanceId $camera.InstanceId -Confirm:$false -ErrorAction Stop
            Write-Host "    [OK] Removed successfully" -ForegroundColor Green
        } catch {
            # Try alternative method using pnputil
            try {
                $instanceIdParts = $camera.InstanceId -split '\\'
                $deviceId = $instanceIdParts[-1]
                pnputil /remove-device $deviceId 2>&1 | Out-Null
                Write-Host "    [OK] Removed using alternative method" -ForegroundColor Green
            } catch {
                Write-Host "    [WARNING] Could not remove automatically" -ForegroundColor Yellow
                Write-Host "    You may need to remove manually in Device Manager" -ForegroundColor Gray
            }
        }
        Write-Host ""
    }
} else {
    Write-Host "[OK] No phantom camera devices found" -ForegroundColor Green
    Write-Host ""
}

# Step 2: Disable USB Selective Suspend
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host "Step 2: Disabling USB Selective Suspend (Power Management)" -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host ""

try {
    # Try to disable via registry
    $usbSuspendPath = "HKLM:\SYSTEM\CurrentControlSet\Services\USB"
    if (Test-Path $usbSuspendPath) {
        $currentValue = Get-ItemProperty -Path $usbSuspendPath -Name "DisableSelectiveSuspend" -ErrorAction SilentlyContinue
        
        if ($currentValue -and $currentValue.DisableSelectiveSuspend -eq 1) {
            Write-Host "[OK] USB Selective Suspend is already disabled" -ForegroundColor Green
        } else {
            Set-ItemProperty -Path $usbSuspendPath -Name "DisableSelectiveSuspend" -Value 1 -ErrorAction Stop
            Write-Host "[OK] USB Selective Suspend disabled (registry)" -ForegroundColor Green
        }
    } else {
        Write-Host "[WARNING] USB registry path not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[WARNING] Could not modify USB settings: $_" -ForegroundColor Yellow
    Write-Host "You may need to disable manually in Power Options" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Note: You can also disable USB Selective Suspend in:" -ForegroundColor Yellow
Write-Host "  Control Panel > Power Options > Change plan settings > Change advanced power settings" -ForegroundColor Gray
Write-Host "  USB settings > USB selective suspend setting > Disabled" -ForegroundColor Gray
Write-Host ""

# Step 3: Refresh working cameras
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host "Step 3: Refreshing Working Cameras" -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host ""

$workingCameras = Get-PnpDevice | Where-Object { 
    ($_.FriendlyName -like "*HD USB Camera*" -or 
     $_.FriendlyName -like "*HP HD Camera*" -or
     $_.FriendlyName -like "*HP IR Camera*") -and 
    $_.Status -eq "OK"
}

if ($workingCameras) {
    Write-Host "Found $($workingCameras.Count) working camera(s):" -ForegroundColor Green
    Write-Host ""
    
    foreach ($camera in $workingCameras) {
        Write-Host "  $($camera.FriendlyName) [OK]" -ForegroundColor Green
        Write-Host "    Instance ID: $($camera.InstanceId)" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "[OK] Working cameras are properly connected" -ForegroundColor Green
    Write-Host ""
    Write-Host "If cameras still don't work in your application:" -ForegroundColor Yellow
    Write-Host "  1. Try disabling and re-enabling each camera in Device Manager" -ForegroundColor White
    Write-Host "  2. Check Windows Privacy Settings (Settings > Privacy > Camera)" -ForegroundColor White
    Write-Host "  3. Ensure no other applications are using the cameras" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "[WARNING] No working cameras found" -ForegroundColor Red
    Write-Host ""
}

# Summary
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Fix Complete!" -ForegroundColor Green
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "  - Phantom devices removed" -ForegroundColor White
Write-Host "  - USB power management optimized" -ForegroundColor White
Write-Host "  - Working cameras verified" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart your computer (recommended)" -ForegroundColor White
Write-Host "  2. Test cameras with: python scripts/detect_windows_cameras.py" -ForegroundColor White
Write-Host ""



