#!/usr/bin/env bash
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then
  exec .venv/bin/python scripts/start_swinglab.py "$@"
fi
exec python3 scripts/start_swinglab.py "$@"
