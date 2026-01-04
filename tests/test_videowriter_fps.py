"""
Test what FPS VideoWriter supports
"""

import cv2
import os

def test_videowriter_fps(fps, codec='H264'):
    """Test if VideoWriter can handle a specific FPS"""
    test_path = f"test_{fps}fps.mp4"
    
    try:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(test_path, fourcc, fps, (640, 480))
        
        if writer.isOpened():
            # Try writing a few frames
            import numpy as np
            for i in range(10):
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                writer.write(frame)
            writer.release()
            
            # Clean up
            if os.path.exists(test_path):
                os.remove(test_path)
            
            return True
        else:
            return False
    except Exception as e:
        print(f"Error testing {fps}fps: {e}")
        if os.path.exists(test_path):
            try:
                os.remove(test_path)
            except:
                pass
        return False

print("Testing VideoWriter FPS support...")
print()

fps_to_test = [30, 60, 120, 240, 300]

for fps in fps_to_test:
    result = test_videowriter_fps(fps)
    status = "[OK]" if result else "[FAIL]"
    print(f"{status} {fps} FPS")

print()
print("Note: Some codecs may have FPS limitations")

