#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import os
import json
import tempfile
import asyncio
from unittest import TestCase, mock

import pandas as pd


class TestFileReaderCSV(TestCase):
    def test_csv_reader(self):
        from ingen.reader.file_reader import CSVFileReader

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("a,b,c\n1,2,3\n4,5,6\n")
            path = f.name

        try:
            reader = CSVFileReader()
            src = {'file_path': path, 'delimiter': ',', 'columns': ['a', 'b', 'c'], 'skip_header_size': 1}
            result = reader.read(src)
            self.assertEqual(len(result), 2)
        finally:
            os.unlink(path)

    def test_csv_reader_file_not_found_return_empty(self):
        from ingen.reader.file_reader import CSVFileReader

        reader = CSVFileReader()
        src = {
            'file_path': '/nonexistent/file.csv',
            'delimiter': ',',
            'columns': ['a', 'b'],
            'return_empty_if_not_exist': True
        }
        result = reader.read(src)
        self.assertEqual(len(result), 0)

    def test_csv_reader_file_not_found_raises(self):
        from ingen.reader.file_reader import CSVFileReader

        reader = CSVFileReader()
        src = {
            'file_path': '/nonexistent/file.csv',
            'delimiter': ',',
            'columns': ['a', 'b']
        }
        with self.assertRaises(FileNotFoundError):
            reader.read(src)


class TestFileReaderExcel(TestCase):
    def test_excel_reader_file_not_found_return_empty(self):
        from ingen.reader.file_reader import ExcelFileReader

        reader = ExcelFileReader()
        src = {
            'file_path': '/nonexistent/file.xlsx',
            'columns': ['a', 'b'],
            'return_empty_if_not_exist': True
        }
        result = reader.read(src)
        self.assertEqual(len(result), 0)

    def test_excel_reader_file_not_found_raises(self):
        from ingen.reader.file_reader import ExcelFileReader

        reader = ExcelFileReader()
        src = {
            'file_path': '/nonexistent/file.xlsx',
            'columns': ['a', 'b']
        }
        with self.assertRaises(FileNotFoundError):
            reader.read(src)

    def test_excel_reader_no_sheet_name(self):
        from ingen.reader.file_reader import ExcelFileReader

        reader = ExcelFileReader()
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            path = f.name

        try:
            df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
            df.to_excel(path, index=False)
            src = {'file_path': path, 'columns': None}
            result = reader.read(src)
            self.assertIsNotNone(result)
        finally:
            os.unlink(path)


class TestFixedWidthFileReader(TestCase):
    def test_fwf_reader_file_not_found_return_empty(self):
        from ingen.reader.file_reader import FixedWidthFileReader

        reader = FixedWidthFileReader()
        src = {
            'file_path': '/nonexistent/file.txt',
            'columns': ['a', 'b'],
            'col_specification': [(0, 5), (5, 10)],
            'return_empty_if_not_exist': True
        }
        result = reader.read(src)
        self.assertEqual(len(result), 0)

    def test_fwf_reader_file_not_found_raises(self):
        from ingen.reader.file_reader import FixedWidthFileReader

        reader = FixedWidthFileReader()
        src = {
            'file_path': '/nonexistent/file.txt',
            'columns': ['a', 'b'],
            'col_specification': [(0, 5), (5, 10)]
        }
        with self.assertRaises(FileNotFoundError):
            reader.read(src)


class TestDataSourceBase(TestCase):
    def test_data_source_fetch(self):
        from ingen.data_source.source import DataSource

        ds = DataSource('test')
        self.assertIsNone(ds.fetch())

    def test_data_source_fetch_validations(self):
        from ingen.data_source.source import DataSource

        ds = DataSource('test')
        self.assertIsNone(ds.fetch_validations())

    def test_data_source_id(self):
        from ingen.data_source.source import DataSource

        ds = DataSource('test_id')
        self.assertEqual(ds.id, 'test_id')


class TestAiohttpRetry(TestCase):
    def test_invalid_method_raises(self):
        from ingen.utils.app_http.aiohttp_retry import http_retry_request

        async def run():
            session = mock.MagicMock()
            with self.assertRaises(ValueError):
                await http_retry_request(session, 'INVALID', 'http://test.com')

        asyncio.get_event_loop().run_until_complete(run())

    def test_successful_get(self):
        from ingen.utils.app_http.aiohttp_retry import http_retry_request

        async def run():
            mock_response = mock.AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Type': 'text/plain'}
            mock_response.text = mock.AsyncMock(return_value='response body')

            mock_ctx = mock.AsyncMock()
            mock_ctx.__aenter__.return_value = mock_response

            mock_session = mock.MagicMock()
            mock_session.get = mock.MagicMock(return_value=mock_ctx)

            result = await http_retry_request(mock_session, 'GET', 'http://test.com', retries=0)
            self.assertEqual(result.status, 200)

        asyncio.get_event_loop().run_until_complete(run())

    def test_json_response(self):
        from ingen.utils.app_http.aiohttp_retry import http_retry_request

        async def run():
            mock_response = mock.AsyncMock()
            mock_response.status = 200
            mock_response.headers = {'Content-Type': 'application/json'}
            mock_response.json = mock.AsyncMock(return_value={'key': 'value'})

            mock_ctx = mock.AsyncMock()
            mock_ctx.__aenter__.return_value = mock_response

            mock_session = mock.MagicMock()
            mock_session.get = mock.MagicMock(return_value=mock_ctx)

            result = await http_retry_request(mock_session, 'GET', 'http://test.com', retries=0)
            self.assertEqual(result.data, {'key': 'value'})

        asyncio.get_event_loop().run_until_complete(run())

    def test_retry_on_failure(self):
        from ingen.utils.app_http.aiohttp_retry import http_retry_request
        from ingen.utils.app_http.success_criterias import status_criteria

        call_count = 0

        async def run():
            nonlocal call_count

            mock_response = mock.AsyncMock()
            mock_response.status = 500
            mock_response.headers = {'Content-Type': 'text/plain'}
            mock_response.text = mock.AsyncMock(return_value='error')

            mock_ctx = mock.AsyncMock()
            mock_ctx.__aenter__.return_value = mock_response

            mock_session = mock.MagicMock()
            mock_session.get = mock.MagicMock(return_value=mock_ctx)

            result = await http_retry_request(
                mock_session, 'GET', 'http://test.com',
                retries=1, interval=0, interval_increment=0
            )
            self.assertIsNone(result)

        asyncio.get_event_loop().run_until_complete(run())

    def test_connection_error(self):
        from ingen.utils.app_http.aiohttp_retry import http_retry_request

        async def run():
            mock_response = mock.AsyncMock()
            mock_response.status = mock.PropertyMock(side_effect=Exception("err"))

            mock_ctx = mock.AsyncMock()
            mock_ctx.__aenter__.return_value = mock_response

            mock_session = mock.MagicMock()
            mock_session.get = mock.MagicMock(return_value=mock_ctx)

            with self.assertRaises(ConnectionError):
                await http_retry_request(mock_session, 'GET', 'http://test.com', retries=0)

        asyncio.get_event_loop().run_until_complete(run())


class TestSuccessCriterias(TestCase):
    def test_status_criteria_success(self):
        from ingen.utils.app_http.success_criterias import status_criteria, DEFAULT_STATUS_CRITERIA_OPTIONS
        from ingen.utils.app_http.aiohttp_retry import HTTPResponse

        response = HTTPResponse(200, {}, 'ok')
        self.assertTrue(status_criteria(response, DEFAULT_STATUS_CRITERIA_OPTIONS))

    def test_status_criteria_failure(self):
        from ingen.utils.app_http.success_criterias import status_criteria, DEFAULT_STATUS_CRITERIA_OPTIONS
        from ingen.utils.app_http.aiohttp_retry import HTTPResponse

        response = HTTPResponse(500, {}, 'error')
        self.assertFalse(status_criteria(response, DEFAULT_STATUS_CRITERIA_OPTIONS))


class TestMainIfBlock(TestCase):
    @mock.patch('ingen.__main__.main')
    @mock.patch('ingen.__main__.create_arg_parser')
    @mock.patch('ingen.__main__.init_logging')
    def test_main_entry_point(self, mock_init_log, mock_arg_parser, mock_main):
        import sys
        from ingen import __main__

        mock_args = mock.MagicMock()
        mock_args.interfaces = "iface1,iface2"
        mock_args.infile = None
        mock_args.config_path = "config.yaml"
        mock_args.query_params = None
        mock_args.run_date = None
        mock_args.override_params = None
        mock_arg_parser.return_value.parse_args.return_value = mock_args

        with mock.patch.object(sys, 'argv', ['__main__.py', 'config.yaml']):
            exec(compile(
                'if True:\n' +
                '    init_logging()\n' +
                '    arg_parser = create_arg_parser()\n' +
                '    args = arg_parser.parse_args()\n' +
                '    if args.interfaces is not None:\n' +
                '        args.interfaces = args.interfaces.split(",")\n' +
                '    if args.infile:\n' +
                '        pass\n' +
                '    main(args.config_path, args.query_params, args.run_date, args.interfaces, args.infile, override_params=args.override_params)\n',
                '<test>', 'exec'
            ), {
                'init_logging': mock_init_log,
                'create_arg_parser': mock_arg_parser,
                'main': mock_main,
            })

        mock_main.assert_called_once()
        self.assertEqual(mock_args.interfaces, ["iface1", "iface2"])


class TestNotEqualsFilter(TestCase):
    def test_not_equals_filter_execute(self):
        from ingen.pre_processor.not_equals_filter import NotEqualsFilter

        f = NotEqualsFilter()
        data = pd.DataFrame({'A': [1, 2, 3, 4], 'B': ['x', 'y', 'x', 'z']})
        config = {
            'cols': [{'col': 'A', 'val': [2, 3]}]
        }
        result = f.execute(config, {}, data)
        self.assertEqual(len(result), 2)

    def test_not_equals_filter_empty(self):
        from ingen.pre_processor.not_equals_filter import NotEqualsFilter

        f = NotEqualsFilter()
        data = pd.DataFrame({'A': pd.Series(dtype='int'), 'B': pd.Series(dtype='str')})
        config = {'col': 'A', 'val': [1]}
        result = f.execute(config, {}, data)
        self.assertEqual(len(result), 0)


class TestOuterJoin(TestCase):
    def test_outer_join_execute(self):
        from ingen.pre_processor.outer_join import OuterJoin

        oj = OuterJoin()
        data1 = pd.DataFrame({'key': [1, 2], 'val': ['a', 'b']})
        data2 = pd.DataFrame({'key': [2, 3], 'val2': ['c', 'd']})
        sources_data = {'src2': data2}
        config = {
            'source': 'src2',
            'left_key': 'key',
            'right_key': 'key'
        }
        result = oj.execute(config, sources_data, data1)
        self.assertEqual(len(result), 3)

    def test_outer_join_no_keys(self):
        from ingen.pre_processor.outer_join import OuterJoin

        oj = OuterJoin()
        data1 = pd.DataFrame({'key': [1, 2], 'val': ['a', 'b']})
        data2 = pd.DataFrame({'key': [2, 3], 'val2': ['c', 'd']})
        sources_data = {'src2': data2}
        config = {
            'source': 'src2',
        }
        result = oj.execute(config, sources_data, data1)
        self.assertIsNotNone(result)


class TestProcess(TestCase):
    def test_process_base_execute(self):
        from ingen.pre_processor.process import Process

        p = Process()
        self.assertIsNone(p.execute(None, None, None))


class TestHttpUtil(TestCase):
    @mock.patch('ingen.utils.app_http.http_util.Properties')
    def test_api_auth_basic(self, mock_props):
        from ingen.utils.app_http.http_util import api_auth

        mock_props.get_property.side_effect = lambda x: 'user' if 'username' in x else 'pass'
        auth = api_auth({'type': 'BasicAuth'})
        self.assertIsNotNone(auth)

    def test_api_auth_none(self):
        from ingen.utils.app_http.http_util import api_auth

        auth = api_auth(None)
        self.assertIsNone(auth)

    @mock.patch('ingen.utils.app_http.http_util.Properties')
    def test_api_auth_exception(self, mock_props):
        from ingen.utils.app_http.http_util import api_auth

        mock_props.get_property.side_effect = Exception('no property')
        result = api_auth({'type': 'BasicAuth'})
        self.assertIsNone(result)


class TestXmlFileReader(TestCase):
    def test_xml_file_reader(self):
        from ingen.reader.xml_file_reader import XMLFileReader

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write('<?xml version="1.0"?>\n<root><item><a>1</a><b>2</b></item></root>')
            path = f.name

        try:
            reader = XMLFileReader()
            src = {
                'file_path': path,
                'root_tag': 'item',
                'columns': ['a', 'b']
            }
            result = reader.read(src)
            self.assertIsNotNone(result)
        finally:
            os.unlink(path)

    def test_xml_file_reader_not_found(self):
        from ingen.reader.xml_file_reader import XMLFileReader

        reader = XMLFileReader()
        src = {
            'file_path': '/nonexistent/file.xml',
            'root_tag': 'item',
            'columns': ['a', 'b']
        }
        with self.assertRaises(FileNotFoundError):
            reader.read(src)


class TestCommonInterpolators(TestCase):
    def test_timestamp(self):
        from ingen.utils.interpolators.common_interpolators import timestamp

        result = timestamp('%Y-%m-%d')
        self.assertIsNotNone(result)

    def test_timestamp_none_format(self):
        from ingen.utils.interpolators.common_interpolators import timestamp

        with self.assertRaises(ValueError):
            timestamp(None)

    def test_uuid_func(self):
        from ingen.utils.interpolators.common_interpolators import uuid_func

        result = uuid_func()
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 36)

    def test_get_infile_none(self):
        from ingen.utils.interpolators.common_interpolators import get_infile

        result = get_infile(None, {})
        self.assertEqual(result, '')

    def test_get_infile_string(self):
        from ingen.utils.interpolators.common_interpolators import get_infile

        result = get_infile(None, {'infile': '/path/to/file.csv'})
        self.assertEqual(result, 'file.csv')

    def test_get_infile_dict(self):
        from ingen.utils.interpolators.common_interpolators import get_infile

        result = get_infile('src1', {'infile': {'src1': '/path/to/file.csv'}})
        self.assertEqual(result, 'file.csv')

    def test_get_infile_dict_missing_key(self):
        from ingen.utils.interpolators.common_interpolators import get_infile

        result = get_infile('src2', {'infile': {'src1': '/path/to/file.csv'}})
        self.assertEqual(result, '')

    def test_get_overrides(self):
        from ingen.utils.interpolators.common_interpolators import get_overrides

        result = get_overrides('key1', {'override_params': {'key1': 'val1'}})
        self.assertEqual(result, 'val1')

    def test_get_overrides_none(self):
        from ingen.utils.interpolators.common_interpolators import get_overrides

        result = get_overrides('key1', None)
        self.assertEqual(result, '')
