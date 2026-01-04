# Script to help move the project to a better path

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Project Path Mover" -ForegroundColor Cyan
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""

$currentPath = Get-Location
Write-Host "Current location: $currentPath" -ForegroundColor Yellow
Write-Host ""

Write-Host "Suggested new locations:" -ForegroundColor Cyan
Write-Host "  1. C:\Users\jmjav\camera_recorder\" -ForegroundColor White
Write-Host "  2. C:\Projects\camera_recorder\" -ForegroundColor White
Write-Host "  3. C:\dev\camera_recorder\" -ForegroundColor White
Write-Host "  4. Custom path" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Select option (1-4) or 'q' to quit"

if ($choice -eq "q") {
    exit 0
}

$newPath = $null
switch ($choice) {
    "1" { $newPath = "C:\Users\jmjav\camera_recorder" }
    "2" { $newPath = "C:\Projects\camera_recorder" }
    "3" { $newPath = "C:\dev\camera_recorder" }
    "4" { 
        $customPath = Read-Host "Enter custom path"
        $newPath = $customPath
    }
    default {
        Write-Host "Invalid choice" -ForegroundColor Red
        exit 1
    }
}

if (-not $newPath) {
    Write-Host "Invalid path" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "New location: $newPath" -ForegroundColor Cyan
$confirm = Read-Host "Move project to this location? (y/n)"

if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Cancelled" -ForegroundColor Yellow
    exit 0
}

# Create destination directory
if (-not (Test-Path $newPath)) {
    New-Item -ItemType Directory -Path $newPath -Force | Out-Null
    Write-Host "Created directory: $newPath" -ForegroundColor Green
}

# Copy all files (excluding .venv if it exists, we'll recreate it)
Write-Host ""
Write-Host "Copying files..." -ForegroundColor Yellow

$excludeItems = @(".venv", "__pycache__", "*.pyc", ".git")

Get-ChildItem -Path $currentPath -File | ForEach-Object {
    $destFile = Join-Path $newPath $_.Name
    Copy-Item $_.FullName $destFile -Force
    Write-Host "  Copied: $($_.Name)" -ForegroundColor Green
}

Get-ChildItem -Path $currentPath -Directory | Where-Object { $_.Name -notin $excludeItems } | ForEach-Object {
    $destDir = Join-Path $newPath $_.Name
    Copy-Item $_.FullName $destDir -Recurse -Force
    Write-Host "  Copied directory: $($_.Name)" -ForegroundColor Green
}

Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "Files copied successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Navigate to: $newPath" -ForegroundColor Cyan
Write-Host "  2. Run: .\setup_env.ps1" -ForegroundColor Cyan
Write-Host "  3. Run: python debug_recorder.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "Old files are still at: $currentPath" -ForegroundColor Yellow
Write-Host "You can delete them after verifying the new location works." -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Cyan

