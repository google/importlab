import imp
import os
import sys
import textwrap

from . import utils


class Config(object):
    def __init__(self):
        self.projects = None
        self.deps = None
        self.output_dir = 'importlab_output'

    def _validate_keys(self, consts):
        valid = {'projects', 'deps', 'output_dir'}
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
        projects = consts.get('projects', [])
        deps = consts.get('deps', [])
        output_dir = consts.get('output_dir', None)
        cwd = os.path.dirname(utils.expand_path(path))
        self.projects = utils.expand_paths(projects, cwd)
        self.deps = utils.expand_paths(deps, cwd)
        if output_dir:
            self.output_dir = utils.expand_path(output_dir, cwd)

    def make_pythonpath(self):
        return ':'.join(self.projects + self.deps)


DUMMY_CONFIG = '''
    # NOTE: All relative paths are relative to the location of this file.

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
