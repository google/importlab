"""Tests for graph.py."""

import contextlib
import os
import sys
import unittest

from importlab import environment
from importlab import fs
from importlab import graph
from importlab import parsepy
from importlab import resolve
from importlab import utils


class FakeImportGraph(graph.DependencyGraph):
    """An ImportGraph with file imports stubbed out.

    Also adds ordered_foo() wrappers around output methods to help in testing.
    """

    def __init__(self, deps, unreadable=None):
        super(FakeImportGraph, self).__init__()
        self.deps = deps
        if unreadable:
            self.unreadable = unreadable
        else:
            self.unreadable = set()

    def get_source_file_provenance(self, filename):
        return resolve.Direct(filename, "module.name")

    def get_file_deps(self, filename):
        if filename in self.unreadable:
            raise parsepy.ParseError()
        if filename in self.deps:
            resolved, unresolved, provenance = self.deps[filename]
            self.provenance.update(provenance)
            return (resolved, unresolved)
        return ([], [])

    def ordered_deps_list(self):
        deps = []
        for k, v in self.deps_list():
            deps.append((k, sorted(v)))
        return list(sorted(deps))

    def ordered_sorted_source_files(self):
        return [list(sorted(x)) for x in self.sorted_source_files()]


# Deps = { file : ([resolved deps], [broken deps], {dep_file:provenance}) }

SIMPLE_DEPS = {
        "a.py": (["b.py", "c.py"], [],
                 {"b.py": resolve.Local("b.py", "b", "fs1"),
                  "c.py": resolve.Local("c.py", "c", "fs2")
                  }),
        "b.py": (["d.py"], ["e"],
                 {"d.py": resolve.System("d.py", "d")})
}

SIMPLE_NONPY_DEPS = {"a.pyi": (["b.py"], [], {})}

SIMPLE_CYCLIC_DEPS = {
        "a.py": (["b.py", "c.py"], ["e"], {}),
        "b.py": (["d.py", "a.py"], ["f"], {}),
}

SIMPLE_SYSTEM_DEPS = {
        "a.py": (["b.py"], [], {"b.py": resolve.System("b.py", "b")}),
        "b.py": (["c.py"], [], {"c.py": resolve.System("c.py", "c")}),
}


class TestDependencyGraph(unittest.TestCase):
    """Tests for DependencyGraph."""

    def check_order(self, xs, *args):
        """Checks that args form an increasing sequence within xs."""
        indices = [xs.index(arg) for arg in args]
        for i in range(1, len(indices)):
            self.assertTrue(indices[i - 1] < indices[i],
                            "%s comes before %s" % (args[i], args[i - 1]))

    def test_simple(self):
        g = FakeImportGraph(SIMPLE_DEPS)
        g.add_file_recursive("a.py")
        g.build()
        self.assertEqual(g.ordered_deps_list(), [
            ("a.py", ["b.py", "c.py"]),
            ("b.py", ["d.py"]),
            ("c.py", []),
            ("d.py", [])])
        self.assertEqual(g.get_all_unresolved(), set(["e"]))
        sources = g.ordered_sorted_source_files()
        self.check_order(sources, ["d.py"], ["b.py"], ["a.py"])
        self.check_order(sources, ["c.py"], ["a.py"])
        self.assertEqual(sorted(g.provenance.keys()),
                         ["a.py", "b.py", "c.py", "d.py"])
        # a.py is a directly added source
        provenance = g.provenance["a.py"]
        self.assertTrue(isinstance(provenance, resolve.Direct))
        self.assertEqual(provenance.module_name, "module.name")
        # b.py came from fs1
        self.assertEqual(g.provenance["b.py"].fs, "fs1")

    def test_simple_cycle(self):
        g = FakeImportGraph(SIMPLE_CYCLIC_DEPS)
        g.add_file_recursive("a.py")
        g.build()
        cycles = [x for x, ys in g.deps_list()
                  if isinstance(x, graph.NodeSet)]
        self.assertEqual(len(cycles), 1)
        self.assertEqual(set(cycles[0].nodes), set(["a.py", "b.py"]))
        self.assertEqual(g.get_all_unresolved(), set(["e", "f"]))
        sources = g.ordered_sorted_source_files()
        self.check_order(sources, ["d.py"], ["a.py", "b.py"])
        self.check_order(sources, ["c.py"], ["a.py", "b.py"])

    def test_trim(self):
        # Untrimmed g1 follows system module b to its dependency c.
        g1 = FakeImportGraph(SIMPLE_SYSTEM_DEPS)
        g1.add_file_recursive("a.py", trim=False)
        g1.build()
        self.assertEqual(g1.ordered_deps_list(), [
            ("a.py", ["b.py"]),
            ("b.py", ["c.py"]),
            ("c.py", [])])
        # Trimmed g2 stops at b.
        g2 = FakeImportGraph(SIMPLE_SYSTEM_DEPS)
        g2.add_file_recursive("a.py", trim=True)
        g2.build()
        self.assertEqual(g2.ordered_deps_list(), [
            ("a.py", ["b.py"]),
            ("b.py", [])])

    def test_unreadable(self):
        # Unreadable py files are kept in the graph to give the caller
        # flexibility on what to do with them.
        g = FakeImportGraph(SIMPLE_DEPS, unreadable={"b.py"})
        g.add_file_recursive("a.py")
        g.build()
        self.assertEqual(g.ordered_deps_list(), [
            ("a.py", ["b.py", "c.py"]),
            ("b.py", []),
            ("c.py", []),
        ])
        sources = g.ordered_sorted_source_files()
        self.check_order(sources, ["c.py"], ["a.py"])
        self.assertEqual(sorted(g.provenance),
                         ["a.py", "b.py", "c.py"])
        self.assertEqual(g.unreadable_files, set(["b.py"]))

    def test_unreadable_direct_source(self):
        # Unreadable py files are kept in the graph to give the caller
        # flexibility on what to do with them.
        g = FakeImportGraph(SIMPLE_DEPS, unreadable={"a.py"})
        g.add_file_recursive("a.py")
        g.build()
        self.assertEqual(g.ordered_deps_list(), [("a.py", [])])

    def test_readable_nonpy(self):
        g = FakeImportGraph(SIMPLE_NONPY_DEPS)
        g.add_file_recursive("a.pyi")
        g.build()
        self.assertEqual(g.ordered_deps_list(), [
            ("a.pyi", ["b.py"]),
            ("b.py", []),
        ])

    def test_unreadable_nonpy(self):
        g = FakeImportGraph(SIMPLE_NONPY_DEPS, unreadable={"a.pyi"})
        g.add_file_recursive("a.pyi")
        g.build()
        # Original source file is unreadable, so return nothing.
        self.assertEqual(g.ordered_deps_list(), [])


FILES = {
        "foo/a.py": "from . import b",
        "foo/b.py": "pass",
        "x.py": "import foo.a"
}


class TestImportGraph(unittest.TestCase):
    """Tests for ImportGraph."""

    def setUp(self):
        self.tempdir = utils.Tempdir()
        self.tempdir.setup()
        self.filenames = [
            self.tempdir.create_file(f, FILES[f])
            for f in FILES]
        self.fs = fs.OSFileSystem(self.tempdir.path)
        self.env = environment.Environment(
            fs.Path([self.fs]), sys.version_info[:2])

    def tearDown(self):
        self.tempdir.teardown()

    def test_basic(self):
        g = graph.ImportGraph.create(self.env, self.filenames)
        self.assertEqual(
                g.sorted_source_files(),
                [[self.tempdir[x]] for x in ["foo/b.py", "foo/a.py", "x.py"]])

    @contextlib.contextmanager
    def patch_resolve_import(self, mock_resolve_file):
        """Patch resolve_import to always return a System file."""
        resolve_import = resolve.Resolver.resolve_import

        def mock_resolve_import(resolver_self, item):
            resolved_file = resolve_import(resolver_self, item)
            return mock_resolve_file(resolved_file)

        resolve.Resolver.resolve_import = mock_resolve_import
        try:
            yield
        finally:
            resolve.Resolver.resolve_import = resolve_import

    def test_trim(self):
        sources = [self.tempdir["x.py"]]
        mock_resolve_file = lambda f: resolve.System(f.path, f.module_name)
        with self.patch_resolve_import(mock_resolve_file):
            # Untrimmed g1 contains foo.b, the dep of system module foo.a.
            g1 = graph.ImportGraph.create(self.env, sources, trim=False)
            self.assertEqual(
                g1.sorted_source_files(),
                [[self.tempdir[x]] for x in ["foo/b.py", "foo/a.py", "x.py"]])
            # Trimmed g2 stops at foo.a.
            g2 = graph.ImportGraph.create(self.env, sources, trim=True)
            self.assertEqual(
                g2.sorted_source_files(),
                [[self.tempdir[x]] for x in ["foo/a.py", "x.py"]])

    def test_system_extension(self):
        """Tests that system .so files are included in deps."""
        sources = [self.tempdir["x.py"]]
        def mock_resolve_file(f):
            path = os.path.splitext(f.path)[0] + ".so"
            return resolve.System(path, f.module_name)
        with self.patch_resolve_import(mock_resolve_file):
            g = graph.ImportGraph.create(self.env, sources, trim=True)
            foo_a = os.path.splitext(self.tempdir["foo/a.py"])[0] + ".so"
            self.assertEqual(g.sorted_source_files(),
                             [[foo_a], [self.tempdir["x.py"]]])

    def test_builtin_extension(self):
        """Tests that builtin .so files are ignored."""
        sources = [self.tempdir["x.py"]]
        def mock_resolve_file(f):
            path = os.path.splitext(f.path)[0] + ".so"
            return resolve.Builtin(path, f.module_name)
        with self.patch_resolve_import(mock_resolve_file):
            g = graph.ImportGraph.create(self.env, sources, trim=True)
            foo_a = os.path.splitext(self.tempdir["foo/a.py"])[0] + ".so"
            self.assertEqual(g.sorted_source_files(), [[self.tempdir["x.py"]]])


if __name__ == "__main__":
    unittest.main()
