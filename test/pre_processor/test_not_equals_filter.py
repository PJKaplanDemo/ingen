#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import unittest

import pandas as pd

from ingen.pre_processor.not_equals_filter import NotEqualsFilter


class TestNotEqualsFilter(unittest.TestCase):

    def setUp(self):
        self.filter = NotEqualsFilter()
        self.df = pd.DataFrame({
            "name": ["Alice", "Bob", "Charlie", "Dave"],
            "status": ["active", "inactive", "active", "pending"]
        })

    def test_basic_exclude(self):
        config = {
            'cols': [{'col': 'status', 'val': ['inactive']}]
        }
        result = self.filter.execute(config, {}, self.df)
        self.assertEqual(len(result), 3)
        self.assertNotIn("inactive", result["status"].values)

    def test_exclude_multiple_values(self):
        config = {
            'cols': [{'col': 'status', 'val': ['inactive', 'pending']}]
        }
        result = self.filter.execute(config, {}, self.df)
        self.assertEqual(len(result), 2)

    def test_empty_dataframe(self):
        config = {
            'cols': [{'col': 'status', 'val': ['inactive']}]
        }
        result = self.filter.execute(config, {}, pd.DataFrame())
        self.assertTrue(result.empty)

    def test_none_dataframe(self):
        config = {
            'cols': [{'col': 'status', 'val': ['inactive']}]
        }
        result = self.filter.execute(config, {}, None)
        self.assertTrue(result.empty)

    def test_no_cols(self):
        config = {'cols': []}
        result = self.filter.execute(config, {}, self.df)
        self.assertEqual(len(result), 4)

    def test_source_from_sources_data(self):
        config = {
            'source': 'src1',
            'cols': [{'col': 'status', 'val': ['active']}]
        }
        result = self.filter.execute(config, {'src1': self.df}, self.df)
        self.assertEqual(len(result), 2)

    def test_nonexistent_column(self):
        config = {
            'cols': [{'col': 'nonexistent', 'val': ['value']}]
        }
        result = self.filter.execute(config, {}, self.df)
        self.assertEqual(len(result), 4)


if __name__ == '__main__':
    unittest.main()
