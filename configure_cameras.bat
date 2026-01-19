@echo off
echo ============================================================
echo Camera Configuration Wizard
echo ============================================================
echo.

if not exist .venv (
    echo Virtual environment not found. Please run setup_env.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python scripts/configure_cameras.py

if %errorlevel% neq 0 (
    echo.
    echo Configuration failed or was cancelled.
    pause
    exit /b 1
)

echo.
echo Configuration complete!
pause
