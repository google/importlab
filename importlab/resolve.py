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

import os

from . import import_finder


class ImportException(ImportError):
    def __init__(self, module_name):
        super(ImportException, self).__init__(module_name)
        self.module_name = module_name


class ModuleAndDependencies(object):
    def __init__(self, filename):
        self.filename = filename
        self.name, self.ext = os.path.splitext(os.path.basename(self.filename))
        self.directory = os.path.dirname(self.filename)


def convert_to_path(name):
    """Converts ".module" to "./module", "..module" to "../module", etc."""
    if name.startswith('.'):
        remainder = name.lstrip('.')
        dot_count = (len(name) - len(remainder))
        prefix = '../'*(dot_count-1)
    else:
        remainder = name
        prefix = ''
    return prefix + os.path.join(*remainder.split('.'))


class Resolver:
    def __init__(self, fs_path, current_filename):
        self.fs_path = fs_path
        self.current_filename = current_filename
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

        if import_finder.is_builtin(name):
            return name + '.so'

        filename = convert_to_path(name)
        if item.is_relative():
            filename = os.path.normpath(
                os.path.join(self.current_directory, filename))

        # The last part in `from a.b.c import d` might be a symbol rather than a
        # module, so we try both a/b/c/d.py and a/b/c.py
        short_name = None
        if item.is_from:
            short_name = os.path.dirname(filename)

        for fs in self.fs_path:
            f = (self._find_file(fs, filename) or
                 (short_name and self._find_file(fs, short_name)))
            if f:
                return f

        # If the module isn't found in the explicit pythonpath, see if python
        # itself resolved it.
        if item.source:
            prefix, ext = os.path.splitext(item.source)
            if ext == '.pyc':
                pyfile = prefix + '.py'
                if os.path.exists(pyfile):
                    return pyfile
            return item.source

        raise ImportException(name)

    def resolve_all(self, import_items):
        """Resolves a list of imports.

        Yields filenames.
        """
        for import_item in import_items:
            try:
                yield self.resolve_import(import_item)
            except ImportException as err:
                print('unknown module', err.module_name)


def show_import_tree(self, seen=None, indent=0):
    seen = seen or set()
    for imported in self._get_imports():
        if imported.name in seen:
            continue
        seen.add(imported.name)
        try:
            mod = self.resolve_import(imported.name)
            print(' '*(indent*4) + str(imported))
            mod.show_import_tree(seen, indent+1)
        except ImportException:
            # mark import we didn't find with '!'
            print(' '*(indent*4) + '!' + str(imported))
