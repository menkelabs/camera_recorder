# How to use SwingLab

This is the field guide for the **Vue + Flask** app. Record Face-On and Down-the-Line (DTL) on two USB cameras, analyze the swing with MediaPipe, and keep local player profiles on a shared machine.

The product UI is the browser.

---

## Windows installer (double-click)

On a Windows studio PC you do **not** need Python or Node installed.

1. Build (or download) **SwingLab-Setup-1.1.0.exe** — see [packaging/README.md](../packaging/README.md).
2. Run the setup wizard. It installs to `%LOCALAPPDATA%\Programs\SwingLab` (no admin required).
3. On first launch, SwingLab opens the camera / player wizard in a browser.
4. Daily start: **SwingLab** from the Start Menu or desktop.

Recordings and `swinglab.local.json` live in `%LOCALAPPDATA%\SwingLab`, not inside Program Files.

Re-run setup later: `SwingLab.exe --setup`.

---

## First-run from source (wizard)

On the machine that has the cameras, install **Python 3.10+** and **Node.js LTS**, then:

```bash
python scripts/setup_wizard.py
```

A browser window opens at **http://127.0.0.1:8765**. The wizard walks through:

1. Prerequisites (Python, pip, Node, npm, disk)
2. Create `.venv` and `pip install -r requirements.txt`
3. `npm install` + `npm run build` for the Vue UI
4. Detect USB cameras and assign Face-On / DTL
5. First player name, recordings folder, port, analysis model
6. Optional desktop shortcut

It writes `swinglab.local.json` (gitignored) and updates `config_linux.json` / `config_windows.json`. Then start the app:

```bash
python scripts/start_swinglab.py
```

Windows: double-click **Start SwingLab.bat**. Linux: `./start-swinglab.sh`. Open **http://localhost:5000** (or the port you chose).

`--no-browser` if you are on SSH: `python scripts/setup_wizard.py --no-browser` then open the printed URL.

**Windows:** check “Add Python to PATH” when installing Python.

**Linux:** two identical USB cameras need **different USB buses**. If camera 2 opens but stays black, move one cable (`lsusb -t`). MediaPipe preview may need `libegl1` / `libgles2`.

Manual install (no wizard) is still: venv → `pip install -r requirements.txt` → `cd frontend && npm install && npm run build` → `python scripts/flask_gui.py`.

---

## Daily start (range / studio)

1. Plug both USB cameras in (Face-On and DTL).
2. Start the app (uses the wizard profile if present):

   ```bash
   python scripts/start_swinglab.py
   ```

   Or `python scripts/flask_gui.py --camera1 0 --camera2 2` to override indices.

4. Open **http://localhost:5000**.
5. In the header, pick the **Player** (PIN if that profile is locked).
6. Go to **Recording** (key `3`). Check the readiness checklist, then record.

You only need `npm run build` again after a frontend update. For UI development with hot reload, see [Dev vs production](#dev-vs-production) below.

---

## The eight tabs

| Key | Tab | What it is for |
|-----|-----|----------------|
| `1` | Camera 1 | Live preview, brightness/exposure sliders, Detect / Reinit |
| `2` | Camera 2 | Same for the second camera |
| `3` | Recording | Dual preview, Space to record, auto-detect, session, metronome |
| `4` | Recordings | Library: claim, favorite, notes, analyze, compare, delete, cleanup |
| `5` | Analysis | Score, metrics, playback, export |
| `6` | Compare | Two swings side by side (not the same timestamp) |
| `7` | Progress | Score and metric trends for the **active player** |
| `8` | Settings | Players, Face-On/DTL roles, archive to USB |

Shortcuts are ignored while you are typing in an input.

---

## Camera setup (tabs 1 & 2)

1. Confirm each preview shows the right view (golfer face-on vs down-the-line).
2. If a feed is black or the wrong device: **Detect** (scans indices) or type a new index and **Reinit**.
3. Adjust sliders for the lighting (exposure, brightness, contrast). **Save** persists them; **Reset** restores defaults.
4. In **Settings**, set Camera 1’s role to Face-On or DTL. The other camera gets the opposite role. Labels and scoring follow those roles.

**USB tip:** put the two cameras on separate controllers. The Recording checklist warns when Linux sees a shared bus or a camera is starving for frames.

Optional lighting/focus tool (not the product UI): `python scripts/camera_test_gui.py` — see [CAMERA_TEST_GUI.md](CAMERA_TEST_GUI.md).

---

## Record a swing (tab 3)

The checklist should show both cameras live, frames arriving, and disk writable before you start.

### Manual

- **Start / Stop** or press **Space** (only on the Recording tab).
- Space does nothing on other tabs, so you will not accidentally start a take from Analysis.

### Auto-detect

- Turn **Auto Detect** on. The detector watches Face-On shoulder turn and starts/stops for you.
- Manual Start/Stop and Space are disabled while auto-detect is armed.
- After a take there is a short cooldown before the next swing.

### Session mode

- **Session mode** loops: armed → record → analyze → review → **Next swing**.
- Use this for a bucket of balls without hunting tabs.

### Metronome

- Optional 3:1 click on the Recording tab (BPM 40–120). Browsers require a click before audio starts.

Recordings land in `recordings/`:

- `recording_YYYYMMDD_HHMMSS_camera1.mp4`
- `recording_YYYYMMDD_HHMMSS_camera2.mp4`

The active player owns a new take as soon as recording starts. Analysis starts when you stop (or auto-detect stops). The UI jumps to **Analysis**.

If Flask restarts mid-session, reopen the browser — the server restores the last in-progress session when it can.

---

## Library (tab 4)

Default scope is **Mine** plus unclaimed files. Filters: all / favorites / reference.

| Action | Notes |
|--------|--------|
| **Claim** | Assign an unclaimed (older) file to the active player. You cannot steal another player’s swing (the API returns 409). |
| **Star** | Favorite for later. |
| **Reference** | Pin a golden swing; Compare defaults Swing A to it. |
| **Notes** | Per-player notes on that timestamp. |
| **Analyze** | Opens Analysis for that saved swing. |
| **Compare** | Prefills Compare with that timestamp. |
| **Delete** | Only your swings (and unclaimed). Hidden for other players. Confirms first. |
| **Clean up** | Deletes **your** + unclaimed files older than N days. Skips favorites and the reference swing. |

---

## Analysis (tab 5)

After a live take you get annotated playback (pose overlay) for both cameras, a 0–100 score / A–F grade, strengths and focus areas, and metric cards (green / yellow / red).

| Key | Action |
|-----|--------|
| Space | Play / pause |
| `←` or `A` | Previous frame |
| `→` or `D` | Next frame |

Pick an older timestamp from the dropdown (or **Analyze** on Recordings) to review a saved swing. Saved review shows metrics and score. Clip export uses in-memory annotated frames for the latest analysis, or re-encodes the original recording from disk for older swings.

Export HTML or CSV from the Analysis tab when you want a shareable report.

---

## Compare & Progress (tabs 6 & 7)

**Compare** needs two **different** analyzed timestamps. Same-swing is rejected. Delta cards and an overlay chart (0–100% swing progress) show what changed.

**Progress** charts the active player’s scores and key metrics over time. Switch Player in the header to see someone else’s trend.

---

## Settings (tab 8)

**Players** — local profiles on this machine (no cloud account). Add a name, optional PIN, rename, or delete (not the last profile; blocked while recording). Progress, favorites, notes, and practice settings are per player.

**Camera roles** — Face-On vs DTL for Camera 1 (Camera 2 flips). Scoring uses the role, not “camera 1 = face-on” hardcoded.

**Archive** — set a USB/external path (example: `/media/you/Seagate8TB/golf`). **Archive new recordings** copies **your** and unclaimed videos, analysis JSON, and settings and remembers what already went. Other players’ swings are left alone. The badge shows connected / disconnected and disk free space.

More on the SQLite file and ownership: [LOCAL_DB.md](LOCAL_DB.md).

---

## Dev vs production

**Field / kiosk (one process):**

```bash
cd frontend && npm run build
python scripts/flask_gui.py --host 0.0.0.0 --port 5000
```

**UI development (two terminals):**

```bash
# terminal 1 — API + cameras + MJPEG
python scripts/flask_gui.py --port 5000

# terminal 2 — Vue with hot reload
cd frontend && npm run dev
```

Open **http://localhost:5173**. Vite proxies API and video to Flask.

Useful flags:

| Flag | Meaning |
|------|---------|
| `--camera1` / `--camera2` | Device indices |
| `--width` `--height` `--fps` | Capture target (default 1280×720 @ 120) |
| `--model-complexity 0\|1\|2` | Analysis model: 0 lite (laptops), 2 heavy (default) |
| `--host` `--port` | Bind address (default `0.0.0.0:5000`) |
| `--skip-cameras` | UI/API only (tests / no USB) |

Laptop example: `python scripts/flask_gui.py --model-complexity 0`.

---

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| “Vue UI not built” | `cd frontend && npm run build` |
| Cameras offline | Plug in, then Detect / Reinit on tab 1 or 2 |
| Cam 2 black | Different USB bus; close Zoom/Teams; Detect again |
| Wrong webcam | `--camera1` / `--camera2` or Detect |
| Space does nothing | You are not on the Recording tab, or auto-detect is on |
| Cannot switch player | Stop recording first; enter PIN if prompted |
| Claim fails | That swing already belongs to someone else |
| Delete missing | You are looking at another player’s row |
| Analysis error | Shown on the Analysis tab; `pip install mediapipe` if missing |
| High CPU | Lower `--fps` or `--model-complexity 0` |

Hardware / platform notes: [PLATFORM_CONFIG.md](PLATFORM_CONFIG.md).

---

## What to run (and what is gone)

| Script | Status |
|--------|--------|
| `scripts/setup_wizard.py` | First-run installer (browser) |
| `scripts/start_swinglab.py` | Daily start (reads `swinglab.local.json`) |
| `scripts/flask_gui.py` | App server (API + cameras + Vue) |
| `scripts/camera_test_gui.py` | Optional lighting/focus bench |
| `scripts/dual_camera_soak.py` | Operator / CI soak |
| `/legacy` in the browser | Redirects to `/` (old Flask HTML GUI is gone) |

Removed: OpenCV desktop GUI (`camera_setup_recorder_gui.py`) and the old CLI recorders (`record_golf_swing.py`, `record_for_mediapipe.py`, `run_dual_recording.py`, `debug_recorder.py`).

Hardware soak (operator, cameras plugged in):

```bash
python scripts/dual_camera_soak.py --hardware --seconds 30 --camera1 0 --camera2 2
```

---

## Tests (developers)

```bash
python run_all_tests.py --unit          # default CI; no cameras
python run_all_tests.py --smoke         # real MediaPipe on a short clip
cd frontend && npm test && npm run test:e2e
```

See the [README](../README.md#testing) for the full matrix.
