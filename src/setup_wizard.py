"""
SwingLab first-run setup wizard.

Stdlib only so it can run before pip/npm. Serves a browser UI on
http://127.0.0.1:8765 and installs the app into the project checkout.

    python scripts/setup_wizard.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from install_config import (
    default_install_config,
    load_install_config,
    resolve_recordings_dir,
    save_install_config,
    venv_python,
)

WIZARD_PORT = 8765
HTML_NAME = 'setup_wizard.html'

_DETECT_SNIPPET = r'''
import json, sys
try:
    import cv2
except Exception as exc:
    print(json.dumps({"error": "opencv_missing", "detail": str(exc)}))
    sys.exit(2)

found = []
for idx in range(8):
    cap = None
    try:
        if sys.platform == "win32":
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            continue
        ok, frame = cap.read()
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        found.append({
            "id": idx,
            "width": width,
            "height": height,
            "status": "ok" if ok and frame is not None else "opens_but_no_frames",
        })
    except Exception as exc:
        found.append({"id": idx, "status": "error", "detail": str(exc)})
    finally:
        if cap is not None:
            cap.release()
print(json.dumps({"cameras": found}))
'''


def project_root_from_here() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def html_path(root: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), HTML_NAME)


def _which(name: str) -> Optional[str]:
    return shutil.which(name)


def _run_version(cmd: List[str]) -> Optional[str]:
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = (proc.stdout or proc.stderr or '').strip().splitlines()
    return out[0] if out else None


def check_prerequisites(root: str, python_exe: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return check rows. ``required`` items must pass before install jobs."""
    exe = python_exe or sys.executable
    version = sys.version_info
    py_ok = version >= (3, 10)
    venv_help = subprocess.run(
        [exe, '-m', 'venv', '--help'],
        capture_output=True, text=True, timeout=20, check=False,
    )
    pip_help = subprocess.run(
        [exe, '-m', 'pip', '--version'],
        capture_output=True, text=True, timeout=20, check=False,
    )
    node = _run_version(['node', '--version'])
    npm = _run_version(['npm', '--version'])
    writable = os.access(root, os.W_OK)
    req = os.path.isfile(os.path.join(root, 'requirements.txt'))
    pkg = os.path.isfile(os.path.join(root, 'frontend', 'package.json'))
    dist = os.path.isfile(os.path.join(root, 'frontend', 'dist', 'index.html'))
    venv = venv_python(root)
    try:
        free = shutil.disk_usage(root).free
        free_gb = free / (1024 ** 3)
        disk_ok = free >= 2 * 1024 ** 3
        disk_detail = f'{free_gb:.1f} GB free'
    except OSError as exc:
        disk_ok = False
        disk_detail = str(exc)

    return [
        {
            'id': 'python',
            'label': 'Python 3.10+',
            'ok': py_ok,
            'required': True,
            'detail': f'{exe} ({version.major}.{version.minor}.{version.micro})',
        },
        {
            'id': 'venv',
            'label': 'Python venv module',
            'ok': venv_help.returncode == 0,
            'required': True,
            'detail': 'python -m venv',
        },
        {
            'id': 'pip',
            'label': 'pip',
            'ok': pip_help.returncode == 0,
            'required': True,
            'detail': (pip_help.stdout or pip_help.stderr or '').strip() or 'python -m pip',
        },
        {
            'id': 'node',
            'label': 'Node.js',
            'ok': bool(node),
            'required': True,
            'detail': node or 'Install from https://nodejs.org (LTS)',
        },
        {
            'id': 'npm',
            'label': 'npm',
            'ok': bool(npm),
            'required': True,
            'detail': npm or 'Comes with Node.js',
        },
        {
            'id': 'writable',
            'label': 'Project folder is writable',
            'ok': writable,
            'required': True,
            'detail': root,
        },
        {
            'id': 'disk',
            'label': 'At least 2 GB free disk',
            'ok': disk_ok,
            'required': False,
            'detail': disk_detail,
        },
        {
            'id': 'requirements',
            'label': 'requirements.txt present',
            'ok': req,
            'required': True,
            'detail': os.path.join(root, 'requirements.txt'),
        },
        {
            'id': 'frontend',
            'label': 'frontend/package.json present',
            'ok': pkg,
            'required': True,
            'detail': os.path.join(root, 'frontend', 'package.json'),
        },
        {
            'id': 'venv_exists',
            'label': 'Virtualenv already created',
            'ok': bool(venv),
            'required': False,
            'detail': venv or 'Will create .venv',
        },
        {
            'id': 'ui_built',
            'label': 'Vue UI already built',
            'ok': dist,
            'required': False,
            'detail': 'frontend/dist/index.html' if dist else 'Will run npm run build',
        },
    ]


class JobRunner:
    def __init__(self, root: str):
        self.root = root
        self.lock = threading.Lock()
        self.jobs: Dict[str, Dict[str, Any]] = {
            'python': self._empty_job(),
            'ui': self._empty_job(),
        }

    def _empty_job(self) -> Dict[str, Any]:
        return {'status': 'idle', 'log': [], 'error': None, 'returncode': None}

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return json.loads(json.dumps(self.jobs))

    def start(self, name: str) -> Dict[str, Any]:
        with self.lock:
            current = self.jobs[name]
            if current['status'] == 'running':
                return current
            self.jobs[name] = self._empty_job()
            self.jobs[name]['status'] = 'running'
        thread = threading.Thread(target=self._run, args=(name,), daemon=True)
        thread.start()
        return self.snapshot()[name]

    def _append(self, name: str, text: str) -> None:
        with self.lock:
            self.jobs[name]['log'].append(text)

    def _run(self, name: str) -> None:
        try:
            if name == 'python':
                code = self._install_python()
            elif name == 'ui':
                code = self._install_ui()
            else:
                raise ValueError(f'Unknown job {name}')
            with self.lock:
                self.jobs[name]['returncode'] = code
                self.jobs[name]['status'] = 'ok' if code == 0 else 'error'
                if code != 0:
                    self.jobs[name]['error'] = f'Command exited {code}'
        except Exception as exc:
            with self.lock:
                self.jobs[name]['status'] = 'error'
                self.jobs[name]['error'] = str(exc)
                self.jobs[name]['log'].append(f'\nERROR: {exc}\n')

    def _stream(self, name: str, cmd: List[str], cwd: Optional[str] = None) -> int:
        self._append(name, f'$ {" ".join(cmd)}\n')
        proc = subprocess.Popen(
            cmd,
            cwd=cwd or self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            self._append(name, line)
        return proc.wait()

    def _install_python(self) -> int:
        exe = sys.executable
        venv_dir = os.path.join(self.root, '.venv')
        if not venv_python(self.root):
            code = self._stream('python', [exe, '-m', 'venv', venv_dir])
            if code != 0:
                return code
        py = venv_python(self.root) or exe
        req = os.path.join(self.root, 'requirements.txt')
        code = self._stream('python', [py, '-m', 'pip', 'install', '--upgrade', 'pip'])
        if code != 0:
            return code
        return self._stream('python', [py, '-m', 'pip', 'install', '-r', req])

    def _install_ui(self) -> int:
        npm = _which('npm')
        if not npm:
            raise RuntimeError('npm not found on PATH')
        frontend = os.path.join(self.root, 'frontend')
        # npm.cmd on Windows needs shell-less list form
        code = self._stream('ui', [npm, 'install'], cwd=frontend)
        if code != 0:
            return code
        return self._stream('ui', [npm, 'run', 'build'], cwd=frontend)


def suggest_cameras(cameras: List[Dict[str, Any]]) -> Dict[str, int]:
    live = [c for c in cameras if c.get('status') == 'ok']
    if len(live) >= 2:
        return {'camera1_id': int(live[0]['id']), 'camera2_id': int(live[1]['id'])}
    if len(live) == 1:
        other = 1 if int(live[0]['id']) == 0 else 0
        return {'camera1_id': int(live[0]['id']), 'camera2_id': other}
    return {'camera1_id': 0, 'camera2_id': 2 if os.name == 'nt' else 1}


def detect_cameras(root: str) -> Dict[str, Any]:
    py = venv_python(root) or sys.executable
    proc = subprocess.run(
        [py, '-c', _DETECT_SNIPPET],
        capture_output=True, text=True, timeout=60, check=False, cwd=root,
    )
    raw = (proc.stdout or '').strip() or (proc.stderr or '').strip()
    try:
        payload = json.loads(raw.splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {
            'cameras': [],
            'error': 'detect_failed',
            'message': raw or f'Camera scan failed (exit {proc.returncode}). Finish the Python packages step first.',
        }
    if payload.get('error'):
        return {
            'cameras': [],
            'error': payload.get('error'),
            'message': payload.get('detail') or 'OpenCV is not available in the venv yet.',
        }
    cameras = payload.get('cameras') or []
    suggested = suggest_cameras(cameras)
    return {
        'cameras': cameras,
        'suggested': suggested,
        'message': f'Found {len(cameras)} camera index(es).',
    }


def merge_platform_camera_config(
    root: str,
    camera1_id: int,
    camera2_id: int,
    detected: Optional[List[Dict[str, Any]]] = None,
) -> str:
    name = 'config_windows.json' if os.name == 'nt' else 'config_linux.json'
    path = os.path.join(root, name)
    data: Dict[str, Any] = {}
    if os.path.isfile(path):
        try:
            with open(path, encoding='utf-8') as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                data = loaded
        except (OSError, json.JSONDecodeError):
            data = {}
    data['platform'] = 'windows' if os.name == 'nt' else 'linux'
    data['camera1_id'] = int(camera1_id)
    data['camera2_id'] = int(camera2_id)
    if detected is not None:
        data['detected_cameras'] = detected
        data['detection_date'] = datetime.now().date().isoformat()
    data.setdefault('notes', 'Written by SwingLab setup wizard')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2)
        fh.write('\n')
    return path


def write_launchers(root: str) -> List[str]:
    written = []
    bat = os.path.join(root, 'Start SwingLab.bat')
    with open(bat, 'w', encoding='utf-8', newline='\r\n') as fh:
        fh.write(
            '@echo off\r\n'
            'cd /d "%~dp0"\r\n'
            'if exist ".venv\\Scripts\\python.exe" (\r\n'
            '  ".venv\\Scripts\\python.exe" "scripts\\start_swinglab.py" %*\r\n'
            ') else (\r\n'
            '  python "scripts\\start_swinglab.py" %*\r\n'
            ')\r\n'
        )
    written.append(bat)
    sh = os.path.join(root, 'start-swinglab.sh')
    with open(sh, 'w', encoding='utf-8') as fh:
        fh.write(
            '#!/usr/bin/env bash\n'
            'cd "$(dirname "$0")"\n'
            'if [ -x .venv/bin/python ]; then\n'
            '  exec .venv/bin/python scripts/start_swinglab.py "$@"\n'
            'fi\n'
            'exec python3 scripts/start_swinglab.py "$@"\n'
        )
    try:
        os.chmod(sh, 0o755)
    except OSError:
        pass
    written.append(sh)
    return written


def write_desktop_shortcut(root: str) -> Optional[str]:
    home = os.path.expanduser('~')
    desktop = os.path.join(home, 'Desktop')
    if not os.path.isdir(desktop):
        return None
    if os.name == 'nt':
        dest = os.path.join(desktop, 'Start SwingLab.bat')
        with open(dest, 'w', encoding='utf-8', newline='\r\n') as fh:
            fh.write(
                '@echo off\r\n'
                f'cd /d "{root}"\r\n'
                'if exist ".venv\\Scripts\\python.exe" (\r\n'
                '  ".venv\\Scripts\\python.exe" "scripts\\start_swinglab.py"\r\n'
                ') else (\r\n'
                '  python "scripts\\start_swinglab.py"\r\n'
                ')\r\n'
            )
        return dest
    dest = os.path.join(desktop, 'SwingLab.desktop')
    py = venv_python(root) or 'python3'
    with open(dest, 'w', encoding='utf-8') as fh:
        fh.write(
            '[Desktop Entry]\n'
            'Type=Application\n'
            'Name=SwingLab\n'
            f'Exec={py} {os.path.join(root, "scripts", "start_swinglab.py")}\n'
            f'Path={root}\n'
            'Terminal=true\n'
            'Categories=Utility;\n'
        )
    try:
        os.chmod(dest, 0o755)
    except OSError:
        pass
    return dest


def apply_studio_extras(root: str, config: Dict[str, Any]) -> List[str]:
    """Rename default player and set camera roles using the venv, if ready."""
    notes = []
    py = venv_python(root)
    if not py:
        notes.append('venv not ready; player/roles will be applied on first app start')
        return notes
    rec_dir = resolve_recordings_dir(root, config=config)
    os.makedirs(rec_dir, exist_ok=True)
    snippet = (
        'import json,sys,os\n'
        f'sys.path.insert(0, {os.path.join(root, "src")!r})\n'
        'from local_db import get_db\n'
        'from practice_settings import update_practice_settings\n'
        f'rec = {rec_dir!r}\n'
        f'name = {config.get("player_name") or "Player 1"!r}\n'
        f'roles = {json.dumps(config.get("camera_roles") or {})!r}\n'
        'db = get_db(rec)\n'
        'users = db.list_users()\n'
        'if users:\n'
        '    db.update_user(users[0]["id"], name=name)\n'
        'else:\n'
        '    db.create_user(name)\n'
        'if roles:\n'
        '    update_practice_settings(rec, {"camera_roles": json.loads(roles)})\n'
        'print("ok")\n'
    )
    proc = subprocess.run(
        [py, '-c', snippet],
        capture_output=True, text=True, timeout=30, check=False, cwd=root,
    )
    if proc.returncode != 0:
        notes.append((proc.stderr or proc.stdout or 'player setup failed').strip())
    else:
        notes.append('player and camera roles saved')
    return notes


def finish_install(
    root: str,
    settings: Dict[str, Any],
    detected: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    cfg = default_install_config(root)
    cfg.update({k: settings[k] for k in cfg if k in settings})
    if isinstance(settings.get('camera_roles'), dict):
        cfg['camera_roles'] = {
            **cfg['camera_roles'],
            **settings['camera_roles'],
        }
    path = save_install_config(root, cfg)
    saved = load_install_config(root) or cfg
    rec_dir = resolve_recordings_dir(root, config=saved)
    os.makedirs(rec_dir, exist_ok=True)
    cam_path = merge_platform_camera_config(
        root,
        int(saved['camera1_id']),
        int(saved['camera2_id']),
        detected=detected,
    )
    launchers = write_launchers(root)
    shortcut = None
    if settings.get('desktop_shortcut'):
        shortcut = write_desktop_shortcut(root)
    notes = apply_studio_extras(root, saved)
    port = int(saved.get('port') or 5000)
    return {
        'ok': True,
        'config_path': path,
        'camera_config': cam_path,
        'recordings_dir': rec_dir,
        'launchers': launchers,
        'shortcut': shortcut,
        'notes': notes,
        'url': f'http://127.0.0.1:{port}',
        'start': 'python scripts/start_swinglab.py',
    }


def start_app(root: str) -> Dict[str, Any]:
    cfg = load_install_config(root) or default_install_config(root)
    py = venv_python(root) or sys.executable
    script = os.path.join(root, 'scripts', 'start_swinglab.py')
    if not os.path.isfile(script):
        script = os.path.join(root, 'scripts', 'flask_gui.py')
    env = os.environ.copy()
    env['SWINGLAB_RECORDINGS_DIR'] = resolve_recordings_dir(root, env=env, config=cfg)
    subprocess.Popen(
        [py, script],
        cwd=root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    port = int(cfg.get('port') or 5000)
    return {
        'ok': True,
        'url': f'http://127.0.0.1:{port}',
        'message': f'SwingLab starting at http://127.0.0.1:{port}',
    }


class WizardState:
    def __init__(self, root: str):
        self.root = root
        self.jobs = JobRunner(root)
        self.last_cameras: List[Dict[str, Any]] = []


def _json_bytes(payload: Dict[str, Any], status: int = 200):
    body = json.dumps(payload).encode('utf-8')
    return status, body


def handle_request(
    state: WizardState,
    method: str,
    path: str,
    body: bytes,
) -> tuple[int, bytes, str]:
    parsed = urlparse(path)
    route = parsed.path
    if method == 'GET' and route == '/':
        html = html_path(state.root)
        with open(html, encoding='utf-8') as fh:
            return 200, fh.read().encode('utf-8'), 'text/html; charset=utf-8'
    if method == 'GET' and route == '/api/state':
        status, payload = _json_bytes({
            'root': state.root,
            'config': load_install_config(state.root),
            'jobs': state.jobs.snapshot(),
        })
        return status, payload, 'application/json'
    if method == 'GET' and route == '/api/jobs':
        status, payload = _json_bytes({'jobs': state.jobs.snapshot()})
        return status, payload, 'application/json'
    if method == 'POST' and route == '/api/check':
        status, payload = _json_bytes({'checks': check_prerequisites(state.root)})
        return status, payload, 'application/json'
    if method == 'POST' and route == '/api/jobs/python':
        status, payload = _json_bytes({'job': state.jobs.start('python')})
        return status, payload, 'application/json'
    if method == 'POST' and route == '/api/jobs/ui':
        status, payload = _json_bytes({'job': state.jobs.start('ui')})
        return status, payload, 'application/json'
    if method == 'POST' and route == '/api/cameras/detect':
        result = detect_cameras(state.root)
        state.last_cameras = result.get('cameras') or []
        code = 200 if not result.get('error') else 400
        status, payload = _json_bytes(result, code)
        return status, payload, 'application/json'
    if method == 'POST' and route == '/api/finish':
        try:
            settings = json.loads(body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            status, payload = _json_bytes({'error': 'invalid JSON'}, 400)
            return status, payload, 'application/json'
        result = finish_install(
            state.root,
            settings,
            detected=state.last_cameras or None,
        )
        status, payload = _json_bytes(result)
        return status, payload, 'application/json'
    if method == 'POST' and route == '/api/start':
        status, payload = _json_bytes(start_app(state.root))
        return status, payload, 'application/json'
    status, payload = _json_bytes({'error': 'not found'}, 404)
    return status, payload, 'application/json'


class WizardHandler(BaseHTTPRequestHandler):
    state: WizardState

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write('wizard: ' + (fmt % args) + '\n')

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        status, body, ctype = handle_request(self.state, 'GET', self.path, b'')
        self._send(status, body, ctype)

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(length) if length else b''
        status, body, ctype = handle_request(self.state, 'POST', self.path, raw)
        self._send(status, body, ctype)


def serve_wizard(
    root: str,
    host: str = '127.0.0.1',
    port: int = WIZARD_PORT,
    open_browser: bool = True,
) -> ThreadingHTTPServer:
    handler = type('BoundWizardHandler', (WizardHandler,), {'state': WizardState(root)})
    server = ThreadingHTTPServer((host, port), handler)
    url = f'http://{host}:{server.server_port}'
    print()
    print('=' * 60)
    print(f'  SwingLab setup wizard  {url}')
    print(f'  Project: {root}')
    print('  Press Ctrl+C when finished')
    print('=' * 60)
    print()
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    return server


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description='SwingLab setup wizard (browser). See docs/HOW_TO_USE.md.',
    )
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=WIZARD_PORT)
    parser.add_argument('--root', default=project_root_from_here())
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f'Project root not found: {root}', file=sys.stderr)
        return 2
    server = serve_wizard(
        root, host=args.host, port=args.port, open_browser=not args.no_browser,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nWizard stopped.')
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
