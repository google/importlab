import collections

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

    def get_file_deps(self, filename):
        r = resolve.Resolver(self.path, filename)
        imports = parsepy.scan_file(filename)
        return [imported_filename
                for imported_filename in r.resolve_all(imports)
                if not imported_filename.endswith(".so")]

    def add_file(self, filename):
        for imported_filename in self.get_file_deps(filename):
            self.deps[filename].add(imported_filename)

    def add_file_recursive(self, filename):
        queue = collections.deque([filename])
        while queue:
            filename = queue.popleft()
            deps = self.get_file_deps(filename)
            for f in deps:
                self.deps[filename].add(f)
                if not f in self.deps and f.endswith(".py"):
                    queue.append(f)

    def print_edges(self):
        keys = self.deps.keys()
        prefix = os.path.commonprefix(keys)
        if not os.path.isdir(prefix):
            prefix = os.path.dirname(prefix)

        print prefix
        for key in sorted(keys):
            for value in sorted(self.deps[key]):
                k = os.path.relpath(key, prefix)
                if value.startswith(self.typeshed_location):
                    v = "[%s]" % os.path.relpath(value, self.typeshed_location)
                else:
                    v = os.path.relpath(value, prefix)
                print "  %s -> %s" % (k, v)

    def print_tree(self):
       pass
