import os
import sys

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


def check_python_exe(args):
    error = []
    required = args.python_version
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
