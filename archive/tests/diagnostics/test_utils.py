"""
Test utilities for camera configuration
Provides functions to load camera IDs from config files
"""

import sys
import os
import json


def load_windows_camera_config(config_path=None):
    """Load Windows camera configuration from JSON file"""
    if sys.platform != 'win32':
        return None
    
    if config_path is None:
        # Default to config_windows.json in project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(project_root, 'config_windows.json')
    
    if not os.path.exists(config_path):
        return None
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except (json.JSONDecodeError, IOError):
        return None


def get_camera_ids():
    """Get camera IDs for testing - uses config file on Windows, defaults otherwise"""
    if sys.platform == 'win32':
        config = load_windows_camera_config()
        if config:
            return config.get('camera1_id', 0), config.get('camera2_id', 2)
        # Fallback to Windows defaults
        return 0, 2
    else:
        # Linux/Other defaults
        return 0, 1




