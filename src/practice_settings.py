"""
Practice settings: reference (golden) swing pin and related prefs.
"""

from __future__ import annotations

import json
import os
import re
import threading
from typing import Any, Dict, Optional

_lock = threading.Lock()
_TS_RE = re.compile(r'^\d{8}_\d{6}$')


def settings_path(recordings_dir: str) -> str:
    return os.path.join(recordings_dir, 'practice_settings.json')


def _empty() -> Dict[str, Any]:
    return {
        'version': 1,
        'reference_timestamp': None,
    }


def load_practice_settings(recordings_dir: str) -> Dict[str, Any]:
    path = settings_path(recordings_dir)
    if not os.path.exists(path):
        return _empty()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _empty()
        data.setdefault('version', 1)
        data.setdefault('reference_timestamp', None)
        return data
    except (json.JSONDecodeError, OSError):
        return _empty()


def save_practice_settings(recordings_dir: str, data: Dict[str, Any]) -> None:
    path = settings_path(recordings_dir)
    os.makedirs(recordings_dir, exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    os.replace(tmp, path)


def get_reference_timestamp(recordings_dir: str) -> Optional[str]:
    return load_practice_settings(recordings_dir).get('reference_timestamp')


def set_reference_timestamp(recordings_dir: str, timestamp: Optional[str]) -> Dict[str, Any]:
    """
    Pin or clear the golden/reference swing.
    Pass timestamp=None to clear.
    """
    if timestamp is not None and not _TS_RE.match(timestamp):
        raise ValueError(f'Invalid timestamp format: {timestamp}')
    with _lock:
        data = load_practice_settings(recordings_dir)
        data['reference_timestamp'] = timestamp
        save_practice_settings(recordings_dir, data)
    return data
