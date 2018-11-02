import collections
import os

import networkx as nx

from . import resolve
from . import parsepy


class Cycle(object):
    """A cycle of nodes, some of which might be cycles."""

    def __init__(self, edges):
        self.edges = edges
        self.nodes = [x[0] for x in self.edges]

    def _fmt(self, node):
        if isinstance(node, Cycle):
            return node.pp()
        else:
            return node

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
        return 'Cycle(' + '->'.join([self._fmt(f) for f in self.nodes]) + ')'

    def __str__(self):
        return self.pp()


class NodeSet(object):
    """The flattened version of a cycle - a set of mutually dependent files."""

    def __init__(self, cycle):
        self.nodes = cycle.flatten_nodes()

    def __contains__(self, v):
        return v in self.nodes

    def pp(self):
        return '[' + '->'.join([str(f) for f in self.nodes]) + ']'

    def __str__(self):
        return self.pp()

    def __len__(self):
        return len(self.nodes)

    def __iter__(self):
        return self.nodes.__iter__()


def is_source_node(x):
    return isinstance(x, (Cycle, NodeSet)) or x.endswith('.py')


class DependencyGraph(object):
    """A set of file dependencies stored in a graph structure.

    The graph needs to be constructed in two phases:
    1. Call add_file_recursive() for every root file to add to the graph.
    2. Call build() to collapse cycles and build the final graph.

    Calling build() sets self.final = True and treats the graph as immutable
    thereafter.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        # import statements that did not resolve to python files.
        self.broken_deps = collections.defaultdict(set)
        # files that were not syntactically valid python.
        self.unreadable_files = set()
        # once self.final is set the graph can no longer be modified.
        self.final = False
        # sources is a set of files directly added to the graph via
        # add_file or add_file_recursive.
        self.sources = set()
        # provenance is a map of file path (as stored in the graph) to where the
        # file was sourced from (see resolve.ResolvedFile)
        self.provenance = {}

    def get_file_deps(self, filename):
        raise NotImplementedError()

    def add_source_file(self, filename):
        self.sources.add(filename)
        self.provenance[filename] = self.get_source_file_provenance(filename)

    def get_source_file_provenance(self, filename):
        return resolve.Direct(filename)

    def add_file(self, filename):
        """Add a file and all its immediate dependencies to the graph."""

        assert not self.final, 'Trying to mutate a final graph.'
        self.add_source_file(filename)
        resolved, unresolved = self.get_file_deps(filename)
        self.graph.add_node(filename)
        for f in resolved:
            self.graph.add_node(f)
            self.graph.add_edge(filename, f)
        for imp in unresolved:
            self.broken_deps[filename].add(imp)

    def follow_file(self, f, seen, trim):
        """Whether to recurse into a file's dependencies."""
        return (f not in self.graph.nodes and
                f not in seen and
                f.endswith('.py') and
                (not trim or
                 not isinstance(self.provenance[f],
                                (resolve.Builtin, resolve.System))))

    def add_file_recursive(self, filename, trim=False):
        """Add a file and all its recursive dependencies to the graph.

        Args:
          filename: The name of the file.
          trim: Whether to trim the dependencies of builtin and system files.
        """

        assert not self.final, 'Trying to mutate a final graph.'
        self.add_source_file(filename)
        queue = collections.deque([filename])
        seen = set()
        while queue:
            filename = queue.popleft()
            self.graph.add_node(filename)
            try:
                deps, broken = self.get_file_deps(filename)
            except parsepy.ParseError:
                # We have found a dependency, but python couldn't parse it.
                self.unreadable_files.add(filename)
                self.graph.remove_node(filename)
                continue
            for f in broken:
                self.broken_deps[filename].add(f)
            for f in deps:
                if self.follow_file(f, seen, trim):
                    queue.append(f)
                    seen.add(f)
                self.graph.add_node(f)
                self.graph.add_edge(filename, f)

    def extract_cycle(self, cycle):
        assert not self.final, 'Trying to mutate a final graph.'
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
        if isinstance(node, (Cycle, NodeSet)):
            return node.pp()
        else:
            return node

    def inspect_graph(self):
        keys = set(x[0] for x in self.graph.edges)
        for key in sorted(keys):
            k = self.format(key)
            for _, value in sorted(self.graph.edges([key])):
                v = self.format(value)
                print('  %s -> %s' % (k, v))
            for value in sorted(self.broken_deps[key]):
                print('  %s -> <%s>' % (k, value))

    def build(self):
        """Finalise the graph, after adding all input files to it."""

        assert not self.final, 'Trying to mutate a final graph.'

        # Recursively extract cycles until the graph is cycle-free.
        while True:
            try:
                cycle = Cycle(nx.find_cycle(self.graph))
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

        assert self.final, 'Call build() before using the graph.'
        out = []
        for node in nx.topological_sort(self.graph):
            if isinstance(node, NodeSet):
                out.append(node.nodes)
            elif node.endswith('.py'):
                # add a one-element list for uniformity
                out.append([node])
            else:
                # We don't care about other deps
                pass
        return list(reversed(out))

    def deps_list(self):
        """Returns a list of (target, dependencies)."""

        assert self.final, 'Call build() before using the graph.'
        out = []
        for node in nx.topological_sort(self.graph):
            if is_source_node(node):
                deps = [v for k, v in self.graph.out_edges([node])
                        if is_source_node(v)]
                out.append((node, deps))
        return out

    def get_all_unresolved(self):
        """Returns a set of all unresolved imports."""
        assert self.final, 'Call build() before using the graph.'
        out = set()
        for v in self.broken_deps.values():
            out |= v
        return out


class ImportGraph(DependencyGraph):
    """A dependency graph built from file imports."""

    def __init__(self, env):
        super(ImportGraph, self).__init__()
        self.env = env
        self.path = env.path
        self.major_version = env.python_version[0]

    @classmethod
    def create(cls, env, filenames, trim=False):
        """Create and return a final graph.

        Args:
          env: An environment.Environment object
          filenames: A list of filenames
          trim: Whether to trim the dependencies of builtin and system files.

        Returns:
          An immutable ImportGraph with the recursive dependencies of all the
          files in filenames
        """
        import_graph = cls(env)
        for filename in filenames:
            import_graph.add_file_recursive(os.path.abspath(filename), trim)
        import_graph.build()
        return import_graph

    def get_source_file_provenance(self, filename):
        """Infer the module name if possible."""
        module_name = resolve.infer_module_name(filename, self.path)
        return resolve.Direct(filename, module_name)

    def get_file_deps(self, filename):
        resolved = []
        unresolved = []
        parent = self.provenance[filename]
        r = resolve.Resolver(self.path, parent)
        for imp in parsepy.get_imports(filename, self.env.python_version):
            try:
                f = r.resolve_import(imp)
                if f.is_extension():
                    continue
                full_path = os.path.abspath(f.path)
                resolved.append(full_path)
                self.provenance[full_path] = f
            except resolve.ImportException:
                unresolved.append(imp)
        return (resolved, unresolved)
