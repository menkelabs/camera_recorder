#!/usr/bin/env python3
"""Start SwingLab using swinglab.local.json from the setup wizard."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from install_config import (  # noqa: E402
    flask_argv_from_config,
    load_install_config,
    resolve_recordings_dir,
    venv_python,
)


def main(argv: list[str] | None = None) -> int:
    extra = list(sys.argv[1:] if argv is None else argv)
    cfg = load_install_config(ROOT)
    py = venv_python(ROOT) or sys.executable
    script = os.path.join(ROOT, 'scripts', 'flask_gui.py')
    env = os.environ.copy()
    env['SWINGLAB_RECORDINGS_DIR'] = resolve_recordings_dir(ROOT, env=env, config=cfg)
    cmd = [py, script, *flask_argv_from_config(cfg), *extra]
    os.chdir(ROOT)
    if os.name == 'nt':
        import subprocess
        return subprocess.call(cmd, env=env)
    os.execvpe(cmd[0], cmd, env)
    return 0


if __name__ == '__main__':
    sys.exit(main())
