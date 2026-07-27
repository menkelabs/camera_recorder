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

## Tests

```bash
npm test
```
