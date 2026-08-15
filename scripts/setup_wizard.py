#!/usr/bin/env python3
"""Open the SwingLab setup wizard in a browser. Stdlib only — run this first."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))

from setup_wizard import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
