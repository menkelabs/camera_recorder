#!/usr/bin/env python3
"""
Build a frozen SwingLab app (PyInstaller onedir) and, on Windows, an Inno Setup installer.

    python scripts/build_installer.py
    python scripts/build_installer.py --skip-frontend
    python scripts/build_installer.py --pyinstaller-only

Outputs:
  dist/SwingLab/SwingLab.exe          (or SwingLab on Linux)
  dist/installer/SwingLab-Setup-*.exe (Windows, if ISCC is on PATH)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from install_config import APP_VERSION  # noqa: E402


def run(cmd: list[str], cwd: str | None = None) -> None:
    print('+ ' + ' '.join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=cwd or ROOT)


def build_frontend() -> None:
    npm = shutil.which('npm')
    if not npm:
        raise SystemExit('npm not found. Install Node.js LTS or pass --skip-frontend.')
    frontend = os.path.join(ROOT, 'frontend')
    run([npm, 'ci'], cwd=frontend)
    run([npm, 'run', 'build'], cwd=frontend)
    index = os.path.join(frontend, 'dist', 'index.html')
    if not os.path.isfile(index):
        raise SystemExit(f'Frontend build missing {index}')


def build_pyinstaller() -> str:
    spec = os.path.join(ROOT, 'packaging', 'swinglab.spec')
    exe = shutil.which('pyinstaller')
    cmd = [exe] if exe else [sys.executable, '-m', 'PyInstaller']
    run(cmd + ['--noconfirm', '--clean', spec])
    out_dir = os.path.join(ROOT, 'dist', 'SwingLab')
    binary = os.path.join(out_dir, 'SwingLab.exe' if os.name == 'nt' else 'SwingLab')
    if not os.path.isfile(binary):
        raise SystemExit(f'PyInstaller output missing {binary}')
    return out_dir


def find_iscc() -> str | None:
    found = shutil.which('iscc') or shutil.which('ISCC')
    if found:
        return found
    for path in (
        r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
        r'C:\Program Files\Inno Setup 6\ISCC.exe',
    ):
        if os.path.isfile(path):
            return path
    return None


def build_inno(version: str) -> str:
    iscc = find_iscc()
    if not iscc:
        raise SystemExit(
            'Inno Setup compiler (ISCC) not found. Install Inno Setup 6 '
            'or pass --pyinstaller-only.'
        )
    iss = os.path.join(ROOT, 'packaging', 'swinglab.iss')
    out_dir = os.path.join(ROOT, 'dist', 'installer')
    os.makedirs(out_dir, exist_ok=True)
    run([
        iscc,
        f'/DMyAppVersion={version}',
        f'/DSourceDir={os.path.join(ROOT, "dist", "SwingLab")}',
        f'/DOutputDir={out_dir}',
        iss,
    ])
    expected = os.path.join(out_dir, f'SwingLab-Setup-{version}.exe')
    if not os.path.isfile(expected):
        raise SystemExit(f'Inno output missing {expected}')
    return expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Build the SwingLab installer.')
    parser.add_argument('--skip-frontend', action='store_true')
    parser.add_argument('--pyinstaller-only', action='store_true')
    parser.add_argument('--version', default=APP_VERSION)
    args = parser.parse_args(argv)

    if not args.skip_frontend:
        build_frontend()
    elif not os.path.isfile(os.path.join(ROOT, 'frontend', 'dist', 'index.html')):
        raise SystemExit('frontend/dist is missing. Run without --skip-frontend.')

    out_dir = build_pyinstaller()
    print(f'Frozen app: {out_dir}')
    if os.name == 'nt' and not args.pyinstaller_only:
        installer = build_inno(args.version)
        print(f'Installer: {installer}')
    elif args.pyinstaller_only:
        print('Skipped Inno Setup (--pyinstaller-only).')
    else:
        print('Not Windows — skipped Inno Setup. Use the dist/SwingLab folder directly.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
