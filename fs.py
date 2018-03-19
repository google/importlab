import abc
import os
import sys
import tarfile


class FileSystem(object):
    """Interface for file systems."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def isfile(self, path):
        """Is this a file?"""
        pass

    @abc.abstractmethod
    def isdir(self, path):
        """Is this a directory?"""
        pass

    @abc.abstractmethod
    def read(self, path):
        """Read a file."""
        pass

    @abc.abstractmethod
    def refer_to(self, path):
        """Get a fully qualified path for the given path."""
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

    def refer_to(self, path):
        return path


class OSFileSystem(FileSystem):
    """File system that uses an OS file system underneath."""

    def __init__(self, root):
        assert root is not None
        self.root = root

    def _join(self, path):
        return os.path.join(self.root, path)

    def isfile(self, path):
        assert path is not None
        return os.path.isfile(self._join(path))

    def isdir(self, path):
        assert path is not None
        return os.path.isdir(self._join(path))

    def read(self, path):
        with open(self._join(path), "r") as fi:
            return fi.read()

    def refer_to(self, path):
        return self._join(path)


class PYIFileSystem(FileSystem):
    """File system that transparently changes .pyi to .py."""

    def __init__(self, underlying):
        self.underlying = underlying

    def isfile(self, path):
        return self.underlying.isfile(path + "i")

    def isdir(self, path):
        return self.underlying.isdir(path + "i")

    def read(self, path):
        return self.underlying.read(path + "i")

    def refer_to(self, path):
        return self.underlying.refer_to(path + "i")


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
        return self.tar.extractfile(path).read()

    def refer_to(self, path):
        return "tar:" + path

    @staticmethod
    def read_tarfile(archive_filename):
        tar = tarfile.open(archive_filename)
        return TarFileSystem(tar)
