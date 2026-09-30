# SwingLab — dual USB golf-swing recorder

Browser app for synchronized Face-On and Down-the-Line capture, MediaPipe pose analysis, and local multi-player practice stats. **Vue 3** UI + **Flask** API/MJPEG. Cameras stay on the Python side.

**How to run it on the range:** [docs/HOW_TO_USE.md](docs/HOW_TO_USE.md)

## Quick start

**Windows installer:** build `SwingLab-Setup-*.exe` with `python scripts/build_installer.py` ([packaging/README.md](packaging/README.md)), then double-click it. First launch opens the camera wizard.

**From source** (installs packages, builds the UI, picks cameras):

```bash
python scripts/setup_wizard.py
```

**Every day after that:**

```bash
python scripts/start_swinglab.py
```

Open **http://localhost:5000**. Windows: **Start SwingLab.bat**. Linux: `./start-swinglab.sh`.

Manual (no wizard): `pip install -r requirements.txt`, `cd frontend && npm install && npm run build`, then `python scripts/flask_gui.py`.

Dev (hot reload): Flask on `:5000` and `cd frontend && npm run dev` → **http://localhost:5173**.

```bash
python scripts/flask_gui.py --camera1 0 --camera2 2
python scripts/flask_gui.py --model-complexity 0          # faster analysis on a laptop
python scripts/flask_gui.py --skip-cameras                 # UI/API only
```

The OpenCV desktop GUI and old CLI recorders are **removed**. Start Flask only — [How to use](docs/HOW_TO_USE.md).

## What you get

- Dual live preview and 720p / 120 fps target recording
- Auto swing detect, session loop, optional 3:1 metronome
- Role-aware Face-On / DTL scoring (0–100, A–F) and coaching focus
- Library with claim, favorites, reference swing, scoped delete/cleanup
- Compare two swings; Progress trends per local player
- Archive copies to a USB path; SQLite stats in `recordings/swinglab.db`

Eight tabs: Camera 1, Camera 2, Recording, Recordings, Analysis, Compare, Progress, Settings. Keyboard: `1`–`8` switch tabs; **Space** records only on Recording; Analysis uses Space / A / D for playback.

## Install

Python 3.10+ and Node 18+.

```bash
pip install -r requirements.txt          # opencv-python, numpy, mediapipe, flask, …
cd frontend && npm install
```

Two identical USB cameras must sit on **different USB buses**. Linux: `lsusb -t`. Windows camera map: `python scripts/detect_windows_cameras.py` → `config_windows.json`.

## Testing

```bash
python run_all_tests.py --unit           # CI default; no cameras
python run_all_tests.py --smoke          # real MediaPipe (short public clip if needed)
python scripts/dual_camera_soak.py --mock
cd frontend && npm test
cd frontend && npm run test:e2e:install && npm run test:e2e

# cameras plugged in
python run_all_tests.py --hardware
python scripts/dual_camera_soak.py --hardware --seconds 30
```

## Docs

| Doc | Topic |
|-----|--------|
| [docs/HOW_TO_USE.md](docs/HOW_TO_USE.md) | Field first-run, daily start, tabs, players, leftovers |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | One-page start card |
| [docs/LOCAL_DB.md](docs/LOCAL_DB.md) | SQLite profiles, claim, PIN |
| [docs/PLATFORM_CONFIG.md](docs/PLATFORM_CONFIG.md) | Windows / Linux camera config |
| [docs/CAMERA_TEST_GUI.md](docs/CAMERA_TEST_GUI.md) | Optional lighting/focus bench |
| [frontend/README.md](frontend/README.md) | Vue stack and tests |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Repo layout |

Older capture notes (`docs/QUICK_START.md`, `docs/GOLF_SWING_CAPTURE_GUIDE.md`, …) are historical — start with How to use.

## License

Free to use and modify for your projects.
