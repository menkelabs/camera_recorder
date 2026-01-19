# PowerShell script to run the Qt Dashboard GUI

# Activate virtual environment
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & .venv\Scripts\Activate.ps1
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    & venv\Scripts\Activate.ps1
}

# Add current directory to PYTHONPATH
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"

# Run the dashboard
Write-Host "Starting Dashboard..." -ForegroundColor Green
python scripts/dashboard_gui_qt.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Dashboard exited with error code $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
}
