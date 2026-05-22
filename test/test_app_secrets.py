#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import unittest
from unittest.mock import patch, MagicMock

from ingen.utils.app_secrets import AppSecrets


class TestAppSecrets(unittest.TestCase):

    def setUp(self):
        AppSecrets.vault_client = None

    @patch('ingen.utils.app_secrets.hvac.Client')
    def test_connect_client_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client_cls.return_value = mock_client

        result = AppSecrets.connect_client()
        self.assertEqual(result, mock_client)

    @patch('ingen.utils.app_secrets.hvac.Client')
    def test_connect_client_not_authenticated(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = False
        mock_client_cls.return_value = mock_client

        with self.assertRaises(Exception):
            AppSecrets.connect_client()

    @patch('ingen.utils.app_secrets.hvac.Client')
    def test_connect_client_reuses_existing(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client_cls.return_value = mock_client

        AppSecrets.connect_client()
        AppSecrets.connect_client()
        mock_client_cls.assert_called_once()

    @patch.object(AppSecrets, 'connect_client')
    def test_get_secret(self, mock_connect):
        mock_client = MagicMock()
        mock_client.secrets.kv.v2.read_secret_version.return_value = {"data": {"data": {"key": "value"}}}
        mock_connect.return_value = mock_client

        result = AppSecrets.get_secret("secret/path", version=1)
        mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with("secret/path", 1)
        self.assertEqual(result["data"]["data"]["key"], "value")

    @patch.object(AppSecrets, 'connect_client')
    def test_get_secret_no_version(self, mock_connect):
        mock_client = MagicMock()
        mock_connect.return_value = mock_client

        AppSecrets.get_secret("secret/path")
        mock_client.secrets.kv.v2.read_secret_version.assert_called_once_with("secret/path", None)


if __name__ == '__main__':
    unittest.main()
