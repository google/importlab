"""Tests for graph.py.

Run as
$ python -m tests.graph_test
"""

import unittest

from importlab import graph


class TestCycle(unittest.TestCase):
    """Tests for Cycle."""

    def test_flatten(self):
        a = graph.Cycle([[1, 2], [2, 3], [3, 1]])
        b = graph.Cycle([[4, 5], [5, 4]])
        c = graph.Cycle([[a, 6], [6, b], [b, 7], [7, a]])
        nodes = c.flatten_nodes()
        self.assertEqual(sorted(nodes), [1, 2, 3, 4, 5, 6, 7])


class FakeImportGraph(graph.DependencyGraph):
    """An ImportGraph with file imports stubbed out.

    Also adds ordered_foo() wrappers around output methods to help in testing.
    """

    def __init__(self, deps):
        super(FakeImportGraph, self).__init__()
        self.deps = deps

    def get_file_deps(self, filename):
        if filename in self.deps:
            return self.deps[filename]
        return ([], [])

    def ordered_deps_list(self):
        deps = []
        for k, v in self.deps_list():
            deps.append((k, sorted(v)))
        return list(sorted(deps))

    def ordered_sorted_source_files(self):
        return [list(sorted(x)) for x in self.sorted_source_files()]


# Deps = { file : ([resolved deps], [broken deps]) }

SIMPLE_DEPS = {
        "a.py": (["b.py", "c.py"], []),
        "b.py": (["d.py"], ["e"])
        }

SIMPLE_CYCLIC_DEPS = {
        "a.py": (["b.py", "c.py"], ["e"]),
        "b.py": (["d.py", "a.py"], ["f"]),
        }


class TestImportGraph(unittest.TestCase):
    """Tests for ImportGraph."""

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

    def test_simple_cycle(self):
        g = FakeImportGraph(SIMPLE_CYCLIC_DEPS)
        g.add_file_recursive("a.py")
        g.build()
        cycles = [x for x, ys in g.ordered_deps_list()
                if isinstance(x, graph.NodeSet)]
        self.assertEqual(len(cycles), 1)
        self.assertItemsEqual(cycles[0].nodes, ["a.py", "b.py"])
        self.assertEqual(g.get_all_unresolved(), set(["e", "f"]))
        sources = g.ordered_sorted_source_files()
        self.check_order(sources, ["d.py"], ["a.py", "b.py"])
        self.check_order(sources, ["c.py"], ["a.py", "b.py"])



if __name__ == "__main__":
    unittest.main()
