"""
Practice settings: reference swing, camera roles, metronome, session prefs.

Backed by local SQLite (``swinglab.db``) with a JSON mirror
(``practice_settings.json``) for backup / older tooling.
"""

from __future__ import annotations

import re
import threading
from typing import Any, Dict, Optional

from local_db import get_db

_lock = threading.Lock()
_TS_RE = re.compile(r'^\d{8}_\d{6}$')
VALID_ROLES = ('face_on', 'dtl')


def settings_path(recordings_dir: str) -> str:
    import os
    return os.path.join(recordings_dir, 'practice_settings.json')


def _empty() -> Dict[str, Any]:
    return {
        'version': 1,
        'reference_timestamp': None,
        'camera_roles': {
            'camera1': 'face_on',
            'camera2': 'dtl',
        },
        'metronome': {
            'enabled': False,
            'bpm': 60,
            'ratio': '3:1',
        },
        'session': {
            'enabled': False,
            'auto_detect': True,
            'auto_advance': True,
        },
    }


def _merge_defaults(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    defaults = _empty()
    if not data or not isinstance(data, dict):
        return defaults
    merged = _empty()
    merged.update({k: v for k, v in data.items() if k in merged or k == 'version'})
    for section in ('camera_roles', 'metronome', 'session'):
        if isinstance(data.get(section), dict):
            merged[section] = {**defaults[section], **data[section]}
    if 'reference_timestamp' in data:
        merged['reference_timestamp'] = data['reference_timestamp']
    return merged


def load_practice_settings(recordings_dir: str) -> Dict[str, Any]:
    stored = get_db(recordings_dir).get_practice_settings()
    return _merge_defaults(stored)


def save_practice_settings(recordings_dir: str, data: Dict[str, Any]) -> None:
    get_db(recordings_dir).save_practice_settings(_merge_defaults(data))


def update_practice_settings(recordings_dir: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """Shallow/section merge of practice settings."""
    with _lock:
        data = load_practice_settings(recordings_dir)
        for key, value in patch.items():
            if key in ('camera_roles', 'metronome', 'session') and isinstance(value, dict):
                data[key] = {**data.get(key, {}), **value}
            elif key == 'reference_timestamp':
                if value is not None and not _TS_RE.match(str(value)):
                    raise ValueError(f'Invalid timestamp format: {value}')
                data[key] = value
            else:
                data[key] = value
        roles = data.get('camera_roles') or {}
        for cam in ('camera1', 'camera2'):
            if roles.get(cam) not in VALID_ROLES:
                roles[cam] = 'face_on' if cam == 'camera1' else 'dtl'
        if roles.get('camera1') == roles.get('camera2'):
            roles['camera2'] = 'dtl' if roles['camera1'] == 'face_on' else 'face_on'
        data['camera_roles'] = roles
        save_practice_settings(recordings_dir, data)
        return data


def get_reference_timestamp(recordings_dir: str) -> Optional[str]:
    return load_practice_settings(recordings_dir).get('reference_timestamp')


def set_reference_timestamp(recordings_dir: str, timestamp: Optional[str]) -> Dict[str, Any]:
    """Pin or clear the golden/reference swing. Pass timestamp=None to clear."""
    return update_practice_settings(recordings_dir, {'reference_timestamp': timestamp})


def role_label(role: str) -> str:
    return 'Face-On' if role == 'face_on' else 'Down-the-Line'


def camera_labels(settings: Optional[Dict] = None) -> Dict[str, str]:
    """Human labels for camera1 / camera2 from settings."""
    roles = (settings or _empty()).get('camera_roles') or {}
    return {
        'camera1': role_label(roles.get('camera1', 'face_on')),
        'camera2': role_label(roles.get('camera2', 'dtl')),
    }
