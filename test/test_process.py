#  Copyright (c) 2023 BlackRock, Inc.
#  All Rights Reserved.

import unittest

from ingen.pre_processor.process import Process


class TestProcess(unittest.TestCase):

    def test_execute_returns_none(self):
        p = Process()
        self.assertIsNone(p.execute({}, {}, None))


if __name__ == '__main__':
    unittest.main()
