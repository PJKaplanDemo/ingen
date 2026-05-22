#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import unittest

import pandas as pd

from ingen.pre_processor.outer_join import OuterJoin


class TestOuterJoin(unittest.TestCase):

    def setUp(self):
        self.join = OuterJoin()
        self.left_df = pd.DataFrame({
            "id": [1, 2, 3],
            "name": ["Alice", "Bob", "Charlie"]
        })
        self.right_df = pd.DataFrame({
            "id": [2, 3, 4],
            "score": [90, 80, 70]
        })

    def test_basic_outer_join(self):
        config = {
            'source': 'right',
            'left_key': 'id',
            'right_key': 'id'
        }
        sources_data = {'right': self.right_df}
        result = self.join.execute(config, sources_data, self.left_df)
        self.assertEqual(len(result), 4)

    def test_nan_replaced_with_empty_string(self):
        config = {
            'source': 'right',
            'left_key': 'id',
            'right_key': 'id'
        }
        sources_data = {'right': self.right_df}
        result = self.join.execute(config, sources_data, self.left_df)
        self.assertNotIn(float('nan'), result.values.flatten().tolist())

    def test_left_key_not_in_left_raises(self):
        config = {
            'source': 'right',
            'left_key': 'nonexistent',
            'right_key': 'id'
        }
        sources_data = {'right': self.right_df}
        with self.assertRaises(KeyError):
            self.join.execute(config, sources_data, self.left_df)

    def test_right_key_not_in_right_raises(self):
        config = {
            'source': 'right',
            'left_key': 'id',
            'right_key': 'nonexistent'
        }
        sources_data = {'right': self.right_df}
        with self.assertRaises(KeyError):
            self.join.execute(config, sources_data, self.left_df)


if __name__ == '__main__':
    unittest.main()
