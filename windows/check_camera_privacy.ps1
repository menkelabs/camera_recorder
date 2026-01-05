#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Check Windows camera privacy settings that may block camera access
    
.DESCRIPTION
    This script checks Windows privacy settings that can prevent applications
    from accessing cameras. It checks:
    - Camera privacy settings (Settings > Privacy > Camera)
    - Registry values for camera access
    - Whether cameras are allowed for desktop apps
#>

Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Windows Camera Privacy Settings Check" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""

$issues = @()

# Check Camera Privacy Setting in Registry
Write-Host "Checking Camera Privacy Settings..." -ForegroundColor Yellow

$cameraPrivacyPath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam"

if (Test-Path $cameraPrivacyPath) {
    $value = Get-ItemProperty -Path $cameraPrivacyPath -Name "Value" -ErrorAction SilentlyContinue
    if ($value) {
        Write-Host "  Camera Privacy Registry Value: $($value.Value)" -ForegroundColor $(if ($value.Value -eq "Allow") { "Green" } else { "Red" })
        if ($value.Value -ne "Allow") {
            $issues += "Camera privacy setting is not set to 'Allow' (current: $($value.Value))"
        }
    } else {
        Write-Host "  Camera Privacy Registry Value: Not set (defaults to Deny)" -ForegroundColor Red
        $issues += "Camera privacy registry value is not set (may default to Deny)"
    }
} else {
    Write-Host "  Camera Privacy Registry Path: Not found" -ForegroundColor Yellow
    $issues += "Camera privacy registry path not found (may need to access Settings)"
}

# Check for NonPackaged app access (desktop apps)
Write-Host ""
Write-Host "Checking NonPackaged App Access (Desktop Apps)..." -ForegroundColor Yellow

$nonPackagedPath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam\NonPackaged"
if (Test-Path $nonPackagedPath) {
    # Check if there are any entries allowing desktop apps
    $allowedApps = Get-ChildItem -Path $nonPackagedPath -ErrorAction SilentlyContinue | Where-Object {
        $appValue = Get-ItemProperty -Path $_.PSPath -Name "Value" -ErrorAction SilentlyContinue
        $appValue -and $appValue.Value -eq "Allow"
    }
    
    if ($allowedApps) {
        Write-Host "  Found $($allowedApps.Count) allowed desktop app(s)" -ForegroundColor Green
    } else {
        Write-Host "  No desktop apps explicitly allowed" -ForegroundColor Yellow
        Write-Host "  (Python/OpenCV apps may need explicit permission)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  NonPackaged registry path not found" -ForegroundColor Yellow
}

# Check Windows Settings via Registry (alternative method)
Write-Host ""
Write-Host "Checking Additional Camera Settings..." -ForegroundColor Yellow

$cameraSettingPath = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\webcam"
$denyPath = Join-Path $cameraSettingPath "Deny"
$allowPath = Join-Path $cameraSettingPath "Allow"

if (Test-Path $denyPath) {
    $deniedApps = Get-ChildItem -Path $denyPath -ErrorAction SilentlyContinue
    if ($deniedApps) {
        Write-Host "  Found $($deniedApps.Count) denied application(s)" -ForegroundColor Yellow
    }
}

# Summary
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan

if ($issues.Count -eq 0) {
    Write-Host "✓ No obvious privacy setting issues found" -ForegroundColor Green
    Write-Host ""
    Write-Host "If cameras still don`'t work, try:" -ForegroundColor Yellow
    Write-Host '  1. Open Settings > Privacy & Security > Camera' -ForegroundColor White
    Write-Host "  2. Ensure 'Camera access' is ON" -ForegroundColor White
    Write-Host '  3. Ensure "Let desktop apps access your camera" is ON' -ForegroundColor White
    Write-Host "  4. Restart your computer after changing settings" -ForegroundColor White
} else {
    Write-Host "⚠ Found $($issues.Count) potential issue(s):" -ForegroundColor Red
    foreach ($issue in $issues) {
        Write-Host "  - $issue" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "To fix:" -ForegroundColor Yellow
    Write-Host "  1. Press Windows Key + I to open Settings" -ForegroundColor White
    Write-Host '  2. Go to Privacy & Security > Camera' -ForegroundColor White
    Write-Host '  3. Turn ON Camera access' -ForegroundColor White
    Write-Host '  4. Turn ON Let desktop apps access your camera' -ForegroundColor White
    Write-Host '  5. Restart your computer' -ForegroundColor White
}

Write-Host ""

