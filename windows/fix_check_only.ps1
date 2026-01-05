#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Check camera status and provide fix instructions (no admin required)
#>

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Camera Status Check" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Check phantom devices
Write-Host "Checking for phantom camera devices..." -ForegroundColor Yellow
Write-Host ""

$phantomCameras = Get-PnpDevice | Where-Object { 
    ($_.FriendlyName -like "*HD USB Camera*" -or 
     $_.FriendlyName -like "*USB Camera*" -or
     $_.FriendlyName -like "*OBSBOT*" -or
     $_.FriendlyName -like "*StreamCamera*") -and 
    $_.Problem -eq 24  # CM_PROB_PHANTOM
}

if ($phantomCameras) {
    Write-Host "[WARNING] Found $($phantomCameras.Count) phantom camera device(s):" -ForegroundColor Yellow
    Write-Host ""
    foreach ($camera in $phantomCameras) {
        Write-Host "  - $($camera.FriendlyName)" -ForegroundColor Red
        Write-Host "    Status: $($camera.Status) (Problem Code: CM_PROB_PHANTOM)" -ForegroundColor Gray
        Write-Host "    Instance ID: $($camera.InstanceId)" -ForegroundColor Gray
        Write-Host ""
    }
    Write-Host "These should be removed (requires Admin rights)" -ForegroundColor Yellow
} else {
    Write-Host "[OK] No phantom camera devices found" -ForegroundColor Green
}
Write-Host ""

# Check working cameras
Write-Host "Checking working cameras..." -ForegroundColor Yellow
Write-Host ""

$workingCameras = Get-PnpDevice | Where-Object { 
    ($_.FriendlyName -like "*HD USB Camera*" -or 
     $_.FriendlyName -like "*HP HD Camera*" -or
     $_.FriendlyName -like "*HP IR Camera*") -and 
    $_.Status -eq "OK"
}

if ($workingCameras) {
    Write-Host "[OK] Found $($workingCameras.Count) working camera(s):" -ForegroundColor Green
    Write-Host ""
    foreach ($camera in $workingCameras) {
        Write-Host "  - $($camera.FriendlyName) [OK]" -ForegroundColor Green
        Write-Host "    Instance ID: $($camera.InstanceId)" -ForegroundColor Gray
    }
} else {
    Write-Host "[WARNING] No working cameras found" -ForegroundColor Red
}
Write-Host ""

# Summary and instructions
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "To Fix Issues:" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

if ($phantomCameras) {
    Write-Host "1. Remove phantom devices (requires Admin):" -ForegroundColor Yellow
    Write-Host "   - Right-click 'RUN_FIX_AS_ADMIN.bat' and select 'Run as administrator'" -ForegroundColor White
    Write-Host "   OR" -ForegroundColor Gray
    Write-Host "   - Open PowerShell as Administrator" -ForegroundColor White
    Write-Host "   - Run: .\windows\fix_all_camera_issues.ps1" -ForegroundColor White
    Write-Host ""
}

Write-Host "2. If cameras still don't work:" -ForegroundColor Yellow
Write-Host "   - Open Device Manager (Win+X, then M)" -ForegroundColor White
Write-Host "   - Expand 'Cameras'" -ForegroundColor White
Write-Host "   - Right-click each working camera" -ForegroundColor White
Write-Host "   - Select 'Disable device', wait 5 seconds" -ForegroundColor White
Write-Host "   - Right-click again, select 'Enable device'" -ForegroundColor White
Write-Host ""
Write-Host "3. Check Windows Privacy Settings:" -ForegroundColor Yellow
Write-Host "   - Settings > Privacy & Security > Camera" -ForegroundColor White
Write-Host "   - Turn ON 'Camera access'" -ForegroundColor White
Write-Host "   - Turn ON 'Let desktop apps access your camera'" -ForegroundColor White
Write-Host ""
Write-Host "4. Test cameras:" -ForegroundColor Yellow
Write-Host "   python scripts/detect_windows_cameras.py" -ForegroundColor White
Write-Host ""



