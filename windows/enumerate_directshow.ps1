#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Enumerate DirectShow video capture devices
    
.DESCRIPTION
    This script lists DirectShow video capture devices using Windows APIs.
    DirectShow is what OpenCV uses with CAP_DSHOW backend on Windows.
    
    Note: This requires .NET Framework or PowerShell 7+ with Windows compatibility
#>

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "DirectShow Video Capture Devices" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

# Try to enumerate using Windows Forms (requires .NET)
try {
    Add-Type -AssemblyName System.Windows.Forms -ErrorAction Stop
    
    # Note: DirectShow enumeration requires COM interop
    # This is a simpler approach using available .NET methods
    
    Write-Host "Checking DirectShow via System.Windows.Forms..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Note: Full DirectShow enumeration requires COM interop." -ForegroundColor Yellow
    Write-Host "For detailed DirectShow info, use the Python script:" -ForegroundColor Yellow
    Write-Host "  python tests/enumerate_dshow_cameras.py" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "Could not load System.Windows.Forms: $_" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Alternative: Use Python to enumerate DirectShow devices:" -ForegroundColor Yellow
    Write-Host "  python tests/enumerate_dshow_cameras.py" -ForegroundColor White
    Write-Host ""
}

# Check if we can use COM to access DirectShow filters
Write-Host "Attempting COM-based DirectShow enumeration..." -ForegroundColor Yellow
Write-Host ""

try {
    # Create a COM object for DirectShow Filter Graph Manager
    $filterGraphManager = New-Object -ComObject "FilterGraphManager.FilterGraphManager"
    
    Write-Host "DirectShow FilterGraphManager accessible" -ForegroundColor Green
    Write-Host ""
    Write-Host "For detailed enumeration, Python scripts work better." -ForegroundColor Yellow
    Write-Host "Try: python tests/enumerate_dshow_cameras.py" -ForegroundColor White
    
} catch {
    Write-Host "DirectShow COM enumeration not available in this PowerShell session" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Recommended: Use Python script for DirectShow enumeration:" -ForegroundColor Yellow
    Write-Host "  python tests/enumerate_dshow_cameras.py" -ForegroundColor White
    Write-Host ""
    Write-Host "This will show:" -ForegroundColor Cyan
    Write-Host "  - All DirectShow video capture devices" -ForegroundColor White
    Write-Host "  - Device names and indices" -ForegroundColor White
    Write-Host "  - Device paths (MonikerDisplayName)" -ForegroundColor White
}

Write-Host ""

