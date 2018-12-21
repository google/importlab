"""Tests for import_finder.py."""

import unittest

from importlab import import_finder


class TestImportFinder(unittest.TestCase):
    """Tests for import_finder."""

    def test_find_submodule(self):
        # networkx should always be findable because importlab uses it.
        name = 'networkx.algorithms.cluster'
        self.assertIsNotNone(import_finder.resolve_import(name, True, False))


if __name__ == '__main__':
    unittest.main()
