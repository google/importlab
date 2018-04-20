import os
import sys

from . import fs
from pytype.tools import runner
from pytype.tools import environment as pytype_env


def split_version(version):
   return [int(v) for v in version.split('.')]


def check_all_or_die(env):
    pytype_env.check_pytype_or_die()
    pytype_env.check_python_exe_or_die(env.python_version_string)


class Environment(object):
    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.typeshed = pytype_env.initialize_typeshed_or_die(self.args)
        self.python_version_string = config.python_version
        self.pythonpath = config.make_pythonpath()
        self.python_version = split_version(self.python_version_string)
        self.path = self._make_path()

    def _make_path(self):
        path = [
            fs.OSFileSystem(path)
            for path in self.pythonpath.split(os.pathsep)]
        path += self._make_typeshed_path()
        return path

    def _make_typeshed_path(self):
        """Get the names of all modules in typeshed and pytype/pytd/builtins."""
        return [fs.PYIFileSystem(fs.OSFileSystem(path))
                for path in self.typeshed.get_paths(self.python_version)]


