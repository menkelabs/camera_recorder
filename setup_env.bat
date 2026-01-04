@echo off
echo ============================================================
echo Dual Camera Recorder - Environment Setup
echo ============================================================
echo.

echo Checking for Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo   Found Python
    python --version
    set PYTHON_CMD=python
    goto :create_venv
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    echo   Found Python (py launcher)
    py --version
    set PYTHON_CMD=py
    goto :create_venv
)

echo   Python not found!
echo.
echo Please install Python from https://www.python.org/downloads/
echo Make sure to check 'Add Python to PATH' during installation.
echo.
pause
exit /b 1

:create_venv
echo.
echo Creating virtual environment...
if exist .venv (
    echo Virtual environment already exists.
    set /p RECREATE="Do you want to recreate it? (y/n): "
    if /i "%RECREATE%"=="y" (
        rmdir /s /q .venv
    ) else (
        goto :activate_venv
    )
)

%PYTHON_CMD% -m venv .venv
if %errorlevel% neq 0 (
    echo   Failed to create virtual environment!
    pause
    exit /b 1
)
echo   Virtual environment created

:activate_venv
echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo   Failed to activate virtual environment!
    pause
    exit /b 1
)
echo   Virtual environment activated

echo.
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

echo.
echo Installing dependencies...
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo   requirements.txt not found, installing basic packages...
    pip install opencv-python numpy mediapipe
)

if %errorlevel% neq 0 (
    echo   Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Setup Complete!
echo.
echo You can now run:
echo   python debug_recorder.py
echo   python test_cameras.py
echo   python dual_camera_recorder.py
echo ============================================================
echo.
pause

