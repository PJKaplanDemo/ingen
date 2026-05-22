#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import unittest

import pandas as pd

from ingen.post_processor.post_processor import PostProcessor


class TestPostProcessorFull(unittest.TestCase):

    def test_no_post_processes(self):
        df = pd.DataFrame({"a": [1, 2]})
        pp = PostProcessor(None, df)
        result = pp.apply_post_processing()
        pd.testing.assert_frame_equal(result, df)

    def test_non_dataframe_raises(self):
        pp = PostProcessor([{"type": "pivot"}], "not a dataframe")
        with self.assertRaises(TypeError):
            pp.apply_post_processing()

    def test_empty_dataframe_raises(self):
        pp = PostProcessor([{"type": "pivot"}], pd.DataFrame())
        with self.assertRaises(ValueError):
            pp.apply_post_processing()

    def test_unknown_processor_raises(self):
        df = pd.DataFrame({"a": [1]})
        pp = PostProcessor([{"type": "unknown_proc"}], df)
        with self.assertRaises(NameError):
            pp.apply_post_processing()

    def test_get_processor_func_valid(self):
        df = pd.DataFrame({"a": [1]})
        pp = PostProcessor([], df)
        func = pp.get_processor_func({"type": "pivot"})
        self.assertIsNotNone(func)


if __name__ == '__main__':
    unittest.main()
