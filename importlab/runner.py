import os
import subprocess


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


def can_run(exe, *args):
    try:
        BinaryRun([exe] + list(args)).communicate()
        return True
    except OSError:
        return False


def run_py_file(version, path, *args):
    exe = 'python%d.%d' % version
    args = [exe, path] + list(args)
    r = BinaryRun(args)
    return r.communicate()
