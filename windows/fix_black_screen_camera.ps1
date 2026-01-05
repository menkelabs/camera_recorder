#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Fix HD USB Camera that shows black screen (camera detected but no video)
    
.DESCRIPTION
    This script helps diagnose and fix cameras that are detected and open
    but show only a black screen. Common causes:
    - Camera is physically disconnected but still detected
    - USB power/connection issue
    - Driver needs refresh
    - Another process is using the camera
    - DirectShow filter issue
#>

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Fix Black Screen Camera Issue" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

Write-Host "Scanning for HD USB Camera devices..." -ForegroundColor Yellow
Write-Host ""

$hdCameras = Get-PnpDevice | Where-Object { $_.FriendlyName -like "*HD USB Camera*" } | Sort-Object InstanceId

if ($hdCameras) {
    Write-Host "Found $($hdCameras.Count) HD USB Camera device(s):" -ForegroundColor Green
    Write-Host ""
    
    $index = 1
    foreach ($camera in $hdCameras) {
        $status = $camera.Status
        $instanceId = $camera.InstanceId
        $problem = $camera.Problem
        
        Write-Host "Camera $index : $($camera.FriendlyName)" -ForegroundColor White
        Write-Host "  Status: $status" -ForegroundColor $(if ($status -eq "OK") { "Green" } else { "Red" })
        Write-Host "  Instance ID: $instanceId" -ForegroundColor Gray
        
        if ($problem -and $problem -ne 0) {
            Write-Host "  Problem Code: $problem" -ForegroundColor Red
        }
        Write-Host ""
        $index++
    }
    
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "Fix Steps for Black Screen Camera" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Step 1: Check Physical Connection" -ForegroundColor Yellow
    Write-Host "  - Unplug the USB camera that shows black screen" -ForegroundColor White
    Write-Host "  - Wait 10 seconds" -ForegroundColor White
    Write-Host "  - Plug it back in (try a different USB port if possible)" -ForegroundColor White
    Write-Host "  - Wait for Windows to recognize it" -ForegroundColor White
    Write-Host ""
    
    Write-Host "Step 2: Refresh Camera Driver (RECOMMENDED FIRST)" -ForegroundColor Yellow
    Write-Host "  In Device Manager:" -ForegroundColor White
    Write-Host "  1. Open Device Manager (Win+X, then M)" -ForegroundColor Gray
    Write-Host "  2. Expand 'Cameras'" -ForegroundColor Gray
    Write-Host "  3. Find the HD USB Camera showing black screen" -ForegroundColor Gray
    Write-Host "  4. Right-click it > 'Disable device'" -ForegroundColor Gray
    Write-Host "  5. Wait 10 seconds" -ForegroundColor Gray
    Write-Host "  6. Right-click again > 'Enable device'" -ForegroundColor Gray
    Write-Host "  7. Wait 10 seconds for it to reinitialize" -ForegroundColor Gray
    Write-Host ""
    
    if ($isAdmin) {
        Write-Host "Step 3: Try Automatic Driver Refresh" -ForegroundColor Yellow
        Write-Host "  Attempting to refresh the cameras..." -ForegroundColor White
        Write-Host ""
        
        foreach ($camera in $hdCameras) {
            Write-Host "  Refreshing: $($camera.FriendlyName)" -ForegroundColor White
            Write-Host "    Instance ID: $($camera.InstanceId)" -ForegroundColor Gray
            
            try {
                # Disable and re-enable the device
                Disable-PnpDevice -InstanceId $camera.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 3
                Enable-PnpDevice -InstanceId $camera.InstanceId -Confirm:$false -ErrorAction Stop
                Write-Host "    [OK] Device refreshed" -ForegroundColor Green
            } catch {
                Write-Host "    [WARNING] Could not refresh automatically: $_" -ForegroundColor Yellow
                Write-Host "    Please try manually in Device Manager (see Step 2)" -ForegroundColor Gray
            }
            Write-Host ""
        }
    } else {
        Write-Host "Step 3: Automatic Driver Refresh (Requires Admin)" -ForegroundColor Yellow
        Write-Host "  Run PowerShell as Administrator to enable automatic refresh" -ForegroundColor White
        Write-Host ""
    }
    
    Write-Host "Step 4: Reinstall Camera Driver (If Step 2 doesn't work)" -ForegroundColor Yellow
    Write-Host "  In Device Manager:" -ForegroundColor White
    Write-Host "  1. Right-click the HD USB Camera showing black screen" -ForegroundColor Gray
    Write-Host "  2. Select 'Uninstall device'" -ForegroundColor Gray
    Write-Host "  3. Check 'Delete the driver software for this device'" -ForegroundColor Gray
    Write-Host "  4. Click 'Uninstall'" -ForegroundColor Gray
    Write-Host "  5. Unplug the USB camera" -ForegroundColor Gray
    Write-Host "  6. Wait 10 seconds" -ForegroundColor Gray
    Write-Host "  7. Plug the USB camera back in" -ForegroundColor Gray
    Write-Host "  8. Windows will reinstall the driver automatically" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Step 5: Check USB Power Management" -ForegroundColor Yellow
    Write-Host "  USB power management can cause cameras to disconnect:" -ForegroundColor White
    Write-Host "  1. Control Panel > Power Options > Change plan settings" -ForegroundColor Gray
    Write-Host "  2. Change advanced power settings" -ForegroundColor Gray
    Write-Host "  3. USB settings > USB selective suspend setting > Disabled" -ForegroundColor Gray
    Write-Host "  4. Restart computer" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "Step 6: Check for Processes Using Camera" -ForegroundColor Yellow
    Write-Host "  Another application might be using the camera:" -ForegroundColor White
    
    $cameraProcesses = @("Camera", "WindowsCamera", "msedge", "chrome", "firefox", "obs64", "obs32", "zoom", "Teams", "skype", "python")
    $foundProcesses = @()
    
    foreach ($procName in $cameraProcesses) {
        $procs = Get-Process -Name $procName -ErrorAction SilentlyContinue
        if ($procs) {
            foreach ($proc in $procs) {
                $foundProcesses += $proc
                Write-Host "    [FOUND] $($proc.ProcessName) (PID: $($proc.Id))" -ForegroundColor Red
            }
        }
    }
    
    if ($foundProcesses.Count -eq 0) {
        Write-Host "    [OK] No common camera-using processes found" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "    Close these processes before testing the camera" -ForegroundColor Yellow
        Write-Host "    To close: Stop-Process -Id <PID>" -ForegroundColor Gray
    }
    Write-Host ""
    
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "Summary" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Black screen usually means:" -ForegroundColor Yellow
    Write-Host "  - Camera is physically disconnected but Windows still sees it" -ForegroundColor White
    Write-Host "  - USB connection is unstable (power/data issue)" -ForegroundColor White
    Write-Host "  - Driver needs to be refreshed" -ForegroundColor White
    Write-Host "  - Another application is locking the camera" -ForegroundColor White
    Write-Host ""
    Write-Host "Try Step 2 first (Disable/Enable in Device Manager) - this fixes most cases" -ForegroundColor Yellow
    Write-Host ""
    
} else {
    Write-Host "[WARNING] No HD USB Camera devices found" -ForegroundColor Red
    Write-Host ""
}

Write-Host ""



