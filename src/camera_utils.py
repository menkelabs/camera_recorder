"""
Camera utility functions for platform-agnostic camera handling
Supports both Linux (development/testing) and Windows (production)
"""

import cv2
import sys
from typing import Optional, Tuple


def create_camera_capture(camera_id, backend=None):
    """
    Create a VideoCapture object with platform-appropriate backend
    
    Args:
        camera_id: Camera index (int) or device path (str)
        backend: Optional backend override (for testing)
                  Use cv2.CAP_DSHOW on Windows, None on Linux
        
    Returns:
        cv2.VideoCapture object
        
    Raises:
        ValueError: If camera cannot be opened
    """
    # Determine backend based on platform
    if backend is None:
        # Windows: Use DirectShow for better compatibility
        # Linux: Use default backend (V4L2)
        if sys.platform == 'win32' and isinstance(camera_id, int):
            cap = cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(camera_id)
    else:
        # Use specified backend
        cap = cv2.VideoCapture(camera_id, backend)
    
    if not cap.isOpened():
        raise ValueError(f"Failed to open camera {camera_id}")
    
    return cap


def get_platform_info():
    """
    Get platform information for configuration
    
    Returns:
        dict with platform information
    """
    return {
        'platform': sys.platform,
        'is_windows': sys.platform == 'win32',
        'is_linux': sys.platform.startswith('linux'),
        'is_mac': sys.platform == 'darwin',
    }


def get_default_camera_ids():
    """
    Get default camera IDs for current platform
    
    Windows production: typically 0, 2 (skips built-in camera at 1)
    Linux development: typically 0, 1 (both USB cameras)
    
    Returns:
        tuple: (camera1_id, camera2_id)
    """
    platform_info = get_platform_info()
    
    if platform_info['is_windows']:
        # Windows: Use cameras 0 and 2 (skip built-in at 1)
        return (0, 2)
    else:
        # Linux/Other: Use cameras 0 and 1
        return (0, 1)

