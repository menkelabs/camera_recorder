# GUI v2.0 — React Experience Plan

**Branch:** `cursor/gui-v2-react-600c`  
**Goal:** Replace the monolithic Flask `templates/index.html` SPA with a React frontend, while keeping the Python/Flask camera + analysis backend. Eventually merge to `master` as the default UI.

**Non-goals for v2.0:** Rewrite MediaPipe/analysis, replace OpenCV capture, or drop the REST API surface.

---

## 1. Current state (v1)

| Layer | Today |
|-------|--------|
| UI | Single file `templates/index.html` (~3.7k lines inline CSS + vanilla JS) |
| Live video | MJPEG `/video_feed/<cam>` |
| API | Flask REST (`/api/*`) |
| Refresh | `setInterval(pollStatus, 500)` forever |
| Charts | Hand-drawn `<canvas>` |
| Desktop legacy | `scripts/camera_setup_recorder_gui.py` (OpenCV) — keep for now, not in v2 scope |

**Known UX defects to fix in v2 (must-hit):**

1. **No live preview while recording** — `generate_frames` returns a placeholder when `is_recording`; preview cams are released and `DualCameraRecorder` does not publish frames back to the MJPEG path.
2. **Analysis playback seek storm** — `setInterval` calls `seekFrame` without awaiting prior work; each tick = POST `/api/analysis/frame` + image GETs → backlog at 2x/4x.
3. **Hidden tabs keep MJPEG open** — Setup + Recording both embed `/video_feed/1` and `/2`; CSS-hidden `<img>` tags still stream.

---

## 2. Target architecture

```
┌─────────────────────────────────────────────────────────────┐
│  frontend/   Vite + React 18 + TypeScript                   │
│  - App shell, tabs, status store                            │
│  - CameraPreview (mount/unmount stream)                     │
│  - AnalysisPlayback (serialized seek / frame cache)         │
│  - Feature pages: Setup, Record, Library, Analysis, …       │
└───────────────────────────┬─────────────────────────────────┘
                            │ fetch / EventSource (later)
┌───────────────────────────▼─────────────────────────────────┐
│  scripts/flask_gui.py   (API + MJPEG, mostly unchanged)     │
│  src/*                  DualCameraRecorder, PoseProcessor…  │
└─────────────────────────────────────────────────────────────┘
```

**Stack choices**

- **Vite + React + TypeScript** — fast HMR, standard tooling, good for eventual replacement of main.
- **No Next.js** — app is local/LAN, not SSR; Flask remains the server.
- **CSS:** CSS modules or a single `tokens.css` port of current variables (`--bg`, `--accent`, …). Avoid heavy UI kits unless needed; keep the dark GitHub-like look initially for familiarity, then refine.
- **State:** lightweight (`zustand` or React context). Avoid Redux.
- **Charts:** keep canvas helpers ported to TS modules first; optional Chart.js later.
- **Dev:** Vite proxies `/api` and `/video_feed` → Flask `:5000`.
- **Prod:** `npm run build` → `frontend/dist`; Flask serves that as `/` and keeps `templates/index.html` at `/legacy` until cutover.

**Why keep Flask API:** cameras, recording, MediaPipe, and file I/O already work and are tested. React is a presentation layer swap, not a backend rewrite.

---

## 3. Must-hit fixes (do early — backend + React)

### 3.1 Live preview while recording

**Root cause:** On `start_recording`, preview `cap1`/`cap2` are released; recorder owns the devices; MJPEG path short-circuits to a placeholder.

**Backend work (`src/dual_camera_recorder.py`, `scripts/flask_gui.py`):**

1. Add a **non-destructive latest-frame snapshot** on each `CameraCapture` (e.g. `self.latest_frame` + lock updated in `_capture_loop`, separate from the write queue so preview does not steal frames from the recorder).
2. Expose `DualCameraRecorder.get_preview_frame(cam_num) -> Optional[np.ndarray]`.
3. Change `CameraManager.get_frame` / `generate_frames`:
   - If recording and recorder present → serve `recorder.get_preview_frame(n)`.
   - Else → existing preview buffer.
4. While recording, preview at **reduced cost**: JPEG quality ~60–70, ~15 fps (not 30), optional downscale to 640px width — protects USB bandwidth / encode CPU.
5. Show a subtle **REC** badge in the UI (React), not a full-screen placeholder.

**Acceptance:** Recording tab shows moving dual preview for the entire recording; file write frame counts remain within normal variance vs baseline.

### 3.2 Playback seek fix

**Root cause:** Fire-and-forget `seekFrame` inside `setInterval`.

**React `AnalysisPlayback` design:**

1. Keep `frameIndex` in client state; slider/play only updates that index.
2. **Serialize** frame loads: one in-flight request; drop/skip superseded indices (or queue only the latest).
3. Prefer **GET** `/api/analysis/frame/<cam>?index=N` (already supports query `index`) without requiring POST for every tick. Optionally keep POST for “shared server index” when multiple clients matter (they don’t locally).
4. Optional v2.1: bulk or blob cache of nearby JPEGs; for v2.0, serialized single-frame fetch is enough.
5. Play loop uses `requestAnimationFrame` or a timer that **awaits** the previous paint before advancing.

**Acceptance:** 1x/2x/4x play does not stall or jump backward; scrubbing the slider stays responsive.

### 3.3 Pause hidden feeds

**React `CameraPreview`:**

```tsx
// Only set img.src when mounted + tab visible + streamEnabled
useEffect(() => {
  if (!active) return;
  setSrc(`/video_feed/${cameraNum}?t=${session}`); // session busts cache after reinit
  return () => setSrc(''); // unload → browser closes MJPEG
}, [active, cameraNum, session]);
```

Rules:

- One logical preview consumer per camera globally (Recording tab reuses the same component instance pattern; Setup tabs only mount their cam).
- On tab hide / `document.hidden`, clear `src`.
- After reinit/detect, bump `session` so streams reconnect cleanly.

**Acceptance:** With Recording tab active, only two MJPEG connections; switching to Analysis drops both; CPU/network fall accordingly.

---

## 4. Phased delivery (branch → master)

Work stays on `cursor/gui-v2-react-600c` (or stacked PRs into it). Merge to `master` only after Phase D cutover criteria.

### Phase A — Foundation + must-hit backend (first PR slice)

| Item | Detail | Status |
|------|--------|--------|
| A1 | Scaffold `frontend/` (Vite React TS), proxy config, `npm` scripts | Done |
| A2 | Flask: serve `frontend/dist` when present; `/legacy` → old template | Done |
| A3 | Backend: recorder preview snapshots + MJPEG while recording | Done |
| A4 | Unit tests for preview-while-recording (mock recorder frames) | Done |
| A5 | Thin React shell: header, tab nav, status poll, CameraPreview, AnalysisPlayback sequencer | Done |

**Exit:** `npm run dev` + Flask shows shell; MJPEG live during record works even with `/legacy` or a minimal React Recording page.

### Phase B — React shell + three UX fixes end-to-end

| Item | Detail | Status |
|------|--------|--------|
| B1 | `CameraPreview` with pause-on-hide | Done |
| B2 | Setup Cam1 / Cam2 pages (properties, reset, save, detect/reinit) | Done |
| B3 | Recording page (checklist, start/stop, auto-detect, session, metronome) using live-while-recording preview | Done |
| B4 | Analysis page + `AnalysisPlayback` seek fix + score/metrics | Done |
| B5 | Frontend unit tests (Vitest) for playback sequencer + preview mount logic | Done |

**Exit:** Operator can configure → record (watching live) → analyze → scrub/play without seek backlog; unused feeds stop.

### Phase C — Feature parity

Port remaining v1 tabs, matching existing REST contracts:

1. Recordings library (favorites, notes, reference, delete/cleanup)
2. Analysis complete (score, metrics cards, phase badge, canvas chart, export/clip)
3. Compare
4. Progress
5. Settings (roles, archive)

Also in C:

- Keyboard shortcuts 1–8, Space record (when not in inputs)
- Smarter polling: 1–2s idle; faster only while `is_recording` / `is_analyzing`
- Optional SSE later (`/api/events`) — not required for parity

**Exit:** Feature checklist vs v1 README complete; no intentional regressions.

### Phase D — Cutover to default on master

| Item | Detail |
|------|--------|
| D1 | Default `/` → React build; `/legacy` retained one release |
| D2 | README + quick-start updated; v1 monolith marked deprecated |
| D3 | CI: `npm test` + `npm run build` + `run_all_tests.py --unit` |
| D4 | Remove `/legacy` + `templates/index.html` monolith in a follow-up once stable |

**Exit:** Master ships React as the only supported GUI.

---

## 5. Proposed frontend layout

```
frontend/
  package.json
  vite.config.ts          # proxy /api, /video_feed → localhost:5000
  index.html
  src/
    main.tsx
    App.tsx
    styles/tokens.css
    api/client.ts         # typed fetch wrappers
    api/types.ts          # Status, AnalysisResults, …
    store/statusStore.ts
    hooks/useStatusPoll.ts
    hooks/useTabVisibility.ts
    components/
      AppHeader.tsx
      TabBar.tsx
      CameraPreview.tsx
      StatusToast.tsx
      MetricCard.tsx
      TimeseriesChart.tsx
    features/
      setup/CameraSetupPage.tsx
      recording/RecordingPage.tsx
      recordings/RecordingsPage.tsx
      analysis/AnalysisPage.tsx
      analysis/AnalysisPlayback.tsx
      compare/ComparePage.tsx
      progress/ProgressPage.tsx
      settings/SettingsPage.tsx
```

Python side stays under `scripts/` + `src/`; add only small preview APIs/helpers as needed.

---

## 6. Testing strategy

| Layer | What |
|-------|------|
| Python | Extend `tests/test_gui_stability.py` / Flask tests: preview frames served when `is_recording`; hidden-feed N/A on server |
| Frontend unit | Playback sequencer (no overlapping seeks); CameraPreview clears src on unmount |
| Manual / E2E later | Playwright against Flask+Vite: tab switch stops network to `/video_feed/*` |
| Existing | Keep `run_all_tests.py --unit` green; mock-video analysis suite remains backend-focused |

---

## 7. Risks & mitigations

| Risk | Mitigation |
|------|------------|
| USB bandwidth if preview+record both hot | Downscale/lower fps/quality while recording; single consumer per cam |
| Peek frame races with writer | Copy under lock; never `queue.get` for preview |
| Dual maintenance v1+v2 | Short overlap; `/legacy` only; feature freeze on monolith after Phase B |
| Scope creep (full redesign) | v2.0 = parity + three fixes; visual refresh is v2.1 |
| OpenCV GUI confusion | Docs: Flask/React is primary; OpenCV GUI unsupported for new features |

---

## 8. Cutover checklist (merge to master)

- [ ] Live dual preview throughout recording
- [ ] Analysis play/scrub stable at 0.25x–4x
- [ ] Only active-tab camera feeds connected
- [ ] Feature parity with v1 tabs
- [ ] `npm run build` artifacts served by Flask
- [ ] Unit tests (Py + Vitest) in CI path
- [ ] README documents React dev (`npm run dev` + `python scripts/flask_gui.py`)
- [ ] `/legacy` optional safety valve for one release

---

## 9. Immediate next implementation steps

When implementation starts on this branch:

1. Scaffold `frontend/` Vite React TS + Flask dist/legacy routing.
2. Implement recorder latest-frame peek + MJPEG during recording + tests.
3. Build React `CameraPreview` + Recording/Analysis pages with seek sequencer.
4. Parity port remaining tabs.
5. Cut over default route; deprecate monolith.

This document is the source of truth for v2.0 scope. Change it via PR if scope shifts.
