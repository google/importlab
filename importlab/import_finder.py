import ast
import csv
import sys

class ImportFinder(ast.NodeVisitor):
    """Walk an AST collecting import statements."""

    def __init__(self):
        # tuples of (name, alias, is_from, is_star)
        self.imports = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append((alias.name, alias.asname, False, False))

    def visit_ImportFrom(self, node):
        module_name = '.'*node.level + (node.module or '')
        for alias in node.names:
            if alias.name == '*':
                self.imports.append((module_name, alias.asname, True, True))
            else:
                if not module_name.endswith('.'):
                    module_name = module_name + '.'
                name = module_name + alias.name
                asname = alias.asname or alias.name
                self.imports.append((name, asname, True, False))


def get_imports(filename):
    with open(filename, "rb") as f:
        src = f.read()
    finder = ImportFinder()
    finder.visit(ast.parse(src))
    return finder.imports


def print_imports(filename):
    """Print imports in csv format to stdout."""
    writer = csv.writer(sys.stdout)
    writer.writerows(get_imports(filename))


if __name__ == "__main__":
    # This is used to parse a file with a different python version, launching a
    # subprocess and communicating with it via reading stdout.
    filename = sys.argv[1]
    print_imports(filename)

