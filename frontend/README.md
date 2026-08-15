# SwingLab GUI (Vue)

Vite + Vue 3 + TypeScript frontend served by the Flask API.

Replaces the React v2.0 UI with the same REST/MJPEG contracts so packaging stays: `npm run build` → `frontend/dist` → Flask `/`.

## Dev

```bash
# terminal 1 — API + MJPEG
python scripts/flask_gui.py --port 5000

# terminal 2 — Vue HMR
cd frontend && npm install && npm run dev
```

Open http://localhost:5173

## Production build

```bash
cd frontend && npm run build
python scripts/flask_gui.py
# http://localhost:5000 → Vue dist
```

## Stack

- Vue 3 + `<script setup>` + TypeScript
- Pinia for app/tab/status state
- CSS modules + `styles/tokens.css`
- Vitest + Testing Library Vue
- Playwright E2E against Flask + built dist

## Tests

```bash
npm test
npm run test:e2e:install   # once
npm run test:e2e
```
