# Local SQLite stats DB (multi-user)

SwingLab keeps **practice stats on-device** in SQLite so Progress, favorites, notes, and settings survive packaging and optional archive of bulky video/JSON files.

Local **multi-profile** support lets several golfers share one machine (kiosk / family PC) without cloud accounts.

## Location

| Item | Default |
|------|---------|
| DB file | `{recordings_dir}/swinglab.db` |
| Override | env `SWINGLAB_DB_PATH` (absolute path) |
| JSON mirrors | `recording_meta.json`, `practice_settings.json` (active user’s backup) |

`recordings_dir` is the same folder Flask uses for MP4 / analysis JSON (typically `./recordings`).

**Packaging note:** treat `swinglab.db` as **user data**, not part of the app bundle. On first run, create/open it under a writable user directory (e.g. next to recordings). Never ship a shared DB inside a read-only install tree.

## What’s stored

| Table | Purpose |
|-------|---------|
| `users` | Local profiles (name, optional PIN hash, color) |
| `recording_owners` | Which profile owns each recording timestamp |
| `recording_meta` | favorite / notes / tags **per user** |
| `settings` | practice settings JSON **per user** |
| `swing_stats` | Progress metrics **per user** |
| `practice_events` | optional timeline **per user** |
| `schema_migrations` / `app_meta` | versioning, migration flags, `active_user_id` |

Schema version **2**. Full analysis timeseries remain in `analysis_*.json` (and videos as MP4).

## Multi-user behavior

- Fresh DB creates **Player 1** and sets them active
- Upgrading a v1 DB assigns all existing rows + ownership to Player 1
- New recordings are **claimed** for the active user when recording starts
- Library / Progress / practice settings follow the **active** user
- Unclaimed legacy files appear for the active user with a **Claim** action
- Claim never steals a recording already owned by another profile (API returns 409)
- Optional PIN required to switch into a locked profile
- User switch blocked while recording
- Last profile cannot be deleted; deleting a profile removes their stats/meta and reassigns file ownership to another profile

## Migration

On first open for a recordings folder:

1. Ensure schema (v1 → v2 multi-user if needed)
2. Import `recording_meta.json` / `practice_settings.json` for the active user
3. Scan `analysis_*.json` into `swing_stats` (skips other users’ owned timestamps)

Corrupt JSON does not prevent DB creation; bad entries are skipped.

## API

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/users` | List profiles + active |
| POST | `/api/users` | Create `{name, pin?, color?}` |
| PATCH | `/api/users/<id>` | Rename / set or clear PIN |
| DELETE | `/api/users/<id>` | Delete (not last; blocked while recording) |
| POST | `/api/users/active` | Switch `{user_id, pin?}` |
| POST | `/api/recordings/<ts>/claim` | Claim for active user |
| GET | `/api/recordings?scope=mine\|all\|unclaimed` | Default `mine` (+ unclaimed) |
| GET | `/api/status` | Includes `active_user` + `users` |
| GET | `/api/db/status` | Diagnostics + active user |

Meta / practice / progress APIs are unchanged in path; they operate on the **active** user.

## Edge cases covered by tests

See `tests/test_local_db.py`:

- Default user on fresh DB
- Per-user isolation of stats / settings / meta
- PIN gate on switch
- Cannot delete last user
- Claim / ownership (no steal; API 409 when already owned)
- Recordings `?scope=` filter
- Progress JSON fallback skips other users' files
- v1 → v2 migration keeps data under Player 1
- Progress API scoped to active user
- Switch blocked while recording
- Corrupt / empty legacy JSON
- Concurrent meta writes
- `SWINGLAB_DB_PATH` override

## Packaging / wizard

The setup wizard (`python scripts/setup_wizard.py`) writes `swinglab.local.json` with a `recordings_dir`. Flask honors `SWINGLAB_RECORDINGS_DIR` first, then that profile, then `./recordings`.

Still useful later:

1. Resolve `recordings_dir` to a per-install writable path when frozen (PyInstaller/`sys.frozen`)
2. Optional export/import of `swinglab.db` for backup
3. Optional cloud sync later — local profiles remain the source of truth offline
