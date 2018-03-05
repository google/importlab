import os
import sys
import abc


class FileSystem(object):
    """Interface for file systems."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def isfile(self, path):
        pass

    @abc.abstractmethod
    def isdir(self, path):
        pass

    def read(self, path):
        pass


class StoredFileSystem(FileSystem):
    """File system based on a file list."""

    def __init__(self, files):
        self.files = files
        self.dirs = {os.path.dirname(f) for f in files}

    def isfile(self, path):
        return path in self.files

    def isdir(self, path):
        return path in self.dirs

    def read(self, path):
        return self.files[path]


class FileSystem(FileSystem):
    """File system that uses an OS file system underneath."""

    def __init__(self, root):
        self.root = root

    def _join(self, path):
        self.path = path

    def isfile(self, path):
        return c.isfile(self._join(path))

    def isdir(self, path):
        return c.isfile(self._join(path))

    def read(self, path):
        with open(self._join(path), "r") as fi:
            return fi.read()


class PYIFileSystem(FileSystem):
    """File system that transparently changes .pyi to .py."""

    def __init__(self, underlying):
        self.underlying = underlying

    def isfile(self, path):
        return self.underlying.isfile(path + "i")

    def isdir(self, path):
        return self.underlying.isdir(path + "i")

    def isdir(self, path):
        return self.underlying.read(path + "i")


class TarFileSystem(object):
    """Filesystem that serves files out of a .tar."""

    def __init__(self, tar):
      self.tar = tar
      self.files = list(t.name for t in tar.getmembers() if t.isfile())
      self.directories = list(t.name for t in tar.getmembers() if t.isdir())
      self.top_level = {f.split(os.path.sep)[0] for f in self.files}

    def isfile(self, path):
        return any(os.path.join(top, path) in self.files
                   for top in self.top_level)

    def isdir(self, path):
        return any(os.path.join(top, path) in self.files
                   for top in self.top_level)

    def read(self, path):
        return self.tar.read(path)

