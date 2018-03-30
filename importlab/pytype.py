"""Pytype integration."""

import os

from . import runner
from . import utils

def filename_to_module_name(filename):
    if os.path.dirname(filename).startswith(os.pardir):
      # Don't try to infer a module name for filenames starting with ../
      return None
    return filename.replace(os.sep, ".")


class Runner(object):
    def __init__(self, imports, env):
      self.imports = imports
      self.env = env
      cfg = env.config
      self.output_dir = cfg.output_dir
      self.deps = cfg.deps
      self.projects = cfg.projects
      self.system_env = {
          b'TYPESHED_HOME': env.typeshed_location.encode('utf-8')
      }
      self.pyi_dir = os.path.join(self.output_dir, 'pyi')
      try:
          os.makedirs(self.output_dir)
      except:
          pass
      self.log_file = os.path.join(self.output_dir, 'pytype.log')
      self.logger = utils.setup_logging('pytype', self.log_file)


    def infer_module_name(self, filename):
        filename, _ = os.path.splitext(filename)
        # We want '' in our lookup path, but we don't want it for prefix tests.
        for path in filter(bool, self.env.pythonpath):
            path = os.path.abspath(path)
            if not path.endswith(os.sep):
                path += os.sep
            if filename.startswith(path):
                filename = filename[len(path):]
                return (path, filename_to_module_name(filename))
        # We have not found filename relative to path.
        return '', filename_to_module_name(filename)

    def run_pytype(self, filename, root, report_errors=True):
        path, module_name = self.infer_module_name(filename)
        target = os.path.relpath(filename, path)
        out = os.path.join(self.pyi_dir, target + 'i')
        err = os.path.join(self.pyi_dir, target + '.errors')
        in_projects = any(path.startswith(d) for d in self.projects)
        in_deps = any(path.startswith(d) for d in self.deps)
        if in_deps and not in_projects:
            report_errors = False
        if not report_errors:
          print('  %s*' % out)
        else:
          print('  %s' % out)
        try:
            os.makedirs(os.path.dirname(out))
        except:
            pass
        pytype_exe = 'pytype'
        run_cmd = [
            pytype_exe,
            '-P', self.pyi_dir,
            '-V', self.env.python_version_string,
            '-o', out,
            '--quick',
            '--module-name', module_name
        ]
        if not report_errors:
            run_cmd += ['--no-report-errors']
        run_cmd = run_cmd + [filename]
        self.logger.info('Running: ' + ' '.join(run_cmd))
        run = runner.BinaryRun(run_cmd, env=self.system_env)
        try:
            returncode, _, stderr = run.communicate()
        except OSError:
            self.logger.error('Cannot run pytype.')
            return
        if returncode:
            print('    errors written to:', err)
            error = stderr.decode('utf-8')
            with open(err, 'w') as f:
                f.write(error)
            if not self.env.args.quiet:
                print(error)
            # Log as WARNING since this is not an error in importlab.
            self.logger.warning(error)


    def run(self):
      root = self.imports.find_root()
      deps = list(self.imports.sorted_source_files())
      print('Writing logs to:', self.log_file)
      print()
      print('Generating %d targets' % sum(len(x) for x in deps))
      self.logger.info('------------- Starting importlab run. -------------')
      self.logger.info('source tree:\n' + self.imports.formatted_deps_list())
      for files in deps:
          if len(files) == 1:
              self.run_pytype(files[0], root)
          else:
              for f in files:
                  self.run_pytype(f, root, report_errors=False)
              for f in files:
                  self.run_pytype(f, root, report_errors=True)
