#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Check USB camera devices in Windows Device Manager
    
.DESCRIPTION
    This script enumerates USB camera devices and checks their status,
    driver information, and potential issues.
#>

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "USB Camera Device Check" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Get all camera devices using WMI
Write-Host "Enumerating Camera Devices..." -ForegroundColor Yellow
Write-Host ""

try {
    $cameras = Get-PnpDevice -Class Camera -ErrorAction SilentlyContinue
    
    if ($cameras) {
        $workingCameras = @()
        $problemCameras = @()
        
        foreach ($camera in $cameras) {
            $status = $camera.Status
            $friendlyName = $camera.FriendlyName
            $instanceId = $camera.InstanceId
            $problem = $camera.Problem
            $statusInfo = $camera.StatusInfo
            
            Write-Host "Device: $friendlyName" -ForegroundColor White
            Write-Host "  Status: $status" -ForegroundColor $(if ($status -eq "OK") { "Green" } else { "Red" })
            Write-Host "  Instance ID: $instanceId" -ForegroundColor Gray
            
            if ($problem -and $problem -ne 0) {
                Write-Host "  Problem Code: $problem" -ForegroundColor Red
                $problemCameras += $camera
            } else {
                $workingCameras += $camera
            }
            
            # Get more details using Win32_PnPEntity
            $pnpDevice = Get-WmiObject -Class Win32_PnPEntity -Filter "InstanceId='$instanceId'" -ErrorAction SilentlyContinue
            if ($pnpDevice) {
                if ($pnpDevice.PNPClass -eq "Camera") {
                    Write-Host "  Type: Camera (PNP Class)" -ForegroundColor Green
                }
                if ($pnpDevice.Service) {
                    Write-Host "  Driver Service: $($pnpDevice.Service)" -ForegroundColor Gray
                }
            }
            
            Write-Host ""
        }
        
        Write-Host ("=" * 70) -ForegroundColor Cyan
        Write-Host "Summary" -ForegroundColor Cyan
        Write-Host ("=" * 70) -ForegroundColor Cyan
        Write-Host "Total Cameras Found: $($cameras.Count)" -ForegroundColor White
        Write-Host "Working: $($workingCameras.Count)" -ForegroundColor $(if ($workingCameras.Count -gt 0) { "Green" } else { "Red" })
        Write-Host "With Issues: $($problemCameras.Count)" -ForegroundColor $(if ($problemCameras.Count -eq 0) { "Green" } else { "Red" })
        Write-Host ""
        
        if ($problemCameras.Count -gt 0) {
            Write-Host "⚠ Cameras with problems found:" -ForegroundColor Red
            foreach ($cam in $problemCameras) {
                Write-Host "  - $($cam.FriendlyName) (Problem Code: $($cam.Problem))" -ForegroundColor Red
            }
            Write-Host ""
            Write-Host "To fix camera issues:" -ForegroundColor Yellow
            Write-Host "  1. Open Device Manager (Win+X, then M)" -ForegroundColor White
            Write-Host "  2. Expand 'Cameras' or 'Imaging devices'" -ForegroundColor White
            Write-Host "  3. Right-click the problematic camera" -ForegroundColor White
            Write-Host "  4. Select 'Update driver' or 'Uninstall device'" -ForegroundColor White
            Write-Host "  5. If uninstalling, disconnect and reconnect the USB camera" -ForegroundColor White
        }
        
        if ($workingCameras.Count -eq 0) {
            Write-Host "⚠ No working cameras found!" -ForegroundColor Red
            Write-Host ""
            Write-Host "Troubleshooting steps:" -ForegroundColor Yellow
            Write-Host "  1. Disconnect and reconnect USB cameras" -ForegroundColor White
            Write-Host "  2. Try different USB ports" -ForegroundColor White
            Write-Host "  3. Check if cameras work on another computer" -ForegroundColor White
            Write-Host "  4. Update camera drivers in Device Manager" -ForegroundColor White
        }
    } else {
        Write-Host "⚠ No camera devices found in Device Manager" -ForegroundColor Red
        Write-Host ""
        Write-Host "This could mean:" -ForegroundColor Yellow
        Write-Host "  - Cameras are not connected" -ForegroundColor White
        Write-Host "  - Cameras are not recognized by Windows" -ForegroundColor White
        Write-Host "  - Drivers are not installed" -ForegroundColor White
        Write-Host ""
        Write-Host "Try:" -ForegroundColor Yellow
        Write-Host "  1. Disconnect and reconnect USB cameras" -ForegroundColor White
        Write-Host "  2. Check Device Manager for unknown devices" -ForegroundColor White
        Write-Host "  3. Install camera drivers from manufacturer website" -ForegroundColor White
    }
} catch {
    Write-Host "Error checking cameras: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Try running as Administrator if this persists" -ForegroundColor Yellow
}

Write-Host ""

# Also check USB video devices
Write-Host "Checking USB Video Class (UVC) Devices..." -ForegroundColor Yellow
Write-Host ""

try {
    $uvcDevices = Get-PnpDevice | Where-Object { 
        $_.Class -eq "Camera" -or 
        $_.Class -eq "USB" -and $_.FriendlyName -like "*camera*" -or
        $_.FriendlyName -like "*webcam*" -or
        $_.FriendlyName -like "*USB Video*"
    }
    
    if ($uvcDevices) {
        Write-Host "Found $($uvcDevices.Count) USB video device(s):" -ForegroundColor Green
        foreach ($device in $uvcDevices) {
            Write-Host "  - $($device.FriendlyName) [$($device.Status)]" -ForegroundColor White
        }
    } else {
        Write-Host "No USB video devices found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not check USB video devices: $_" -ForegroundColor Yellow
}

Write-Host ""

