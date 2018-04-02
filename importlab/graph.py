import collections
import os

import networkx as nx

from . import resolve
from . import parsepy
from . import import_finder


class Cycle(object):
    """A cycle of nodes, some of which might be cycles."""

    def __init__(self, edges, root=''):
        self.root = root
        self.edges = edges
        self.nodes = [x[0] for x in self.edges]

    def _fmt(self, node):
        if isinstance(node, Cycle):
            return node.pp()
        else:
            return os.path.relpath(node, self.root)

    def flatten_nodes(self):
        out = []
        for n in self.nodes:
            if isinstance(n, Cycle):
                out.extend(n.flatten_nodes())
            else:
                out.append(n)
        return out

    def __contains__(self, v):
        return v in self.nodes

    def pp(self):
        return "Cycle(" + '->'.join([self._fmt(f) for f in self.nodes]) + ")"

    def __str__(self):
        return self.pp()


class NodeSet(object):
    """The flattened version of a cycle - a set of mutually dependent files."""

    def __init__(self, cycle):
        self.root = cycle.root
        self.nodes = cycle.flatten_nodes()

    def __contains__(self, v):
        return v in self.nodes

    def _fmt(self, node):
        return os.path.relpath(node, self.root)

    def pp(self):
        return "[" + '->'.join([self._fmt(f) for f in self.nodes]) + "]"

    def __str__(self):
        return self.pp()

    def __len__(self):
        return len(self.nodes)

    def __iter__(self):
        return self.nodes.__iter__()


def is_source_node(x):
    return isinstance(x, (Cycle, NodeSet)) or x.endswith(".py")


class ImportGraph(object):
    """A set of dependencies stored in a graph structure.

    The ImportGraph needs to be constructed in two phases:
    1. Call add_file_recursive() for every root file you want to add to the graph.
    2. Call build() to collapse cycles and build the final graph.

    Calling build() sets self.final = True and treats the graph as immutable
    thereafter.
    """

    def __init__(self, env):
        self.env = env
        self.major_version = env.python_version[0]
        self.broken_deps = collections.defaultdict(set)
        self.graph = nx.DiGraph()
        self.root = None
        self.final = False

    def get_file_deps(self, filename):
        r = resolve.Resolver(self.env.path, filename)
        resolved = []
        unresolved = []
        for imp in parsepy.get_imports(filename, self.major_version):
            try:
                f = r.resolve_import(imp)
                if not f.endswith(".so"):
                    resolved.append(os.path.abspath(f))
            except resolve.ImportException:
                unresolved.append(imp)
        return (resolved, unresolved)

    def add_file(self, filename):
        """Add a file and all its immediate dependencies to the graph."""

        assert not self.final, "Trying to mutate a final graph."
        resolved, unresolved = self.get_file_deps(filename)
        self.graph.add_node(filename)
        for f in resolved:
            self.graph.add_node(f)
            self.graph.add_edge(filename, f)
        for imp in unresolved:
            self.broken_deps[filename].add(imp)

    def add_file_recursive(self, filename):
        """Add a file and all its recursive dependencies to the graph."""

        assert not self.final, "Trying to mutate a final graph."
        queue = collections.deque([filename])
        seen = set()
        while queue:
            filename = queue.popleft()
            self.graph.add_node(filename)
            deps, broken = self.get_file_deps(filename)
            for f in broken:
                self.broken_deps[filename].add(f)
            for f in deps:
                if (not f in self.graph.nodes and
                    not f in seen and
                    f.endswith(".py")):
                    queue.append(f)
                    seen.add(f)
                self.graph.add_node(f)
                self.graph.add_edge(filename, f)

    def find_root(self, recalculate=False):
        if recalculate or not self.root:
            keys = set(x[0] for x in self.graph.edges)
            prefix = os.path.commonprefix(list(keys))
            if not os.path.isdir(prefix):
                prefix = os.path.dirname(prefix)
            self.root = prefix
        return self.root

    def extract_cycle(self, cycle):
        assert not self.final, "Trying to mutate a final graph."
        self.graph.add_node(cycle)
        edges = list(self.graph.edges)
        for k, v in edges:
            if k not in cycle and v in cycle:
                self.graph.remove_edge(k, v)
                self.graph.add_edge(k, cycle)
            elif k in cycle and v not in cycle:
                self.graph.remove_edge(k, v)
                self.graph.add_edge(cycle, v)
        for node in cycle.nodes:
            self.graph.remove_node(node)

    def format(self, node):
        prefix = self.find_root()
        if isinstance(node, (Cycle, NodeSet)):
            return node.pp()
        elif node.startswith(self.env.typeshed_location):
            return "[%s]" % os.path.relpath(node, self.env.typeshed_location)
        else:
            return os.path.relpath(node, prefix)

    def inspect_graph(self):
        prefix = self.find_root()
        keys = set(x[0] for x in self.graph.edges)
        for key in sorted(keys):
            k = self.format(key)
            for _, value in sorted(self.graph.edges([key])):
                v = self.format(value)
                print("  %s -> %s" % (k, v))
            for value in sorted(self.broken_deps[key]):
                print("  %s -> <%s>" % (k, value))

    def build(self):
        """Finalise the graph, after adding all input files to it."""

        assert not self.final, "Trying to mutate a final graph."

        # Recursively extract cycles until the graph is cycle-free.
        prefix = self.find_root()
        while True:
            try:
                cycle = Cycle(nx.find_cycle(self.graph), prefix)
                self.extract_cycle(cycle)
            except nx.NetworkXNoCycle:
                break

        # Now that we have reduced the graph to a tree, we can flatten cycle
        # nodes into NodeSets
        def transform_node(node):
            if isinstance(node, Cycle):
                return NodeSet(node)
            else:
                return node
        self.graph = nx.relabel_nodes(self.graph, transform_node)
        self.final = True

    def sorted_source_files(self):
        """Returns a list of targets in topologically sorted order."""

        assert self.final, "Call build() before using the graph."
        out = []
        for node in nx.topological_sort(self.graph):
            if isinstance(node, NodeSet):
                out.append(node.nodes)
            elif node.endswith(".py"):
                # add a one-element list for uniformity
                out.append([node])
            else:
                # We don't care about pyi deps
                pass
        return reversed(out)

    def deps_list(self):
        """Returns a list of (target, dependencies)."""

        assert self.final, "Call build() before using the graph."
        out = []
        for node in nx.topological_sort(self.graph):
            if is_source_node(node):
                deps = [v for k, v in self.graph.out_edges([node])
                        if is_source_node(v)]
                out.append((node, deps))
        return out

    def get_all_unresolved(self):
        """Returns a set of all unresolved imports."""
        assert self.final, "Call build() before using the graph."
        out = set()
        for v in self.broken_deps.values():
            out |= v
        return out

    def _print_tree(self, root, seen, indent=0):
        if root in seen:
            return
        if not is_source_node(root):
            return
        seen.add(root)
        print('  '*indent + self.format(root))
        for _, v in self.graph.out_edges([root]):
            self._print_tree(v, seen, indent=indent+2)

    def print_tree(self):
        seen = set()
        for root in nx.topological_sort(self.graph):
            if not self.graph.in_edges([root]):
                self._print_tree(root, seen)

    def print_topological_sort(self):
        for node in nx.topological_sort(self.graph):
            if is_source_node(node):
                print(self.format(node))

    def formatted_deps_list(self):
        out = []
        for node, deps in self.deps_list():
            out.append('source: ' + self.format(node))
            if deps:
              out.append('deps:')
              for dep in deps:
                  out.append('  ' + self.format(dep))
        return '\n'.join(out)
