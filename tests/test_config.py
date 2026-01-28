# tests/test_config.py

import unittest
from unittest.mock import patch, mock_open
from pathlib import Path
from unified_stack_manager.core.config import UnifiedConfig

class TestConfig(unittest.TestCase):

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="apache:\n  default_php_version: '8.2'\nsecurity:\n  require_sudo: true\nmysql:\n  default_collation: 'utf8mb4_unicode_ci'")
    def test_default_config_loading(self, mock_file, mock_exists):
        """Test that default config is loaded with mocks."""
        mock_exists.return_value = True
        config = UnifiedConfig()

        self.assertEqual(config.get('apache.default_php_version'), '8.2')
        self.assertEqual(config.get('security.require_sudo'), True)

    @patch('pathlib.Path.exists')
    def test_user_config_overrides_defaults(self, mock_exists):
        """Test that a user YAML file correctly overrides default values."""
        default_yaml = "apache:\n  default_php_version: '8.2'\nsecurity:\n  require_sudo: true"
        user_yaml = "apache:\n  default_php_version: '8.1'\nsecurity:\n  require_sudo: false"

        mock_exists.return_value = True

        # side_effect for open to return different content based on path
        def mocked_open(path, *args, **kwargs):
            if 'default.yml' in str(path):
                return mock_open(read_data=default_yaml).return_value
            else:
                return mock_open(read_data=user_yaml).return_value

        with patch('builtins.open', side_effect=mocked_open):
            config = UnifiedConfig(config_file=Path('/fake/path/config.yml'))
            self.assertEqual(config.get('apache.default_php_version'), '8.1')
            self.assertEqual(config.get('security.require_sudo'), False)

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="mysql:\n  default_collation: 'utf8mb4_unicode_ci'")
    def test_get_with_dot_notation(self, mock_file, mock_exists):
        """Test the .get() method with dot notation."""
        mock_exists.return_value = True
        config = UnifiedConfig()
        self.assertEqual(config.get('mysql.default_collation'), 'utf8mb4_unicode_ci')

    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="{}")
    def test_get_with_default_value(self, mock_file, mock_exists):
        """Test that .get() returns the default value for a non-existent key."""
        mock_exists.return_value = True
        config = UnifiedConfig()
        self.assertEqual(config.get('non.existent.key', 'default_val'), 'default_val')

if __name__ == '__main__':
    unittest.main()
