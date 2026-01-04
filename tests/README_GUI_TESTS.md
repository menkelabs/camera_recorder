# GUI Tests

Comprehensive test suite for the Camera Setup & Recording GUI.

## Test Files

### `test_gui.py` - Unit Tests
Comprehensive unit tests using unittest framework with mocked dependencies.

**Test Coverage:**
- GUI initialization (platform defaults, explicit IDs)
- Tab switching (cycling, direct selection)
- Recording controls (start/stop recording)
- Analysis integration (state, triggers, requirements)
- Camera property adjustment
- Analysis tab rendering (various states)

**Run tests:**
```bash
python3 tests/test_gui.py
```

**Results:** 19 tests - all passing ✓

### `test_gui_interactive.py` - Interactive Tests
Tests that work with actual cameras when available.

**Test Coverage:**
- GUI initialization with real cameras
- Tab switching logic
- Camera opening (actual hardware)
- Method existence verification
- State variable initialization

**Run tests:**
```bash
python3 tests/test_gui_interactive.py
```

**Results:** 5 tests - all passing ✓

## Test Results Summary

### Unit Tests (test_gui.py)
- ✓ 19/19 tests passing
- Tests GUI logic without requiring cameras
- Uses mocks for isolation
- Fast execution (< 0.02s)

### Interactive Tests (test_gui_interactive.py)
- ✓ 5/5 tests passing
- Tests with actual camera hardware
- Verifies cameras can be opened
- Checks method existence and state

## What's Tested

### Initialization
- Platform-appropriate camera defaults (Linux: 0,1 | Windows: 0,2)
- Explicit camera ID override
- Tab structure (4 tabs: Setup 1, Setup 2, Recording, Analysis)
- Initial state variables

### Tab Switching
- Tab cycling (Tab key)
- Direct tab selection (1/2/3/4 keys)
- All 4 tabs accessible

### Recording Controls
- Start recording creates DualCameraRecorder
- Stop recording stops recording
- Recording state tracking
- Automatic analysis trigger after recording stops

### Analysis Integration
- Analysis state initialization
- Analysis requires video files
- Analysis triggered after recording stops
- Analysis tab rendering (no results, with results, analyzing)

### Camera Properties
- Property adjustment (brightness, exposure, etc.)
- Property ranges defined

### Rendering
- Analysis tab renders correctly in all states
- No crashes during rendering

## Running All Tests

Run all GUI tests:
```bash
# Unit tests (mocked)
python3 tests/test_gui.py

# Interactive tests (real cameras)
python3 tests/test_gui_interactive.py

# Run both
python3 tests/test_gui.py && python3 tests/test_gui_interactive.py
```

## Test Coverage

The tests cover:
- ✓ Button/keyboard handler logic
- ✓ Tab switching functionality
- ✓ Recording start/stop
- ✓ Analysis integration
- ✓ State management
- ✓ Platform detection
- ✓ Camera property adjustment
- ✓ GUI rendering logic

All core GUI functionality is tested and verified to work correctly!

