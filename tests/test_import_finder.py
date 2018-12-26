"""Tests for import_finder.py."""

import sys
import unittest

from importlab import import_finder


class TestImportFinder(unittest.TestCase):
    """Tests for import_finder."""

    def test_find_submodule(self):
        # networkx should always be findable because importlab uses it.
        name = 'networkx.algorithms.cluster'
        self.assertIsNotNone(import_finder.resolve_import(name, True, False))

    @unittest.skipIf(sys.version_info[0] == 2, 'py2 uses imp, not importlib')
    def test_importlib_exception(self):
        from unittest import mock
        with mock.patch('importlib.util.find_spec', side_effect=AssertionError):
            self.assertIsNone(import_finder.resolve_import('', False, False))


if __name__ == '__main__':
    unittest.main()
