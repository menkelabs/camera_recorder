# Local SQLite stats DB

SwingLab keeps **user practice stats on-device** in SQLite so Progress, favorites, notes, and settings survive packaging and optional archive of bulky video/JSON files.

## Location

| Item | Default |
|------|---------|
| DB file | `{recordings_dir}/swinglab.db` |
| Override | env `SWINGLAB_DB_PATH` (absolute path) |
| JSON mirrors | `recording_meta.json`, `practice_settings.json` (best-effort backup) |

`recordings_dir` is the same folder Flask uses for MP4 / analysis JSON (typically `./recordings`).

**Packaging note:** treat `swinglab.db` as **user data**, not part of the app bundle. On first run, create/open it under a writable user directory (e.g. next to recordings). Never ship a shared DB inside a read-only install tree.

## What’s stored

| Table | Purpose |
|-------|---------|
| `recording_meta` | favorite, notes, tags per swing timestamp |
| `settings` | practice settings JSON (roles, metronome, session, reference) |
| `swing_stats` | score, grade, trend metrics for Progress charts |
| `practice_events` | optional timeline (session/analyze events) |
| `schema_migrations` / `app_meta` | versioning + one-shot migration flags |

Full analysis timeseries remain in `analysis_*.json` (and videos as MP4). SQLite holds the **index + user annotations** needed for Progress and library UX.

## Migration

On first open for a recordings folder:

1. Import `recording_meta.json` (skips invalid timestamps)
2. Import `practice_settings.json`
3. Scan `analysis_*.json` into `swing_stats` (skips rows already present)

Corrupt JSON does not prevent DB creation; bad entries are skipped.

## API behavior

- Meta / practice settings APIs unchanged (`/api/recordings/<ts>/meta`, `/api/practice/settings`, …)
- `GET /api/progress` prefers SQLite `swing_stats`; falls back to scanning analysis JSON and backfills the DB
- Saving analysis (`_save_analysis_json`) upserts `swing_stats` and logs an `analyze` event
- Deleting a recording removes meta **and** stats for that timestamp

## Edge cases covered by tests

See `tests/test_local_db.py`:

- Corrupt / empty legacy JSON
- Invalid timestamps rejected
- Notes/tags length limits
- Concurrent meta writes
- Idempotent re-open / migration
- Upsert same timestamp after re-analyze
- Delete clears meta + stats
- `SWINGLAB_DB_PATH` override
- Progress empty / score delta
- Role conflict auto-repair (same role on both cameras)
- Integrity check (`ok`)

## Future packaging hooks

1. Resolve `recordings_dir` to a per-user writable path when frozen (PyInstaller/`sys.frozen`)
2. Optional export/import of `swinglab.db` for backup
3. Optional `profile_id` column if multi-golfer profiles are needed later
