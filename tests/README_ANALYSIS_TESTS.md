# Analysis Navigation & Summary Tests

Comprehensive test suite for analysis tab frame navigation, summary correctness, and live metrics.

## Test File

### `test_analysis_navigation.py` - Analysis Navigation Tests
Tests for frame navigation, summary correctness, and live metrics display.

**Test Coverage:**
- Frame navigation (forward/backward, boundaries)
- Summary correctness for each camera
- Live metrics access
- Per-video summary verification
- Analysis tab rendering with navigation

**Run tests:**
```bash
python3 tests/test_analysis_navigation.py
```

## Test Classes

### TestFrameNavigation
Tests frame navigation functionality:
- ✓ Frame index initialization (starts at 0)
- ✓ Navigate forward through frames
- ✓ Navigate backward through frames
- ✓ Navigation respects boundaries (can't go before 0 or past max)
- ✓ Frame index clamping to valid range

### TestSummaryCorrectness
Tests that summary metrics are correct:
- ✓ Camera1 summary structure (max_sway_left, max_sway_right)
- ✓ Camera2 summary structure (max_shoulder_turn, max_hip_turn, max_x_factor)
- ✓ Max values in summary are actually maximums
- ✓ Both cameras have summary data

### TestLiveMetrics
Tests live metrics display for current frame:
- ✓ Current frame sway value
- ✓ Current frame shoulder turn value
- ✓ Current frame hip turn value
- ✓ Current frame x-factor value
- ✓ Access metrics for all frames

### TestAnalysisTabRendering
Tests analysis tab rendering with navigation:
- ✓ Analysis tab renders with frame navigation
- ✓ Frame count is calculated correctly

### TestPerVideoSummary
Tests that each video has its own summary:
- ✓ Camera1 video summary (face-on)
- ✓ Camera2 video summary (down-the-line)
- ✓ Both videos maintain separate summaries

## Test Results

**All tests passing:** ✓

## What's Tested

### Frame Navigation
- Forward/backward navigation
- Boundary checking
- Index clamping
- Both cameras (different frame counts handled)

### Summary Correctness
- Summary structure for each camera
- Max values are actually maximums
- Both cameras have summaries
- Independent summaries per video

### Live Metrics
- Access current frame metrics
- All metrics available (sway, shoulder, hip, x-factor)
- Works for all frame indices
- Handles different frame counts between cameras

### Per-Video Summary
- Camera1 summary (face-on: sway metrics)
- Camera2 summary (down-the-line: rotation metrics)
- Summaries are independent

## Running Tests

```bash
# Run analysis navigation tests
python3 tests/test_analysis_navigation.py

# Run with verbose output
python3 tests/test_analysis_navigation.py -v

# Run all GUI tests (including analysis)
python3 tests/test_gui.py
python3 tests/test_analysis_navigation.py
```

## Test Data Structure

### Camera1 Analysis Structure
```python
{
    'sway': [list of per-frame sway values],
    'summary': {
        'max_sway_left': float,
        'max_sway_right': float
    },
    'detection_rate': float
}
```

### Camera2 Analysis Structure
```python
{
    'shoulder_turn': [list of per-frame shoulder turn values],
    'hip_turn': [list of per-frame hip turn values],
    'x_factor': [list of per-frame x-factor values],
    'summary': {
        'max_shoulder_turn': float,
        'max_hip_turn': float,
        'max_x_factor': float
    },
    'detection_rate': float
}
```

All core analysis functionality is tested and verified to work correctly!

