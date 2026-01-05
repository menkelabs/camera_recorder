#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Remove phantom HD USB Camera device from Device Manager
    
.DESCRIPTION
    This script helps remove phantom camera devices (CM_PROB_PHANTOM status)
    from Device Manager. Phantom devices are cameras that were disconnected
    but Windows still has them in the device list.
    
    Requires Administrator rights.
#>

param(
    [switch]$Force
)

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Remove Phantom HD USB Camera Device" -ForegroundColor Cyan
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

# Get phantom HD USB Camera devices
Write-Host "Scanning for phantom HD USB Camera devices..." -ForegroundColor Yellow
Write-Host ""

$phantomCameras = Get-PnpDevice | Where-Object { 
    $_.FriendlyName -like "*HD USB Camera*" -and 
    $_.Problem -eq 24  # CM_PROB_PHANTOM
}

if ($phantomCameras) {
    Write-Host "Found $($phantomCameras.Count) phantom HD USB Camera device(s):" -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($camera in $phantomCameras) {
        Write-Host "  - $($camera.FriendlyName)" -ForegroundColor White
        Write-Host "    Instance ID: $($camera.InstanceId)" -ForegroundColor Gray
        Write-Host "    Status: $($camera.Status) (Problem Code: $($camera.Problem))" -ForegroundColor Red
        Write-Host ""
    }
    
    if (-not $Force) {
        Write-Host "This will remove the phantom device(s) from Device Manager." -ForegroundColor Yellow
        Write-Host "Note: The device(s) are not physically connected, so this is safe." -ForegroundColor Yellow
        Write-Host ""
        $confirm = Read-Host "Continue? (Y/N)"
        if ($confirm -ne "Y" -and $confirm -ne "y") {
            Write-Host "Cancelled." -ForegroundColor Yellow
            exit 0
        }
        Write-Host ""
    }
    
    Write-Host "Removing phantom camera devices..." -ForegroundColor Yellow
    
    foreach ($camera in $phantomCameras) {
        try {
            Write-Host "  Removing $($camera.FriendlyName)..." -ForegroundColor White
            
            # Use PnPUtil or Remove-PnpDevice
            Remove-PnpDevice -InstanceId $camera.InstanceId -Confirm:$false -ErrorAction Stop
            
            Write-Host "    [OK] Removed successfully" -ForegroundColor Green
        } catch {
            Write-Host "    [ERROR] Failed to remove: $_" -ForegroundColor Red
            Write-Host ""
            Write-Host "    Try manually in Device Manager:" -ForegroundColor Yellow
            Write-Host "      1. Open Device Manager (Win+X, then M)" -ForegroundColor Gray
            Write-Host "      2. Expand 'Cameras'" -ForegroundColor Gray
            Write-Host "      3. Right-click the phantom camera" -ForegroundColor Gray
            Write-Host "      4. Select 'Uninstall device'" -ForegroundColor Gray
            Write-Host "      5. Check 'Delete the driver software for this device'" -ForegroundColor Gray
            Write-Host "      6. Click 'Uninstall'" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "Done!" -ForegroundColor Green
    Write-Host ""
    Write-Host "The phantom device(s) have been removed." -ForegroundColor Green
    Write-Host "If you reconnect the camera, Windows will reinstall it automatically." -ForegroundColor Yellow
    Write-Host ""
    
} else {
    Write-Host "[OK] No phantom HD USB Camera devices found" -ForegroundColor Green
    Write-Host ""
    Write-Host "All HD USB Camera devices are properly connected or have been removed." -ForegroundColor Yellow
    Write-Host ""
}



