"""Pytype integration."""

import os
import re
import subprocess
import sys

class BinaryRun(object):
    def __init__(self, args, dry_run=False, env=None):
        self.args = args
        self.results = None

        if dry_run:
            self.results = (0, '', '')
        else:
            if env is not None:
                full_env = os.environ.copy()
                full_env.update(env)
            else:
                full_env = None
            self.proc = subprocess.Popen(
                self.args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=full_env)

    def communicate(self):
        if self.results:
            return self.results

        stdout, stderr = self.proc.communicate()
        self.results = self.proc.returncode, stdout, stderr
        return self.results


def can_run(path, exe, *args):
    exe = os.path.join(path, exe)
    try:
        BinaryRun([exe] + list(args)).communicate()
        return True
    except OSError:
        return False


def filename_to_module_name(filename):
    if os.path.dirname(filename).startswith(os.pardir):
      # Don't try to infer a module name for filenames starting with ../
      return None
    return filename.replace(os.sep, ".")


class Runner(object):
  def __init__(self, imports, args):
    self.imports = imports
    self.args = args
    if 'pythonpath' in args:
      self.pythonpath = args['pythonpath'].split(':')
    else:
      self.pythonpath = [imports.find_root()]

  def infer_module_name(self, filename):
      filename, _ = os.path.splitext(filename)
      # We want '' in our lookup path, but we don't want it for prefix tests.
      for path in filter(bool, self.pythonpath):
          path = os.path.abspath(path)
          if not path.endswith(os.sep):
              path += os.sep
          if filename.startswith(path):
              filename = filename[len(path):]
              return (path, filename_to_module_name(filename))
      # We have not found filename relative to path.
      return '', filename_to_module_name(filename)

  def run_pytype(self, filename, root, quick=False):
      path, module_name = self.infer_module_name(filename)
      out = os.path.relpath(filename, path)
      out = os.path.join('pyi', out + 'i')
      if quick:
        print("  %s*" % out)
      else:
        print("  %s" % out)
      try:
          os.makedirs(os.path.dirname(out))
      except:
          pass
      pytype_exe = 'pytype'
      if not can_run('', pytype_exe, '-h'):
          print('Cannot find pytype in path.')
          return 0, 0

      run_cmd = [
          pytype_exe,
          '-P', 'pyi',
          '-V', self.args['python_version'],
          '-o', out,
          '--module-name', module_name
      ]
      if quick:
          run_cmd += ['--quick']
      print(" ".join(run_cmd))
      run = BinaryRun(run_cmd + [filename])
      returncode, _, stderr = run.communicate()
      if returncode:
        print(stderr.decode("utf-8"))

  def run(self):
    root = self.imports.find_root()
    deps = list(self.imports.deps_list())
    print("Generating %d targets" % sum(len(x) for x in deps))
    for files in deps:
        if len(files) == 1:
            self.run_pytype(files[0], root)
        else:
            for f in files:
                self.run_pytype(f, root, quick=True)
            for f in files:
                self.run_pytype(f, root, quick=False)
