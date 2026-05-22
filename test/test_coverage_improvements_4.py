#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import collections
import io
import tempfile
import os
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

import pandas as pd


class TestXMLFileReader(unittest.TestCase):
    """Tests for xml_file_reader.py to cover lines 24, 36-37, 43-46, 53, 58, 62-71, 75-76"""

    def _create_xml_file(self, content):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8')
        f.write(content)
        f.close()
        return f.name

    def test_read_simple_xml(self):
        from ingen.reader.xml_file_reader import XMLFileReader
        xml_content = '<?xml version="1.0"?><root><item><name>test</name><value>123</value></item></root>'
        path = self._create_xml_file(xml_content)
        try:
            reader = XMLFileReader()
            src = {'file_path': path, 'root_tag': 'item', 'columns': ['name', 'value']}
            df = reader.read(src)
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]['name'], 'test')
        finally:
            os.unlink(path)

    def test_read_xml_multiple_items(self):
        from ingen.reader.xml_file_reader import XMLFileReader
        xml_content = '<?xml version="1.0"?><root><item><name>a</name></item><item><name>b</name></item></root>'
        path = self._create_xml_file(xml_content)
        try:
            reader = XMLFileReader()
            src = {'file_path': path, 'root_tag': 'item', 'columns': ['name']}
            df = reader.read(src)
            self.assertEqual(len(df), 2)
        finally:
            os.unlink(path)

    def test_read_xml_missing_root_tag(self):
        from ingen.reader.xml_file_reader import XMLFileReader
        xml_content = '<?xml version="1.0"?><root><other><name>test</name></other></root>'
        path = self._create_xml_file(xml_content)
        try:
            reader = XMLFileReader()
            src = {'file_path': path, 'root_tag': 'item', 'columns': ['name']}
            df = reader.read(src)
            self.assertEqual(len(df), 0)
        finally:
            os.unlink(path)

    def test_read_xml_with_namespace(self):
        from ingen.reader.xml_file_reader import XMLFileReader
        # xmltodict uses the prefix:tag format, not the {uri}tag format
        xml_content = '<?xml version="1.0"?><root xmlns="http://example.com"><item><name>test</name></item></root>'
        path = self._create_xml_file(xml_content)
        try:
            reader = XMLFileReader()
            src = {'file_path': path, 'root_tag': 'item', 'columns': ['name']}
            df = reader.read(src)
            self.assertEqual(len(df), 1)
        finally:
            os.unlink(path)

    def test_read_xml_with_nested_dict_text(self):
        from ingen.reader.xml_file_reader import XMLFileReader
        xml_content = '<?xml version="1.0"?><root><item><name attr="x">test</name></item></root>'
        path = self._create_xml_file(xml_content)
        try:
            reader = XMLFileReader()
            src = {'file_path': path, 'root_tag': 'item', 'columns': ['name']}
            df = reader.read(src)
            self.assertEqual(len(df), 1)
        finally:
            os.unlink(path)

    def test_read_xml_with_none_value(self):
        from ingen.reader.xml_file_reader import XMLFileReader
        xml_content = '<?xml version="1.0"?><root><item><name>test</name></item></root>'
        path = self._create_xml_file(xml_content)
        try:
            reader = XMLFileReader()
            src = {'file_path': path, 'root_tag': 'item', 'columns': ['name', 'missing_col']}
            df = reader.read(src)
            self.assertEqual(len(df), 1)
        finally:
            os.unlink(path)

    def test_get_record_nested(self):
        from ingen.reader.xml_file_reader import get_record
        obj = {'parent': {'child': 'value'}}
        vals = []
        get_record(obj, 'parent.child', vals)
        self.assertIn('value', vals)

    def test_get_record_list(self):
        from ingen.reader.xml_file_reader import get_record
        obj = [{'name': 'a'}, {'name': 'b'}]
        vals = []
        get_record(obj, 'name', vals)
        self.assertEqual(len(vals), 2)

    def test_get_record_none(self):
        from ingen.reader.xml_file_reader import get_record
        vals = []
        get_record(None, 'name', vals)
        self.assertIn('', vals)

    def test_get_record_nested_list(self):
        from ingen.reader.xml_file_reader import get_record
        obj = {'parent': [{'child': 'a'}, {'child': 'b'}]}
        vals = []
        get_record(obj, 'parent.child', vals)
        self.assertEqual(len(vals), 2)


class TestAPIReader(unittest.TestCase):
    """Tests for api_reader.py to cover lines 14-22, 31-32"""

    @patch('ingen.reader.api_reader.execute_requests')
    @patch('ingen.reader.api_reader.get_json_to_df_convertor')
    def test_init_default(self, mock_convertor, mock_exec):
        from ingen.reader.api_reader import APIReader
        mock_convertor.return_value = MagicMock()
        reader = APIReader([])
        self.assertFalse(reader._response_to_list)

    @patch('ingen.reader.api_reader.execute_requests')
    @patch('ingen.reader.api_reader.get_json_to_df_convertor')
    def test_init_with_reader_params(self, mock_convertor, mock_exec):
        from ingen.reader.api_reader import APIReader
        mock_convertor.return_value = MagicMock()
        reader = APIReader([], reader_params={'json_convertor': 'custom'})
        self.assertIsNotNone(reader.json_convertor)

    @patch('ingen.reader.api_reader.execute_requests')
    @patch('ingen.reader.api_reader.get_json_to_df_convertor')
    def test_init_with_response_to_list(self, mock_convertor, mock_exec):
        from ingen.reader.api_reader import APIReader
        mock_convertor.return_value = MagicMock()
        reader = APIReader([], reader_params={'response_to_list': True})
        self.assertIsNotNone(reader.json_convertor)

    @patch('ingen.reader.api_reader.execute_requests')
    @patch('ingen.reader.api_reader.get_json_to_df_convertor')
    def test_execute(self, mock_convertor, mock_exec):
        from ingen.reader.api_reader import APIReader
        mock_fn = MagicMock(return_value=pd.DataFrame())
        mock_convertor.return_value = mock_fn
        mock_exec.return_value = [{'data': 'test'}]
        reader = APIReader([])
        result = reader.execute(data_node='node', data_key='key', meta='meta')
        mock_fn.assert_called_once()


class TestCryptor(unittest.TestCase):
    """Tests for cryptor.py to cover lines 30-33, 43-44, 52-55, 63-66, 106"""

    @patch('ingen.lib.cryptor.properties')
    def test_cryptor_init(self, mock_props):
        from ingen.lib.cryptor import Cryptor
        mock_props.get_property = MagicMock(return_value='test_value')
        c = Cryptor()
        self.assertEqual(c.config['vault_path'], 'test_value')

    @patch('ingen.lib.cryptor.properties')
    @patch('ingen.lib.cryptor.AppSecrets')
    @patch('subprocess.check_output')
    def test_encrypt_decrypt(self, mock_subprocess, mock_secrets, mock_props):
        from ingen.lib.cryptor import Cryptor
        mock_props.get_property = MagicMock(return_value='test_path')

        # Mock vault response with 32-byte keys
        aes_key = 'a' * 32
        hmac_key = 'b' * 32
        import base64
        encoded_aes = base64.b64encode(aes_key.encode()).decode()
        encoded_hmac = base64.b64encode(hmac_key.encode()).decode()

        mock_secrets.get_secret.return_value = {
            'data': {'data': {'test_path': encoded_aes, 'test_path': encoded_hmac}}
        }

        # Mock GPG decryption to return the key as-is
        mock_subprocess.return_value = aes_key.encode()

        c = Cryptor()
        # Clear any LRU caches
        c._Cryptor__decrypt_gpg_kek.cache_clear()
        c._Cryptor__fetch_key.cache_clear()
        c._Cryptor__get_key.cache_clear()
        c._Cryptor__get_hmac_key.cache_clear()

        encrypted = c.encrypt('hello')
        self.assertIsInstance(encrypted, str)

        decrypted = c.decrypt(encrypted)
        self.assertEqual(decrypted, 'hello')

    @patch('ingen.lib.cryptor.properties')
    @patch('ingen.lib.cryptor.AppSecrets')
    @patch('subprocess.check_output')
    def test_hmac_tampering(self, mock_subprocess, mock_secrets, mock_props):
        from ingen.lib.cryptor import Cryptor
        import base64, json
        mock_props.get_property = MagicMock(return_value='test_path')

        aes_key = 'a' * 32
        hmac_key = 'b' * 32
        encoded_key = base64.b64encode(aes_key.encode()).decode()
        mock_secrets.get_secret.return_value = {
            'data': {'data': {'test_path': encoded_key}}
        }
        mock_subprocess.return_value = aes_key.encode()

        c = Cryptor()
        c._Cryptor__decrypt_gpg_kek.cache_clear()
        c._Cryptor__fetch_key.cache_clear()
        c._Cryptor__get_key.cache_clear()
        c._Cryptor__get_hmac_key.cache_clear()

        encrypted = c.encrypt('hello')
        # Tamper with the MAC
        decoded = base64.b64decode(encrypted.encode()).decode()
        cipher_dict = json.loads(decoded)
        cipher_dict['mac'] = 'tampered'
        tampered = base64.b64encode(json.dumps(cipher_dict).encode()).decode()

        with self.assertRaises(Exception) as ctx:
            c.decrypt(tampered)
        self.assertIn('tampered', str(ctx.exception))


class TestAPISource(unittest.TestCase):
    """Tests for api_source.py to cover lines 32, 69-78, 85, 92"""

    @patch('ingen.data_source.api_source.Interpolator')
    def test_init_with_params(self, mock_interp):
        from ingen.data_source.api_source import APISource
        mock_interp_instance = MagicMock()
        mock_interp.return_value = mock_interp_instance
        source = {
            'id': 'test',
            'url': 'http://test.com',
            'url_params': None,
            'batch': None,
            'data_node': None,
            'data_key': None,
            'meta': None,
            'auth': None,
            'response_to_list': None,
            'method': 'GET',
            'request_body': None,
            'headers': None,
            'retries': 2,
            'interval': 1,
            'interval_increment': 2,
            'success_criteria': 'status_criteria',
            'criteria_options': None,
            'convertor_method': None,
            'tasks_len': 1,
            'queue_size': 1,
            'ssl': True,
            'ignore_failure': True,
            'src_data_checks': []
        }
        api = APISource(source)
        self.assertEqual(api._url, 'http://test.com')

    @patch('ingen.data_source.api_source.Interpolator')
    def test_init_no_params(self, mock_interp):
        from ingen.data_source.api_source import APISource
        mock_interp_instance = MagicMock()
        mock_interp.return_value = mock_interp_instance
        source = {'id': 'test', 'url': 'http://test.com'}
        api = APISource(source, params_map=None)
        self.assertIsNone(api._batch)

    @patch('ingen.data_source.api_source.Interpolator')
    def test_fetch_validations(self, mock_interp):
        from ingen.data_source.api_source import APISource
        mock_interp.return_value = MagicMock()
        source = {'id': 'test', 'url': 'http://test.com', 'src_data_checks': [{'col': 'x'}]}
        api = APISource(source)
        self.assertEqual(api.fetch_validations(), [{'col': 'x'}])

    @patch('ingen.data_source.api_source.Interpolator')
    def test_parse_headers(self, mock_interp):
        from ingen.data_source.api_source import APISource
        mock_interp_instance = MagicMock()
        mock_interp_instance.interpolate = MagicMock(side_effect=lambda x: x)
        mock_interp.return_value = mock_interp_instance
        source = {'id': 'test', 'url': 'http://test.com', 'headers': {'Auth': 'Bearer token'}}
        api = APISource(source)
        self.assertEqual(api._headers, {'Auth': 'Bearer token'})

    @patch('ingen.data_source.api_source.Interpolator')
    @patch('ingen.data_source.api_source.UrlConstructor')
    @patch('ingen.data_source.api_source.APIReader')
    def test_fetch(self, mock_reader_cls, mock_url_cls, mock_interp):
        from ingen.data_source.api_source import APISource
        mock_interp_instance = MagicMock()
        mock_interp_instance.interpolate = MagicMock(return_value='http://test.com')
        mock_interp.return_value = mock_interp_instance
        mock_url_cls.return_value.get_urls.return_value = ['http://test.com']
        mock_reader = MagicMock()
        mock_reader.execute.return_value = pd.DataFrame({'a': [1]})
        mock_reader_cls.return_value = mock_reader
        source = {'id': 'test', 'url': 'http://test.com'}
        api = APISource(source)
        result = api.fetch()
        self.assertIsInstance(result, pd.DataFrame)


class TestMainModule(unittest.TestCase):
    """Tests for __main__.py to cover lines 101-111"""

    def test_main_module_importable(self):
        import ingen.__main__
        self.assertTrue(hasattr(ingen.__main__, 'main'))


class TestJsonDfConvertors(unittest.TestCase):
    """Tests for json_df_convertors.py"""

    def test_pandas_normalize_empty(self):
        from ingen.utils.json_df_convertors import pandas_normalize
        result = pandas_normalize([], None, None)
        self.assertEqual(len(result), 0)

    def test_pandas_normalize_list_of_lists(self):
        from ingen.utils.json_df_convertors import pandas_normalize
        responses = [[{'a': 1}, {'a': 2}], [{'a': 3}]]
        result = pandas_normalize(responses, None, None)
        self.assertEqual(len(result), 3)

    def test_pandas_normalize_list_of_strings(self):
        from ingen.utils.json_df_convertors import pandas_normalize
        responses = ['abc', 'def']
        result = pandas_normalize(responses, None, None)
        self.assertEqual(len(result), 2)

    def test_pandas_normalize_dicts(self):
        from ingen.utils.json_df_convertors import pandas_normalize
        responses = [{'name': 'a', 'val': 1}, {'name': 'b', 'val': 2}]
        result = pandas_normalize(responses, None, None)
        self.assertEqual(len(result), 2)

    def test_pandas_normalize_with_data_key_and_meta(self):
        from ingen.utils.json_df_convertors import pandas_normalize
        responses = [{'name': 'a', 'items': [{'x': 1}], 'id': 'A'}]
        result = pandas_normalize(responses, 'items', ['x'], ['id'])
        self.assertIn('x', result.columns)

    def test_filtered_df_with_list_meta(self):
        from ingen.utils.json_df_convertors import _filtered_df
        df = pd.DataFrame({'a': [1], 'b.c': [2], 'd': [3]})
        result = _filtered_df(df, ['a'], [['b', 'c']])
        self.assertIn('a', result.columns)
        self.assertIn('b.c', result.columns)

    def test_filtered_df_with_string_meta(self):
        from ingen.utils.json_df_convertors import _filtered_df
        df = pd.DataFrame({'a': [1], 'b': [2]})
        result = _filtered_df(df, ['a'], ['b'])
        self.assertEqual(list(result.columns), ['a', 'b'])

    def test_response_to_list(self):
        from ingen.utils.json_df_convertors import response_to_list
        responses = [{'key1': {'a': 1}, 'key2': {'a': 2}}]
        result = response_to_list(responses, None, None, None)
        self.assertTrue(len(result) > 0)

    def test_response_to_list_empty(self):
        from ingen.utils.json_df_convertors import response_to_list
        result = response_to_list([], None, None, None)
        self.assertEqual(len(result), 0)

    def test_get_convertor(self):
        from ingen.utils.json_df_convertors import get_json_to_df_convertor
        fn = get_json_to_df_convertor('pandas_normalize')
        self.assertTrue(callable(fn))
        fn2 = get_json_to_df_convertor('response_to_list')
        self.assertTrue(callable(fn2))


class TestBaseInterfaceGenerator(unittest.TestCase):
    """Tests for base_interface_generator.py to cover lines 73, 83, 93, 103, 113, 131"""

    def test_abstract_methods_exist(self):
        from ingen.generators.base_interface_generator import BaseInterfaceGenerator
        import inspect
        members = inspect.getmembers(BaseInterfaceGenerator)
        member_names = [m[0] for m in members]
        self.assertIn('read', member_names)
        self.assertIn('pre_process', member_names)
        self.assertIn('format', member_names)


if __name__ == '__main__':
    unittest.main()
