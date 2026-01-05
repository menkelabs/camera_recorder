#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test cameras with Python to see which ones work
#>

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Testing Cameras with Python" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

Write-Host "Running camera detection script..." -ForegroundColor Yellow
Write-Host ""

try {
    python scripts/detect_windows_cameras.py
} catch {
    Write-Host "[ERROR] Could not run Python script: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure Python is installed and in PATH" -ForegroundColor Yellow
    Write-Host ""
}



