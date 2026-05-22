#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import os
import tempfile
from unittest import TestCase, mock

import pandas as pd
import numpy as np


class TestLogger(TestCase):
    def test_init_logging(self):
        from ingen.logger import init_logging
        init_logging()


class TestMainModule(TestCase):
    @mock.patch('ingen.__main__.MetaDataParser')
    def test_main_success(self, mock_parser_cls):
        from ingen.__main__ import main

        mock_metadata = mock.MagicMock()
        mock_metadata.name = "test_interface"
        mock_run_config = mock.MagicMock()
        mock_generator = mock.MagicMock()
        mock_run_config.generator.return_value = mock_generator
        mock_parser_instance = mock.MagicMock()
        mock_parser_instance.parse_metadata.return_value = [mock_metadata]
        mock_parser_instance.run_config = mock_run_config
        mock_parser_cls.return_value = mock_parser_instance

        main("config.yaml", None, None, None)

    @mock.patch('ingen.__main__.MetaDataParser')
    def test_main_with_dynamic_data(self, mock_parser_cls):
        from ingen.__main__ import main

        mock_metadata = mock.MagicMock()
        mock_metadata.name = "test_interface"
        mock_run_config = mock.MagicMock()
        mock_generator = mock.MagicMock()
        mock_generator.generate.return_value = '{"data": "test"}'
        mock_run_config.generator.return_value = mock_generator
        mock_parser_instance = mock.MagicMock()
        mock_parser_instance.parse_metadata.return_value = [mock_metadata]
        mock_parser_instance.run_config = mock_run_config
        mock_parser_cls.return_value = mock_parser_instance

        result = main("config.yaml", None, None, None, dynamic_data='{"key": "val"}')
        self.assertIsNotNone(result)

    @mock.patch('ingen.__main__.MetaDataParser')
    def test_main_exception_handling(self, mock_parser_cls):
        from ingen.__main__ import main

        mock_metadata = mock.MagicMock()
        mock_metadata.name = "test_interface"
        mock_run_config = mock.MagicMock()
        mock_generator = mock.MagicMock()
        mock_generator.generate.side_effect = Exception("generation failed")
        mock_run_config.generator.return_value = mock_generator
        mock_parser_instance = mock.MagicMock()
        mock_parser_instance.parse_metadata.return_value = [mock_metadata]
        mock_parser_instance.run_config = mock_run_config
        mock_parser_cls.return_value = mock_parser_instance

        main("config.yaml", None, None, None)

    def test_create_arg_parser(self):
        from ingen.__main__ import create_arg_parser
        parser = create_arg_parser()
        self.assertIsNotNone(parser)

    @mock.patch('ingen.__main__.MetaDataParser')
    def test_process_json(self, mock_parser_cls):
        from ingen.__main__ import process_json

        mock_metadata = mock.MagicMock()
        mock_metadata.name = "test"
        mock_run_config = mock.MagicMock()
        mock_generator = mock.MagicMock()
        mock_generator.generate.return_value = '{"result": "ok"}'
        mock_run_config.generator.return_value = mock_generator
        mock_parser_instance = mock.MagicMock()
        mock_parser_instance.parse_metadata.return_value = [mock_metadata]
        mock_parser_instance.run_config = mock_run_config
        mock_parser_cls.return_value = mock_parser_instance

        result = process_json("config.yaml", '{"data": "test"}')


class TestSourceFactory(TestCase):
    def test_parse_file_source(self):
        from ingen.data_source.source_factory import SourceFactory
        from ingen.data_source.file_source import FileSource

        factory = SourceFactory()
        source = {'type': 'file', 'id': 'test', 'file_path': '/tmp/test.csv',
                  'file_type': 'csv', 'delimiter': ','}
        result = factory.parse_source(source, {})
        self.assertIsInstance(result, FileSource)

    def test_parse_json_source(self):
        from ingen.data_source.source_factory import SourceFactory
        from ingen.data_source.json_source import JsonSource

        factory = SourceFactory()
        source = {'type': 'json', 'id': 'test', 'data': '{}'}
        result = factory.parse_source(source, {}, dynamic_data='{}')
        self.assertIsInstance(result, JsonSource)

    def test_parse_unknown_source_raises(self):
        from ingen.data_source.source_factory import SourceFactory

        factory = SourceFactory()
        source = {'type': 'unknown', 'id': 'test'}
        with self.assertRaises(ValueError):
            factory.parse_source(source, {})

    def test_parse_api_source(self):
        from ingen.data_source.source_factory import SourceFactory

        factory = SourceFactory()
        source = {
            'type': 'api', 'id': 'test',
            'url': 'http://example.com',
            'response_type': 'json',
            'query_params': {},
            'headers': {}
        }
        result = factory.parse_source(source, {})
        self.assertIsNotNone(result)

    @mock.patch('ingen.data_source.mysql_source.pymysql')
    @mock.patch('ingen.data_source.mysql_source.properties')
    def test_parse_mysql_source(self, mock_props, mock_pymysql):
        from ingen.data_source.source_factory import SourceFactory
        from ingen.data_source.mysql_source import MYSQLSource

        MYSQLSource._connection = None
        mock_props.get_property.return_value = 'localhost'
        mock_pymysql.connect.return_value = mock.MagicMock()
        factory = SourceFactory()
        source = {'type': 'mysql', 'id': 'test', 'query': 'SELECT 1'}
        result = factory.parse_source(source, {})
        self.assertIsInstance(result, MYSQLSource)
        MYSQLSource._connection = None

    def test_parse_rawdata_source(self):
        from ingen.data_source.source_factory import SourceFactory
        from ingen.data_source.rawdata_source import RawDataSource

        factory = SourceFactory()
        source = {'type': 'rawdatastore', 'id': 'test', 'data': [{'a': 1}]}
        result = factory.parse_source(source, {})
        self.assertIsInstance(result, RawDataSource)


class TestFilter(TestCase):
    def test_filter_by_column_and(self):
        from ingen.pre_processor.filter import Filter

        f = Filter()
        data = pd.DataFrame({'A': ['a', 'b', 'c'], 'B': [1, 2, 3]})
        cols = [{'col': 'A', 'val': ['a', 'b']}]
        result = f.filter_by_column(data, cols, 'and')
        self.assertEqual(len(result), 2)

    def test_filter_by_column_or(self):
        from ingen.pre_processor.filter import Filter

        f = Filter()
        data = pd.DataFrame({'A': ['a', 'b', 'c'], 'B': [1, 2, 3]})
        cols = [{'col': 'A', 'val': ['a']}, {'col': 'B', 'val': [3]}]
        result = f.filter_by_column(data, cols, 'or')
        self.assertEqual(len(result), 2)

    def test_filter_empty_data(self):
        from ingen.pre_processor.filter import Filter

        f = Filter()
        data = pd.DataFrame({'A': pd.Series(dtype='str'), 'B': pd.Series(dtype='int')})
        result = f.filter_by_column(data, [{'col': 'A', 'val': ['a']}], 'and')
        self.assertEqual(len(result), 0)

    def test_make_filter_map(self):
        from ingen.pre_processor.filter import Filter

        f = Filter()
        cols = [{'col': 'A', 'val': ['a', 'b']}, {'col': 'B', 'val': [1]}]
        result = f.make_filter_map(cols)
        self.assertEqual(result, {'A': ['a', 'b'], 'B': [1]})

    def test_filter_no_operator(self):
        from ingen.pre_processor.filter import Filter

        f = Filter()
        data = pd.DataFrame({'A': ['a', 'b'], 'B': [1, 2]})
        result = f.filter_by_column(data, [{'col': 'A', 'val': ['a']}], None)
        self.assertEqual(len(result), 2)


class TestPostProcessor(TestCase):
    def test_apply_no_post_processes(self):
        from ingen.post_processor.post_processor import PostProcessor

        df = pd.DataFrame({'A': [1, 2]})
        pp = PostProcessor(None, df)
        result = pp.apply_post_processing()
        pd.testing.assert_frame_equal(result, df)

    def test_apply_post_processing_not_dataframe(self):
        from ingen.post_processor.post_processor import PostProcessor

        pp = PostProcessor([{'type': 'pivot'}], "not a df")
        with self.assertRaises(TypeError):
            pp.apply_post_processing()

    def test_apply_post_processing_empty_dataframe(self):
        from ingen.post_processor.post_processor import PostProcessor

        df = pd.DataFrame()
        pp = PostProcessor([{'type': 'pivot'}], df)
        with self.assertRaises(ValueError):
            pp.apply_post_processing()

    def test_get_processor_func_unknown(self):
        from ingen.post_processor.post_processor import PostProcessor

        pp = PostProcessor(None, None)
        with self.assertRaises(NameError):
            pp.get_processor_func({'type': 'unknown'})




class TestCommonPostProcessor(TestCase):
    def test_pivot_missing_pivot_col(self):
        from ingen.post_processor.common_post_processor import pivot_to_dynamic_columns

        df = pd.DataFrame({'A': [1], 'B': [2]})
        with self.assertRaises(KeyError):
            pivot_to_dynamic_columns(df, {'pivot_col': 'MISSING', 'value_col': 'B'})

    def test_pivot_missing_value_col(self):
        from ingen.post_processor.common_post_processor import pivot_to_dynamic_columns

        df = pd.DataFrame({'A': [1], 'B': [2]})
        with self.assertRaises(KeyError):
            pivot_to_dynamic_columns(df, {'pivot_col': 'A', 'value_col': 'MISSING'})


class TestProperties(TestCase):
    def test_get_property_default(self):
        from ingen.utils.properties import Properties

        Properties._instance = None
        props = Properties()
        result = props.get_property('nonexistent', 'default_val')
        self.assertEqual(result, 'default_val')

    def test_initialize_with_config_path(self):
        from ingen.utils.properties import Properties

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = os.path.join(tmpdir, "config.properties")
            with open(config_file, 'w') as f:
                f.write("key1=value1\nkey2=value2\ninvalid_line\n")

            Properties._instance = None
            with mock.patch.dict(os.environ, {'config_path': tmpdir}):
                props = Properties()
                self.assertEqual(props.get_property('key1'), 'value1')
                self.assertEqual(props.get_property('key2'), 'value2')

    def test_initialize_with_missing_file(self):
        from ingen.utils.properties import Properties

        Properties._instance = None
        with mock.patch.dict(os.environ, {'config_path': '/nonexistent/path'}):
            props = Properties()
            self.assertIsNotNone(props.property_map)


class TestAppSecrets(TestCase):
    @mock.patch('ingen.utils.app_secrets.hvac')
    def test_connect_client(self, mock_hvac):
        from ingen.utils.app_secrets import AppSecrets

        AppSecrets.vault_client = None
        mock_client = mock.MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_hvac.Client.return_value = mock_client

        result = AppSecrets.connect_client()
        self.assertEqual(result, mock_client)

    @mock.patch('ingen.utils.app_secrets.hvac')
    def test_connect_client_not_authenticated(self, mock_hvac):
        from ingen.utils.app_secrets import AppSecrets

        AppSecrets.vault_client = None
        mock_client = mock.MagicMock()
        mock_client.is_authenticated.return_value = False
        mock_hvac.Client.return_value = mock_client

        with self.assertRaises(Exception):
            AppSecrets.connect_client()

    @mock.patch('ingen.utils.app_secrets.hvac')
    def test_get_secret(self, mock_hvac):
        from ingen.utils.app_secrets import AppSecrets

        AppSecrets.vault_client = None
        mock_client = mock.MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client.secrets.kv.v2.read_secret_version.return_value = {"data": {"data": {"key": "val"}}}
        mock_hvac.Client.return_value = mock_client

        result = AppSecrets.get_secret("path/to/secret")
        self.assertEqual(result["data"]["data"]["key"], "val")


class TestUtils(TestCase):
    def test_compare_eq(self):
        from ingen.utils.utils import compare

        df = pd.DataFrame({'A': [1, 2, 3]})
        result = compare(df, 'A', ['==', 2])
        self.assertTrue(result[1])
        self.assertFalse(result[0])

    def test_compare_ne(self):
        from ingen.utils.utils import compare

        df = pd.DataFrame({'A': [1, 2, 3]})
        result = compare(df, 'A', ['!=', 2])
        self.assertTrue(result[0])
        self.assertFalse(result[1])

    def test_compare_in(self):
        from ingen.utils.utils import compare

        df = pd.DataFrame({'A': [1, 2, 3]})
        result = compare(df, 'A', ['in', [1, 3]])
        self.assertTrue(result[0])
        self.assertFalse(result[1])
        self.assertTrue(result[2])

    def test_compare_in_not_list(self):
        from ingen.utils.utils import compare

        df = pd.DataFrame({'A': [1, 2]})
        with self.assertRaises(ValueError):
            compare(df, 'A', ['in', 'not_a_list'])

    def test_compare_none_eq(self):
        from ingen.utils.utils import compare

        df = pd.DataFrame({'A': [1, None, 3]})
        result = compare(df, 'A', ['==', None])
        self.assertFalse(result[0])
        self.assertTrue(result[1])

    def test_compare_none_ne(self):
        from ingen.utils.utils import compare

        df = pd.DataFrame({'A': [1, None, 3]})
        result = compare(df, 'A', ['!=', None])
        self.assertTrue(result[0])
        self.assertFalse(result[1])

    def test_compare_invalid_column(self):
        from ingen.utils.utils import compare

        df = pd.DataFrame({'A': [1]})
        with self.assertRaises(ValueError):
            compare(df, 'B', ['==', 1])

    def test_compare_invalid_operator(self):
        from ingen.utils.utils import compare

        df = pd.DataFrame({'A': [1]})
        with self.assertRaises(ValueError):
            compare(df, 'A', ['!!', 1])

    def test_compare_invalid_input(self):
        from ingen.utils.utils import compare

        df = pd.DataFrame({'A': [1]})
        with self.assertRaises(ValueError):
            compare(df, 'A', None)

    def test_key_value_or_string_none(self):
        from ingen.utils.utils import KeyValueOrString
        import argparse

        action = KeyValueOrString(option_strings=['--test'], dest='test')
        ns = argparse.Namespace()
        action(None, ns, None)
        self.assertIsNone(ns.test)

    def test_key_value_or_string_single(self):
        from ingen.utils.utils import KeyValueOrString
        import argparse

        action = KeyValueOrString(option_strings=['--test'], dest='test')
        ns = argparse.Namespace()
        action(None, ns, ['single_value'])
        self.assertEqual(ns.test, 'single_value')

    def test_key_value_or_string_pairs(self):
        from ingen.utils.utils import KeyValueOrString
        import argparse

        action = KeyValueOrString(option_strings=['--test'], dest='test')
        ns = argparse.Namespace()
        action(None, ns, ['key1=val1', 'key2=val2'])
        self.assertEqual(ns.test, {'key1': 'val1', 'key2': 'val2'})


class TestDataSource(TestCase):
    @mock.patch('mysql.connector.connection.MySQLConnection')
    def test_data_source_init_and_connect(self, mock_mysql_conn_cls):
        from ingen.reader.data_source import DataSource

        mock_conn_inst = mock.MagicMock()
        mock_mysql_conn_cls.return_value = mock_conn_inst
        ds = DataSource(host='localhost', user='user', passwd='pass', database='db')
        conn = ds.get_connection()
        self.assertEqual(conn, mock_conn_inst)

    @mock.patch('mysql.connector.connection.MySQLConnection')
    def test_get_connection_failure(self, mock_mysql_conn_cls):
        from ingen.reader.data_source import DataSource
        from mysql.connector import Error

        mock_mysql_conn_cls.side_effect = Error("connection failed")
        ds = DataSource(host='localhost', user='user', passwd='pass', database='db')
        with self.assertRaises(RuntimeError):
            ds.get_connection()

    @mock.patch('mysql.connector.connection.MySQLConnection')
    def test_get_cursor(self, mock_mysql_conn_cls):
        from ingen.reader.data_source import DataSource

        mock_conn_inst = mock.MagicMock()
        mock_mysql_conn_cls.return_value = mock_conn_inst
        ds = DataSource(host='localhost', user='user', passwd='pass', database='db')
        ds.get_connection()
        cursor = ds.get_cursor()
        self.assertIsNotNone(cursor)

    @mock.patch('mysql.connector.connection.MySQLConnection')
    def test_reuse_connection(self, mock_mysql_conn_cls):
        from ingen.reader.data_source import DataSource

        mock_conn_inst = mock.MagicMock()
        mock_mysql_conn_cls.return_value = mock_conn_inst
        ds = DataSource(host='localhost', user='user', passwd='pass', database='db')
        conn1 = ds.get_connection()
        conn2 = ds.get_connection()
        mock_mysql_conn_cls.assert_called_once()


class TestJsonFileReader(TestCase):
    def test_read_json_file(self):
        from ingen.reader.json_reader import JSONFileReader
        import json

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([{'a': 1, 'b': 2}, {'a': 3, 'b': 4}], f)
            path = f.name

        try:
            reader = JSONFileReader()
            result = reader.read({'file_path': path})
            self.assertEqual(len(result), 2)
        finally:
            os.unlink(path)

    def test_read_json_file_not_found(self):
        from ingen.reader.json_reader import JSONFileReader

        reader = JSONFileReader()
        with self.assertRaises(FileNotFoundError):
            reader.read({'file_path': '/nonexistent/file.json'})


class TestJsonWriterComponents(TestCase):
    def test_convertor_factory_single(self):
        from ingen.writer.json_writer.convertors.convertor_factory import get_json_convertor
        from ingen.writer.json_writer.convertors.df_to_single_json_convertor import DFToSingleJsonConvertor

        result = get_json_convertor('single')
        self.assertIsInstance(result, DFToSingleJsonConvertor)

    def test_convertor_factory_unknown(self):
        from ingen.writer.json_writer.convertors.convertor_factory import get_json_convertor

        result = get_json_convertor('unknown')
        self.assertIsNone(result)

    def test_destination_factory_file(self):
        from ingen.writer.json_writer.destinations.destination_factory import get_json_destination
        from ingen.writer.json_writer.destinations.file_destination import FileDestination

        result = get_json_destination('file')
        self.assertIsInstance(result, FileDestination)

    def test_destination_factory_unknown(self):
        from ingen.writer.json_writer.destinations.destination_factory import get_json_destination

        result = get_json_destination('unknown')
        self.assertIsNone(result)

    def test_file_destination_write(self):
        from ingen.writer.json_writer.destinations.file_destination import FileDestination

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name

        try:
            dest = FileDestination()
            dest.handle(['{"test": true}'], {'path': path})
            with open(path) as f:
                content = f.read()
            self.assertIn('test', content)
        finally:
            os.unlink(path)

    def test_df_to_single_json_convertor(self):
        from ingen.writer.json_writer.convertors.df_to_single_json_convertor import DFToSingleJsonConvertor

        df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        convertor = DFToSingleJsonConvertor()
        column_details = {'resultant_columns': [], 'schema': []}
        result = convertor.convert(df, {'indent': 2, 'orient': 'records', 'column_details': column_details})
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
