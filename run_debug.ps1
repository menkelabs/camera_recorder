# Start SwingLab using the project venv (explicit Python path).

Write-Host "Activating virtual environment..." -ForegroundColor Yellow

if (-not (Test-Path ".venv")) {
    Write-Host "Virtual environment not found! Run setup_env.ps1 or python scripts/setup_wizard.py first." -ForegroundColor Red
    exit 1
}

$pythonExe = Join-Path (Get-Location) ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "Python not found in virtual environment!" -ForegroundColor Red
    Write-Host "Run setup_env.ps1 or python scripts/setup_wizard.py first." -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting SwingLab..." -ForegroundColor Yellow
Write-Host "Using Python: $pythonExe" -ForegroundColor Cyan
Write-Host ""

& $pythonExe "scripts\start_swinglab.py" @args
