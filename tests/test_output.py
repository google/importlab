"""Tests for output.py."""

import contextlib
import io
import sys
import unittest

from importlab import environment
from importlab import fs
from importlab import graph
from importlab import output
from importlab import utils


FILES = {
        "foo/a.py": "from . import b",
        "foo/b.py": "pass",
        "x.py": "import foo.a",
        "y.py": "import sys",
        "z.py": "import unresolved"
}


# For Python 2 compatibility, since contextlib.redirect_stdout is 3-only.
@contextlib.contextmanager
def redirect_stdout(out):
    old = sys.stdout
    sys.stdout = out
    try:
        yield
    finally:
        sys.stdout = old


class TestOutput(unittest.TestCase):
    """Basic sanity tests for output methods."""

    def setUp(self):
        self.tempdir = utils.Tempdir()
        self.tempdir.setup()
        filenames = [
            self.tempdir.create_file(f, FILES[f])
            for f in FILES]
        self.fs = fs.OSFileSystem(self.tempdir.path)
        env = environment.Environment(fs.Path([self.fs]), sys.version_info[:2])
        self.graph = graph.ImportGraph.create(env, filenames)

    def tearDown(self):
        self.tempdir.teardown()

    def assertString(self, val):
        if sys.version_info[0] == 3:
            self.assertTrue(isinstance(val, str))
        else:
            self.assertTrue(isinstance(val, (str, unicode)))  # noqa: F821

    def assertPrints(self, fn):
        out = io.StringIO()
        with redirect_stdout(out):
            fn(self.graph)
        self.assertTrue(out.getvalue())

    def test_inspect_graph(self):
        self.assertPrints(output.inspect_graph)

    def test_print_tree(self):
        self.assertPrints(output.print_tree)

    def test_print_topological_sort(self):
        self.assertPrints(output.print_topological_sort)

    def test_formatted_deps_list(self):
        self.assertString(output.formatted_deps_list(self.graph))

    def test_print_unresolved(self):
        self.assertPrints(output.print_unresolved_dependencies)


if __name__ == "__main__":
    unittest.main()
