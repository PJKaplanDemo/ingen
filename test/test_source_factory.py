#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import unittest
from unittest.mock import patch, MagicMock

from ingen.data_source.source_factory import SourceFactory
from ingen.data_source.data_source_type import DataSourceType


class TestSourceFactory(unittest.TestCase):

    def setUp(self):
        self.factory = SourceFactory()

    @patch('ingen.data_source.source_factory.FileSource')
    def test_parse_file_source(self, mock_file_source):
        source = {'type': DataSourceType.File.value, 'id': 'test'}
        params_map = {}
        self.factory.parse_source(source, params_map)
        mock_file_source.assert_called_once_with(source, params_map)

    @patch('ingen.data_source.source_factory.MYSQLSource')
    def test_parse_mysql_source(self, mock_mysql_source):
        source = {'type': DataSourceType.MYSQL.value, 'id': 'test'}
        self.factory.parse_source(source, {})
        mock_mysql_source.assert_called_once_with(source)

    @patch('ingen.data_source.source_factory.RawDataSource')
    def test_parse_rawdata_source(self, mock_raw_source):
        source = {'type': DataSourceType.RawDataStore.value, 'id': 'test'}
        self.factory.parse_source(source, {})
        mock_raw_source.assert_called_once_with(source)

    @patch('ingen.data_source.source_factory.JsonSource')
    def test_parse_json_source(self, mock_json_source):
        source = {'type': DataSourceType.JSON.value, 'id': 'test'}
        self.factory.parse_source(source, {}, dynamic_data='{"key": "val"}')
        mock_json_source.assert_called_once_with(source, '{"key": "val"}')

    def test_parse_api_source(self):
        source = {'type': DataSourceType.Api.value, 'id': 'test', 'url': 'http://example.com', 'data_node': 'data', 'data_key': 'key'}
        with patch('ingen.data_source.api_source.APISource.__init__', return_value=None):
            self.factory.parse_source(source, {})

    def test_parse_unknown_source_raises(self):
        source = {'type': 'unknown'}
        with self.assertRaises(ValueError):
            self.factory.parse_source(source, {})


if __name__ == '__main__':
    unittest.main()
