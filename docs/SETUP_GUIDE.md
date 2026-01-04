# Setup Guide

## Python Installation

If Python is not installed or not found:

1. **Download Python**: Go to https://www.python.org/downloads/
2. **Install Python**: 
   - Download Python 3.8 or higher
   - **IMPORTANT**: Check "Add Python to PATH" during installation
   - Install to default location (usually `C:\Python3x\` or `C:\Users\YourName\AppData\Local\Programs\Python\Python3x\`)

3. **Verify Installation**:
   ```powershell
   python --version
   ```
   or
   ```powershell
   py --version
   ```

## Path Warning Fix

If you're getting a warning about special characters in the path:

### Option 1: Move the project (Recommended)
Move your project to a path without special characters:
- ❌ Bad: `C:\Users\jmjav\cursor\` (if "cursor" causes issues)
- ✅ Good: `C:\Users\jmjav\dual_camera_recorder\`
- ✅ Good: `C:\Projects\dual_camera_recorder\`
- ✅ Good: `C:\dev\camera_recorder\`

### Option 2: Use a shorter path
- ✅ Good: `C:\camera\`
- ✅ Good: `D:\camera_recorder\`

### Option 3: Work around it
The warning is usually just a warning - the code should still work. You can ignore it if everything functions correctly.

## Virtual Environment Setup

Once Python is installed, run these commands:

```powershell
# Create virtual environment
python -m venv .venv

# Activate it (PowerShell)
.venv\Scripts\Activate.ps1

# If you get an execution policy error, run this first:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install dependencies
pip install -r requirements.txt

# Run the debug script
python debug_recorder.py
```

## Quick Setup Script

I've created `setup_env.ps1` - run it to automate the setup process.

