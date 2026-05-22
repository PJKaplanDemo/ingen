#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

"""Tests to improve coverage for modules with gaps."""

import logging
import os
import tempfile
import unittest
from unittest import mock

import pandas as pd


class TestLogger(unittest.TestCase):
    """Cover ingen/logger.py"""

    def test_init_logging(self):
        from ingen.logger import init_logging
        init_logging()
        root_logger = logging.getLogger()
        self.assertTrue(root_logger.level <= logging.INFO)


class TestProperties(unittest.TestCase):
    """Cover ingen/utils/properties.py"""

    def test_properties_with_config_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            props_file = os.path.join(tmpdir, "config.properties")
            with open(props_file, 'w') as f:
                f.write("key1=value1\nkey2=value2\n\ninvalid_line\n")
            with mock.patch.dict(os.environ, {"config_path": tmpdir}):
                from ingen.utils.properties import Properties
                Properties._instance = None
                p = Properties()
                self.assertEqual(p.get_property("key1"), "value1")
                self.assertEqual(p.get_property("key2"), "value2")
                self.assertIsNone(p.get_property("nonexistent"))
                self.assertEqual(p.get_property("nonexistent", "default"), "default")

    def test_properties_file_not_found(self):
        with mock.patch.dict(os.environ, {"config_path": "/nonexistent/path"}):
            from ingen.utils.properties import Properties
            Properties._instance = None
            p = Properties()
            self.assertEqual(p.property_map, {})

    def test_properties_no_config_path(self):
        env = os.environ.copy()
        env.pop("config_path", None)
        with mock.patch.dict(os.environ, env, clear=True):
            from ingen.utils.properties import Properties
            Properties._instance = None
            p = Properties()
            self.assertEqual(p.property_map, {})


class TestAppSecrets(unittest.TestCase):
    """Cover ingen/utils/app_secrets.py"""

    @mock.patch('ingen.utils.app_secrets.hvac.Client')
    @mock.patch('ingen.utils.app_secrets.properties')
    def test_connect_client_success(self, mock_props, mock_hvac_client):
        mock_props.get_property.return_value = "http://localhost:8200"
        mock_client = mock.MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        from ingen.utils.app_secrets import AppSecrets
        AppSecrets.vault_client = None
        result = AppSecrets.connect_client()
        self.assertEqual(result, mock_client)

    @mock.patch('ingen.utils.app_secrets.hvac.Client')
    @mock.patch('ingen.utils.app_secrets.properties')
    def test_connect_client_auth_failure(self, mock_props, mock_hvac_client):
        mock_props.get_property.return_value = "http://localhost:8200"
        mock_client = mock.MagicMock()
        mock_client.is_authenticated.return_value = False
        mock_hvac_client.return_value = mock_client

        from ingen.utils.app_secrets import AppSecrets
        AppSecrets.vault_client = None
        with self.assertRaises(Exception):
            AppSecrets.connect_client()

    @mock.patch('ingen.utils.app_secrets.hvac.Client')
    @mock.patch('ingen.utils.app_secrets.properties')
    def test_get_secret(self, mock_props, mock_hvac_client):
        mock_props.get_property.return_value = "http://localhost:8200"
        mock_client = mock.MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.return_value = {"data": "secret"}
        mock_hvac_client.return_value = mock_client

        from ingen.utils.app_secrets import AppSecrets
        AppSecrets.vault_client = None
        result = AppSecrets.get_secret("my/path", version=1)
        self.assertEqual(result, {"data": "secret"})


class TestMainModule(unittest.TestCase):
    """Cover ingen/__main__.py"""

    def test_create_arg_parser(self):
        from ingen.__main__ import create_arg_parser
        parser = create_arg_parser()
        args = parser.parse_args(["test_config.yaml"])
        self.assertEqual(args.config_path, "test_config.yaml")

    def test_create_arg_parser_with_options(self):
        from ingen.__main__ import create_arg_parser
        parser = create_arg_parser()
        args = parser.parse_args([
            "test_config.yaml", "2024-01-01",
            "--interfaces", "iface1,iface2",
            "--override_params", "key1=val1"
        ])
        self.assertEqual(args.config_path, "test_config.yaml")
        self.assertEqual(args.interfaces, "iface1,iface2")

    @mock.patch('ingen.__main__.MetaDataParser')
    def test_main_with_dynamic_data(self, mock_parser_cls):
        mock_metadata = mock.MagicMock()
        mock_metadata.name = "test_iface"
        mock_parser = mock.MagicMock()
        mock_parser.parse_metadata.return_value = [mock_metadata]
        mock_run_config = mock.MagicMock()
        mock_run_config.generator.return_value.generate.return_value = '{"key": "val"}'
        mock_parser.run_config = mock_run_config
        mock_parser_cls.return_value = mock_parser

        from ingen.__main__ import main
        result = main("config.yaml", None, None, None, dynamic_data='{"key": "val"}')
        self.assertEqual(result, '{"key": "val"}')

    @mock.patch('ingen.__main__.MetaDataParser')
    def test_main_exception_handling(self, mock_parser_cls):
        mock_metadata = mock.MagicMock()
        mock_metadata.name = "test_interface"
        mock_parser = mock.MagicMock()
        mock_parser.parse_metadata.return_value = [mock_metadata]
        mock_run_config = mock.MagicMock()
        mock_run_config.generator.return_value.generate.side_effect = Exception("test error")
        mock_parser.run_config = mock_run_config
        mock_parser_cls.return_value = mock_parser

        from ingen.__main__ import main
        main("config.yaml", None, None, None)


class TestSourceFactory(unittest.TestCase):
    """Cover ingen/data_source/source_factory.py"""

    def test_unknown_source_type(self):
        from ingen.data_source.source_factory import SourceFactory
        factory = SourceFactory()
        with self.assertRaises(ValueError):
            factory.parse_source({'type': 'unknown_type'}, {})


class TestDataSource(unittest.TestCase):
    """Cover ingen/data_source/source.py"""

    def test_data_source_id(self):
        from ingen.data_source.source import DataSource
        ds = DataSource("test_id")
        self.assertEqual(ds.id, "test_id")

    def test_data_source_fetch(self):
        from ingen.data_source.source import DataSource
        ds = DataSource("test_id")
        self.assertIsNone(ds.fetch())

    def test_data_source_fetch_validations(self):
        from ingen.data_source.source import DataSource
        ds = DataSource("test_id")
        self.assertIsNone(ds.fetch_validations())


class TestFileDestination(unittest.TestCase):
    """Cover writer/json_writer/destinations/file_destination.py"""

    def test_handle_writes_to_file(self):
        from ingen.writer.json_writer.destinations.file_destination import FileDestination
        dest = FileDestination()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name

        dest.handle(['{"key": "value"}'], {'path': path})
        with open(path, 'r') as f:
            self.assertEqual(f.read(), '{"key": "value"}')
        os.unlink(path)


class TestDFToSingleJsonConvertor(unittest.TestCase):
    """Cover writer/json_writer/convertors/df_to_single_json_convertor.py"""

    def test_convert(self):
        from ingen.writer.json_writer.convertors.df_to_single_json_convertor import DFToSingleJsonConvertor
        convertor = DFToSingleJsonConvertor()
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        configs = {
            "indent": 2,
            "orient": "records",
            "column_details": {
                "resultant_columns": ["a", "b"],
                "schema": [{"field_name": "a", "field_type": "int", "field_attr": None, "field_action": None}]
            }
        }
        result = convertor.convert(df, configs)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)


class TestConvertorFactory(unittest.TestCase):
    """Cover writer/json_writer/convertors/convertor_factory.py"""

    def test_get_single_convertor(self):
        from ingen.writer.json_writer.convertors.convertor_factory import get_json_convertor
        from ingen.writer.json_writer.convertors.df_to_single_json_convertor import DFToSingleJsonConvertor
        result = get_json_convertor('single')
        self.assertIsInstance(result, DFToSingleJsonConvertor)

    def test_get_multiple_convertor(self):
        from ingen.writer.json_writer.convertors.convertor_factory import get_json_convertor
        from ingen.writer.json_writer.convertors.df_to_multiple_json_convertor import DFToMultipleJsonConvertor
        result = get_json_convertor('multiple')
        self.assertIsInstance(result, DFToMultipleJsonConvertor)

    def test_get_unknown_convertor(self):
        from ingen.writer.json_writer.convertors.convertor_factory import get_json_convertor
        result = get_json_convertor('unknown')
        self.assertIsNone(result)


class TestDestinationFactory(unittest.TestCase):
    """Cover writer/json_writer/destinations/destination_factory.py"""

    def test_get_file_destination(self):
        from ingen.writer.json_writer.destinations.destination_factory import get_json_destination
        from ingen.writer.json_writer.destinations.file_destination import FileDestination
        result = get_json_destination('file')
        self.assertIsInstance(result, FileDestination)

    def test_get_api_destination(self):
        from ingen.writer.json_writer.destinations.destination_factory import get_json_destination
        from ingen.writer.json_writer.destinations.api_destination import ApiDestination
        result = get_json_destination('api', params={})
        self.assertIsInstance(result, ApiDestination)

    def test_get_unknown_destination(self):
        from ingen.writer.json_writer.destinations.destination_factory import get_json_destination
        result = get_json_destination('unknown')
        self.assertIsNone(result)


class TestPostProcessor(unittest.TestCase):
    """Cover post_processor/post_processor.py"""

    def test_apply_post_processing_none(self):
        from ingen.post_processor.post_processor import PostProcessor
        df = pd.DataFrame({"a": [1, 2]})
        pp = PostProcessor(None, df)
        result = pp.apply_post_processing()
        pd.testing.assert_frame_equal(result, df)

    def test_apply_post_processing_not_dataframe(self):
        from ingen.post_processor.post_processor import PostProcessor
        pp = PostProcessor([{"type": "pivot"}], "not a dataframe")
        with self.assertRaises(TypeError):
            pp.apply_post_processing()

    def test_apply_post_processing_empty_dataframe(self):
        from ingen.post_processor.post_processor import PostProcessor
        pp = PostProcessor([{"type": "pivot"}], pd.DataFrame())
        with self.assertRaises(ValueError):
            pp.apply_post_processing()

    def test_get_processor_func_unknown(self):
        from ingen.post_processor.post_processor import PostProcessor
        pp = PostProcessor([], pd.DataFrame({"a": [1]}))
        with self.assertRaises(NameError):
            pp.get_processor_func({"type": "unknown_processor"})


class TestJSONWriter(unittest.TestCase):
    """Cover writer/json_writer/json_writer.py"""

    def test_validate_writer_config_missing_props(self):
        from ingen.writer.json_writer.json_writer import JSONWriter
        df = pd.DataFrame({"a": [1]})
        with self.assertRaises(ValueError):
            JSONWriter(df, {"convertor": "single"})

    def test_write(self):
        from ingen.writer.json_writer.json_writer import JSONWriter

        mock_convertor = mock.MagicMock()
        mock_convertor.convert.return_value = ['{"a": 1}']
        mock_destination = mock.MagicMock()

        df = pd.DataFrame({"a": [1]})
        configs = {
            'convertor': 'single',
            'convertor_props': {},
            'destination': 'file',
            'destination_props': {'path': '/tmp/test.json'}
        }
        writer = JSONWriter(df, configs, params={},
                            json_convertor_factory=lambda x: mock_convertor,
                            json_destination_factory=lambda x, y: mock_destination)
        writer.write()
        mock_convertor.convert.assert_called_once()
        mock_destination.handle.assert_called_once()


class TestInterfaceWriter(unittest.TestCase):
    """Cover writer/writer.py"""

    def test_file_writer_json(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({"a": [1]})
        props = {'path': '/tmp/test_output.json', 'action': None, 'header': None, 'footer': None, 'api_call': None}

        with mock.patch('ingen.writer.writer.OldJSONWriter') as mock_json_writer:
            writer = InterfaceWriter(df, 'json', props, {})
            writer.write()
            mock_json_writer.assert_called_once()

    def test_file_writer_invalid_type(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({"a": [1]})
        props = {'path': '/tmp/test.txt', 'action': None, 'header': None, 'footer': None, 'api_call': None}
        writer = InterfaceWriter(df, 'invalid_type', props, {})
        writer.write()

    def test_file_writer_rawdatastore(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({"a": [1]})
        props = {'path': '/tmp/test.raw', 'action': None, 'header': None, 'footer': None, 'api_call': None,
                 'raw_data_store_name': 'test'}

        with mock.patch('ingen.writer.writer.DataFrameWriter') as mock_df_writer:
            writer = InterfaceWriter(df, 'rawdatastore', props, {})
            writer.write()
            mock_df_writer.assert_called_once()

    def test_file_writer_excel(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({"a": [1]})
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            path = f.name
        props = {'path': path, 'action': None, 'header': None, 'footer': None, 'api_call': None}
        with mock.patch.object(df, 'to_excel') as mock_excel:
            writer = InterfaceWriter(df, 'excel', props, {})
            writer.write()
            mock_excel.assert_called_once()
        if os.path.exists(path):
            os.unlink(path)


class TestBaseInterfaceGenerator(unittest.TestCase):
    """Cover generators/base_interface_generator.py"""

    def test_notify_does_nothing(self):
        from ingen.generators.base_interface_generator import BaseInterfaceGenerator

        class ConcreteGenerator(BaseInterfaceGenerator):
            def read(self, sources): pass
            def pre_process(self, pre_processes, sources): pass
            def format(self, data, columns, params): pass
            def write(self, data, destination, params): pass
            def validate(self, df, columns, data=None, sources=None): return df, []
            def post_process(self, formatted_data, post_processes): pass

        gen = ConcreteGenerator()
        gen.notify({}, None, {})


class TestFileSource(unittest.TestCase):
    """Cover data_source/file_source.py"""

    def test_file_source_with_infile_string(self):
        from ingen.data_source.file_source import FileSource
        source = {
            'id': 'test',
            'type': 'file',
            'file_type': 'csv',
            'file_path': '/original/path.csv',
            'delimiter': ',',
            'use_infile': True,
        }
        params_map = {'infile': '/override/path.csv'}
        fs = FileSource(source, params_map)
        self.assertEqual(fs._src['file_path'], '/override/path.csv')

    def test_file_source_with_infile_dict(self):
        from ingen.data_source.file_source import FileSource
        source = {
            'id': 'test',
            'type': 'file',
            'file_type': 'csv',
            'file_path': '/original/path.csv',
            'delimiter': ',',
            'use_infile': True,
        }
        params_map = {'infile': {'test': '/dict/path.csv'}}
        fs = FileSource(source, params_map)
        self.assertEqual(fs._src['file_path'], '/dict/path.csv')


class TestUtils(unittest.TestCase):
    """Cover ingen/utils/utils.py"""

    def test_key_value_action(self):
        from ingen.utils.utils import KeyValue
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--params", nargs="*", action=KeyValue)
        args = parser.parse_args(["--params", "key1=val1", "key2=val2"])
        self.assertEqual(args.params, {"key1": "val1", "key2": "val2"})


class TestDataSourceReader(unittest.TestCase):
    """Cover reader/data_source.py"""

    def test_get_connection_success(self):
        with mock.patch('mysql.connector.connection.MySQLConnection') as mock_conn:
            mock_conn.return_value = mock.MagicMock()
            from importlib import reload
            import ingen.reader.data_source as ds_mod
            reload(ds_mod)
            ds = ds_mod.DataSource(host='localhost', user='root', passwd='pass', database='testdb')
            conn = ds.get_connection()
            self.assertIsNotNone(conn)

    def test_get_connection_failure(self):
        from mysql.connector import Error
        with mock.patch('mysql.connector.connection.MySQLConnection', side_effect=Error("connection failed")):
            from importlib import reload
            import ingen.reader.data_source as ds_mod
            reload(ds_mod)
            ds = ds_mod.DataSource()
            with self.assertRaises(RuntimeError):
                ds.get_connection()

    def test_get_cursor(self):
        with mock.patch('mysql.connector.connection.MySQLConnection') as mock_conn:
            mock_connection = mock.MagicMock()
            mock_conn.return_value = mock_connection
            from importlib import reload
            import ingen.reader.data_source as ds_mod
            reload(ds_mod)
            ds = ds_mod.DataSource(host='localhost', user='root', passwd='pass', database='testdb')
            ds.get_connection()
            cursor = ds.get_cursor()
            mock_connection.cursor.assert_called_once()


class TestFilter(unittest.TestCase):
    """Cover pre_processor/filter.py"""

    def test_filter_by_column_and(self):
        from ingen.pre_processor.filter import Filter
        f = Filter()
        df = pd.DataFrame({
            'name': ['alice', 'bob', 'charlie'],
            'age': [25, 30, 35]
        })
        # applymap was removed in newer pandas, use map instead
        if not hasattr(df, 'applymap'):
            pd.DataFrame.applymap = pd.DataFrame.map
        config = {
            'cols': [{'col': 'name', 'val': ['alice', 'bob']}],
            'operator': 'and'
        }
        result = f.execute(config, {}, df)
        self.assertEqual(len(result), 2)

    def test_filter_by_column_or(self):
        from ingen.pre_processor.filter import Filter
        f = Filter()
        df = pd.DataFrame({
            'name': ['alice', 'bob', 'charlie'],
            'age': [25, 30, 35]
        })
        if not hasattr(df, 'applymap'):
            pd.DataFrame.applymap = pd.DataFrame.map
        config = {
            'cols': [
                {'col': 'name', 'val': ['alice']},
                {'col': 'age', 'val': [35]}
            ],
            'operator': 'or'
        }
        result = f.execute(config, {}, df)
        self.assertEqual(len(result), 2)

    def test_filter_empty_dataframe(self):
        from ingen.pre_processor.filter import Filter
        f = Filter()
        df = pd.DataFrame({'name': pd.Series(dtype=str), 'age': pd.Series(dtype=int)})
        if not hasattr(df, 'applymap'):
            pd.DataFrame.applymap = pd.DataFrame.map
        config = {
            'cols': [{'col': 'name', 'val': ['alice']}],
            'operator': 'and'
        }
        result = f.execute(config, {}, df)
        self.assertTrue(result.empty)


class TestCryptor(unittest.TestCase):
    """Cover lib/cryptor.py"""

    @mock.patch('ingen.lib.cryptor.properties')
    @mock.patch('ingen.lib.cryptor.AppSecrets')
    @mock.patch('ingen.lib.cryptor.subprocess.check_output')
    def test_encrypt_decrypt(self, mock_subprocess, mock_secrets, mock_props):
        mock_props.get_property.return_value = 'test_path'
        aes_key = b'0123456789abcdef0123456789abcdef'
        hmac_key = b'hmac_secret_key_for_testing_only!'
        mock_subprocess.return_value = aes_key
        mock_secrets.get_secret.return_value = {
            'data': {'data': {
                'aes_key': 'base64encoded',
                'hmac_key': 'base64encoded'
            }}
        }

        from ingen.lib.cryptor import Cryptor
        with mock.patch.object(Cryptor, '_Cryptor__decrypt_gpg_kek', side_effect=[aes_key, hmac_key]):
            with mock.patch.object(Cryptor, '_Cryptor__fetch_key', side_effect=[
                (aes_key.decode(), None),
                (hmac_key.decode(), None),
            ]):
                c = Cryptor()
                c._Cryptor__get_key.cache_clear()
                c._Cryptor__get_hmac_key.cache_clear()

                with mock.patch.object(c, '_Cryptor__get_key', return_value=(aes_key, None)), \
                     mock.patch.object(c, '_Cryptor__get_hmac_key', return_value=(hmac_key, None)):
                    encrypted = c.encrypt("hello world")
                    decrypted = c.decrypt(encrypted)
                    self.assertEqual(decrypted, "hello world")


class TestUtilsCompare(unittest.TestCase):
    """Cover utils/utils.py compare function"""

    def test_compare_eq(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = compare(df, "a", ["==", 2])
        self.assertEqual(result.sum(), 1)

    def test_compare_ne(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = compare(df, "a", ["!=", 2])
        self.assertEqual(result.sum(), 2)

    def test_compare_in(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({"a": [1, 2, 3]})
        result = compare(df, "a", ["in", [1, 3]])
        self.assertEqual(result.sum(), 2)

    def test_compare_in_non_list(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({"a": [1, 2, 3]})
        with self.assertRaises(ValueError):
            compare(df, "a", ["in", 1])

    def test_compare_eq_none(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({"a": [1, None, 3]})
        result = compare(df, "a", ["==", None])
        self.assertEqual(result.sum(), 1)

    def test_compare_ne_none(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({"a": [1, None, 3]})
        result = compare(df, "a", ["!=", None])
        self.assertEqual(result.sum(), 2)

    def test_compare_invalid_operator(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({"a": [1, 2, 3]})
        with self.assertRaises(ValueError):
            compare(df, "a", ["??", 1])

    def test_compare_missing_column(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({"a": [1, 2, 3]})
        with self.assertRaises(ValueError):
            compare(df, "b", ["==", 1])

    def test_compare_bad_input(self):
        from ingen.utils.utils import compare
        df = pd.DataFrame({"a": [1, 2, 3]})
        with self.assertRaises(ValueError):
            compare(df, "a", None)


class TestHolidayCalendar(unittest.TestCase):
    """Cover utils/utils.py holiday_calendar"""

    @mock.patch('ingen.utils.utils.properties')
    def test_holiday_calendar(self, mock_props):
        mock_props.get_property.return_value = 'US'
        from ingen.utils.utils import holiday_calendar
        result = holiday_calendar(year=2024)
        self.assertIsNotNone(result)

    @mock.patch('ingen.utils.utils.properties')
    def test_holiday_calendar_no_country(self, mock_props):
        mock_props.get_property.return_value = None
        from ingen.utils.utils import holiday_calendar
        with self.assertRaises(ValueError):
            holiday_calendar(country=None, year=2024)

    @mock.patch('ingen.utils.utils.properties')
    def test_get_business_day(self, mock_props):
        mock_props.get_property.return_value = 'US'
        from ingen.utils.utils import get_business_day
        import datetime
        monday = datetime.date(2024, 1, 8)
        result = get_business_day(monday)
        self.assertEqual(result, monday)


class TestKeyValueOrString(unittest.TestCase):
    """Cover utils/utils.py KeyValueOrString"""

    def test_single_value(self):
        import argparse
        from ingen.utils.utils import KeyValueOrString
        parser = argparse.ArgumentParser()
        parser.add_argument("--infile", nargs="*", action=KeyValueOrString)
        args = parser.parse_args(["--infile", "somefile.csv"])
        self.assertEqual(args.infile, "somefile.csv")

    def test_key_value_pairs(self):
        import argparse
        from ingen.utils.utils import KeyValueOrString
        parser = argparse.ArgumentParser()
        parser.add_argument("--infile", nargs="*", action=KeyValueOrString)
        args = parser.parse_args(["--infile", "src1=file1.csv", "src2=file2.csv"])
        self.assertEqual(args.infile, {"src1": "file1.csv", "src2": "file2.csv"})


class TestWriterDelimited(unittest.TestCase):
    """Cover writer/writer.py delimited file path"""

    def test_file_writer_delimited_with_result_header(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
            path = f.name
        props = {
            'path': path,
            'action': None,
            'header': {'type': 'delimited_result_header'},
            'footer': None,
            'api_call': None,
            'delimiter': ','
        }
        with mock.patch.object(df, 'to_csv') as mock_csv:
            writer = InterfaceWriter(df, 'delimited_file', props, {})
            writer.write()
            mock_csv.assert_called_once()
        if os.path.exists(path):
            os.unlink(path)

    def test_file_writer_delimited_no_header(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
            path = f.name
        props = {
            'path': path,
            'action': None,
            'header': None,
            'footer': None,
            'api_call': None,
        }
        with mock.patch.object(df, 'to_csv') as mock_csv:
            writer = InterfaceWriter(df, 'delimited_file', props, {})
            writer.write()
            mock_csv.assert_called_once()
        if os.path.exists(path):
            os.unlink(path)

    def test_file_writer_multiple_paths(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({"a": [1]})
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f1, \
             tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f2:
            path1, path2 = f1.name, f2.name
        props = {
            'path': [path1, path2],
            'action': None,
            'header': None,
            'footer': None,
            'api_call': None,
        }
        with mock.patch.object(df, 'to_csv') as mock_csv:
            writer = InterfaceWriter(df, 'delimited_file', props, {})
            writer.write()
        if os.path.exists(path1):
            os.unlink(path1)
        if os.path.exists(path2):
            os.unlink(path2)

    def test_file_writer_delimited_custom_header_footer(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({"a": [1, 2]})
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w') as f:
            path = f.name
        props = {
            'path': path,
            'action': None,
            'header': {'type': 'custom', 'function': 'row_count'},
            'footer': {'type': 'custom', 'function': 'row_count'},
            'api_call': None,
        }
        with mock.patch.object(df, 'to_csv'):
            with mock.patch('ingen.writer.writer.get_custom_value', return_value='2'):
                writer = InterfaceWriter(df, 'delimited_file', props, {'run_date': '2024-01-01'})
                writer.write()
        if os.path.exists(path):
            with open(path, 'r') as fh:
                content = fh.read()
                self.assertIn('2', content)
            os.unlink(path)

    def test_file_writer_excel_with_result_header(self):
        from ingen.writer.writer import InterfaceWriter
        df = pd.DataFrame({"a": [1]})
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            path = f.name
        props = {
            'path': path,
            'action': None,
            'header': {'type': 'delimited_result_header'},
            'footer': None,
            'api_call': None,
        }
        with mock.patch.object(df, 'to_excel') as mock_excel:
            writer = InterfaceWriter(df, 'excel', props, {})
            writer.write()
            mock_excel.assert_called_once_with(path, index=False)
        if os.path.exists(path):
            os.unlink(path)


class TestPostProcessorApply(unittest.TestCase):
    """Cover post_processor/post_processor.py apply with valid pivot"""

    def test_apply_pivot(self):
        if not hasattr(pd.DataFrame, 'applymap'):
            pd.DataFrame.applymap = pd.DataFrame.map
        from ingen.post_processor.post_processor import PostProcessor
        df = pd.DataFrame({
            'id': [1, 1, 2, 2],
            'attr': ['color', 'size', 'color', 'size'],
            'value': ['red', 'large', 'blue', 'small']
        })
        post_processes = [{'type': 'pivot', 'processing_values': {'pivot_col': 'attr', 'value_col': 'value'}}]
        pp = PostProcessor(post_processes, df)
        result = pp.apply_post_processing()
        self.assertIn('color', result.columns)
        self.assertIn('size', result.columns)


class TestReaderFactory(unittest.TestCase):
    """Cover reader/file_reader.py ReaderFactory"""

    def test_get_csv_reader(self):
        from ingen.reader.file_reader import ReaderFactory, CSVFileReader
        reader = ReaderFactory.get_reader({'file_type': 'delimited_file'})
        self.assertIsInstance(reader, CSVFileReader)

    def test_get_unknown_reader(self):
        from ingen.reader.file_reader import ReaderFactory
        reader = ReaderFactory.get_reader({'file_type': 'unknown'})
        self.assertIsNone(reader)


class TestJSONWriterWritecsv(unittest.TestCase):
    """Cover json_writer writecsv method"""

    def test_writecsv(self):
        from ingen.writer.json_writer.json_writer import JSONWriter
        mock_destination = mock.MagicMock()
        df = pd.DataFrame({"a": [1]})
        configs = {
            'convertor': 'single',
            'convertor_props': {},
            'destination': 'file',
            'destination_props': {'path': '/tmp/test.csv', 'payload': 'test_data'}
        }
        with mock.patch('ingen.writer.json_writer.json_writer.PathParser') as mock_pp:
            mock_pp.return_value.parse.return_value = 'parsed_data'
            writer = JSONWriter(df, configs, params={},
                                json_convertor_factory=lambda x: mock.MagicMock(),
                                json_destination_factory=lambda x, y: mock_destination)
            writer.writecsv()
            mock_destination.handle.assert_called_once()


class TestSourceFactoryAll(unittest.TestCase):
    """Cover source_factory.py lines 16, 20-21, 23"""

    @mock.patch('ingen.data_source.mysql_source.pymysql.connect')
    @mock.patch('ingen.data_source.mysql_source.properties')
    def test_mysql_source(self, mock_props, mock_connect):
        mock_props.get_property.return_value = 'test'
        mock_connect.return_value = mock.MagicMock()
        from ingen.data_source.source_factory import SourceFactory
        from ingen.data_source.mysql_source import MYSQLSource
        MYSQLSource._connection = None
        source = {'type': 'mysql', 'db_host': 'localhost', 'db_user': 'root',
                  'db_password': 'pass', 'database': 'test', 'query': 'SELECT 1', 'id': 'test'}
        factory = SourceFactory()
        result = factory.parse_source(source, {})
        self.assertIsNotNone(result)

    def test_api_source(self):
        from ingen.data_source.source_factory import SourceFactory
        source = {'type': 'api', 'id': 'test', 'url': 'http://example.com',
                  'response_type': 'json', 'reader_config': {}}
        factory = SourceFactory()
        result = factory.parse_source(source, {})
        self.assertIsNotNone(result)

    def test_rawdata_source(self):
        from ingen.data_source.source_factory import SourceFactory
        source = {'type': 'rawdatastore', 'id': 'test', 'raw_data_store_name': 'test'}
        factory = SourceFactory()
        result = factory.parse_source(source, {})
        self.assertIsNotNone(result)


class TestNotEqualsFilter(unittest.TestCase):
    """Cover pre_processor/not_equals_filter.py"""

    def test_not_equals_filter(self):
        from ingen.pre_processor.not_equals_filter import NotEqualsFilter
        f = NotEqualsFilter()
        df = pd.DataFrame({'name': ['alice', 'bob', 'charlie'], 'age': [25, 30, 35]})
        config = {
            'source': None,
            'cols': [{'col': 'name', 'val': ['alice']}]
        }
        result = f.execute(config, {}, df)
        self.assertEqual(len(result), 2)
        self.assertNotIn('alice', result['name'].values)

    def test_not_equals_filter_with_source(self):
        from ingen.pre_processor.not_equals_filter import NotEqualsFilter
        f = NotEqualsFilter()
        df = pd.DataFrame({'name': ['alice', 'bob'], 'age': [25, 30]})
        config = {'source': 'src1', 'cols': [{'col': 'name', 'val': ['alice']}]}
        result = f.execute(config, {'src1': df}, pd.DataFrame())
        self.assertEqual(len(result), 1)

    def test_not_equals_filter_empty_cols(self):
        from ingen.pre_processor.not_equals_filter import NotEqualsFilter
        f = NotEqualsFilter()
        df = pd.DataFrame({'name': ['alice', 'bob']})
        config = {'source': None, 'cols': []}
        result = f.execute(config, {}, df)
        self.assertEqual(len(result), 2)

    def test_not_equals_filter_missing_column(self):
        from ingen.pre_processor.not_equals_filter import NotEqualsFilter
        f = NotEqualsFilter()
        df = pd.DataFrame({'name': ['alice', 'bob']})
        config = {'source': None, 'cols': [{'col': 'nonexistent', 'val': ['alice']}]}
        result = f.execute(config, {}, df)
        self.assertEqual(len(result), 2)

    def test_not_equals_filter_empty_df(self):
        from ingen.pre_processor.not_equals_filter import NotEqualsFilter
        f = NotEqualsFilter()
        config = {'source': None, 'cols': [{'col': 'name', 'val': ['alice']}]}
        result = f.execute(config, {}, pd.DataFrame())
        self.assertTrue(result.empty)


class TestOuterJoin(unittest.TestCase):
    """Cover pre_processor/outer_join.py"""

    def test_outer_join(self):
        from ingen.pre_processor.outer_join import OuterJoin
        oj = OuterJoin()
        left = pd.DataFrame({'id': [1, 2], 'val_left': ['a', 'b']})
        right = pd.DataFrame({'id': [2, 3], 'val_right': ['c', 'd']})
        config = {'source': 'right_src', 'left_key': 'id', 'right_key': 'id'}
        result = oj.execute(config, {'right_src': right}, left)
        self.assertEqual(len(result), 3)

    def test_outer_join_missing_left_key(self):
        from ingen.pre_processor.outer_join import OuterJoin
        oj = OuterJoin()
        left = pd.DataFrame({'id': [1, 2]})
        right = pd.DataFrame({'id': [2, 3]})
        config = {'source': 'right_src', 'left_key': 'missing', 'right_key': 'id'}
        with self.assertRaises(KeyError):
            oj.execute(config, {'right_src': right}, left)

    def test_outer_join_missing_right_key(self):
        from ingen.pre_processor.outer_join import OuterJoin
        oj = OuterJoin()
        left = pd.DataFrame({'id': [1, 2]})
        right = pd.DataFrame({'id': [2, 3]})
        config = {'source': 'right_src', 'left_key': 'id', 'right_key': 'missing'}
        with self.assertRaises(KeyError):
            oj.execute(config, {'right_src': right}, left)


class TestProcessJson(unittest.TestCase):
    """Cover __main__.py process_json"""

    @mock.patch('ingen.__main__.main')
    def test_process_json(self, mock_main):
        mock_main.return_value = '{"key": "val"}'
        from ingen.__main__ import process_json
        result = process_json("config.yaml", '{"key": "val"}')
        self.assertEqual(result, '{"key": "val"}')


class TestReaderFileReader(unittest.TestCase):
    """Cover reader/file_reader.py"""

    def test_csv_reader_file_not_found_with_return_empty(self):
        from ingen.reader.file_reader import CSVFileReader
        reader = CSVFileReader()
        src = {
            'file_path': '/nonexistent.csv',
            'delimiter': ',',
            'return_empty_if_not_exist': True,
            'columns': ['a', 'b']
        }
        result = reader.read(src)
        self.assertTrue(result.empty)
        self.assertListEqual(list(result.columns), ['a', 'b'])

    def test_csv_reader_file_not_found_raises(self):
        from ingen.reader.file_reader import CSVFileReader
        reader = CSVFileReader()
        src = {
            'file_path': '/nonexistent.csv',
            'delimiter': ','
        }
        with self.assertRaises(FileNotFoundError):
            reader.read(src)


class TestCommonFormatters(unittest.TestCase):
    """Cover formatters/common_formatters.py missing lines"""

    def test_date_formatter_ms(self):
        from ingen.formatters.common_formatters import date_formatter
        df = pd.DataFrame({'date_col': [1704067200000]})
        result = date_formatter(df, 'date_col', {'src': 'ms', 'des': '%Y-%m-%d'}, {})
        self.assertIsNotNone(result)

    def test_concat_formatter_bad_column(self):
        from ingen.formatters.common_formatters import sum_value_formatter
        df = pd.DataFrame({'a': [1], 'b': [2]})
        with self.assertRaises(ValueError):
            sum_value_formatter(df, 'result', ['a', 'nonexistent'], {})

    def test_fill_empty_values_missing_column(self):
        from ingen.formatters.common_formatters import fill_empty_values
        df = pd.DataFrame({'a': [1, None]})
        with self.assertRaises(KeyError):
            fill_empty_values(df, 'a', {'column': 'nonexistent'}, {})

    def test_fill_empty_values_with_condition(self):
        import numpy as np
        from ingen.formatters.common_formatters import fill_empty_values_with_custom_value
        df = pd.DataFrame({
            'val': [None, 'existing', None],
            'type': ['match', 'other', 'nomatch']
        })
        result = fill_empty_values_with_custom_value(
            df, 'val',
            {'value': 'filled', 'condition': {'match_col': 'type', 'pattern': 'match'}},
            {}
        )
        self.assertEqual(result['val'].iloc[0], 'filled')

    def test_fill_empty_values_without_condition(self):
        from ingen.formatters.common_formatters import fill_empty_values_with_custom_value
        df = pd.DataFrame({'val': [None, 'existing', None]})
        result = fill_empty_values_with_custom_value(df, 'val', {'value': 'filled'}, {})
        self.assertEqual(result['val'].iloc[0], 'filled')
        self.assertEqual(result['val'].iloc[2], 'filled')

    def test_fill_empty_values_missing_col(self):
        from ingen.formatters.common_formatters import fill_empty_values_with_custom_value
        df = pd.DataFrame({'val': [1]})
        with self.assertRaises(KeyError):
            fill_empty_values_with_custom_value(df, 'nonexistent', {'value': 0}, {})

    def test_arithmetic_invalid_operation(self):
        from ingen.formatters.common_formatters import arithmetic_calculation_formatter
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        with self.assertRaises(ValueError):
            arithmetic_calculation_formatter(df, 'result', {'cols': ['a', 'b'], 'operation': 'invalid'}, {})

    def test_split_column_formatter_missing_col(self):
        from ingen.formatters.common_formatters import split_column_formatter
        df = pd.DataFrame({'col': ['a,b']})
        with self.assertRaises(KeyError):
            split_column_formatter(df, 'missing', {'new_col_names': ['p1']}, {})

    def test_split_column_formatter_empty_df(self):
        from ingen.formatters.common_formatters import split_column_formatter
        df = pd.DataFrame({'col': pd.Series(dtype=str)})
        with self.assertRaises(ValueError):
            split_column_formatter(df, 'col', {'new_col_names': ['p1']}, {})

    def test_split_column_formatter_with_list(self):
        from ingen.formatters.common_formatters import split_column_formatter
        df = pd.DataFrame({'col': [[1, 2], [3, 4]]})
        result = split_column_formatter(df, 'col', {'new_col_names': ['p1', 'p2']}, {})
        self.assertIn('p1', result.columns)
        self.assertIn('p2', result.columns)

    def test_split_column_all_na(self):
        from ingen.formatters.common_formatters import split_column_formatter
        df = pd.DataFrame({'col': ['na', 'na']})
        result = split_column_formatter(df, 'col', {'new_col_names': ['p1']}, {})
        self.assertNotIn('p1', result.columns)


class TestJsonUtil(unittest.TestCase):
    """Cover writer/json_util.py json_sum"""

    def test_json_sum_simple_list(self):
        from ingen.writer.json_util import json_sum
        result = json_sum([1, 2, 3])
        self.assertEqual(result, 6.0)

    def test_json_sum_with_field(self):
        from ingen.writer.json_util import json_sum
        obj = {'nums': [1, 2, 3]}
        result = json_sum(obj, field='nums', result='total')
        self.assertEqual(result['total'], 6.0)

    def test_json_sum_with_subfield(self):
        from ingen.writer.json_util import json_sum
        obj = {'items': [{'val': 1}, {'val': 2}]}
        result = json_sum(obj, field='items', subfield='val', result='total')
        self.assertEqual(result['total'], 3.0)


class TestMetadata(unittest.TestCase):
    """Cover metadata/metadata.py"""

    def test_metadata_from_config(self):
        from ingen.metadata.metadata import MetaData
        config = {
            'name': 'test_interface',
            'sources': [{'id': 'src1', 'type': 'file', 'file_type': 'delimited_file',
                         'file_path': 'test.csv'}],
            'columns': [{'src_col_name': 'a'}],
            'output': {'type': 'delimited_file', 'path': 'out.csv'},
        }
        m = MetaData('test_interface', config, {})
        self.assertEqual(m.name, 'test_interface')


if __name__ == '__main__':
    unittest.main()
