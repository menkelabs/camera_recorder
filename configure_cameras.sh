#!/bin/bash

# Configuration Script for Linux

echo "============================================================"
echo "Camera Configuration Wizard"
echo "============================================================"
echo

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Please run ./setup_env.sh first."
    exit 1
fi

source .venv/bin/activate
python3 scripts/configure_cameras.py
