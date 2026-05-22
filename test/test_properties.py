#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import os
import tempfile
import unittest
from unittest.mock import patch

from ingen.utils.properties import Properties


class TestProperties(unittest.TestCase):

    def _make_fresh_instance(self):
        Properties._instance = None
        return Properties()

    def test_get_property_default(self):
        props = self._make_fresh_instance()
        result = props.get_property("nonexistent_key_xyz", "default_val")
        self.assertEqual(result, "default_val")

    def test_get_property_existing(self):
        props = self._make_fresh_instance()
        props.property_map["test_key"] = "test_value"
        result = props.get_property("test_key")
        self.assertEqual(result, "test_value")

    def test_initialize_with_config_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_content = "key1=value1\nkey2=value2\n"
            with open(os.path.join(tmpdir, "config.properties"), 'w') as f:
                f.write(config_content)

            os.environ['config_path'] = tmpdir
            Properties._instance = None
            props = Properties()

            self.assertEqual(props.get_property("key1"), "value1")
            self.assertEqual(props.get_property("key2"), "value2")
            if 'config_path' in os.environ:
                del os.environ['config_path']

    def test_initialize_with_no_config_path(self):
        if 'config_path' in os.environ:
            del os.environ['config_path']
        Properties._instance = None
        props = Properties()
        self.assertIsNotNone(props.property_map)

    def test_initialize_with_missing_file(self):
        os.environ['config_path'] = '/nonexistent/path'
        Properties._instance = None
        props = Properties()
        self.assertEqual(props.property_map, {})
        del os.environ['config_path']

    def test_initialize_with_invalid_property_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_content = "key1=value1\ninvalid_line_no_equals\nkey2=value2\n"
            with open(os.path.join(tmpdir, "config.properties"), 'w') as f:
                f.write(config_content)

            os.environ['config_path'] = tmpdir
            Properties._instance = None
            props = Properties()

            self.assertEqual(props.get_property("key1"), "value1")
            self.assertEqual(props.get_property("key2"), "value2")
            del os.environ['config_path']

    def test_initialize_with_empty_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_content = "key1=value1\n\n  \nkey2=value2\n"
            with open(os.path.join(tmpdir, "config.properties"), 'w') as f:
                f.write(config_content)

            os.environ['config_path'] = tmpdir
            Properties._instance = None
            props = Properties()

            self.assertEqual(props.get_property("key1"), "value1")
            self.assertEqual(props.get_property("key2"), "value2")
            del os.environ['config_path']

    def tearDown(self):
        Properties._instance = None


if __name__ == '__main__':
    unittest.main()
