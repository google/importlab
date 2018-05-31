# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Logic for resolving import paths."""

import logging
import os

from . import import_finder
from . import utils


class ImportException(ImportError):
    def __init__(self, module_name):
        super(ImportException, self).__init__(module_name)
        self.module_name = module_name


class ResolvedFile(object):
    def __init__(self, path, module_name):
        self.path = path
        self.module_name = module_name

    def is_extension(self):
        return self.path.endswith('.so')

    @property
    def package_name(self):
        f, _ = os.path.splitext(self.path)
        if f.endswith('__init__'):
            return self.module_name
        else:
            return self.module_name[:self.module_name.rfind('.')]

    @property
    def short_path(self):
        # TODO: We really need to know the module name of the including file
        # (which is not always available at this point) to correctly compute
        # this for relative imports. However, this is why we do not cache this
        # in a member variable - callers should be able to set self.module_name
        # based on the parent file, and then have short_path work correctly.
        parts = self.path.split(os.path.sep)
        n = self.module_name.count('.')
        if parts[-1] == '__init__.py':
            n += 1
        parts = parts[-(n+1):]
        return os.path.join(*parts)


class Direct(ResolvedFile):
    """Files added directly as arguments."""
    def __init__(self, path, module_name=''):
        # We do not necessarily have a module name for a directly added file.
        super(Direct, self).__init__(path, module_name)


class Builtin(ResolvedFile):
    """Imports that are resolved via python's builtins."""
    def is_extension(self):
        return True


class System(ResolvedFile):
    """Imports that are resolved by python."""
    pass


class Local(ResolvedFile):
    """Imports that are found in a local pythonpath."""
    def __init__(self, path, module_name, fs):
        super(Local, self).__init__(path, module_name)
        self.fs = fs


class Relative(ResolvedFile):
    """Imports that are found relative to another file."""
    pass


def convert_to_path(name):
    """Converts ".module" to "./module", "..module" to "../module", etc."""
    if name.startswith('.'):
        remainder = name.lstrip('.')
        dot_count = (len(name) - len(remainder))
        prefix = '../'*(dot_count-1)
    else:
        remainder = name
        dot_count = 0
        prefix = ''
    filename = prefix + os.path.join(*remainder.split('.'))
    return (filename, dot_count)


def infer_module_name(filename, fspath):
    """Convert a python filename to a module relative to pythonpath."""
    filename, ext = os.path.splitext(filename)
    if not ext == '.py':
        return ''
    for path in fspath:
        root = getattr(path, 'root', None)
        if not root:
            continue
        if filename.startswith(root):
            short_name = filename[len(root) + 1:]
            return short_name.replace(os.path.sep, '.')
    else:
        # We have not found filename relative to anywhere in pythonpath.
        return ''


def get_absolute_name(package, relative_name):
    """Joins a package name and a relative name.

    Args:
      package: A dotted name, e.g. foo.bar.baz
      relative_name: A dotted name with possibly some leading dots, e.g. ..x.y

    Returns:
      The relative name appended to the parent's package, after going up one
      level for each leading dot.
        e.g. foo.bar.baz + ..hello.world -> foo.hello.world
      relative_name if it does not start with a dot
      None if the relative name has too many leading dots.
    """
    path = package.split('.') if package else []
    name = relative_name.lstrip('.')
    ndots = len(relative_name) - len(name)
    if ndots > len(path):
        return None
    prefix = ''.join([p + '.' for p in path[:len(path) + 1 - ndots]])
    return prefix + name


class Resolver:
    def __init__(self, fs_path, current_filename, current_module=None):
        if current_module:
            assert isinstance(current_module, ResolvedFile)
        self.fs_path = fs_path
        self.current_filename = current_filename
        self.current_module = current_module
        self.current_directory = os.path.dirname(current_filename)

    def _find_file(self, fs, name):
        init = os.path.join(name, '__init__.py')
        py = name + '.py'
        for x in [init, py]:
            if fs.isfile(x):
                return fs.refer_to(x)
        return None

    def resolve_import(self, item):
        """Simulate how Python resolves imports.

        Returns the filename of the source file Python would load
        when processing a statement like 'import name' in the module
        we're currently under.

        Args:
            item: An instance of ImportItem

        Returns:
            A filename

        Raises:
            ImportException: If the module doesn't exist.
        """
        name = item.name
        # The last part in `from a.b.c import d` might be a symbol rather than a
        # module, so we try a.b.c and a.b.c.d as names.
        short_name = None
        if item.is_from and not item.is_star:
            short_name = name[:name.rfind('.')]

        if import_finder.is_builtin(name):
            filename = name + '.so'
            return Builtin(filename, name)

        filename, level = convert_to_path(name)
        if level:
            # This is a relative import; we need to resolve the filename
            # relative to the importing file path.
            filename = os.path.normpath(
                os.path.join(self.current_directory, filename))

        files = [(name, filename)]
        if short_name:
            short_filename = os.path.dirname(filename)
            files.append((short_name, short_filename))

        for fs in self.fs_path:
            for module_name, path in files:
                f = self._find_file(fs, path)
                if not f:
                    continue
                if item.is_relative():
                    if self.current_module:
                        module_name = get_absolute_name(
                                self.current_module.package_name, module_name)
                    # TODO(martindemello): If we do have a current_module,
                    # perhaps we should return a module of the same type as
                    # current_module rather than Relative.
                    return Relative(f, module_name or '')
                else:
                    return Local(f, module_name, fs)

        # If the module isn't found in the explicit pythonpath, see if python
        # itself resolved it.
        if item.source:
            prefix, ext = os.path.splitext(item.source)
            mod_name = name
            # We need to check for importing a symbol here too.
            if short_name:
                mod = prefix.replace(os.path.sep, '.')
                mod = utils.strip_suffix(mod, '.__init__')
                if not mod.endswith(name) and mod.endswith(short_name):
                    mod_name = short_name

            if ext == '.pyc':
                pyfile = prefix + '.py'
                if os.path.exists(pyfile):
                    return System(pyfile, mod_name)
            return System(item.source, mod_name)

        raise ImportException(name)

    def resolve_all(self, import_items):
        """Resolves a list of imports.

        Yields filenames.
        """
        for import_item in import_items:
            try:
                yield self.resolve_import(import_item)
            except ImportException as err:
                logging.info('unknown module %s', err.module_name)
