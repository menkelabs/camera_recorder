"""
Machine-local SwingLab install profile written by the setup wizard.

File: ``<project_root>/swinglab.local.json`` (gitignored).
Stdlib only — the wizard imports this before pip/npm have run.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

APP_NAME = 'SwingLab'
APP_VERSION = '1.1.0'
LOCAL_CONFIG_NAME = 'swinglab.local.json'
DEFAULT_PORT = 5000
DEFAULT_HOST = '0.0.0.0'
DEFAULT_FPS = 120
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_MODEL_COMPLEXITY = 2


def is_frozen() -> bool:
    return bool(getattr(sys, 'frozen', False)) and hasattr(sys, '_MEIPASS')


def source_root() -> str:
    """Repo root when running from a checkout (parent of ``src/``)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bundle_dir() -> str:
    """Read-only resources: Vue ``frontend/dist``, wizard HTML, bundled libs."""
    if is_frozen():
        return getattr(sys, '_MEIPASS')
    return source_root()


def app_home(env: Optional[Dict[str, str]] = None) -> str:
    """Writable data dir (profile, recordings, camera config).

    Frozen installs use ``%LOCALAPPDATA%\\SwingLab`` (Windows) or
    ``~/.local/share/swinglab`` (Linux). Source checkouts use the repo root.
    Override with ``SWINGLAB_HOME``.
    """
    environ = env if env is not None else os.environ
    override = (environ.get('SWINGLAB_HOME') or '').strip()
    if override:
        return os.path.abspath(override)
    if is_frozen():
        if os.name == 'nt':
            base = environ.get('LOCALAPPDATA') or os.path.expanduser('~')
            return os.path.join(base, APP_NAME)
        xdg = environ.get('XDG_DATA_HOME') or os.path.join(
            os.path.expanduser('~'), '.local', 'share',
        )
        return os.path.join(xdg, 'swinglab')
    return source_root()


def resource_path(*parts: str) -> str:
    return os.path.join(bundle_dir(), *parts)


def local_config_path(root: Optional[str] = None) -> str:
    return os.path.join(root or app_home(), LOCAL_CONFIG_NAME)


def default_install_config(root: str) -> Dict[str, Any]:
    return {
        'version': 1,
        'camera1_id': 0,
        'camera2_id': 1 if not os.name == 'nt' else 2,
        'camera_roles': {'camera1': 'face_on', 'camera2': 'dtl'},
        'width': DEFAULT_WIDTH,
        'height': DEFAULT_HEIGHT,
        'fps': DEFAULT_FPS,
        'model_complexity': DEFAULT_MODEL_COMPLEXITY,
        'host': DEFAULT_HOST,
        'port': DEFAULT_PORT,
        'recordings_dir': 'recordings',
        'player_name': 'Player 1',
        'completed_at': None,
    }


def load_install_config(root: str) -> Optional[Dict[str, Any]]:
    path = local_config_path(root)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    merged = default_install_config(root)
    merged.update({k: v for k, v in data.items() if k in merged or k == 'version'})
    if isinstance(data.get('camera_roles'), dict):
        merged['camera_roles'] = {
            **merged['camera_roles'],
            **data['camera_roles'],
        }
    return merged


def save_install_config(root: str, data: Dict[str, Any]) -> str:
    merged = default_install_config(root)
    if data:
        merged.update({k: v for k, v in data.items() if k in merged or k == 'version'})
        if isinstance(data.get('camera_roles'), dict):
            merged['camera_roles'] = {
                **merged['camera_roles'],
                **data['camera_roles'],
            }
    if not merged.get('completed_at'):
        merged['completed_at'] = datetime.now().isoformat(timespec='seconds')
    path = local_config_path(root)
    # A symlink would be followed by open() and truncate a file outside the project.
    if os.path.islink(path):
        raise ValueError('install config must not be a symlink')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(merged, fh, indent=2)
        fh.write('\n')
    return path


def _config_recordings_dir_leaves_home(home: str, raw: Any) -> bool:
    """True when a configured recordings folder resolves outside its home.

    ``SWINGLAB_RECORDINGS_DIR`` is an explicit override and is not checked here.
    Absolute paths, ``..`` components, and symlinks that leave home are refused.
    """
    if not isinstance(raw, str):
        return True
    text = raw.strip() or 'recordings'
    if os.path.isabs(text):
        return True
    parts = text.replace('\\', '/').split('/')
    if any(part == '..' for part in parts):
        return True
    candidate = os.path.abspath(os.path.join(home, text))
    real_home = os.path.realpath(home)
    real_candidate = os.path.realpath(candidate)
    if real_candidate == real_home:
        return False
    return not real_candidate.startswith(real_home + os.sep)


def resolve_recordings_dir(
    root: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """Writable recordings folder: env, then local config, then ``<root>/recordings``."""
    environ = env if env is not None else os.environ
    override = (environ.get('SWINGLAB_RECORDINGS_DIR') or '').strip()
    if override:
        return os.path.abspath(override)
    home = root if root is not None else app_home(environ)
    cfg = config if config is not None else load_install_config(home)
    raw = (cfg or {}).get('recordings_dir') or 'recordings'
    if _config_recordings_dir_leaves_home(home, raw):
        raise ValueError('recordings folder must stay inside the project')
    return os.path.abspath(os.path.join(home, raw))


def should_run_setup(
    *,
    setup: bool = False,
    skip_setup: bool = False,
    config: Optional[Dict[str, Any]] = None,
) -> bool:
    """First launch of a frozen app opens the wizard until a profile exists."""
    if skip_setup:
        return False
    if setup:
        return True
    return not (config and config.get('completed_at'))


def venv_python(root: str) -> Optional[str]:
    if os.name == 'nt':
        candidate = os.path.join(root, '.venv', 'Scripts', 'python.exe')
    else:
        candidate = os.path.join(root, '.venv', 'bin', 'python')
    if os.path.isfile(candidate):
        return candidate
    return None


def flask_argv_from_config(config: Optional[Dict[str, Any]]) -> List[str]:
    """CLI flags for ``scripts/flask_gui.py`` from a local install profile."""
    cfg = config or {}
    args: List[str] = []
    for key, flag in (
        ('camera1_id', '--camera1'),
        ('camera2_id', '--camera2'),
        ('width', '--width'),
        ('height', '--height'),
        ('fps', '--fps'),
        ('model_complexity', '--model-complexity'),
        ('host', '--host'),
        ('port', '--port'),
    ):
        if key in cfg and cfg[key] is not None:
            args.extend([flag, str(cfg[key])])
    return args
