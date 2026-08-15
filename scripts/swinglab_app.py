#!/usr/bin/env python3
"""
Unified SwingLab entry for source runs and the frozen Windows/Linux build.

    SwingLab.exe              # wizard on first launch, then the app
    SwingLab.exe --setup      # force the camera / studio wizard
    SwingLab.exe --skip-setup # Flask only
"""

from __future__ import annotations

import argparse
import os
import sys

if not getattr(sys, 'frozen', False):
    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(ROOT, 'src'))
    sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from install_config import app_home, load_install_config, should_run_setup  # noqa: E402


def parse_launcher_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='SwingLab — dual USB golf-swing recorder',
        add_help=False,
    )
    parser.add_argument('--setup', action='store_true', help='Open the setup wizard')
    parser.add_argument('--skip-setup', action='store_true', help='Skip wizard and start the app')
    parser.add_argument('-h', '--help', action='store_true')
    args, rest = parser.parse_known_args(argv)
    return args, rest


def main(argv: list[str] | None = None) -> int:
    args, rest = parse_launcher_args(argv)
    if args.help:
        print(
            'SwingLab\n'
            '  --setup        Open the first-run / camera wizard\n'
            '  --skip-setup   Start the app without the wizard\n'
            '  --help         This message\n'
            '\n'
            'Other flags are passed to the app (see python scripts/flask_gui.py -h).\n'
        )
        return 0

    home = app_home()
    os.makedirs(home, exist_ok=True)
    config = load_install_config(home)
    if should_run_setup(setup=args.setup, skip_setup=args.skip_setup, config=config):
        from setup_wizard import main as wizard_main
        wizard_args = ['--root', home]
        return wizard_main(wizard_args)

    sys.argv = [sys.argv[0], *rest]
    from flask_gui import main as flask_main
    return flask_main() or 0


if __name__ == '__main__':
    sys.exit(main())
