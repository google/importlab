import imp
import os
import sys
import textwrap

from . import utils

DEFAULT = {
    'projects': [],
    'deps': [],
    'output_dir': 'importlab_output',
    'python_version': '3.6'
}


class Config(object):
    __slots__ = 'projects', 'deps', 'output_dir', 'python_version'

    def __init__(self):
        for k, v in DEFAULT.items():
            setattr(self, k, v)

    def _validate_keys(self, consts):
        valid = set(DEFAULT.keys())
        invalid = set(consts.keys()) - valid
        if invalid:
            err = '''
                Invalid config variables: {}
                Valid options are: {}

                To generate a complete sample config file, run:
                  importlab --generate-config sample.cfg
            '''.format(', '.join(invalid), ', '.join(valid))
            print(textwrap.dedent(err))
            sys.exit(0)

    def read_from_file(self, path):
        path = utils.expand_path(path)
        mod = imp.load_source('config_file', path)
        consts = {k: v for k, v in mod.__dict__.items()
                  if not k.startswith('__')}
        self._validate_keys(consts)
        for k in DEFAULT.keys():
            setattr(self, k, consts.get(k, DEFAULT[k]))
        cwd = os.path.dirname(path)
        self.projects = utils.expand_paths(self.projects, cwd)
        self.deps = utils.expand_paths(self.deps, cwd)
        self.output_dir = utils.expand_path(self.output_dir, cwd)

    def make_pythonpath(self):
        return ':'.join(self.projects + self.deps)

    def show(self):
        for k in DEFAULT.keys():
            print('%s = %r' % (k, getattr(self, k)))


DUMMY_CONFIG = '''
    # NOTE: All relative paths are relative to the location of this file.

    # Python version ('major.minor')
    python_version = '3.6'

    # Dependencies within these directories will be checked for type errors.
    projects = [
      "/path/to/project",
    ]

    # Dependencies within these directories will have type inference
    # run on them, but will not be checked for errors.
    deps = [
      "/path/to/project",
    ]

    # All importlab output goes here.
    output_dir = "importlab_output"
'''


def generate_default(filename):
    if os.path.exists(filename):
        print('Not overwriting existing file: %s' % filename)
        sys.exit(0)
    config = textwrap.dedent(DUMMY_CONFIG)
    with open(filename, 'w') as f:
        f.write(config)
