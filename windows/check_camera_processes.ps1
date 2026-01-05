#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Check for processes that might be using cameras
    
.DESCRIPTION
    Lists processes that commonly use cameras and could prevent other apps
    from accessing them. Windows cameras can typically only be accessed by
    one application at a time.
#>

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Camera Process Check" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# List of processes that commonly use cameras
$cameraProcesses = @(
    "Camera",
    "WindowsCamera",
    "msedge",
    "chrome",
    "firefox",
    "obs64",
    "obs32",
    "zoom",
    "Zoom",
    "Teams",
    "lync",
    "skype",
    "Skype",
    "Discord",
    "discord",
    "WhatsApp",
    "WhatsAppDesktop",
    "viber",
    "Viber",
    "FaceTime",
    "Webex",
    "WebexMTA",
    "BlueJeans",
    "gotomeeting",
    "slack",
    "Snap Camera",
    "ManyCam",
    "XSplit",
    "Wirecast",
    "ffmpeg",
    "python"  # Python apps (like OpenCV)
)

Write-Host "Scanning for camera-using processes..." -ForegroundColor Yellow
Write-Host ""

$foundProcesses = @()
$allProcesses = Get-Process | Select-Object ProcessName, Id, Path

foreach ($procName in $cameraProcesses) {
    $procs = $allProcesses | Where-Object { $_.ProcessName -like "*$procName*" }
    if ($procs) {
        foreach ($proc in $procs) {
            $foundProcesses += $proc
            Write-Host "  [FOUND] $($proc.ProcessName) (PID: $($proc.Id))" -ForegroundColor Red
            if ($proc.Path) {
                Write-Host "    Path: $($proc.Path)" -ForegroundColor Gray
            }
        }
    }
}

Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan

if ($foundProcesses.Count -eq 0) {
    Write-Host "[OK] No common camera-using processes found" -ForegroundColor Green
    Write-Host ""
    Write-Host "Note: Some processes might still be using cameras indirectly." -ForegroundColor Yellow
} else {
    Write-Host "[WARNING] Found $($foundProcesses.Count) process(es) that might be using cameras" -ForegroundColor Red
    Write-Host ""
    Write-Host "These processes could prevent your application from accessing cameras." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To close a process, use:" -ForegroundColor Yellow
    Write-Host "  Stop-Process -Id <PID>" -ForegroundColor White
    Write-Host ""
    Write-Host "Or close the application normally." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Example commands to close found processes:" -ForegroundColor Cyan
    foreach ($proc in $foundProcesses) {
        Write-Host "  Stop-Process -Id $($proc.Id)  # $($proc.ProcessName)" -ForegroundColor Gray
    }
}

Write-Host ""

