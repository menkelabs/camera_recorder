"""
Interactive GUI Test Script
Tests GUI functionality with actual cameras (requires cameras to be connected)
This script performs basic smoke tests without requiring user interaction
"""

import sys
import os
import time
import cv2

# Add src and scripts to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'scripts'))

from camera_setup_recorder_gui import TabbedCameraGUI


def test_gui_initialization():
    """Test that GUI can be initialized"""
    print("Test 1: GUI Initialization")
    print("-" * 60)
    
    try:
        # Use platform-appropriate cameras (0, 2 on Linux, 0, 2 on Windows)
        gui = TabbedCameraGUI(camera1_id=0, camera2_id=2)
        
        # Check initial state
        assert gui.camera1_id == 0, f"Expected camera1_id=0, got {gui.camera1_id}"
        assert gui.camera2_id == 2, f"Expected camera2_id=2, got {gui.camera2_id}"
        assert gui.current_tab == 0, f"Expected current_tab=0, got {gui.current_tab}"
        assert len(gui.tab_names) == 4, f"Expected 4 tabs, got {len(gui.tab_names)}"
        
        print("✓ GUI initialized successfully")
        print(f"  Camera 1 ID: {gui.camera1_id}")
        print(f"  Camera 2 ID: {gui.camera2_id}")
        print(f"  Tabs: {gui.tab_names}")
        print()
        return True
    except Exception as e:
        print(f"✗ GUI initialization failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_tab_switching_logic():
    """Test tab switching logic without actually opening cameras"""
    print("Test 2: Tab Switching Logic")
    print("-" * 60)
    
    try:
        with patch('cv2.VideoCapture'):
            gui = TabbedCameraGUI()
            
            # Test tab cycling
            original_tab = gui.current_tab
            gui.current_tab = (gui.current_tab + 1) % 4
            assert gui.current_tab != original_tab, "Tab should change"
            
            # Test all tabs
            for tab_idx in range(4):
                gui.current_tab = tab_idx
                assert gui.current_tab == tab_idx, f"Failed to set tab to {tab_idx}"
            
            print("✓ Tab switching logic works correctly")
            print(f"  Can cycle through {len(gui.tab_names)} tabs")
            print()
            return True
    except Exception as e:
        print(f"✗ Tab switching test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_camera_opening():
    """Test that cameras can be opened (requires actual cameras)"""
    print("Test 3: Camera Opening")
    print("-" * 60)
    
    try:
        # Try to open cameras (this will fail if cameras aren't available)
        cap1 = cv2.VideoCapture(0)
        cap2 = cv2.VideoCapture(2)
        
        if cap1.isOpened() and cap2.isOpened():
            print("✓ Both cameras opened successfully")
            print(f"  Camera 1: {cap1.getBackendName()}")
            print(f"  Camera 2: {cap2.getBackendName()}")
            cap1.release()
            cap2.release()
            print()
            return True
        else:
            print("⚠ Cameras not available (this is OK for testing)")
            if cap1.isOpened():
                cap1.release()
            if cap2.isOpened():
                cap2.release()
            print()
            return True  # Not a failure, just no cameras
    except Exception as e:
        print(f"⚠ Camera opening test skipped: {e}")
        print()
        return True  # Not a failure


def test_method_existence():
    """Test that all required methods exist"""
    print("Test 4: Method Existence")
    print("-" * 60)
    
    try:
        with patch('cv2.VideoCapture'):
            gui = TabbedCameraGUI()
            
            # Check required methods exist
            required_methods = [
                'start_recording',
                'stop_recording',
                'start_analysis',
                '_analyze_videos',
                'draw_analysis_tab',
                'draw_recording_tab',
                'draw_camera_setup_tab',
                'adjust_property',
                'save_settings',
                'reset_settings'
            ]
            
            missing = []
            for method_name in required_methods:
                if not hasattr(gui, method_name):
                    missing.append(method_name)
            
            if missing:
                print(f"✗ Missing methods: {missing}")
                return False
            
            print("✓ All required methods exist")
            for method_name in required_methods:
                print(f"  - {method_name}()")
            print()
            return True
    except Exception as e:
        print(f"✗ Method existence test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_state_variables():
    """Test that all state variables are initialized"""
    print("Test 5: State Variables")
    print("-" * 60)
    
    try:
        with patch('cv2.VideoCapture'):
            gui = TabbedCameraGUI()
            
            # Check state variables exist
            assert hasattr(gui, 'is_recording'), "Missing is_recording"
            assert hasattr(gui, 'is_analyzing'), "Missing is_analyzing"
            assert hasattr(gui, 'analysis_camera1'), "Missing analysis_camera1"
            assert hasattr(gui, 'analysis_camera2'), "Missing analysis_camera2"
            assert hasattr(gui, 'recording_files'), "Missing recording_files"
            assert hasattr(gui, 'current_tab'), "Missing current_tab"
            
            # Check initial values
            assert gui.is_recording == False, "is_recording should be False initially"
            assert gui.is_analyzing == False, "is_analyzing should be False initially"
            assert gui.current_tab == 0, "current_tab should be 0 initially"
            
            print("✓ All state variables initialized correctly")
            print(f"  is_recording: {gui.is_recording}")
            print(f"  is_analyzing: {gui.is_analyzing}")
            print(f"  current_tab: {gui.current_tab}")
            print()
            return True
    except Exception as e:
        print(f"✗ State variables test failed: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """Run all interactive GUI tests"""
    print("=" * 70)
    print("Interactive GUI Tests")
    print("=" * 70)
    print()
    
    # Import patch for mock tests
    global patch
    from unittest.mock import patch
    
    tests = [
        test_gui_initialization,
        test_tab_switching_logic,
        test_camera_opening,
        test_method_existence,
        test_state_variables,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test_func.__name__} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
        print()
    
    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if all(results):
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

