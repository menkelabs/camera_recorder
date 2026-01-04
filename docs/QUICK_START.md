# Quick Start Guide

## Step 1: Install Python

**Python is not currently installed on your system.**

1. Download Python from: https://www.python.org/downloads/
2. Run the installer
3. **IMPORTANT**: Check the box "Add Python to PATH" during installation
4. Choose "Install Now" (or Customize and ensure PATH is checked)

## Step 2: Verify Python Installation

Open PowerShell and run:
```powershell
python --version
```

You should see something like: `Python 3.11.x` or `Python 3.12.x`

## Step 3: Set Up Virtual Environment

Once Python is installed, run:
```powershell
.\setup_env.ps1
```

Or manually:
```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install -r requirements.txt
```

## Step 4: Run Debug Script

```powershell
# Make sure venv is activated (you should see (.venv) in your prompt)
python debug_recorder.py
```

## About the Path Warning

If you see a warning about special characters in the path:
- The path `C:\Users\jmjav\cursor` should work fine
- This is usually just a VS Code/Cursor warning and can be ignored
- If you want to avoid it, you can move the project to a simpler path like:
  - `C:\Users\jmjav\camera_recorder\`
  - `C:\Projects\camera_recorder\`

## Troubleshooting

### "Python was not found"
- Python is not installed or not in PATH
- Reinstall Python and make sure "Add Python to PATH" is checked
- Restart your terminal/PowerShell after installing

### "Execution Policy" error
Run this command:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Virtual environment activation fails
Make sure you're in the project directory and the `.venv` folder exists.

