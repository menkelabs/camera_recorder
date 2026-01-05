#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Comprehensive Windows camera diagnostic script
    
.DESCRIPTION
    This script runs multiple diagnostic checks to identify camera issues:
    - Camera privacy settings
    - USB device status
    - DirectShow enumeration
    - Processes using cameras
    - Registry settings
    
    Run this script first to get an overview of camera issues.
#>

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Windows Camera Diagnostic Tool" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Check Camera Privacy Settings
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host "1. Checking Camera Privacy Settings..." -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host ""

& "$scriptDir\check_camera_privacy.ps1"

Write-Host ""
Write-Host "Press any key to continue to next check..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# 2. Check USB Camera Devices
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host "2. Checking USB Camera Devices..." -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host ""

& "$scriptDir\check_usb_cameras.ps1"

Write-Host ""
Write-Host "Press any key to continue to next check..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# 3. Check for processes using cameras
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host "3. Checking for processes that might be using cameras..." -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host ""

$cameraProcesses = @("Camera", "WindowsCamera", "msedge", "chrome", "firefox", "obs64", "obs32", "zoom", "teams", "skype")

Write-Host "Checking for common camera-using applications..." -ForegroundColor Yellow
Write-Host ""

$foundProcesses = @()
foreach ($procName in $cameraProcesses) {
    $procs = Get-Process -Name $procName -ErrorAction SilentlyContinue
    if ($procs) {
        foreach ($proc in $procs) {
            Write-Host "  [WARNING] $($proc.ProcessName) is running (PID: $($proc.Id))" -ForegroundColor Red
            $foundProcesses += $proc
        }
    }
}

if ($foundProcesses.Count -eq 0) {
    Write-Host "  [OK] No common camera-using applications found running" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "  ⚠ Found $($foundProcesses.Count) process(es) that might be using cameras" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Recommendation: Close these applications before using cameras:" -ForegroundColor Yellow
    foreach ($proc in $foundProcesses) {
        Write-Host "    - $($proc.ProcessName) (PID: $($proc.Id))" -ForegroundColor White
        Write-Host "      To close: Stop-Process -Id $($proc.Id)" -ForegroundColor Gray
    }
}

Write-Host ""

# 4. Check Windows Camera Service
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host "4. Checking Windows Camera Service..." -ForegroundColor Yellow
Write-Host ("=" * 70) -ForegroundColor Yellow
Write-Host ""

$cameraService = Get-Service -Name "FrameServer" -ErrorAction SilentlyContinue
if ($cameraService) {
    Write-Host "Camera Frame Server Service Status: $($cameraService.Status)" -ForegroundColor $(if ($cameraService.Status -eq "Running") { "Green" } else { "Yellow" })
    if ($cameraService.Status -ne "Running") {
        Write-Host "  Service is not running. This is normal if no Windows Camera app is active." -ForegroundColor Yellow
    }
} else {
    Write-Host "Frame Server service not found (this is normal)" -ForegroundColor Yellow
}

Write-Host ""

# 5. Summary and Recommendations
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "DIAGNOSTIC SUMMARY" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Review the checks above for any issues" -ForegroundColor White
Write-Host "  2. Fix any privacy settings issues found" -ForegroundColor White
Write-Host "  3. Fix any USB device issues in Device Manager" -ForegroundColor White
Write-Host "  4. Close any applications using cameras" -ForegroundColor White
Write-Host "  5. Restart your computer after making changes" -ForegroundColor White
Write-Host "  6. Test cameras with: python scripts/detect_windows_cameras.py" -ForegroundColor White
Write-Host ""

Write-Host "Quick Fixes:" -ForegroundColor Yellow
Write-Host "  - Enable camera in Settings > Privacy > Camera" -ForegroundColor White
Write-Host "  - Enable 'Let desktop apps access your camera'" -ForegroundColor White
Write-Host "  - Update camera drivers in Device Manager" -ForegroundColor White
Write-Host "  - Disconnect and reconnect USB cameras" -ForegroundColor White
Write-Host ""

