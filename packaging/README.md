# Building the SwingLab installer

Produces a double-click Windows setup: **SwingLab-Setup-&lt;version&gt;.exe**.

The installer copies a PyInstaller **onedir** build (Python, OpenCV, MediaPipe, Vue UI) into `%LOCALAPPDATA%\Programs\SwingLab`. First launch runs the camera / player wizard. Recordings and `swinglab.local.json` go to `%LOCALAPPDATA%\SwingLab`.

## On a Windows build machine

1. Install Python 3.12, Node.js 22 LTS, and [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`ISCC.exe` on PATH).
2. From the repo root:

```powershell
python -m pip install -r requirements-build.txt
python scripts/build_installer.py
```

Outputs:

- `dist\SwingLab\SwingLab.exe` — frozen app
- `dist\installer\SwingLab-Setup-1.1.0.exe` — Inno wizard

Flags:

```powershell
python scripts/build_installer.py --skip-frontend      # reuse frontend/dist
python scripts/build_installer.py --pyinstaller-only   # skip Inno
```

## GitHub Actions

Workflow **Windows installer** (`.github/workflows/windows-installer.yml`) runs on version tags (`v*`) or **workflow_dispatch**. It uploads `SwingLab-Setup-*.exe` as an artifact.

## Linux / macOS

`python scripts/build_installer.py --pyinstaller-only` writes `dist/SwingLab/SwingLab`. There is no `.deb` / `.dmg` yet.

## First-run after install

1. Run **SwingLab Setup.exe** (or the Start Menu shortcut).
2. Finish cameras + first player.
3. Daily start: **SwingLab** from the Start Menu or desktop.

`--setup` opens the wizard again. `--skip-setup` goes straight to the app.
