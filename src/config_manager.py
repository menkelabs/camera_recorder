import os
import json
import sys
from typing import Optional, Dict, Any

class ConfigManager:
    """
    Manages loading and saving of camera configuration.
    Supports cross-platform 'camera_config.json' and legacy 'config_windows.json'.
    """
    
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_FILENAME = 'camera_config.json'
    LEGACY_WINDOWS_CONFIG = 'config_windows.json'

    @classmethod
    def get_config_path(cls) -> str:
        return os.path.join(cls.PROJECT_ROOT, cls.CONFIG_FILENAME)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from file.
        Priorities:
        1. Explicit path provided
        2. camera_config.json (Cross-platform)
        3. config_windows.json (Legacy Windows)
        4. Defaults
        """
        
        # 1. Explicit path
        if config_path and os.path.exists(config_path):
            return cls._load_json(config_path)

        # 2. Standard config
        std_path = cls.get_config_path()
        if os.path.exists(std_path):
            return cls._load_json(std_path)

        # 3. Legacy Windows config
        if sys.platform == 'win32':
            legacy_path = os.path.join(cls.PROJECT_ROOT, cls.LEGACY_WINDOWS_CONFIG)
            if os.path.exists(legacy_path):
                return cls._load_json(legacy_path)

        # 4. Defaults
        return cls.get_defaults()

    @classmethod
    def save(cls, config: Dict[str, Any], path: Optional[str] = None) -> bool:
        """Save configuration to file"""
        if path is None:
            path = cls.get_config_path()
            
        try:
            with open(path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    @classmethod
    def get_defaults(cls) -> Dict[str, Any]:
        """Get default configuration based on platform"""
        defaults = {
            'platform': sys.platform,
            'camera1_id': 0,
            'camera2_id': 1
        }
        
        if sys.platform == 'win32':
            defaults['camera2_id'] = 2 # Common on Windows (0 & 2)
            
        return defaults

    @staticmethod
    def _load_json(path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load config from {path}: {e}")
            return {}
