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
