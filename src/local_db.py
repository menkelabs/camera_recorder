"""
Local SQLite store for user practice stats.

Source of truth for:
  - recording meta (favorites / notes / tags)
  - practice settings (roles, metronome, session, reference)
  - swing_stats (score + trend metrics for Progress)
  - practice_events (optional session timeline)

DB path: ``{recordings_dir}/swinglab.db`` (override with env ``SWINGLAB_DB_PATH``).

On first open, migrates legacy JSON files and scans ``analysis_*.json`` into
``swing_stats``. Safe for Flask's threaded server (WAL + RLock).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

_TS_RE = re.compile(r'^\d{8}_\d{6}$')
_SCHEMA_VERSION = 1

_lock = threading.RLock()
_cache: Dict[str, 'LocalDB'] = {}


def _now() -> str:
    return datetime.now().isoformat(timespec='seconds')


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

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recording_meta (
                timestamp TEXT PRIMARY KEY,
                favorite INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS swing_stats (
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

            CREATE TABLE IF NOT EXISTS practice_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                timestamp TEXT,
                payload TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_swing_stats_date
                ON swing_stats(date);
            CREATE INDEX IF NOT EXISTS idx_recording_meta_favorite
                ON recording_meta(favorite);
            CREATE INDEX IF NOT EXISTS idx_practice_events_type
                ON practice_events(event_type);
            """
        )
        row = conn.execute(
            'SELECT MAX(version) AS v FROM schema_migrations'
        ).fetchone()
        current = int(row['v'] or 0)
        if current < _SCHEMA_VERSION:
            conn.execute(
                'INSERT OR REPLACE INTO schema_migrations(version, applied_at) VALUES (?, ?)',
                (_SCHEMA_VERSION, _now()),
            )
        conn.commit()

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

    # ------------------------------------------------------------------
    # Legacy JSON → SQLite (idempotent)
    # ------------------------------------------------------------------

    def _migrate_legacy_json(self) -> None:
        conn = self._require()
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
                                INSERT INTO recording_meta(timestamp, favorite, notes, tags, updated_at)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT(timestamp) DO UPDATE SET
                                  favorite = excluded.favorite,
                                  notes = excluded.notes,
                                  tags = excluded.tags,
                                  updated_at = excluded.updated_at
                                """,
                                (
                                    ts,
                                    1 if entry.get('favorite') else 0,
                                    str(entry.get('notes') or '')[:2000],
                                    json.dumps(list(tags)[:20]),
                                    entry.get('updated_at') or _now(),
                                ),
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
                        self._put_settings_unlocked('practice', data)
                except (OSError, json.JSONDecodeError, TypeError):
                    pass
            self._meta_set('migrated_practice_settings', '1')
            conn.commit()

    def _import_analysis_files(self) -> None:
        """Upsert swing_stats from analysis_*.json (always scans for new files)."""
        if not os.path.isdir(self.recordings_dir):
            return
        conn = self._require()
        existing = {
            r['timestamp']
            for r in conn.execute('SELECT timestamp FROM swing_stats').fetchall()
        }
        for name in os.listdir(self.recordings_dir):
            if not (name.startswith('analysis_') and name.endswith('.json')):
                continue
            ts = name[len('analysis_'):-len('.json')]
            if not _TS_RE.match(ts):
                continue
            # Re-import if missing; also refresh if file newer than row? keep simple: skip if present
            if ts in existing:
                continue
            path = os.path.join(self.recordings_dir, name)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    payload.setdefault('timestamp', ts)
                    self._upsert_swing_stats_unlocked(payload, source_path=path)
            except (OSError, json.JSONDecodeError, TypeError, ValueError):
                continue
        conn.commit()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def _put_settings_unlocked(self, key: str, value: Dict[str, Any]) -> None:
        self._require().execute(
            """
            INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
              value = excluded.value,
              updated_at = excluded.updated_at
            """,
            (key, json.dumps(value), _now()),
        )

    def get_practice_settings(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            row = self._require().execute(
                "SELECT value FROM settings WHERE key = 'practice'"
            ).fetchone()
            if not row:
                return None
            try:
                data = json.loads(row['value'])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None

    def save_practice_settings(self, data: Dict[str, Any]) -> None:
        with self._lock:
            self._put_settings_unlocked('practice', data)
            self._require().commit()
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

    def get_recording_meta(self, timestamp: str) -> Dict[str, Any]:
        if not _TS_RE.match(timestamp or ''):
            raise ValueError(f'Invalid timestamp format: {timestamp}')
        with self._lock:
            row = self._require().execute(
                'SELECT * FROM recording_meta WHERE timestamp = ?', (timestamp,)
            ).fetchone()
            if not row:
                return {
                    'timestamp': timestamp,
                    'favorite': False,
                    'notes': '',
                    'tags': [],
                    'updated_at': None,
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
            }

    def update_recording_meta(
        self,
        timestamp: str,
        *,
        favorite: Optional[bool] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not _TS_RE.match(timestamp or ''):
            raise ValueError(f'Invalid timestamp format: {timestamp}')
        with self._lock:
            current = self.get_recording_meta(timestamp)
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
                INSERT INTO recording_meta(timestamp, favorite, notes, tags, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(timestamp) DO UPDATE SET
                  favorite = excluded.favorite,
                  notes = excluded.notes,
                  tags = excluded.tags,
                  updated_at = excluded.updated_at
                """,
                (
                    timestamp,
                    1 if current['favorite'] else 0,
                    current['notes'],
                    json.dumps(current['tags']),
                    current['updated_at'],
                ),
            )
            self._require().commit()
            self._mirror_recording_meta_json()
            return current

    def delete_recording_meta(self, timestamp: str) -> None:
        if not _TS_RE.match(timestamp or ''):
            return
        with self._lock:
            self._require().execute(
                'DELETE FROM recording_meta WHERE timestamp = ?', (timestamp,)
            )
            self._require().commit()
            self._mirror_recording_meta_json()

    def list_favorites(self) -> List[str]:
        with self._lock:
            rows = self._require().execute(
                'SELECT timestamp FROM recording_meta WHERE favorite = 1 '
                'ORDER BY timestamp DESC'
            ).fetchall()
            return [r['timestamp'] for r in rows]

    def all_recording_meta(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            rows = self._require().execute('SELECT * FROM recording_meta').fetchall()
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

    def upsert_swing_stats(self, analysis: Dict[str, Any], source_path: Optional[str] = None) -> None:
        with self._lock:
            self._upsert_swing_stats_unlocked(analysis, source_path=source_path)
            self._require().commit()

    def _upsert_swing_stats_unlocked(
        self, analysis: Dict[str, Any], source_path: Optional[str] = None
    ) -> None:
        from swing_score import score_analysis

        ts = analysis.get('timestamp')
        if not ts or not _TS_RE.match(str(ts)):
            raise ValueError(f'Invalid analysis timestamp: {ts}')

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
            'SELECT created_at FROM swing_stats WHERE timestamp = ?', (ts,)
        ).fetchone()
        created = existing['created_at'] if existing else now

        self._require().execute(
            """
            INSERT INTO swing_stats(
              timestamp, date, score, grade,
              max_shoulder_turn, max_hip_turn, max_x_factor,
              tempo_ratio, max_sway_right, max_head_sway_right,
              detection_rate_cam1, detection_rate_cam2,
              source_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(timestamp) DO UPDATE SET
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

    def delete_swing_stats(self, timestamp: str) -> None:
        if not _TS_RE.match(timestamp or ''):
            return
        with self._lock:
            self._require().execute(
                'DELETE FROM swing_stats WHERE timestamp = ?', (timestamp,)
            )
            self._require().commit()

    def delete_recording(self, timestamp: str) -> None:
        """Remove meta + stats for a deleted recording."""
        if not _TS_RE.match(timestamp or ''):
            return
        with self._lock:
            conn = self._require()
            conn.execute('DELETE FROM recording_meta WHERE timestamp = ?', (timestamp,))
            conn.execute('DELETE FROM swing_stats WHERE timestamp = ?', (timestamp,))
            conn.commit()
            self._mirror_recording_meta_json()

    def list_swing_stats(self) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._require().execute(
                'SELECT * FROM swing_stats ORDER BY timestamp ASC'
            ).fetchall()
            out = []
            for r in rows:
                out.append({
                    'timestamp': r['timestamp'],
                    'date': r['date'],
                    'score': r['score'],
                    'grade': r['grade'],
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
    ) -> int:
        with self._lock:
            cur = self._require().execute(
                """
                INSERT INTO practice_events(event_type, timestamp, payload, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    event_type,
                    timestamp,
                    json.dumps(payload) if payload is not None else None,
                    _now(),
                ),
            )
            self._require().commit()
            return int(cur.lastrowid)

    def list_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            rows = self._require().execute(
                'SELECT * FROM practice_events ORDER BY id DESC LIMIT ?',
                (max(1, min(limit, 1000)),),
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
            swings = conn.execute('SELECT COUNT(*) AS c FROM swing_stats').fetchone()['c']
            favs = conn.execute(
                'SELECT COUNT(*) AS c FROM recording_meta WHERE favorite = 1'
            ).fetchone()['c']
            events = conn.execute('SELECT COUNT(*) AS c FROM practice_events').fetchone()['c']
            return {
                'db_path': self.path,
                'swing_count': swings,
                'favorite_count': favs,
                'event_count': events,
                'integrity': self.integrity_check(),
            }
