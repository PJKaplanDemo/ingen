#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import logging
import unittest

from ingen.logger import init_logging, LOG_FORMAT


class TestLogger(unittest.TestCase):

    def setUp(self):
        root = logging.getLogger()
        root.handlers = []

    def test_init_logging_sets_level(self):
        init_logging()
        root = logging.getLogger()
        self.assertEqual(root.level, logging.INFO)

    def test_init_logging_adds_handler(self):
        init_logging()
        root = logging.getLogger()
        self.assertTrue(len(root.handlers) > 0)

    def test_init_logging_sets_formatter(self):
        init_logging()
        root = logging.getLogger()
        for handler in root.handlers:
            self.assertEqual(handler.formatter._fmt, LOG_FORMAT)


if __name__ == '__main__':
    unittest.main()
