# Quick script to activate venv and run debug script
# Uses explicit Python path to avoid path issues

Write-Host "Activating virtual environment..." -ForegroundColor Yellow

if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found! Run setup_env.ps1 first." -ForegroundColor Red
    exit 1
}

# Use explicit Python path to avoid path issues
$pythonExe = Join-Path (Get-Location) ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "Python not found in virtual environment!" -ForegroundColor Red
    Write-Host "Run setup_env.ps1 first to create it." -ForegroundColor Yellow
    exit 1
}

Write-Host "Running debug recorder..." -ForegroundColor Yellow
Write-Host "Using Python: $pythonExe" -ForegroundColor Cyan
Write-Host ""

& $pythonExe debug_recorder.py

