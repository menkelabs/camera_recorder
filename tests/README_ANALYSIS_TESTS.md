# Analysis Tests

Coverage for frame navigation, summary correctness, and analysis tools fed by
**mock video captures** (no USB cameras required).

## Test modules

### `test_analysis_navigation.py`
Frame navigation, per-camera summaries, live metrics, and analysis-tab
rendering for the legacy GUI data structures.

```bash
python3 -m unittest tests.test_analysis_navigation -v
```

### `test_analysis_workflow.py`
Legacy GUI analysis start gates (missing files, MediaPipe import errors,
empty detections).

### `test_mock_video_analysis.py` — synthetic captures → analysis tools
Generates OpenCV-readable mock MP4/AVI files at runtime and verifies:

| Area | What is checked |
|------|-----------------|
| Fixtures | `write_mock_video` / `write_mock_swing_pair` produce readable frame counts |
| PoseProcessor | `process_video` over mock captures with a fake landmarker (detect / no-detect) |
| SwayCalculator | Metrics from dual mock swing sequences; blank “lab floor” stability |
| Clip export | JPEG annotated frames → MP4 → re-decode frame count/dims |

Patterns available via helpers: `swing`, `static_pose`, `solid`, `blank`.

```bash
python3 -m unittest tests.test_mock_video_analysis -v
```

### Flask analysis pipeline (stability suite)
`test_gui_stability.py` runs `CameraManager._analyze_videos` against the same
mock swing pairs (PoseProcessor stubbed to decode the real mock files +
SwayCalculator), then hits analysis/frame/clip HTTP endpoints.

## Shared helpers (`tests/helpers.py`)

- `write_mock_video(path, n_frames=..., pattern='swing')`
- `write_mock_swing_pair(dir, timestamp=..., n_frames_cam1=..., n_frames_cam2=...)`
- `landmarks_and_frames_from_video(path, landmark_sequence)`
- `make_annotated_jpeg_frames(...)`
- `make_swing_sequence` / `make_address_pose` (landmark fixtures)

Mock videos are written under temp directories during tests — they are **not**
committed (repo `.gitignore` excludes `*.mp4` / `*.avi`).

## Running

```bash
python run_all_tests.py --unit
python3 -m unittest tests.test_mock_video_analysis tests.test_analysis_navigation -v
```

## Real Face-On / DTL smoke (opt-in)

`test_real_swing_smoke.py` always checks clip discovery. The live MediaPipe
model is **not** part of `--unit` / CI. To smoke-test that a real person is
detected and metrics still populate:

```bash
python run_all_tests.py --smoke
# or
python scripts/smoke_real_swings.py
```

Clip order: `fixtures/real_swings/face_on.mp4` + `dtl.mp4`, else the newest
`recordings/` pair, else a small public GolfDB demo swing (downloaded, not
committed). See `fixtures/real_swings/README.md`.
