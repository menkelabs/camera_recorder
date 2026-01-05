#!/usr/bin/env python3
"""
Run all tests in the camera_recorder project
Uses standard unittest discovery and runs standalone test scripts
Automatically uses .venv Python if available
"""

import sys
import os
import subprocess
import unittest

# Add project paths
project_root = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.join(project_root, 'tests')
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'scripts'))


def get_python_executable():
    """Get the Python executable to use - prefer .venv if it exists"""
    # Check for .venv (cross-platform)
    if sys.platform == 'win32':
        venv_python = os.path.join(project_root, '.venv', 'Scripts', 'python.exe')
    else:
        venv_python = os.path.join(project_root, '.venv', 'bin', 'python')
    
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


def run_unittest_tests(python_exe):
    """Run unittest-based tests using standard unittest discovery"""
    print("=" * 70)
    print("Running unittest-based tests...")
    print("=" * 70)
    
    # Unittest test files (these contain unittest.TestCase classes)
    unittest_test_files = [
        'test_gui',
        'test_config_to_record_workflow',
        'test_analysis_workflow',
        'test_analysis_navigation'
    ]
    
    # Use subprocess to run in the venv Python context
    all_passed = True
    for test_name in unittest_test_files:
        try:
            result = subprocess.run(
                [python_exe, '-m', 'unittest', f'tests.{test_name}'],
                cwd=project_root,
                timeout=300
            )
            if result.returncode != 0:
                all_passed = False
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] {test_name} exceeded 5 minute timeout")
            all_passed = False
        except Exception as e:
            print(f"  [ERROR] Failed to run {test_name}: {e}")
            all_passed = False
    
    return all_passed


def run_standalone_tests(python_exe):
    """Run standalone test scripts as separate processes"""
    print("\n" + "=" * 70)
    print("Running standalone test scripts...")
    print("=" * 70)
    
    standalone_tests = [
        'test_cameras.py',
        'test_60fps.py',
        'test_240fps_no_drops.py',
        'test_frame_drops.py',
        'test_golf_swing_settings.py',
        'test_mediapipe_resolutions.py',
        'test_videowriter_fps.py',
        'verify_dual_recording.py',
    ]
    
    results = {}
    for test_file in standalone_tests:
        test_path = os.path.join(tests_dir, test_file)
        if not os.path.exists(test_path):
            results[test_file] = None
            continue
            
        print(f"\n{'=' * 70}")
        print(f"Running: {test_file}")
        print('=' * 70)
        
        try:
            result = subprocess.run(
                [python_exe, test_path],
                cwd=project_root,
                timeout=300
            )
            results[test_file] = result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"  [TIMEOUT] {test_file} exceeded 5 minute timeout")
            results[test_file] = False
        except Exception as e:
            print(f"  [ERROR] Failed to run {test_file}: {e}")
            results[test_file] = False
    
    return results


def main():
    """Run all tests"""
    # Get the Python executable to use
    python_exe = get_python_executable()
    
    print("\n" + "=" * 70)
    print("CAMERA RECORDER - TEST SUITE")
    print("=" * 70)
    print(f"Using Python: {python_exe}")
    
    # Verify dependencies are available
    try:
        result = subprocess.run(
            [python_exe, '-c', 'import cv2; import numpy; import mediapipe'],
            cwd=project_root,
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            print("\n" + "=" * 70)
            print("ERROR: Required dependencies not found!")
            print("Please install dependencies: pip install -r requirements.txt")
            print("Or activate your virtual environment first")
            print("=" * 70)
            return 1
    except Exception as e:
        print(f"Warning: Could not verify dependencies: {e}")
    
    # Run unittest-based tests
    unittest_success = run_unittest_tests(python_exe)
    
    # Run standalone tests
    standalone_results = run_standalone_tests(python_exe)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Unittest tests: {'PASSED' if unittest_success else 'FAILED'}")
    print("\nStandalone tests:")
    for test_file, result in standalone_results.items():
        if result is None:
            status = "SKIPPED (not found)"
        elif result:
            status = "PASSED"
        else:
            status = "FAILED"
        print(f"  {test_file}: {status}")
    
    # Overall result
    standalone_success = all(r for r in standalone_results.values() if r is not None)
    overall_success = unittest_success and standalone_success
    
    print("\n" + "=" * 70)
    if overall_success:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 70)
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
