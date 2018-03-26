import imp
import collections
import os
import sys
import textwrap

from . import utils


class Config(object):
    def __init__(self):
        self.projects = None
        self.deps = None

    def read_from_file(self, path):
        mod = imp.load_source('config_file', path)
        consts = {k: v for k, v in mod.__dict__.items()
                  if not k.startswith('__')}
        self.projects = utils.expand_paths(consts['projects'])
        self.deps = utils.expand_paths(consts['deps'])

    def make_pythonpath(self):
        return ':'.join(self.projects + self.deps)


DUMMY_CONFIG = '''
    # Dependencies within these directories will be checked for type errors.
    projects = [
      "/path/to/project",
    ]

    # Dependencies within these directories will have type inference
    # run on them, but will not be checked for errors.
    deps = [
      "/path/to/project",
    ]
'''


def generate_default(filename):
    if os.path.exists(filename):
        print('Not overwriting existing file: %s' % filename)
        sys.exit(0)
    config = textwrap.dedent(DUMMY_CONFIG)
    with open(filename, 'w') as f:
        f.write(config)
