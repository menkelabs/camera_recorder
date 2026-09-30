# PyInstaller spec — run from the repo root via scripts/build_installer.py
#   pyinstaller --noconfirm --clean packaging/swinglab.spec

from __future__ import annotations

import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_data_files

SPECDIR = os.path.dirname(os.path.abspath(SPEC))
ROOT = os.path.dirname(SPECDIR)
SRC = os.path.join(ROOT, 'src')
SCRIPTS = os.path.join(ROOT, 'scripts')
FRONTEND_DIST = os.path.join(ROOT, 'frontend', 'dist')

datas = []
binaries = []
hiddenimports = [
    'flask_gui',
    'setup_wizard',
    'install_config',
    'dual_camera_recorder',
    'pose_processor',
    'sway_calculator',
    'swing_detector',
    'camera_utils',
    'swing_score',
    'recording_meta',
    'local_db',
    'practice_reports',
    'practice_settings',
    'clip_exporter',
    'usb_health',
    'flask',
    'cv2',
    'numpy',
    'PIL',
]

if os.path.isdir(FRONTEND_DIST):
    datas.append((FRONTEND_DIST, os.path.join('frontend', 'dist')))

wizard_html = os.path.join(SRC, 'setup_wizard.html')
if os.path.isfile(wizard_html):
    datas.append((wizard_html, 'src'))

for pkg in ('mediapipe', 'cv2', 'flask'):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    except Exception:
        continue
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

try:
    datas += collect_data_files('mediapipe')
except Exception:
    pass

block_cipher = None

a = Analysis(
    [os.path.join(SCRIPTS, 'swinglab_app.py')],
    pathex=[ROOT, SRC, SCRIPTS],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'pytest', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SwingLab',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SwingLab',
)
