# GUI Tests

Test coverage for the Camera Setup & Recording GUI — Flask API + Vue SPA
and the legacy OpenCV desktop GUI.

## Primary UI (Flask API + Vue)

### `test_flask_gui.py` — Unit / route tests
CameraManager init, properties, recording controls, analysis result shaping,
frame navigation, Flask API routes, Vue `/` vs missing-dist hint, `/legacy`
redirect, auto-detect, JPEG frame endpoint, and frame compression.

```bash
python3 -m unittest tests.test_flask_gui -v
```

### `test_gui_stability.py` — Stability + mock video captures
Broader stability coverage against **synthetic dual-camera recordings**
(generated at test time via OpenCV — no USB cameras, no checked-in MP4s):

- Full `CameraManager._analyze_videos` pipeline on mock swing / blank captures
- Analysis JSON persistence and score payload
- Concurrent `/api/status` + analysis-result polling while analyzing
- MJPEG `generate_frames` multipart JPEG chunks (live + recording placeholder)
- Analysis frame JPEG endpoint after a real mock analysis run
- Clip export round-trip (`/api/analysis/export-clip` → readable MP4)
- Unequal Cam1/Cam2 frame counts (navigation clamping)
- Reinit blocked during recording; session phase → `review` after analysis
- Preview `get_frame` copy stability under reader/writer contention

```bash
python3 -m unittest tests.test_gui_stability -v
```

## Legacy OpenCV GUI

### `test_gui.py` — Unit tests (mocked cameras)
TabbedCameraGUI init, tabs, recording, analysis gates, property ranges.

### `test_gui_interactive.py` — Optional hardware
Runs only when real cameras are present.

## Related analysis fixtures

See `test_mock_video_analysis.py` and `helpers.write_mock_video` /
`helpers.write_mock_swing_pair` for the shared synthetic capture helpers.

## Running all GUI-related unit tests

```bash
python run_all_tests.py --unit
# or specifically:
python3 -m unittest tests.test_flask_gui tests.test_gui_stability tests.test_gui -v
```
