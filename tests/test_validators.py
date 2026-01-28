# tests/test_validators.py

import unittest
from unittest.mock import patch
from unified_stack_manager.core.validators import SystemValidator

class TestValidators(unittest.TestCase):

    @patch('os.geteuid')
    @patch('os.statvfs')
    @patch('socket.create_connection')
    def test_prerequisites_success(self, mock_socket, mock_statvfs, mock_geteuid):
        """Test that prerequisite validation passes when all conditions are met."""
        mock_geteuid.return_value = 0  # Running as root
        mock_statvfs.return_value.f_bavail = 2 * 1024**3 # Mock 2GB free space
        mock_statvfs.return_value.f_frsize = 1
        is_valid, errors = SystemValidator.validate_prerequisites()
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    @patch('os.geteuid')
    @patch('os.statvfs')
    @patch('socket.create_connection')
    def test_prerequisites_not_root(self, mock_socket, mock_statvfs, mock_geteuid):
        """Test that prerequisite validation fails when not running as root."""
        mock_geteuid.return_value = 1000 # Not root
        mock_statvfs.return_value.f_bavail = 2 * 1024**3 # Mock 2GB free space
        mock_statvfs.return_value.f_frsize = 1
        is_valid, errors = SystemValidator.validate_prerequisites()
        self.assertFalse(is_valid)
        self.assertIn("Debe ejecutarse con sudo/root", errors)

    def test_site_config_success(self):
        """Test that site config validation passes with valid data."""
        config = {'site_name': 'test.com', 'php_version': '8.2'}
        supported_versions = ['8.1', '8.2']
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False
            is_valid, errors = SystemValidator.validate_site_config(config, supported_versions)
            self.assertTrue(is_valid)
            self.assertEqual(len(errors), 0)

    def test_site_config_invalid_name(self):
        """Test that site config validation fails with an invalid site name."""
        config = {'site_name': '-invalid-', 'php_version': '8.2'}
        supported_versions = ['8.1', '8.2']
        with patch('pathlib.Path.exists'):
            is_valid, errors = SystemValidator.validate_site_config(config, supported_versions)
            self.assertFalse(is_valid)
            self.assertIn("Nombre de sitio inválido", errors[0])

if __name__ == '__main__':
    unittest.main()
