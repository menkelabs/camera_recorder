import unittest
import sys
import os
import json
import tempfile
from unittest.mock import patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from config_manager import ConfigManager

class TestConfigManager(unittest.TestCase):
    
    def test_get_defaults(self):
        defaults = ConfigManager.get_defaults()
        self.assertIn('platform', defaults)
        self.assertIn('camera1_id', defaults)
        
    def test_load_save(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            test_config = {'camera1_id': 99, 'test_val': 'foo'}
            
            # Test Save
            success = ConfigManager.save(test_config, tmp_path)
            self.assertTrue(success)
            
            # Test Load
            loaded = ConfigManager.load(tmp_path)
            self.assertEqual(loaded['camera1_id'], 99)
            self.assertEqual(loaded['test_val'], 'foo')
            
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == '__main__':
    unittest.main()
