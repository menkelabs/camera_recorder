"""
Local SQLite store for multi-user practice stats.

Source of truth for:
  - local user profiles (shared-machine / kiosk)
  - recording ownership (which user recorded a swing)
  - recording meta (favorites / notes / tags) per user
  - practice settings per user
  - swing_stats (Progress) per user
  - practice_events (optional session timeline) per user

DB path: ``{recordings_dir}/swinglab.db`` (override with env ``SWINGLAB_DB_PATH``).

On first open, migrates legacy JSON files and scans ``analysis_*.json`` into
``swing_stats``. Safe for Flask's threaded server (WAL + RLock).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

_TS_RE = re.compile(r'^\d{8}_\d{6}$')
_SCHEMA_VERSION = 2
_DEFAULT_USER_NAME = 'Player 1'
_NAME_MAX = 40

_lock = threading.RLock()
_cache: Dict[str, 'LocalDB'] = {}


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')


def _hash_pin(pin: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.sha256(f'{salt}:{pin}'.encode('utf-8')).hexdigest()
    return f'{salt}${digest}'


def _verify_pin(pin: str, stored: Optional[str]) -> bool:
    if not stored or '$' not in stored:
        return False
    salt, digest = stored.split('$', 1)
    check = _hash_pin(pin, salt).split('$', 1)[1]
    return hmac.compare_digest(check, digest)


def db_path_for(recordings_dir: str) -> str:
    env = os.environ.get('SWINGLAB_DB_PATH')
    if env:
        return env
    return os.path.join(recordings_dir, 'swinglab.db')


def get_db(recordings_dir: str) -> 'LocalDB':
    """Return a cached LocalDB for *recordings_dir* (creates/migrates on first use)."""
    key = os.path.abspath(recordings_dir or '.')
    with _lock:
        db = _cache.get(key)
        if db is None:
            db = LocalDB(key)
            db.open()
            _cache[key] = db
        return db


def reset_db_cache() -> None:
    """Close and drop cached connections (tests)."""
    with _lock:
        for db in _cache.values():
            try:
                db.close()
            except Exception:
                pass
        _cache.clear()


class LocalDB:
    def __init__(self, recordings_dir: str):
        self.recordings_dir = recordings_dir
        self.path = db_path_for(recordings_dir)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self) -> None:
        with self._lock:
            if self._conn is not None:
                return
            os.makedirs(self.recordings_dir, exist_ok=True)
            parent = os.path.dirname(os.path.abspath(self.path))
            if parent:
                os.makedirs(parent, exist_ok=True)
            self._conn = sqlite3.connect(
                self.path,
                check_same_thread=False,
                timeout=30.0,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute('PRAGMA journal_mode=WAL')
            self._conn.execute('PRAGMA synchronous=NORMAL')
            self._conn.execute('PRAGMA foreign_keys=ON')
            self._ensure_schema()
            self._migrate_legacy_json()
            self._import_analysis_files()

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                try:
                    self._conn.close()
                finally:
                    self._conn = None

    def _require(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError('LocalDB is not open')
        return self._conn

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _table_exists(self, name: str) -> bool:
        row = self._require().execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (name,),
        ).fetchone()
        return bool(row)

    def _columns(self, table: str) -> List[str]:
        return [
            r[1] for r in self._require().execute(f'PRAGMA table_info({table})').fetchall()
        ]

    def _schema_version(self) -> int:
        row = self._require().execute(
            'SELECT MAX(version) AS v FROM schema_migrations'
        ).fetchone()
        return int(row['v'] or 0)

    def _set_schema_version(self, version: int) -> None:
        self._require().execute(
            'INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES (?, ?)',
            (version, _now()),
        )

    def _ensure_schema(self) -> None:
        conn = self._require()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        # Create v1-shaped tables when missing so upgrades share one path.
        if not self._table_exists('settings'):
            conn.executescript(
                """
                CREATE TABLE settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE recording_meta (
                    timestamp TEXT PRIMARY KEY,
                    favorite INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT
                );
                CREATE TABLE swing_stats (
                    timestamp TEXT PRIMARY KEY,
                    date TEXT,
                    score REAL,
                    grade TEXT,
                    max_shoulder_turn REAL,
                    max_hip_turn REAL,
                    max_x_factor REAL,
                    tempo_ratio REAL,
                    max_sway_right REAL,
                    max_head_sway_right REAL,
                    detection_rate_cam1 REAL,
                    detection_rate_cam2 REAL,
                    source_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE practice_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    timestamp TEXT,
                    payload TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

        current = self._schema_version()
        if current < 1:
            self._set_schema_version(1)
            current = 1
        if current < 2:
            self._migrate_v1_to_v2()
            self._set_schema_version(2)
        self._ensure_default_user()
        conn.commit()

    def _migrate_v1_to_v2(self) -> None:
        """Add users + per-user scoping. Idempotent if already partially applied."""
        conn = self._require()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                pin_hash TEXT,
                color TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recording_owners (
                timestamp TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                claimed_at TEXT NOT NULL
            );
            """
        )

        uid = self._ensure_default_user()

        if 'user_id' not in self._columns('settings'):
            conn.executescript(
                """
                CREATE TABLE settings_v2 (
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, key)
                );
                """
            )
            conn.execute(
                """
                INSERT INTO settings_v2(user_id, key, value, updated_at)
                SELECT ?, key, value, updated_at FROM settings
                """,
                (uid,),
            )
            conn.execute('DROP TABLE settings')
            conn.execute('ALTER TABLE settings_v2 RENAME TO settings')

        if 'user_id' not in self._columns('recording_meta'):
            conn.executescript(
                """
                CREATE TABLE recording_meta_v2 (
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    timestamp TEXT NOT NULL,
                    favorite INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT,
                    PRIMARY KEY (user_id, timestamp)
                );
                """
            )
            conn.execute(
                """
                INSERT INTO recording_meta_v2(
                  user_id, timestamp, favorite, notes, tags, updated_at
                )
                SELECT ?, timestamp, favorite, notes, tags, updated_at
                FROM recording_meta
                """,
                (uid,),
            )
            conn.execute('DROP TABLE recording_meta')
            conn.execute('ALTER TABLE recording_meta_v2 RENAME TO recording_meta')

        if 'user_id' not in self._columns('swing_stats'):
            conn.executescript(
                """
                CREATE TABLE swing_stats_v2 (
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    timestamp TEXT NOT NULL,
                    date TEXT,
                    score REAL,
                    grade TEXT,
                    max_shoulder_turn REAL,
                    max_hip_turn REAL,
                    max_x_factor REAL,
                    tempo_ratio REAL,
                    max_sway_right REAL,
                    max_head_sway_right REAL,
                    detection_rate_cam1 REAL,
                    detection_rate_cam2 REAL,
                    source_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, timestamp)
                );
                """
            )
            conn.execute(
                """
                INSERT INTO swing_stats_v2(
                  user_id, timestamp, date, score, grade,
                  max_shoulder_turn, max_hip_turn, max_x_factor,
                  tempo_ratio, max_sway_right, max_head_sway_right,
                  detection_rate_cam1, detection_rate_cam2,
                  source_path, created_at, updated_at
                )
                SELECT ?, timestamp, date, score, grade,
                  max_shoulder_turn, max_hip_turn, max_x_factor,
                  tempo_ratio, max_sway_right, max_head_sway_right,
                  detection_rate_cam1, detection_rate_cam2,
                  source_path, created_at, updated_at
                FROM swing_stats
                """,
                (uid,),
            )
            conn.execute('DROP TABLE swing_stats')
            conn.execute('ALTER TABLE swing_stats_v2 RENAME TO swing_stats')

        if 'user_id' not in self._columns('practice_events'):
            conn.executescript(
                """
                CREATE TABLE practice_events_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    timestamp TEXT,
                    payload TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                INSERT INTO practice_events_v2(
                  user_id, event_type, timestamp, payload, created_at
                )
                SELECT ?, event_type, timestamp, payload, created_at
                FROM practice_events
                """,
                (uid,),
            )
            conn.execute('DROP TABLE practice_events')
            conn.execute('ALTER TABLE practice_events_v2 RENAME TO practice_events')

        # Backfill ownership from known timestamps
        timestamps = set()
        for table in ('recording_meta', 'swing_stats'):
            for row in conn.execute(f'SELECT DISTINCT timestamp FROM {table}').fetchall():
                timestamps.add(row['timestamp'])
        for ts in timestamps:
            if not _TS_RE.match(str(ts)):
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO recording_owners(timestamp, user_id, claimed_at)
                VALUES (?, ?, ?)
                """,
                (ts, uid, _now()),
            )

        if self._meta_get('active_user_id') is None:
            self._meta_set('active_user_id', str(uid))

        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_swing_stats_user_date
                ON swing_stats(user_id, date);
            CREATE INDEX IF NOT EXISTS idx_recording_meta_user_favorite
                ON recording_meta(user_id, favorite);
            CREATE INDEX IF NOT EXISTS idx_practice_events_user_type
                ON practice_events(user_id, event_type);
            CREATE INDEX IF NOT EXISTS idx_recording_owners_user
                ON recording_owners(user_id);
            """
        )

    def _ensure_default_user(self) -> int:
        conn = self._require()
        row = conn.execute(
            'SELECT id FROM users ORDER BY id ASC LIMIT 1'
        ).fetchone()
        if row:
            uid = int(row['id'])
            if self._meta_get('active_user_id') is None:
                self._meta_set('active_user_id', str(uid))
            return uid
        now = _now()
        cur = conn.execute(
            """
            INSERT INTO users(name, pin_hash, color, created_at, updated_at)
            VALUES (?, NULL, ?, ?, ?)
            """,
            (_DEFAULT_USER_NAME, '#3fb950', now, now),
        )
        uid = int(cur.lastrowid)
        self._meta_set('active_user_id', str(uid))
        return uid

    def _meta_get(self, key: str) -> Optional[str]:
        row = self._require().execute(
            'SELECT value FROM app_meta WHERE key = ?', (key,)
        ).fetchone()
        return row['value'] if row else None

    def _meta_set(self, key: str, value: str) -> None:
        self._require().execute(
            'INSERT INTO app_meta(key, value) VALUES (?, ?) '
            'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
            (key, value),
        )

    def _user_row_to_dict(self, row: sqlite3.Row, *, active_id: Optional[int] = None) -> Dict[str, Any]:
        uid = int(row['id'])
        return {
            'id': uid,
            'name': row['name'],
            'has_pin': bool(row['pin_hash']),
            'color': row['color'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at'],
            'is_active': active_id is not None and uid == active_id,
        }

    def _normalize_name(self, name: str) -> str:
        cleaned = ' '.join(str(name or '').strip().split())
        if not cleaned:
            raise ValueError('User name is required')
        if len(cleaned) > _NAME_MAX:
            raise ValueError(f'User name must be <= {_NAME_MAX} characters')
        return cleaned

    def _get_user_row(self, user_id: int) -> sqlite3.Row:
        row = self._require().execute(
            'SELECT * FROM users WHERE id = ?', (user_id,)
        ).fetchone()
        if not row:
            raise ValueError(f'User not found: {user_id}')
        return row

    # ------------------------------------------------------------------
    # Users / profiles
    # ------------------------------------------------------------------

    def get_active_user_id(self) -> int:
        with self._lock:
            raw = self._meta_get('active_user_id')
            if raw and raw.isdigit():
                uid = int(raw)
                exists = self._require().execute(
                    'SELECT 1 FROM users WHERE id = ?', (uid,)
                ).fetchone()
                if exists:
                    return uid
            return self._ensure_default_user()

    def get_active_user(self) -> Dict[str, Any]:
        with self._lock:
            uid = self.get_active_user_id()
            row = self._get_user_row(uid)
            return self._user_row_to_dict(row, active_id=uid)

    def list_users(self) -> List[Dict[str, Any]]:
        with self._lock:
            active = self.get_active_user_id()
            rows = self._require().execute(
                'SELECT * FROM users ORDER BY id ASC'
            ).fetchall()
            return [self._user_row_to_dict(r, active_id=active) for r in rows]

    def create_user(self, name: str, pin: Optional[str] = None, color: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            cleaned = self._normalize_name(name)
            pin_hash = None
            if pin is not None and str(pin).strip() != '':
                if len(str(pin)) < 4:
                    raise ValueError('PIN must be at least 4 characters')
                pin_hash = _hash_pin(str(pin))
            now = _now()
            cur = self._require().execute(
                """
                INSERT INTO users(name, pin_hash, color, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cleaned, pin_hash, color or '#58a6ff', now, now),
            )
            self._require().commit()
            return self._user_row_to_dict(
                self._get_user_row(int(cur.lastrowid)),
                active_id=self.get_active_user_id(),
            )

    def update_user(
        self,
        user_id: int,
        *,
        name: Optional[str] = None,
        pin: Optional[str] = None,
        clear_pin: bool = False,
        color: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            row = self._get_user_row(user_id)
            new_name = self._normalize_name(name) if name is not None else row['name']
            new_color = color if color is not None else row['color']
            pin_hash = row['pin_hash']
            if clear_pin:
                pin_hash = None
            elif pin is not None:
                if str(pin).strip() == '':
                    pin_hash = None
                else:
                    if len(str(pin)) < 4:
                        raise ValueError('PIN must be at least 4 characters')
                    pin_hash = _hash_pin(str(pin))
            self._require().execute(
                """
                UPDATE users SET name = ?, pin_hash = ?, color = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_name, pin_hash, new_color, _now(), user_id),
            )
            self._require().commit()
            return self._user_row_to_dict(
                self._get_user_row(user_id),
                active_id=self.get_active_user_id(),
            )

    def delete_user(self, user_id: int) -> None:
        with self._lock:
            users = self._require().execute('SELECT id FROM users ORDER BY id').fetchall()
            if len(users) <= 1:
                raise ValueError('Cannot delete the last user')
            self._get_user_row(user_id)
            active = self.get_active_user_id()
            # Reassign owned recordings to the next remaining user
            fallback = next(int(r['id']) for r in users if int(r['id']) != user_id)
            self._require().execute(
                'UPDATE recording_owners SET user_id = ? WHERE user_id = ?',
                (fallback, user_id),
            )
            self._require().execute('DELETE FROM users WHERE id = ?', (user_id,))
            if active == user_id:
                self._meta_set('active_user_id', str(fallback))
            self._require().commit()

    def set_active_user(self, user_id: int, pin: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            row = self._get_user_row(user_id)
            if row['pin_hash']:
                if pin is None or not _verify_pin(str(pin), row['pin_hash']):
                    raise PermissionError('Incorrect PIN')
            self._meta_set('active_user_id', str(user_id))
            self._require().commit()
            return self._user_row_to_dict(row, active_id=user_id)

    # ------------------------------------------------------------------
    # Recording ownership
    # ------------------------------------------------------------------

    def get_recording_owner(self, timestamp: str) -> Optional[int]:
        if not _TS_RE.match(timestamp or ''):
            return None
        with self._lock:
            row = self._require().execute(
                'SELECT user_id FROM recording_owners WHERE timestamp = ?',
                (timestamp,),
            ).fetchone()
            return int(row['user_id']) if row else None

    def claim_recording(self, timestamp: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        if not _TS_RE.match(timestamp or ''):
            raise ValueError(f'Invalid timestamp format: {timestamp}')
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            self._get_user_row(uid)
            self._require().execute(
                """
                INSERT INTO recording_owners(timestamp, user_id, claimed_at)
                VALUES (?, ?, ?)
                ON CONFLICT(timestamp) DO UPDATE SET
                  user_id = excluded.user_id,
                  claimed_at = excluded.claimed_at
                """,
                (timestamp, uid, _now()),
            )
            self._require().commit()
            return {'timestamp': timestamp, 'user_id': uid}

    def list_owned_timestamps(self, user_id: Optional[int] = None) -> List[str]:
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            rows = self._require().execute(
                'SELECT timestamp FROM recording_owners WHERE user_id = ? '
                'ORDER BY timestamp DESC',
                (uid,),
            ).fetchall()
            return [r['timestamp'] for r in rows]

    def ownership_map(self) -> Dict[str, int]:
        with self._lock:
            rows = self._require().execute(
                'SELECT timestamp, user_id FROM recording_owners'
            ).fetchall()
            return {r['timestamp']: int(r['user_id']) for r in rows}

    # ------------------------------------------------------------------
    # Legacy JSON → SQLite (idempotent)
    # ------------------------------------------------------------------

    def _migrate_legacy_json(self) -> None:
        conn = self._require()
        uid = self.get_active_user_id()
        # recording_meta.json
        if self._meta_get('migrated_recording_meta') != '1':
            path = os.path.join(self.recordings_dir, 'recording_meta.json')
            if os.path.isfile(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    recs = data.get('recordings') or {}
                    if isinstance(recs, dict):
                        for ts, entry in recs.items():
                            if not _TS_RE.match(str(ts)):
                                continue
                            if not isinstance(entry, dict):
                                entry = {}
                            tags = entry.get('tags') or []
                            if not isinstance(tags, list):
                                tags = []
                            conn.execute(
                                """
                                INSERT INTO recording_meta(
                                  user_id, timestamp, favorite, notes, tags, updated_at
                                )
                                VALUES (?, ?, ?, ?, ?, ?)
                                ON CONFLICT(user_id, timestamp) DO UPDATE SET
                                  favorite = excluded.favorite,
                                  notes = excluded.notes,
                                  tags = excluded.tags,
                                  updated_at = excluded.updated_at
                                """,
                                (
                                    uid,
                                    ts,
                                    1 if entry.get('favorite') else 0,
                                    str(entry.get('notes') or '')[:2000],
                                    json.dumps(list(tags)[:20]),
                                    entry.get('updated_at') or _now(),
                                ),
                            )
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO recording_owners(
                                  timestamp, user_id, claimed_at
                                ) VALUES (?, ?, ?)
                                """,
                                (ts, uid, _now()),
                            )
                except (OSError, json.JSONDecodeError, TypeError):
                    pass
            self._meta_set('migrated_recording_meta', '1')
            conn.commit()

        # practice_settings.json
        if self._meta_get('migrated_practice_settings') != '1':
            path = os.path.join(self.recordings_dir, 'practice_settings.json')
            if os.path.isfile(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        self._put_settings_unlocked('practice', data, user_id=uid)
                except (OSError, json.JSONDecodeError, TypeError):
                    pass
            self._meta_set('migrated_practice_settings', '1')
            conn.commit()

    def _import_analysis_files(self) -> None:
        """Upsert swing_stats from analysis_*.json for the active user."""
        if not os.path.isdir(self.recordings_dir):
            return
        conn = self._require()
        uid = self.get_active_user_id()
        existing = {
            r['timestamp']
            for r in conn.execute(
                'SELECT timestamp FROM swing_stats WHERE user_id = ?', (uid,)
            ).fetchall()
        }
        for name in os.listdir(self.recordings_dir):
            if not (name.startswith('analysis_') and name.endswith('.json')):
                continue
            ts = name[len('analysis_'):-len('.json')]
            if not _TS_RE.match(ts):
                continue
            if ts in existing:
                continue
            # Skip files already owned by another user
            owner = conn.execute(
                'SELECT user_id FROM recording_owners WHERE timestamp = ?', (ts,)
            ).fetchone()
            if owner and int(owner['user_id']) != uid:
                continue
            path = os.path.join(self.recordings_dir, name)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    payload.setdefault('timestamp', ts)
                    self._upsert_swing_stats_unlocked(
                        payload, source_path=path, user_id=uid,
                    )
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO recording_owners(
                          timestamp, user_id, claimed_at
                        ) VALUES (?, ?, ?)
                        """,
                        (ts, uid, _now()),
                    )
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
        conn.commit()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _put_settings_unlocked(
        self, key: str, value: Dict[str, Any], user_id: Optional[int] = None,
    ) -> None:
        uid = user_id if user_id is not None else self.get_active_user_id()
        self._require().execute(
            """
            INSERT INTO settings(user_id, key, value, updated_at) VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, key) DO UPDATE SET
              value = excluded.value,
              updated_at = excluded.updated_at
            """,
            (uid, key, json.dumps(value), _now()),
        )

    def get_practice_settings(self, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            row = self._require().execute(
                "SELECT value FROM settings WHERE user_id = ? AND key = 'practice'",
                (uid,),
            ).fetchone()
            if not row:
                return None
            try:
                data = json.loads(row['value'])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None

    def save_practice_settings(
        self, data: Dict[str, Any], user_id: Optional[int] = None,
    ) -> None:
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            self._put_settings_unlocked('practice', data, user_id=uid)
            self._require().commit()
            # Mirror only the active user's settings for older tooling
            if uid == self.get_active_user_id():
                self._mirror_practice_settings_json(data)

    def _mirror_practice_settings_json(self, data: Dict[str, Any]) -> None:
        """Best-effort JSON backup for humans / older tooling."""
        path = os.path.join(self.recordings_dir, 'practice_settings.json')
        try:
            tmp = path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                f.write('\n')
            os.replace(tmp, path)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Recording meta
    # ------------------------------------------------------------------

    def get_recording_meta(
        self, timestamp: str, user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not _TS_RE.match(timestamp or ''):
            raise ValueError(f'Invalid timestamp format: {timestamp}')
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            row = self._require().execute(
                'SELECT * FROM recording_meta WHERE user_id = ? AND timestamp = ?',
                (uid, timestamp),
            ).fetchone()
            if not row:
                return {
                    'timestamp': timestamp,
                    'favorite': False,
                    'notes': '',
                    'tags': [],
                    'updated_at': None,
                    'user_id': uid,
                }
            try:
                tags = json.loads(row['tags'] or '[]')
            except json.JSONDecodeError:
                tags = []
            if not isinstance(tags, list):
                tags = []
            return {
                'timestamp': timestamp,
                'favorite': bool(row['favorite']),
                'notes': row['notes'] or '',
                'tags': tags,
                'updated_at': row['updated_at'],
                'user_id': uid,
            }

    def update_recording_meta(
        self,
        timestamp: str,
        *,
        favorite: Optional[bool] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not _TS_RE.match(timestamp or ''):
            raise ValueError(f'Invalid timestamp format: {timestamp}')
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            current = self.get_recording_meta(timestamp, user_id=uid)
            if favorite is not None:
                current['favorite'] = bool(favorite)
            if notes is not None:
                current['notes'] = str(notes)[:2000]
            if tags is not None:
                cleaned: List[str] = []
                for t in tags:
                    s = str(t).strip()[:40]
                    if s and s not in cleaned:
                        cleaned.append(s)
                current['tags'] = cleaned[:20]
            current['updated_at'] = _now()
            self._require().execute(
                """
                INSERT INTO recording_meta(
                  user_id, timestamp, favorite, notes, tags, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, timestamp) DO UPDATE SET
                  favorite = excluded.favorite,
                  notes = excluded.notes,
                  tags = excluded.tags,
                  updated_at = excluded.updated_at
                """,
                (
                    uid,
                    timestamp,
                    1 if current['favorite'] else 0,
                    current['notes'],
                    json.dumps(current['tags']),
                    current['updated_at'],
                ),
            )
            # Favoriting / annotating implies ownership for the active user
            # only when unclaimed (do not steal from another user).
            owner = self._require().execute(
                'SELECT user_id FROM recording_owners WHERE timestamp = ?',
                (timestamp,),
            ).fetchone()
            if not owner:
                self._require().execute(
                    """
                    INSERT INTO recording_owners(timestamp, user_id, claimed_at)
                    VALUES (?, ?, ?)
                    """,
                    (timestamp, uid, _now()),
                )
            self._require().commit()
            if uid == self.get_active_user_id():
                self._mirror_recording_meta_json()
            return current

    def delete_recording_meta(self, timestamp: str, user_id: Optional[int] = None) -> None:
        if not _TS_RE.match(timestamp or ''):
            return
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            self._require().execute(
                'DELETE FROM recording_meta WHERE user_id = ? AND timestamp = ?',
                (uid, timestamp),
            )
            self._require().commit()
            if uid == self.get_active_user_id():
                self._mirror_recording_meta_json()

    def list_favorites(self, user_id: Optional[int] = None) -> List[str]:
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            rows = self._require().execute(
                'SELECT timestamp FROM recording_meta '
                'WHERE user_id = ? AND favorite = 1 '
                'ORDER BY timestamp DESC',
                (uid,),
            ).fetchall()
            return [r['timestamp'] for r in rows]

    def all_recording_meta(self, user_id: Optional[int] = None) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            rows = self._require().execute(
                'SELECT * FROM recording_meta WHERE user_id = ?', (uid,)
            ).fetchall()
            out: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                try:
                    tags = json.loads(row['tags'] or '[]')
                except json.JSONDecodeError:
                    tags = []
                out[row['timestamp']] = {
                    'favorite': bool(row['favorite']),
                    'notes': row['notes'] or '',
                    'tags': tags if isinstance(tags, list) else [],
                    'updated_at': row['updated_at'],
                }
            return out

    def _mirror_recording_meta_json(self) -> None:
        path = os.path.join(self.recordings_dir, 'recording_meta.json')
        try:
            data = {'version': 1, 'recordings': self.all_recording_meta()}
            tmp = path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                f.write('\n')
            os.replace(tmp, path)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Swing stats (Progress)
    # ------------------------------------------------------------------

    def upsert_swing_stats(
        self,
        analysis: Dict[str, Any],
        source_path: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> None:
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            self._upsert_swing_stats_unlocked(
                analysis, source_path=source_path, user_id=uid,
            )
            ts = analysis.get('timestamp')
            if ts and _TS_RE.match(str(ts)):
                # Claim only when unowned — never steal from another profile
                self._require().execute(
                    """
                    INSERT OR IGNORE INTO recording_owners(
                      timestamp, user_id, claimed_at
                    ) VALUES (?, ?, ?)
                    """,
                    (str(ts), uid, _now()),
                )
            self._require().commit()

    def _upsert_swing_stats_unlocked(
        self,
        analysis: Dict[str, Any],
        source_path: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> None:
        from swing_score import score_analysis

        ts = analysis.get('timestamp')
        if not ts or not _TS_RE.match(str(ts)):
            raise ValueError(f'Invalid analysis timestamp: {ts}')

        uid = user_id if user_id is not None else self.get_active_user_id()
        scored = analysis.get('score')
        if not isinstance(scored, dict) or scored.get('score') is None:
            scored = score_analysis(analysis)

        def summary(cam: int) -> Dict:
            block = analysis.get('camera1' if cam == 1 else 'camera2') or {}
            return block.get('summary') or {}

        s1 = summary(1)
        s2 = summary(2)
        date = analysis.get('date')
        if not date:
            try:
                date = datetime.strptime(ts, '%Y%m%d_%H%M%S').strftime('%Y-%m-%d %H:%M')
            except ValueError:
                date = ts

        cam1 = analysis.get('camera1') or {}
        cam2 = analysis.get('camera2') or {}
        now = _now()
        existing = self._require().execute(
            'SELECT created_at FROM swing_stats WHERE user_id = ? AND timestamp = ?',
            (uid, ts),
        ).fetchone()
        created = existing['created_at'] if existing else now

        self._require().execute(
            """
            INSERT INTO swing_stats(
              user_id, timestamp, date, score, grade,
              max_shoulder_turn, max_hip_turn, max_x_factor,
              tempo_ratio, max_sway_right, max_head_sway_right,
              detection_rate_cam1, detection_rate_cam2,
              source_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, timestamp) DO UPDATE SET
              date = excluded.date,
              score = excluded.score,
              grade = excluded.grade,
              max_shoulder_turn = excluded.max_shoulder_turn,
              max_hip_turn = excluded.max_hip_turn,
              max_x_factor = excluded.max_x_factor,
              tempo_ratio = excluded.tempo_ratio,
              max_sway_right = excluded.max_sway_right,
              max_head_sway_right = excluded.max_head_sway_right,
              detection_rate_cam1 = excluded.detection_rate_cam1,
              detection_rate_cam2 = excluded.detection_rate_cam2,
              source_path = excluded.source_path,
              updated_at = excluded.updated_at
            """,
            (
                uid,
                ts,
                date,
                scored.get('score'),
                scored.get('grade'),
                s2.get('max_shoulder_turn'),
                s2.get('max_hip_turn'),
                s2.get('max_x_factor'),
                s1.get('tempo_ratio'),
                s1.get('max_sway_right'),
                s1.get('max_head_sway_right'),
                cam1.get('detection_rate'),
                cam2.get('detection_rate'),
                source_path,
                created,
                now,
            ),
        )

    def delete_swing_stats(self, timestamp: str, user_id: Optional[int] = None) -> None:
        if not _TS_RE.match(timestamp or ''):
            return
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            self._require().execute(
                'DELETE FROM swing_stats WHERE user_id = ? AND timestamp = ?',
                (uid, timestamp),
            )
            self._require().commit()

    def delete_recording(self, timestamp: str) -> None:
        """Remove meta + stats + ownership for a deleted recording (all users)."""
        if not _TS_RE.match(timestamp or ''):
            return
        with self._lock:
            conn = self._require()
            conn.execute('DELETE FROM recording_meta WHERE timestamp = ?', (timestamp,))
            conn.execute('DELETE FROM swing_stats WHERE timestamp = ?', (timestamp,))
            conn.execute('DELETE FROM recording_owners WHERE timestamp = ?', (timestamp,))
            conn.commit()
            self._mirror_recording_meta_json()

    def list_swing_stats(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            rows = self._require().execute(
                'SELECT * FROM swing_stats WHERE user_id = ? ORDER BY timestamp ASC',
                (uid,),
            ).fetchall()
            out = []
            for r in rows:
                out.append({
                    'timestamp': r['timestamp'],
                    'date': r['date'],
                    'score': r['score'],
                    'grade': r['grade'],
                    'user_id': r['user_id'],
                    'metrics': {
                        'score': r['score'],
                        'max_shoulder_turn': r['max_shoulder_turn'],
                        'max_hip_turn': r['max_hip_turn'],
                        'max_x_factor': r['max_x_factor'],
                        'tempo_ratio': r['tempo_ratio'],
                        'max_sway_right': r['max_sway_right'],
                        'max_head_sway_right': r['max_head_sway_right'],
                    },
                    'detection_rate_cam1': r['detection_rate_cam1'],
                    'detection_rate_cam2': r['detection_rate_cam2'],
                })
            return out

    # ------------------------------------------------------------------
    # Practice events
    # ------------------------------------------------------------------

    def add_event(
        self,
        event_type: str,
        timestamp: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> int:
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            cur = self._require().execute(
                """
                INSERT INTO practice_events(
                  user_id, event_type, timestamp, payload, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    uid,
                    event_type,
                    timestamp,
                    json.dumps(payload) if payload is not None else None,
                    _now(),
                ),
            )
            self._require().commit()
            return int(cur.lastrowid)

    def list_events(
        self, limit: int = 100, user_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            uid = user_id if user_id is not None else self.get_active_user_id()
            rows = self._require().execute(
                'SELECT * FROM practice_events WHERE user_id = ? '
                'ORDER BY id DESC LIMIT ?',
                (uid, max(1, min(limit, 1000))),
            ).fetchall()
            out = []
            for r in rows:
                payload = None
                if r['payload']:
                    try:
                        payload = json.loads(r['payload'])
                    except json.JSONDecodeError:
                        payload = r['payload']
                out.append({
                    'id': r['id'],
                    'user_id': r['user_id'],
                    'event_type': r['event_type'],
                    'timestamp': r['timestamp'],
                    'payload': payload,
                    'created_at': r['created_at'],
                })
            return out

    # ------------------------------------------------------------------
    # Integrity helpers
    # ------------------------------------------------------------------

    def integrity_check(self) -> str:
        with self._lock:
            row = self._require().execute('PRAGMA integrity_check').fetchone()
            return str(row[0] if row else 'unknown')

    def stats_summary(self) -> Dict[str, Any]:
        with self._lock:
            conn = self._require()
            uid = self.get_active_user_id()
            swings = conn.execute(
                'SELECT COUNT(*) AS c FROM swing_stats WHERE user_id = ?', (uid,)
            ).fetchone()['c']
            favs = conn.execute(
                'SELECT COUNT(*) AS c FROM recording_meta '
                'WHERE user_id = ? AND favorite = 1',
                (uid,),
            ).fetchone()['c']
            events = conn.execute(
                'SELECT COUNT(*) AS c FROM practice_events WHERE user_id = ?',
                (uid,),
            ).fetchone()['c']
            users = conn.execute('SELECT COUNT(*) AS c FROM users').fetchone()['c']
            active = self.get_active_user()
            return {
                'db_path': self.path,
                'schema_version': self._schema_version(),
                'swing_count': swings,
                'favorite_count': favs,
                'event_count': events,
                'user_count': users,
                'active_user': active,
                'integrity': self.integrity_check(),
            }
