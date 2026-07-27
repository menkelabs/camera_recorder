# SwingLab GUI v2 (React)

Vite + React + TypeScript frontend that replaces the monolithic Flask template.

See [`../docs/GUI_V2_PLAN.md`](../docs/GUI_V2_PLAN.md) for the full migration plan.

## Dev

```bash
# terminal 1 — API + MJPEG
python scripts/flask_gui.py --port 5000

# terminal 2 — React HMR (proxies /api and /video_feed)
cd frontend && npm install && npm run dev
```

Open http://localhost:5173

## Production build (served by Flask)

```bash
cd frontend && npm run build
python scripts/flask_gui.py
# http://localhost:5000 → React dist
# http://localhost:5000/legacy → v1 template
```

## Feature status (Phase A–D)

- Setup: property sliders, save/reset, detect/reinit
- Recording: live preview while recording, checklist, auto-detect, session, metronome
- Analysis: serialized playback seek, score/grade, per-frame metrics, **Export HTML/CSV**, **Clip Cam1/Cam2**
- Recordings: favorites, notes, reference, bulk delete, cleanup
- Compare: summary deltas + normalized overlay chart
- Progress: multi-metric trends
- Settings: camera roles + archive path/run
- Hidden tabs pause MJPEG feeds

## Tests

```bash
# Unit (Vitest + Testing Library)
npm test

# E2E (Playwright against Flask serving frontend/dist)
npm run test:e2e:install   # once
npm run test:e2e
```
