"""Tests for utils.py."""

import sys
import tempfile
import unittest

from importlab import utils


class TestUtils(unittest.TestCase):
    """Tests for utils."""

    def test_strip_suffix(self):
        a = 'foo bar bar'
        self.assertEqual(a, utils.strip_suffix(a, 'hello'))
        self.assertEqual('foo bar ', utils.strip_suffix(a, 'bar'))
        self.assertEqual(a, utils.strip_suffix(a, 'hbar'))

    def test_run_py_file(self):
        version = sys.version_info[:2]
        with tempfile.NamedTemporaryFile(mode='w') as f:
            f.write('print("test")')
            f.flush()
            ret, stdout, stderr = utils.run_py_file(version, f.name)
        self.assertFalse(ret)
        self.assertEqual(stdout.strip().decode(), 'test')
        self.assertFalse(stderr)


if __name__ == "__main__":
    unittest.main()
