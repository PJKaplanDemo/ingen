#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import unittest

from ingen.data_source.source import DataSource


class TestDataSource(unittest.TestCase):

    def test_init_and_id(self):
        ds = DataSource("test_id")
        self.assertEqual(ds.id, "test_id")

    def test_fetch_returns_none(self):
        ds = DataSource("test_id")
        self.assertIsNone(ds.fetch())

    def test_fetch_validations_returns_none(self):
        ds = DataSource("test_id")
        self.assertIsNone(ds.fetch_validations())


if __name__ == '__main__':
    unittest.main()
