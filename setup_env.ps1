# PowerShell script to set up the virtual environment and install dependencies

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Dual Camera Recorder - Environment Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is available
Write-Host "Checking for Python..." -ForegroundColor Yellow
$pythonCmd = $null

# Try python command
$testResult = & python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    $pythonCmd = "python"
    Write-Host "  Found Python: python" -ForegroundColor Green
    Write-Host "  Version: $testResult" -ForegroundColor Green
}

# Try py command if python didn't work
if (-not $pythonCmd) {
    try {
        $testResult = & py --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = "py"
            Write-Host "  Found Python: py" -ForegroundColor Green
            Write-Host "  Version: $testResult" -ForegroundColor Green
        }
    } catch {
        # py command not available, continue
    }
}

if (-not $pythonCmd) {
    Write-Host "  Python not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installing Python, run this script again." -ForegroundColor Yellow
    exit 1
}

# Check if .venv already exists
if (Test-Path ".venv") {
    Write-Host ""
    Write-Host "Virtual environment already exists." -ForegroundColor Yellow
    $response = Read-Host "Do you want to recreate it? (y/n)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "Removing existing .venv..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force .venv
    } else {
        Write-Host "Using existing .venv" -ForegroundColor Green
    }
}

# Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host ""
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    & $pythonCmd -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Failed to create virtual environment!" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
$activateScript = ".venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
    Write-Host "  Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "  Activation script not found!" -ForegroundColor Red
    exit 1
}

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Yellow
& python -m pip install --upgrade pip --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "  pip upgraded" -ForegroundColor Green
}

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    & pip install -r requirements.txt
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "  Failed to install dependencies!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  requirements.txt not found, installing basic packages..." -ForegroundColor Yellow
    & pip install opencv-python numpy mediapipe
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Basic packages installed" -ForegroundColor Green
    }
}

# Verify installation
Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Yellow
$allGood = $true

$result = & python -c "import cv2; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  cv2 OK" -ForegroundColor Green
} else {
    Write-Host "  cv2 FAILED" -ForegroundColor Red
    $allGood = $false
}

$result = & python -c "import numpy; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  numpy OK" -ForegroundColor Green
} else {
    Write-Host "  numpy FAILED" -ForegroundColor Red
    $allGood = $false
}

$result = & python -c "import mediapipe; print('OK')" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  mediapipe OK" -ForegroundColor Green
} else {
    Write-Host "  mediapipe FAILED" -ForegroundColor Red
    $allGood = $false
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "Setup Complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run:" -ForegroundColor Yellow
    Write-Host "  python debug_recorder.py" -ForegroundColor Cyan
    Write-Host "  python test_cameras.py" -ForegroundColor Cyan
    Write-Host "  python dual_camera_recorder.py" -ForegroundColor Cyan
} else {
    Write-Host "Setup completed with errors. Please check the output above." -ForegroundColor Yellow
}
Write-Host "============================================================" -ForegroundColor Cyan
