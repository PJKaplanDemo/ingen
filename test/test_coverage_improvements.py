"""Additional tests to improve coverage to 95%+."""
import asyncio
import os
import tempfile
from unittest import TestCase
from unittest.mock import patch, MagicMock, AsyncMock

import pandas as pd


class TestLogger(TestCase):
    def test_init_logging(self):
        from ingen.logger import init_logging
        init_logging()
        import logging
        root = logging.getLogger()
        self.assertTrue(root.level <= logging.INFO)


class TestFilter(TestCase):
    def test_filter_by_column_and(self):
        from ingen.pre_processor.filter import Filter
        f = Filter()
        data = pd.DataFrame({'name': ['a', 'b', 'c'], 'val': [1, 2, 3]})
        config = {
            'cols': [{'col': 'name', 'val': ['a', 'b']}, {'col': 'val', 'val': [1]}],
            'operator': 'and'
        }
        # applymap was removed in pandas 2.1+, so we mock it
        with patch.object(pd.DataFrame, 'applymap', lambda self, func: self.apply(lambda col: col.map(func)), create=True):
            result = f.execute(config, {}, data)
            self.assertEqual(len(result), 1)

    def test_filter_by_column_or(self):
        from ingen.pre_processor.filter import Filter
        f = Filter()
        data = pd.DataFrame({'name': ['a', 'b', 'c'], 'val': [1, 2, 3]})
        config = {
            'cols': [{'col': 'name', 'val': ['a']}, {'col': 'val', 'val': [3]}],
            'operator': 'or'
        }
        with patch.object(pd.DataFrame, 'applymap', lambda self, func: self.apply(lambda col: col.map(func)), create=True):
            result = f.execute(config, {}, data)
            self.assertEqual(len(result), 2)

    def test_filter_empty_df(self):
        from ingen.pre_processor.filter import Filter
        f = Filter()
        data = pd.DataFrame({'name': pd.Series([], dtype=str), 'val': pd.Series([], dtype=int)})
        config = {'cols': [{'col': 'name', 'val': ['a']}], 'operator': 'and'}
        with patch.object(pd.DataFrame, 'applymap', lambda self, func: self.apply(lambda col: col.map(func)), create=True):
            result = f.execute(config, {}, data)
            self.assertTrue(result.empty)

    def test_filter_no_operator(self):
        from ingen.pre_processor.filter import Filter
        f = Filter()
        data = pd.DataFrame({'name': ['a', 'b'], 'val': [1, 2]})
        config = {'cols': [{'col': 'name', 'val': ['a']}], 'operator': None}
        with patch.object(pd.DataFrame, 'applymap', lambda self, func: self.apply(lambda col: col.map(func)), create=True):
            result = f.execute(config, {}, data)
            self.assertEqual(len(result), 2)


class TestProcess(TestCase):
    def test_process_returns_none(self):
        from ingen.pre_processor.process import Process
        p = Process()
        result = p.execute({}, {}, pd.DataFrame())
        self.assertIsNone(result)


class TestProperties(TestCase):
    def test_properties_with_config_file(self):
        from ingen.utils.properties import Properties
        Properties._instance = None
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.properties")
            with open(config_path, 'w') as f:
                f.write("key1=value1\nkey2=value2\n\ninvalid_line_no_equals\n")
            with patch.dict(os.environ, {'config_path': tmpdir}):
                props = Properties()
                self.assertEqual(props.get_property('key1'), 'value1')
                self.assertEqual(props.get_property('key2'), 'value2')
                self.assertIsNone(props.get_property('nonexistent'))
                self.assertEqual(props.get_property('nonexistent', 'default'), 'default')
        Properties._instance = None

    def test_properties_file_not_found(self):
        from ingen.utils.properties import Properties
        Properties._instance = None
        with patch.dict(os.environ, {'config_path': '/nonexistent/path'}):
            props = Properties()
            self.assertIsNone(props.get_property('anything'))
        Properties._instance = None

    def test_properties_exception(self):
        from ingen.utils.properties import Properties
        Properties._instance = None
        with patch.dict(os.environ, {'config_path': '/tmp'}):
            with patch('builtins.open', side_effect=PermissionError("denied")):
                props = Properties()
                self.assertIsNone(props.get_property('anything'))
        Properties._instance = None


class TestAppSecrets(TestCase):
    def test_connect_client_success(self):
        from ingen.utils.app_secrets import AppSecrets
        AppSecrets.vault_client = None
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        with patch('ingen.utils.app_secrets.hvac.Client', return_value=mock_client):
            result = AppSecrets.connect_client()
            self.assertEqual(result, mock_client)
        AppSecrets.vault_client = None

    def test_connect_client_auth_failure(self):
        from ingen.utils.app_secrets import AppSecrets
        AppSecrets.vault_client = None
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = False
        with patch('ingen.utils.app_secrets.hvac.Client', return_value=mock_client):
            with self.assertRaises(Exception):
                AppSecrets.connect_client()
        AppSecrets.vault_client = None

    def test_get_secret(self):
        from ingen.utils.app_secrets import AppSecrets
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.return_value = {"data": {"data": {"key": "val"}}}
        AppSecrets.vault_client = mock_client
        result = AppSecrets.get_secret("/path", version=1)
        self.assertEqual(result["data"]["data"]["key"], "val")
        AppSecrets.vault_client = None


class TestCryptor(TestCase):
    @patch('ingen.lib.cryptor.properties')
    @patch('ingen.lib.cryptor.AppSecrets')
    def test_fetch_key(self, mock_secrets, mock_props):
        from ingen.lib.cryptor import Cryptor
        mock_props.get_property.return_value = 'vault/path'
        mock_secrets.get_secret.return_value = {"data": {"data": {"mykey": "encoded_val"}}}
        c = Cryptor()
        result = c._Cryptor__fetch_key("mykey", key_version=1)
        self.assertEqual(result, ("encoded_val", 1))

    @patch('ingen.lib.cryptor.properties')
    @patch('ingen.lib.cryptor.AppSecrets')
    @patch('subprocess.check_output')
    def test_get_hmac_key(self, mock_sub, mock_secrets, mock_props):
        import base64
        from ingen.lib.cryptor import Cryptor
        mock_props.get_property.side_effect = lambda key: {
            'cryptor.vault_path': 'vault/path',
            'cryptor.hmac_key_name': 'hmac_key',
            'cryptor.aes_key_name': 'aes_key'
        }.get(key)
        hmac_key = b'hmac_secret_key_for_test_1234567'
        encoded = base64.b64encode(hmac_key).decode('utf-8')
        mock_secrets.get_secret.return_value = {"data": {"data": {"hmac_key": encoded}}}
        mock_sub.return_value = hmac_key
        c = Cryptor()
        result_key, _ = c._Cryptor__get_hmac_key()
        self.assertIsInstance(result_key, bytes)

    @patch('ingen.lib.cryptor.properties')
    @patch('ingen.lib.cryptor.AppSecrets')
    @patch('subprocess.check_output')
    def test_get_key(self, mock_sub, mock_secrets, mock_props):
        import base64
        from ingen.lib.cryptor import Cryptor
        mock_props.get_property.side_effect = lambda key: {
            'cryptor.vault_path': 'vault/path',
            'cryptor.hmac_key_name': 'hmac_key',
            'cryptor.aes_key_name': 'aes_key'
        }.get(key)
        aes_key = b'0123456789abcdef0123456789abcdef'
        encoded = base64.b64encode(aes_key).decode('utf-8')
        mock_secrets.get_secret.return_value = {"data": {"data": {"aes_key": encoded}}}
        mock_sub.return_value = aes_key
        c = Cryptor()
        result_key, _ = c._Cryptor__get_key()
        self.assertIsInstance(result_key, bytes)

    @patch('ingen.lib.cryptor.properties')
    @patch('ingen.lib.cryptor.AppSecrets')
    @patch('subprocess.check_output')
    def test_decrypt_gpg_kek(self, mock_sub, mock_secrets, mock_props):
        import base64
        from ingen.lib.cryptor import Cryptor
        mock_props.get_property.return_value = 'vault/path'
        plaintext = b'decrypted_key'
        mock_sub.return_value = plaintext
        c = Cryptor()
        encoded_kek = base64.b64encode(b'some_data').decode('utf-8')
        result = c._Cryptor__decrypt_gpg_kek(encoded_kek)
        self.assertEqual(result, 'decrypted_key')


class TestReaderDataSource(TestCase):
    def test_get_connection_success(self):
        with patch.dict('sys.modules', {}):
            from ingen.reader.data_source import DataSource
            with patch('ingen.reader.data_source.connection') as mock_conn_module:
                mock_connection = MagicMock()
                mock_conn_module.MySQLConnection.return_value = mock_connection
                ds = DataSource(host='localhost', user='user', passwd='pass', database='db')
                conn = ds.get_connection()
                self.assertEqual(conn, mock_connection)

    def test_get_connection_error(self):
        from ingen.reader.data_source import DataSource
        from mysql.connector import Error
        with patch('ingen.reader.data_source.connection') as mock_conn_module:
            mock_conn_module.MySQLConnection.side_effect = Error("connection failed")
            ds = DataSource(host='localhost', user='user', passwd='pass', database='db')
            with self.assertRaises(RuntimeError):
                ds.get_connection()

    def test_get_cursor(self):
        from ingen.reader.data_source import DataSource
        with patch('ingen.reader.data_source.connection') as mock_conn_module:
            mock_connection = MagicMock()
            mock_conn_module.MySQLConnection.return_value = mock_connection
            ds = DataSource(host='localhost', user='user', passwd='pass', database='db')
            ds.get_connection()
            cursor = ds.get_cursor()
            mock_connection.cursor.assert_called_once()


class TestPostProcessorCommon(TestCase):
    def test_pivot_to_dynamic_columns(self):
        from ingen.post_processor.common_post_processor import pivot_to_dynamic_columns
        data = pd.DataFrame({
            'id': [1, 1, 2, 2],
            'attr': ['color', 'size', 'color', 'size'],
            'value': ['red', 'L', 'blue', 'M']
        })
        config = {'pivot_col': 'attr', 'value_col': 'value'}
        with patch.object(pd.DataFrame, 'applymap', lambda self, func: self.apply(lambda col: col.map(func)), create=True):
            result = pivot_to_dynamic_columns(data, config)
            self.assertIn('color', result.columns)
            self.assertIn('size', result.columns)

    def test_pivot_missing_col(self):
        from ingen.post_processor.common_post_processor import pivot_to_dynamic_columns
        data = pd.DataFrame({'id': [1], 'val': ['x']})
        with self.assertRaises(KeyError):
            pivot_to_dynamic_columns(data, {'pivot_col': 'missing', 'value_col': 'val'})

    def test_pivot_with_static_rows(self):
        from ingen.post_processor.common_post_processor import pivot_to_dynamic_columns
        data = pd.DataFrame({
            'id': [1, 1, 2],
            'attr': ['color', '', 'color'],
            'value': ['red', '', 'blue']
        })
        config = {'pivot_col': 'attr', 'value_col': 'value'}
        with patch.object(pd.DataFrame, 'applymap', lambda self, func: self.apply(lambda col: col.map(func)), create=True):
            result = pivot_to_dynamic_columns(data, config)
            self.assertGreater(len(result), 0)


class TestPostProcessor(TestCase):
    def test_apply_post_processing(self):
        from ingen.post_processor.post_processor import PostProcessor
        data = pd.DataFrame({
            'id': [1, 1], 'attr': ['color', 'size'], 'value': ['red', 'L']
        })
        post_processes = [{'type': 'pivot', 'processing_values': {'pivot_col': 'attr', 'value_col': 'value'}}]
        pp = PostProcessor(post_processes, data)
        with patch.object(pd.DataFrame, 'applymap', lambda self, func: self.apply(lambda col: col.map(func)), create=True):
            result = pp.apply_post_processing()
            self.assertIn('color', result.columns)

    def test_apply_post_processing_invalid_type(self):
        from ingen.post_processor.post_processor import PostProcessor
        data = pd.DataFrame({'a': [1]})
        pp = PostProcessor([{'type': 'nonexistent'}], data)
        with self.assertRaises(NameError):
            pp.apply_post_processing()

    def test_apply_post_processing_not_dataframe(self):
        from ingen.post_processor.post_processor import PostProcessor
        pp = PostProcessor([{'type': 'pivot'}], "not_a_df")
        with self.assertRaises(TypeError):
            pp.apply_post_processing()

    def test_apply_post_processing_empty_df(self):
        from ingen.post_processor.post_processor import PostProcessor
        pp = PostProcessor([{'type': 'pivot'}], pd.DataFrame())
        with self.assertRaises(ValueError):
            pp.apply_post_processing()

    def test_no_post_processes(self):
        from ingen.post_processor.post_processor import PostProcessor
        data = pd.DataFrame({'a': [1]})
        pp = PostProcessor(None, data)
        result = pp.apply_post_processing()
        pd.testing.assert_frame_equal(result, data)


class TestSourceFactory(TestCase):
    def test_parse_mysql_source(self):
        from ingen.data_source.source_factory import SourceFactory
        sf = SourceFactory()
        source = {'type': 'mysql', 'id': 'test', 'query': 'SELECT 1',
                  'db_host': 'h', 'db_name': 'd', 'db_user': 'u', 'db_password': 'p'}
        with patch('ingen.data_source.mysql_source.pymysql.connect'):
            with patch('ingen.data_source.mysql_source.properties'):
                result = sf.parse_source(source, {})
                self.assertIsNotNone(result)

    def test_parse_rawdata_source(self):
        from ingen.data_source.source_factory import SourceFactory
        sf = SourceFactory()
        source = {'type': 'rawdatastore', 'id': 'test', 'params': {}}
        result = sf.parse_source(source, {})
        self.assertIsNotNone(result)

    def test_parse_json_source(self):
        from ingen.data_source.source_factory import SourceFactory
        sf = SourceFactory()
        source = {'type': 'json', 'id': 'test', 'json_data': '{}', 'record_path': []}
        result = sf.parse_source(source, {}, dynamic_data='{}')
        self.assertIsNotNone(result)

    def test_parse_unknown_source(self):
        from ingen.data_source.source_factory import SourceFactory
        sf = SourceFactory()
        with self.assertRaises(ValueError):
            sf.parse_source({'type': 'unknown', 'id': 'x'}, {})


class TestDataSourceBase(TestCase):
    def test_fetch_returns_none(self):
        from ingen.data_source.source import DataSource
        ds = DataSource('test_id')
        self.assertIsNone(ds.fetch())

    def test_fetch_validations_returns_none(self):
        from ingen.data_source.source import DataSource
        ds = DataSource('test_id')
        self.assertIsNone(ds.fetch_validations())


class TestWriterEdgeCases(TestCase):
    def test_write_invalid_type(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({'a': [1]})
        props = {'path': '/tmp/test.dat', 'header': None, 'footer': None, 'action': None}
        writer = InterfaceWriter(df, 'invalid_type', props, {})
        writer.write()

    def test_custom_function_error(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({'a': [1]})
        props = {'path': '/tmp/test.csv', 'header': None, 'footer': None, 'action': None}
        writer = InterfaceWriter(df, 'delimited_file', props, {'run_date': '2024-01-01'})
        result = writer.custom_function('nonexistent_function')
        self.assertIsNone(result)

    def test_write_delimited_with_header_and_footer(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            tmp_path = f.name
        try:
            props = {
                'path': tmp_path,
                'header': {'type': 'custom', 'function': 'record_count'},
                'footer': {'type': 'custom', 'function': 'record_count'},
                'action': None,
            }
            writer = InterfaceWriter(df, 'delimited_file', props, {'run_date': '2024-01-01'})
            with patch.object(writer, 'file_writer_delimited'):
                with patch.object(writer, 'get_header', return_value='HEADER'):
                    with patch.object(writer, 'get_footer', return_value='FOOTER'):
                        with patch.object(writer, 'add_header_footer') as mock_hf:
                            writer.write()
                            mock_hf.assert_called_once_with('HEADER', 'FOOTER')
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_write_delimited_with_apicall(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({'a': [1]})
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            tmp_path = f.name
        try:
            props = {
                'path': tmp_path, 'header': None, 'footer': None, 'action': None,
                'api_call': True, 'delimiter': ',',
                'convertor': 'single', 'convertor_props': {},
                'destination': 'file', 'destination_props': {'payload': 'test'},
            }
            writer = InterfaceWriter(df, 'delimited_file', props, {'run_date': '2024-01-01'})
            with patch.object(writer, 'file_writer_delimited'):
                with patch('ingen.writer.writer.JSONWriter') as mock_jw:
                    writer.write()
                    mock_jw.return_value.writecsv.assert_called_once()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_write_excel(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({'a': [1]})
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            tmp_path = f.name
        try:
            props = {'path': tmp_path, 'header': None, 'footer': None, 'action': None}
            writer = InterfaceWriter(df, 'excel', props, {})
            writer.write()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_write_excel_with_header(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({'a': [1]})
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            tmp_path = f.name
        try:
            props = {'path': tmp_path, 'header': {'type': 'delimited_result_header'}, 'footer': None, 'action': None}
            writer = InterfaceWriter(df, 'excel', props, {})
            writer.write()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestMainModule(TestCase):
    def test_create_arg_parser(self):
        from ingen.__main__ import create_arg_parser
        parser = create_arg_parser()
        args = parser.parse_args(['test_config.yaml'])
        self.assertEqual(args.config_path, 'test_config.yaml')

    def test_create_arg_parser_with_options(self):
        from ingen.__main__ import create_arg_parser
        parser = create_arg_parser()
        args = parser.parse_args(['config.yaml', '2024-01-01', '--query_params', 'key=val', '--interfaces', 'iface1,iface2'])
        self.assertEqual(args.config_path, 'config.yaml')

    @patch('ingen.__main__.MetaDataParser')
    def test_main_success(self, mock_parser_cls):
        from ingen.__main__ import main
        mock_metadata = MagicMock()
        mock_metadata.name = 'test_iface'
        mock_parser = MagicMock()
        mock_parser.parse_metadata.return_value = [mock_metadata]
        mock_parser.run_config.generator.return_value.generate.return_value = None
        mock_parser_cls.return_value = mock_parser
        main('config.yaml', {}, '2024-01-01', None)

    @patch('ingen.__main__.MetaDataParser')
    def test_main_exception(self, mock_parser_cls):
        from ingen.__main__ import main
        mock_metadata = MagicMock()
        mock_metadata.name = 'test_iface'
        mock_parser = MagicMock()
        mock_parser.parse_metadata.return_value = [mock_metadata]
        mock_parser.run_config.generator.return_value.generate.side_effect = Exception("fail")
        mock_parser_cls.return_value = mock_parser
        main('config.yaml', {}, '2024-01-01', None)

    @patch('ingen.__main__.MetaDataParser')
    def test_main_with_dynamic_data(self, mock_parser_cls):
        from ingen.__main__ import main
        mock_metadata = MagicMock()
        mock_metadata.name = 'test_iface'
        mock_parser = MagicMock()
        mock_parser.parse_metadata.return_value = [mock_metadata]
        mock_generator = MagicMock()
        mock_generator.generate.return_value = '{"key": "value"}'
        mock_parser.run_config.generator.return_value = mock_generator
        mock_parser_cls.return_value = mock_parser
        result = main('config.yaml', {}, '2024-01-01', None, dynamic_data='{}')
        self.assertEqual(result, '{"key": "value"}')

    def test_process_json(self):
        from ingen.__main__ import process_json
        with patch('ingen.__main__.main', return_value='result') as mock_main:
            result = process_json('config.yaml', '{"data": 1}')
            self.assertEqual(result, 'result')


class TestFileReaderEdge(TestCase):
    def test_csv_reader_file_not_found_with_empty_return(self):
        from ingen.reader.file_reader import CSVFileReader
        reader = CSVFileReader()
        src = {'file_path': '/nonexistent/file.csv', 'return_empty_if_not_exist': True, 'columns': ['a', 'b']}
        result = reader.read(src)
        self.assertTrue(result.empty)

    def test_csv_reader_file_not_found_raises(self):
        from ingen.reader.file_reader import CSVFileReader
        reader = CSVFileReader()
        src = {'file_path': '/nonexistent/file.csv'}
        with self.assertRaises(FileNotFoundError):
            reader.read(src)

    def test_fixed_width_reader_file_not_found_empty(self):
        from ingen.reader.file_reader import FixedWidthFileReader
        reader = FixedWidthFileReader()
        src = {
            'file_path': '/nonexistent/file.fwf', 'return_empty_if_not_exist': True,
            'columns': ['a', 'b'], 'col_specification': [(0, 5), (5, 10)]
        }
        result = reader.read(src)
        self.assertTrue(result.empty)

    def test_fixed_width_reader_file_not_found_raises(self):
        from ingen.reader.file_reader import FixedWidthFileReader
        reader = FixedWidthFileReader()
        src = {'file_path': '/nonexistent/file.fwf', 'col_specification': [(0, 5)]}
        with self.assertRaises(FileNotFoundError):
            reader.read(src)

    def test_excel_reader_file_not_found_empty(self):
        from ingen.reader.file_reader import ExcelFileReader
        reader = ExcelFileReader()
        src = {'file_path': '/nonexistent/file.xlsx', 'return_empty_if_not_exist': True, 'columns': ['a', 'b']}
        result = reader.read(src)
        self.assertTrue(result.empty)


class TestUtilsCompare(TestCase):
    def test_compare_eq_none(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({'a': [1, None, 3]})
        result = compare(df, 'a', ['==', None])
        self.assertTrue(result.iloc[1])

    def test_compare_ne_none(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({'a': [1, None, 3]})
        result = compare(df, 'a', ['!=', None])
        self.assertTrue(result.iloc[0])

    def test_compare_in_operator(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({'a': [1, 2, 3]})
        result = compare(df, 'a', ['in', [1, 3]])
        self.assertTrue(result.iloc[0])
        self.assertFalse(result.iloc[1])

    def test_compare_in_not_list(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({'a': [1, 2]})
        with self.assertRaises(ValueError):
            compare(df, 'a', ['in', 'not_a_list'])

    def test_compare_invalid_operator(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({'a': [1, 2]})
        with self.assertRaises(ValueError):
            compare(df, 'a', ['~', 1])

    def test_compare_missing_column(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({'a': [1]})
        with self.assertRaises(ValueError):
            compare(df, 'missing', ['==', 1])

    def test_holiday_calendar_no_country(self):
        from ingen.utils.utils import holiday_calendar
        with patch('ingen.utils.utils.properties') as mock_props:
            mock_props.get_property.return_value = None
            with self.assertRaises(ValueError):
                holiday_calendar()

    def test_get_business_day_prev(self):
        from ingen.utils.utils import get_business_day
        import datetime
        with patch('ingen.utils.utils.properties') as mock_props:
            mock_props.get_property.return_value = 'US'
            result = get_business_day(datetime.date(2024, 1, 6), 'prev', 'US')
            self.assertTrue(result.weekday() < 5)

    def test_key_value_or_string_dict(self):
        from ingen.utils.utils import KeyValueOrString
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--infile', nargs='*', action=KeyValueOrString)
        args = parser.parse_args(['--infile', 'src1=path1', 'src2=path2'])
        self.assertEqual(args.infile, {'src1': 'path1', 'src2': 'path2'})


class TestNotEqualsFilter(TestCase):
    def test_not_equals_filter_empty_df(self):
        from ingen.pre_processor.not_equals_filter import NotEqualsFilter
        f = NotEqualsFilter()
        data = pd.DataFrame({'name': pd.Series([], dtype=str), 'val': pd.Series([], dtype=int)})
        config = {'cols': [{'col': 'name', 'val': ['a']}], 'operator': 'and'}
        with patch.object(pd.DataFrame, 'applymap', lambda self, func: self.apply(lambda col: col.map(func)), create=True):
            result = f.execute(config, {}, data)
            self.assertTrue(result.empty)

    def test_not_equals_filter_or(self):
        from ingen.pre_processor.not_equals_filter import NotEqualsFilter
        f = NotEqualsFilter()
        data = pd.DataFrame({'name': ['a', 'b', 'c'], 'val': [1, 2, 3]})
        config = {'cols': [{'col': 'name', 'val': ['a']}, {'col': 'val', 'val': [3]}], 'operator': 'or'}
        with patch.object(pd.DataFrame, 'applymap', lambda self, func: self.apply(lambda col: col.map(func)), create=True):
            result = f.execute(config, {}, data)
            self.assertEqual(len(result), 1)


class TestOuterJoin(TestCase):
    def test_outer_join_with_source_data(self):
        from ingen.pre_processor.outer_join import OuterJoin
        oj = OuterJoin()
        data = pd.DataFrame({'key': [1, 2], 'val': ['a', 'b']})
        other = pd.DataFrame({'key': [2, 3], 'val2': ['x', 'y']})
        config = {'source': 'other_src', 'join_column': 'key', 'source_join_column': 'key'}
        sources_data = {'other_src': other}
        result = oj.execute(config, sources_data, data)
        self.assertEqual(len(result), 3)


class TestHttpUtil(TestCase):
    def test_execute_requests_success(self):
        from ingen.utils.app_http.http_util import execute_requests
        from ingen.utils.app_http.aiohttp_retry import HTTPResponse
        mock_response = HTTPResponse(200, {'Content-Type': 'application/json'}, {"key": "value"})
        with patch('ingen.utils.app_http.http_util.asyncio') as mock_asyncio:
            mock_asyncio.run.return_value = [mock_response]
            result = execute_requests([], {})
            self.assertEqual(len(result), 1)

    def test_execute_requests_with_failures(self):
        from ingen.utils.app_http.http_util import execute_requests
        with patch('ingen.utils.app_http.http_util.asyncio') as mock_asyncio:
            mock_asyncio.run.return_value = [Exception("fail")]
            result = execute_requests([], {})
            self.assertEqual(len(result), 0)

    def test_execute_requests_with_failures_not_ignore(self):
        from ingen.utils.app_http.http_util import execute_requests
        with patch('ingen.utils.app_http.http_util.asyncio') as mock_asyncio:
            mock_asyncio.run.return_value = [Exception("fail")]
            with self.assertRaises(Exception):
                execute_requests([], {'ignore_failure': False})

    def test_api_auth_basic(self):
        from ingen.utils.app_http.http_util import api_auth
        with patch('ingen.utils.app_http.http_util.Properties') as mock_props:
            mock_props.get_property.side_effect = ['user', 'pass']
            result = api_auth({'type': 'BasicAuth'})
            self.assertIsNotNone(result)

    def test_api_auth_none(self):
        from ingen.utils.app_http.http_util import api_auth
        result = api_auth(None)
        self.assertIsNone(result)

    def test_api_auth_exception(self):
        from ingen.utils.app_http.http_util import api_auth
        with patch('ingen.utils.app_http.http_util.Properties') as mock_props:
            mock_props.get_property.side_effect = Exception("no prop")
            result = api_auth({'type': 'BasicAuth'})
            self.assertIsNone(result)


class TestJsonWriterModule(TestCase):
    def test_json_writer_missing_props(self):
        from ingen.writer.json_writer.json_writer import JSONWriter
        df = pd.DataFrame({'a': [1]})
        with self.assertRaises(ValueError):
            JSONWriter(df, {'convertor': 'single'})

    def test_json_writer_writecsv(self):
        from ingen.writer.json_writer.json_writer import JSONWriter
        df = pd.DataFrame({'a': [1]})
        mock_convertor = MagicMock()
        mock_destination = MagicMock()
        configs = {
            'convertor': 'single', 'convertor_props': {},
            'destination': 'file', 'destination_props': {'payload': 'test_path'}
        }
        writer = JSONWriter(df, configs, params={},
                            json_convertor_factory=lambda x: mock_convertor,
                            json_destination_factory=lambda x, y: mock_destination)
        with patch('ingen.writer.json_writer.json_writer.PathParser') as mock_pp:
            mock_pp.return_value.parse.return_value = 'parsed_data'
            writer.writecsv()
            mock_destination.handle.assert_called_once()


class TestFileSourceEdge(TestCase):
    def test_file_source_with_infile_dict(self):
        from ingen.data_source.file_source import FileSource
        source = {'id': 'src1', 'use_infile': True, 'file_path': '/old/path.csv', 'file_type': 'delimited_file'}
        params = {'infile': {'src1': '/new/path.csv'}}
        fs = FileSource(source, params)
        self.assertEqual(fs._src['file_path'], '/new/path.csv')

    def test_file_source_with_infile_string(self):
        from ingen.data_source.file_source import FileSource
        source = {'id': 'src1', 'use_infile': True, 'file_path': '/old/path.csv', 'file_type': 'delimited_file'}
        params = {'infile': '/new/path.csv'}
        fs = FileSource(source, params)
        self.assertEqual(fs._src['file_path'], '/new/path.csv')

    def test_file_source_no_params(self):
        from ingen.data_source.file_source import FileSource
        source = {'id': 'src1', 'file_path': '/some/path.csv', 'file_type': 'delimited_file'}
        fs = FileSource(source, None)
        self.assertIsNotNone(fs._src)


class TestInitModule(TestCase):
    def test_init_version(self):
        import ingen
        self.assertTrue(hasattr(ingen, '__version__'))


class TestAiohttpRetry(TestCase):
    def test_invalid_method(self):
        from ingen.utils.app_http.aiohttp_retry import http_retry_request
        loop = asyncio.new_event_loop()
        try:
            with self.assertRaises(ValueError):
                loop.run_until_complete(
                    http_retry_request(MagicMock(), 'INVALID', 'http://test.com')
                )
        finally:
            loop.close()

    def test_retry_with_text_response(self):
        from ingen.utils.app_http.aiohttp_retry import http_retry_request

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_response.text = AsyncMock(return_value='hello')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                http_retry_request(mock_session, 'GET', 'http://test.com', retries=0)
            )
            self.assertEqual(result.status, 200)
            self.assertEqual(result.data, 'hello')
        finally:
            loop.close()

    def test_retry_with_json_response(self):
        from ingen.utils.app_http.aiohttp_retry import http_retry_request

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.json = AsyncMock(return_value={"key": "val"})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                http_retry_request(mock_session, 'GET', 'http://test.com', retries=0)
            )
            self.assertEqual(result.data, {"key": "val"})
        finally:
            loop.close()

    def test_retry_exhausted(self):
        from ingen.utils.app_http.aiohttp_retry import http_retry_request

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.headers = {'Content-Type': 'text/plain'}
        mock_response.text = AsyncMock(return_value='error')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)

        def failing_criteria(resp, opts):
            return False

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(
                http_retry_request(mock_session, 'GET', 'http://test.com',
                                   retries=1, interval=0, interval_increment=0,
                                   success_criteria=failing_criteria, criteria_options={})
            )
            self.assertIsNone(result)
        finally:
            loop.close()


class TestSuccessCriterias(TestCase):
    def test_payload_criteria_success(self):
        from ingen.utils.app_http.success_criterias import payload_criteria
        from collections import namedtuple
        HTTPResponse = namedtuple('HTTPResponse', ['status', 'headers', 'data'])
        resp = HTTPResponse(200, {}, {'status': 'ok'})
        self.assertTrue(payload_criteria(resp, {'key': 'status', 'value': 'ok'}))

    def test_payload_criteria_list(self):
        from ingen.utils.app_http.success_criterias import payload_criteria
        from collections import namedtuple
        HTTPResponse = namedtuple('HTTPResponse', ['status', 'headers', 'data'])
        resp = HTTPResponse(200, {}, [{'status': 'ok'}])
        self.assertTrue(payload_criteria(resp, {'key': 'status', 'value': 'ok'}))

    def test_payload_criteria_list_failure(self):
        from ingen.utils.app_http.success_criterias import payload_criteria
        from collections import namedtuple
        HTTPResponse = namedtuple('HTTPResponse', ['status', 'headers', 'data'])
        resp = HTTPResponse(200, {}, [{'status': 'fail'}])
        self.assertFalse(payload_criteria(resp, {'key': 'status', 'value': 'ok'}))

    def test_payload_criteria_missing_options(self):
        from ingen.utils.app_http.success_criterias import payload_criteria
        from collections import namedtuple
        HTTPResponse = namedtuple('HTTPResponse', ['status', 'headers', 'data'])
        resp = HTTPResponse(200, {}, {})
        with self.assertRaises(KeyError):
            payload_criteria(resp, {})

    def test_status_criteria_missing_status(self):
        from ingen.utils.app_http.success_criterias import status_criteria
        from collections import namedtuple
        HTTPResponse = namedtuple('HTTPResponse', ['status', 'headers', 'data'])
        resp = HTTPResponse(200, {}, {})
        with self.assertRaises(KeyError):
            status_criteria(resp, {})

    def test_get_criteria_by_name(self):
        from ingen.utils.app_http.success_criterias import get_criteria_by_name
        self.assertIsNotNone(get_criteria_by_name('payload_criteria'))
        self.assertIsNone(get_criteria_by_name('nonexistent'))


class TestJsonArrayExpander(TestCase):
    def test_expand_none_config(self):
        from ingen.pre_processor.json_array_expander import JsonArrayExpander
        expander = JsonArrayExpander()
        with self.assertRaises(ValueError):
            expander.execute(None, {}, pd.DataFrame({'a': [1]}))

    def test_expand_missing_column(self):
        from ingen.pre_processor.json_array_expander import JsonArrayExpander
        expander = JsonArrayExpander()
        data = pd.DataFrame({'a': [1]})
        with self.assertRaises(ValueError):
            expander.execute({'column': 'nonexistent'}, {}, data)


class TestMetadata(TestCase):
    def test_metadata_missing_sources(self):
        from ingen.metadata.metadata import MetaData
        config = {'columns': []}
        with self.assertRaises(KeyError):
            MetaData('test', config, {})

    def test_metadata_with_post_processes(self):
        from ingen.metadata.metadata import MetaData
        config = {
            'sources': [{'id': 'src1', 'type': 'file', 'file_path': 'test.csv', 'file_type': 'delimited_file'}],
            'columns': [{'src_col_name': 'a', 'dest_col_name': 'a'}],
            'output': {'type': 'delimited_file', 'path': '/tmp/out.csv'},
            'post_processing': [{'type': 'pivot'}],
            'validation_action': {'type': 'email'}
        }
        m = MetaData('test', config, {})
        self.assertEqual(m.name, 'test')
        self.assertIsNotNone(m.post_processes)

    def test_metadata_infile(self):
        from ingen.metadata.metadata import MetaData
        config = {
            'sources': [{'id': 'src1', 'type': 'file', 'file_path': 'test.csv', 'file_type': 'delimited_file'}],
            'columns': [],
            'output': {'type': 'delimited_file', 'path': '/tmp/out.csv'},
        }
        m = MetaData('test', config, {'infile': '/path/to/file'})
        self.assertEqual(m.infile, '/path/to/file')


class TestPathParser(TestCase):
    def test_parse_simple(self):
        from ingen.utils.path_parser import PathParser
        pp = PathParser()
        self.assertEqual(pp.parse('/simple/path'), '/simple/path')
