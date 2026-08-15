# Quick reference

Product UI: **Vue + Flask**. Full walkthrough: [docs/HOW_TO_USE.md](docs/HOW_TO_USE.md).

## Start

```bash
python scripts/setup_wizard.py          # first run (browser wizard)
python scripts/start_swinglab.py        # every day after that
```

Open **http://localhost:5000**. Pick **Player** in the header. Tab **3** (Recording) → checklist → **Space** or Auto Detect.

```bash
python scripts/flask_gui.py --camera1 0 --camera2 2
python scripts/flask_gui.py --model-complexity 0
```

## Tabs

`1` Camera 1 · `2` Camera 2 · `3` Recording · `4` Recordings · `5` Analysis · `6` Compare · `7` Progress · `8` Settings

- **Space** records only on Recording (disabled when auto-detect is on).
- Analysis: Space play/pause · `A`/`←` prev · `D`/`→` next.

## Files

`recordings/recording_<timestamp>_camera1.mp4` + `_camera2.mp4`  
Stats: `recordings/swinglab.db` ([docs/LOCAL_DB.md](docs/LOCAL_DB.md))

## Optional

| Command | Use |
|---------|-----|
| `python scripts/camera_test_gui.py` | Lighting/focus bench (not the product UI) |
| `python scripts/dual_camera_soak.py --hardware` | Operator soak with real cameras |
