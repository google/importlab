import collections
import resolve
import parsepy
import os

class File(object):
    """A file in the file system. E.g. "/foo/bar/baz.py".

    In the presence of symlinks and hard links, a file may exist in multiple places.
    We do not model that, and instead treat files with different (absolute) paths
    as different.
    """
    __slots__ = [
            "path",  # absolute path, e.g. "/foo/bar/baz.py"
            "modules",  # modules implemented by this file
            "deps",  # files this file depends on
            "rdeps",  # files that depend on us
    ]

    def __init__(self, path):
        self.path = path
        self.modules = []
        self.deps = []
        self.rdeps = []


class Module(object):
    """A Python module. E.g. "foo.bar.baz".

    We treat modules and packages the same. In other words, a file like
    "foo/bar/__init__.py" might represent the module "foo.bar".
    """
    __slots__ = [
            "name",  # name of the module, e.g. "foo.bar.baz"
            "file",  # file defining this module.
    ]


class FileCollection(object):
    """A list of files."""

    def __init__(self, files=()):
        self.files = {f.path: f for f in files}

    def add_file(self, f):
        self.files[f.path] = f

    def __iter__(self):
        return iter(self.files.values())


class ImportGraph(object):
    def __init__(self, path, typeshed_location):
        self.path = path
        self.typeshed_location = typeshed_location
        self.deps = collections.defaultdict(set)
        self.broken_deps = collections.defaultdict(set)

    def get_file_deps(self, filename):
        r = resolve.Resolver(self.path, filename)
        resolved = []
        unresolved = []
        for imp in parsepy.scan_file(filename):
            try:
                f = r.resolve_import(imp)
                if not f.endswith(".so"):
                    resolved.append(os.path.abspath(f))
            except resolve.ImportException:
                unresolved.append(imp)
        return (resolved, unresolved)

    def add_file(self, filename):
        resolved, unresolved = self.get_file_deps(filename)
        for imported_filename in resolved:
            self.deps[filename].add(imported_filename)
        for imp in unresolved:
            self.broken_deps[filename].add(imp)

    def add_file_recursive(self, filename):
        queue = collections.deque([filename])
        seen = set()
        while queue:
            filename = queue.popleft()
            deps, broken = self.get_file_deps(filename)
            for f in broken:
                self.broken_deps[filename].add(f)
            for f in deps:
                self.deps[filename].add(f)
                if (not f in self.deps and
                    not f in seen and
                    f.endswith(".py")):
                    queue.append(f)
                    seen.add(f)

    def inspect_edges(self):
        keys = self.deps.keys()
        prefix = os.path.commonprefix(keys)
        if not os.path.isdir(prefix):
            prefix = os.path.dirname(prefix)

        print prefix
        for key in sorted(keys):
            k = os.path.relpath(key, prefix)
            for value in sorted(self.deps[key]):
                if value.startswith(self.typeshed_location):
                    v = "[%s]" % os.path.relpath(value, self.typeshed_location)
                else:
                    v = os.path.relpath(value, prefix)
                print "  %s -> %s" % (k, v)
            for value in sorted(self.broken_deps[key]):
                print "  %s -> <%s>" % (k, value)

    def print_tree(self):
       pass
