#!/usr/bin/env python3
"""
Smoke-test MediaPipe + swing metrics on real Face-On / DTL clips.

Does not train anything. Looks for local fixtures first, then a recordings
pair, then downloads the small GolfDB demo swing.

    python scripts/smoke_real_swings.py
    python scripts/smoke_real_swings.py --no-fetch
"""

from __future__ import annotations

import argparse
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))
sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'tests'))

from real_swing_smoke import run_smoke  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Real Face-On / DTL MediaPipe smoke')
    parser.add_argument(
        '--no-fetch',
        action='store_true',
        help='Do not download the public GolfDB demo clip',
    )
    parser.add_argument(
        '--min-detection',
        type=float,
        default=0.25,
        help='Minimum pose detection rate (default 0.25)',
    )
    args = parser.parse_args(argv)
    try:
        results = run_smoke(
            fetch_public=not args.no_fetch,
            min_detection=args.min_detection,
        )
    except Exception as exc:
        print(f'SMOKE FAILED: {exc}')
        return 1
    print('Real-swing MediaPipe smoke')
    for item in results:
        turn = item.get('max_shoulder_turn')
        sway = item.get('max_sway_right')
        print(
            f"  {item['view']:8}  det={item['detection_rate']:.0%}  "
            f"frames={item['frames']}  "
            f"shoulder={turn if turn is None else round(turn, 1)}  "
            f"sway={sway if sway is None else round(sway, 3)}  "
            f"({item.get('source')}) {os.path.basename(item['path'])}"
        )
    print('SMOKE PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
