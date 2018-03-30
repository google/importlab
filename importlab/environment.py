import os
import sys

from . import fs
from . import runner


def check_pytype():
    if not runner.can_run('pytype', '-h'):
        print('Cannot run pytype. Check that it is installed and in your path')
        sys.exit(1)


def check_python_version(exe, required):
    try:
        # python --version outputs to stderr for earlier versions
        _, out, err = runner.BinaryRun([exe, '--version']).communicate()
        version = out or err
        version = version.decode('utf-8')
        if version.startswith('Python %s' % required):
            return True, exe
        else:
            return False, version.rstrip()
    except OSError:
        return False, 'Could not run'


def check_python_exe(required):
    error = []
    for exe in ['python', 'python%s' % required]:
        valid, out = check_python_version(exe, required)
        if valid:
            return out
        else:
            error += ['%s: %s' % (exe, out)]
    print('Could not find a valid python%s interpreter in path:' % required)
    print('--------------------------------------------------------')
    print('\n'.join(error))
    sys.exit(1)


def get_typeshed_location(args):
    arg = args.typeshed_location
    env = os.environ.get('TYPESHED_HOME', None)
    ret = arg or env or ''
    if not os.path.isdir(os.path.join(ret, 'stdlib')):
        print('Cannot find a valid typeshed installation.')
        print('Searched in:')
        print('  --typeshed-location argument: ', arg)
        print('  TYPESHED_HOME environment variable: ', env)
        sys.exit(1)
    return ret


def split_version(version):
   return [int(v) for v in version.split('.')]


class Environment(object):
    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.typeshed_location = get_typeshed_location(self.args)
        self.python_version_string = args.python_version
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
        major, minor = self.python_version
        subdirs = ["stdlib/%d" % major,
                   "stdlib/2and3",
                  ]
        if major == 3:
          for i in range(0, minor + 1):
            # iterate over 3.0, 3.1, 3.2, ...
            subdirs.append("stdlib/3.%d" % i)
        out = []
        for subdir in subdirs:
            path = os.path.join(self.typeshed_location, subdir)
            d = fs.PYIFileSystem(fs.OSFileSystem(path))
            out.append(d)
        return out


