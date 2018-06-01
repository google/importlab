"""Tests for utils.py."""

import unittest

from importlab import utils


class TestUtils(unittest.TestCase):
    """Tests for utils."""

    def test_strip_suffix(self):
        a = 'foo bar bar'
        self.assertEqual(a, utils.strip_suffix(a, 'hello'))
        self.assertEqual('foo bar ', utils.strip_suffix(a, 'bar'))
        self.assertEqual(a, utils.strip_suffix(a, 'hbar'))


if __name__ == "__main__":
    unittest.main()
