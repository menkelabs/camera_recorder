"""
Per-recording metadata: favorites, notes, and tags.

Stored as recordings/recording_meta.json so notes survive even when
analysis JSON is archived separately.
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

_lock = threading.Lock()
_TS_RE = re.compile(r'^\d{8}_\d{6}$')


def meta_path(recordings_dir: str) -> str:
    return os.path.join(recordings_dir, 'recording_meta.json')


def _empty() -> Dict[str, Any]:
    return {'version': 1, 'recordings': {}}


def load_meta(recordings_dir: str) -> Dict[str, Any]:
    path = meta_path(recordings_dir)
    if not os.path.exists(path):
        return _empty()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty()
        data.setdefault('version', 1)
        data.setdefault('recordings', {})
        return data
    except (json.JSONDecodeError, OSError):
        return _empty()


def save_meta(recordings_dir: str, data: Dict[str, Any]) -> None:
    path = meta_path(recordings_dir)
    os.makedirs(recordings_dir, exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    os.replace(tmp, path)


def _validate_ts(timestamp: str) -> None:
    if not _TS_RE.match(timestamp or ''):
        raise ValueError(f'Invalid timestamp format: {timestamp}')


def get_recording_meta(recordings_dir: str, timestamp: str) -> Dict[str, Any]:
    """Return meta for one recording (defaults if missing)."""
    _validate_ts(timestamp)
    data = load_meta(recordings_dir)
    entry = data['recordings'].get(timestamp) or {}
    return {
        'timestamp': timestamp,
        'favorite': bool(entry.get('favorite', False)),
        'notes': entry.get('notes') or '',
        'tags': list(entry.get('tags') or []),
        'updated_at': entry.get('updated_at'),
    }


def update_recording_meta(
    recordings_dir: str,
    timestamp: str,
    *,
    favorite: Optional[bool] = None,
    notes: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Patch meta fields for a recording. Pass only fields to change.
    Returns the updated meta dict.
    """
    _validate_ts(timestamp)
    with _lock:
        data = load_meta(recordings_dir)
        entry = dict(data['recordings'].get(timestamp) or {})
        if favorite is not None:
            entry['favorite'] = bool(favorite)
        if notes is not None:
            entry['notes'] = str(notes)[:2000]
        if tags is not None:
            cleaned = []
            for t in tags:
                s = str(t).strip()[:40]
                if s and s not in cleaned:
                    cleaned.append(s)
            entry['tags'] = cleaned[:20]
        entry['updated_at'] = datetime.now().isoformat(timespec='seconds')
        data['recordings'][timestamp] = entry
        save_meta(recordings_dir, data)
    return get_recording_meta(recordings_dir, timestamp)


def delete_recording_meta(recordings_dir: str, timestamp: str) -> None:
    """Remove meta when a recording is deleted."""
    if not _TS_RE.match(timestamp or ''):
        return
    with _lock:
        data = load_meta(recordings_dir)
        if timestamp in data['recordings']:
            del data['recordings'][timestamp]
            save_meta(recordings_dir, data)


def list_favorites(recordings_dir: str) -> List[str]:
    data = load_meta(recordings_dir)
    return sorted(
        [ts for ts, e in data['recordings'].items() if e.get('favorite')],
        reverse=True,
    )


def attach_meta_to_pairs(recordings_dir: str, pairs: List[Dict]) -> List[Dict]:
    """Enrich recording-pair dicts with favorite/notes/tags."""
    data = load_meta(recordings_dir)
    recs = data.get('recordings') or {}
    out = []
    for p in pairs:
        ts = p.get('timestamp')
        entry = recs.get(ts) or {}
        enriched = dict(p)
        enriched['favorite'] = bool(entry.get('favorite', False))
        enriched['notes'] = entry.get('notes') or ''
        enriched['tags'] = list(entry.get('tags') or [])
        out.append(enriched)
    return out
