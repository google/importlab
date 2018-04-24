from __future__ import print_function

import networkx as nx


def inspect_graph(import_graph):
    prefix = import_graph.find_root()
    keys = set(x[0] for x in import_graph.graph.edges)
    for key in sorted(keys):
        k = import_graph.format(key)
        for _, value in sorted(import_graph.graph.edges([key])):
            v = import_graph.format(value)
            print("  %s -> %s" % (k, v))
        for value in sorted(import_graph.broken_deps[key]):
            print("  %s -> <%s>" % (k, value))


def print_tree(import_graph):
    def _print_tree(root, indent=0):
        if root in seen:
            return
        if not is_source_node(root):
            return
        seen.add(root)
        print('  '*indent + import_graph.format(root))
        for _, v in import_graph.graph.out_edges([root]):
            _print_tree(v, indent=indent+2)

    seen = set()
    for root in nx.topological_sort(import_graph.graph):
        if not import_graph.graph.in_edges([root]):
            import_graph._print_tree(root)


def print_topological_sort(import_graph):
    for node in nx.topological_sort(import_graph.graph):
        if is_source_node(node):
            print(import_graph.format(node))


def formatted_deps_list(import_graph):
    out = []
    for node, deps in import_graph.deps_list():
        out.append('source: ' + import_graph.format(node))
        if deps:
          out.append('deps:')
          for dep in deps:
              out.append('  ' + import_graph.format(dep))
    return '\n'.join(out)
