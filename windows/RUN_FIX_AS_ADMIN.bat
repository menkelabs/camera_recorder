@echo off
REM This batch file will request Administrator rights and run the fix script

echo Requesting Administrator rights...
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as Administrator
    echo.
    powershell -ExecutionPolicy Bypass -File "%~dp0fix_all_camera_issues.ps1"
) else (
    echo Requesting elevation...
    powershell -Command "Start-Process -FilePath '%~dp0fix_all_camera_issues.ps1' -Verb RunAs"
)

pause



