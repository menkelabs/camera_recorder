"""
Per-recording metadata: favorites, notes, and tags.

Backed by local SQLite (``swinglab.db``) with a JSON mirror
(``recording_meta.json``) for backup / older tooling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from local_db import get_db


def meta_path(recordings_dir: str) -> str:
    """Legacy JSON path (still written as a mirror)."""
    import os
    return os.path.join(recordings_dir, 'recording_meta.json')


def get_recording_meta(recordings_dir: str, timestamp: str) -> Dict[str, Any]:
    """Return meta for one recording (defaults if missing)."""
    return get_db(recordings_dir).get_recording_meta(timestamp)


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
    return get_db(recordings_dir).update_recording_meta(
        timestamp, favorite=favorite, notes=notes, tags=tags,
    )


def delete_recording_meta(recordings_dir: str, timestamp: str) -> None:
    """Remove meta when a recording is deleted."""
    get_db(recordings_dir).delete_recording(timestamp)


def list_favorites(recordings_dir: str) -> List[str]:
    return get_db(recordings_dir).list_favorites()


def attach_meta_to_pairs(recordings_dir: str, pairs: List[Dict]) -> List[Dict]:
    """Enrich recording-pair dicts with favorite/notes/tags."""
    recs = get_db(recordings_dir).all_recording_meta()
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


# Kept for tests / callers that imported these helpers
def load_meta(recordings_dir: str) -> Dict[str, Any]:
    return {'version': 1, 'recordings': get_db(recordings_dir).all_recording_meta()}


def save_meta(recordings_dir: str, data: Dict[str, Any]) -> None:
    """Replace-all write used by older code paths; upserts into SQLite."""
    db = get_db(recordings_dir)
    for ts, entry in (data.get('recordings') or {}).items():
        if not isinstance(entry, dict):
            continue
        db.update_recording_meta(
            ts,
            favorite=bool(entry.get('favorite', False)),
            notes=entry.get('notes') or '',
            tags=list(entry.get('tags') or []),
        )
