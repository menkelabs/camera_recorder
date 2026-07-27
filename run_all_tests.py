#!/usr/bin/env python3
"""
Run camera_recorder tests on Windows or Linux from the same entry point.

Usage:
    python run_all_tests.py              # unit tests only (default, no cameras)
    python run_all_tests.py --unit       # same as default
    python run_all_tests.py --hardware   # camera / FPS / recording scripts
    python run_all_tests.py --all        # unit + hardware
    python run_all_tests.py --list       # show what would run
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import unittest

project_root = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.join(project_root, 'tests')
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, tests_dir)

from test_utils import describe_platform_setup, fix_console_encoding, print_platform_banner


# Unittest modules that do not need real cameras
UNIT_TEST_MODULES = [
    'test_platform_config',
    'test_gui',
    'test_flask_gui',
    'test_preview_while_recording',
    'test_gui_stability',
    'test_dual_camera_soak',
    'test_config_to_record_workflow',
    'test_analysis_workflow',
    'test_analysis_navigation',
    'test_mock_video_analysis',
    'test_sway_calculator',
    'test_swing_comparison',
    'test_recording_management',
    'test_swing_detector',
    'test_archive',
    'test_practice_features',
]

# Standalone scripts that open real cameras / write video
HARDWARE_TEST_SCRIPTS = [
    'test_cameras.py',
    'test_60fps.py',
    'test_240fps_no_drops.py',
    'test_frame_drops.py',
    'test_golf_swing_settings.py',
    'test_mediapipe_resolutions.py',
    'test_videowriter_fps.py',
    'verify_dual_recording.py',
]


def get_python_executable():
    """Prefer project .venv Python when present."""
    if sys.platform == 'win32':
        venv_python = os.path.join(project_root, '.venv', 'Scripts', 'python.exe')
    else:
        venv_python = os.path.join(project_root, '.venv', 'bin', 'python')
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


def run_unittest_tests(python_exe, modules):
    """Run unittest modules one-by-one; return (passed, failed, details)."""
    print("=" * 70)
    print("Running unittest suites (no cameras required)...")
    print("=" * 70)

    details = {}
    for test_name in modules:
        print(f"\n--- tests.{test_name} ---")
        try:
            result = subprocess.run(
                [python_exe, '-m', 'unittest', f'tests.{test_name}', '-v'],
                cwd=project_root,
                timeout=300,
            )
            ok = result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] {test_name} exceeded 5 minute timeout")
            ok = False
        except Exception as exc:
            print(f"  [ERROR] Failed to run {test_name}: {exc}")
            ok = False
        details[test_name] = ok

    passed = sum(1 for v in details.values() if v)
    failed = len(details) - passed
    return passed, failed, details


def run_hardware_tests(python_exe, scripts):
    """Run standalone hardware scripts; return (passed, failed, skipped, details)."""
    print("\n" + "=" * 70)
    print("Running hardware / camera scripts...")
    print("=" * 70)
    print("These need real USB cameras. Skip with: python run_all_tests.py --unit")

    details = {}
    for test_file in scripts:
        test_path = os.path.join(tests_dir, test_file)
        if not os.path.exists(test_path):
            details[test_file] = None
            continue

        print(f"\n{'=' * 70}")
        print(f"Running: {test_file}")
        print('=' * 70)

        try:
            result = subprocess.run(
                [python_exe, test_path],
                cwd=project_root,
                timeout=300,
            )
            details[test_file] = result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] {test_file} exceeded 5 minute timeout")
            details[test_file] = False
        except Exception as exc:
            print(f"  [ERROR] Failed to run {test_file}: {exc}")
            details[test_file] = False

    passed = sum(1 for v in details.values() if v is True)
    failed = sum(1 for v in details.values() if v is False)
    skipped = sum(1 for v in details.values() if v is None)
    return passed, failed, skipped, details


def main(argv=None):
    fix_console_encoding()
    parser = argparse.ArgumentParser(
        description='Cross-platform test runner for camera_recorder'
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--unit', action='store_true', default=False,
                       help='Run unittest suites only (default)')
    group.add_argument('--hardware', action='store_true',
                       help='Run camera/FPS hardware scripts only')
    group.add_argument('--all', action='store_true',
                       help='Run unit + hardware tests')
    parser.add_argument('--list', action='store_true',
                        help='List tests and platform setup, then exit')
    args = parser.parse_args(argv)

    # Default mode is unit-only when no flag is given
    run_unit = args.unit or args.all or not (args.hardware or args.all)
    run_hw = args.hardware or args.all
    if args.hardware and not args.all:
        run_unit = False
    if not args.unit and not args.hardware and not args.all:
        run_unit = True
        run_hw = False

    python_exe = get_python_executable()
    print_platform_banner("CAMERA RECORDER - TEST SUITE")
    print(f"Using Python: {python_exe}")
    print(f"Mode: {'unit' if run_unit and not run_hw else 'hardware' if run_hw and not run_unit else 'all'}")

    if args.list:
        print("\nUnit test modules:")
        for name in UNIT_TEST_MODULES:
            print(f"  tests.{name}")
        print("\nHardware scripts:")
        for name in HARDWARE_TEST_SCRIPTS:
            print(f"  tests/{name}")
        return 0

    # Dependency check (opencv/numpy required for almost everything)
    try:
        result = subprocess.run(
            [python_exe, '-c', 'import cv2; import numpy'],
            cwd=project_root,
            capture_output=True,
            timeout=15,
        )
        if result.returncode != 0:
            print("\nERROR: Required dependencies not found!")
            print("Install with: pip install -r requirements.txt")
            return 1
    except Exception as exc:
        print(f"Warning: Could not verify dependencies: {exc}")

    unit_details = {}
    hw_details = {}
    unit_failed = 0
    hw_failed = 0

    if run_unit:
        _, unit_failed, unit_details = run_unittest_tests(python_exe, UNIT_TEST_MODULES)

    if run_hw:
        _, hw_failed, _, hw_details = run_hardware_tests(python_exe, HARDWARE_TEST_SCRIPTS)

    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    if unit_details:
        print("Unit tests:")
        for name, ok in unit_details.items():
            print(f"  {name}: {'PASSED' if ok else 'FAILED'}")
    if hw_details:
        print("Hardware tests:")
        for name, result in hw_details.items():
            if result is None:
                status = "SKIPPED (not found)"
            elif result:
                status = "PASSED"
            else:
                status = "FAILED"
            print(f"  {name}: {status}")

    overall_ok = unit_failed == 0 and hw_failed == 0
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED" if overall_ok else "SOME TESTS FAILED")
    print("=" * 70)
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
