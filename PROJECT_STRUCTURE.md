# Project structure

The product entry point is `scripts/flask_gui.py` (API + cameras) serving `frontend/dist` (Vue). See [docs/HOW_TO_USE.md](docs/HOW_TO_USE.md).

```
camera_recorder/
├── frontend/                 # Vue 3 + Vite + Pinia UI
│   ├── src/                  # tabs, API client, playback
│   └── dist/                 # production build (gitignored; Flask serves this)
├── scripts/
│   ├── setup_wizard.py       # first-run browser installer
│   ├── start_swinglab.py     # daily start (wizard profile)
│   ├── flask_gui.py          # API + cameras + Vue
│   ├── camera_test_gui.py    # optional lighting/focus bench
│   ├── dual_camera_soak.py   # mock / hardware soak
│   └── smoke_real_swings.py  # opt-in MediaPipe smoke
├── src/                      # capture, pose, score, local DB
├── tests/                    # Python unit + hardware helpers
├── docs/
│   ├── HOW_TO_USE.md         # field + daily usage
│   ├── LOCAL_DB.md
│   └── PLATFORM_CONFIG.md
├── recordings/               # MP4s + swinglab.db (gitignored)
├── requirements.txt
└── run_all_tests.py
```

```bash
python scripts/setup_wizard.py      # first run
python scripts/start_swinglab.py    # daily
cd frontend && npm run dev          # UI hot reload against Flask :5000
python run_all_tests.py --unit
```
