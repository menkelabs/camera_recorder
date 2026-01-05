@echo off
REM This batch file will request Administrator rights and disable camera power management

echo ======================================================================
echo Disable Camera Power Management
echo ======================================================================
echo.
echo This will disable USB power management to prevent cameras from resetting.
echo Administrator rights are required.
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as Administrator
    echo.
    powershell -ExecutionPolicy Bypass -File "%~dp0disable_camera_power_management.ps1"
) else (
    echo Requesting elevation...
    powershell -ExecutionPolicy Bypass -Command "Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -File \"%~dp0disable_camera_power_management.ps1\"' -Verb RunAs"
)

echo.
pause

