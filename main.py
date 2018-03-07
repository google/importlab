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

"""main entry point."""

import argparse
import collections
import os
import sys

import fs
import parsepy
import resolve


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", metavar="filename", type=str, nargs="+",
                        help="input file(s)")
    parser.add_argument("--tree", dest="tree", action="store_true",
                        default=False,
                        help="Display import tree.")
    parser.add_argument("-P", "--python-version", dest="python_version", action="store",
                        default="2.7",
                        help="Python version for the project you\"re analyzing")
    parser.add_argument("-p", "--pythonpath", dest="pythonpath", action="store",
                        default="",
                        help="PYTHONPATH")
    parser.add_argument("-T", "--typeshed", dest="typeshed", action="store",
                        default=None,
                        help="Location of typeshed.")
    return parser.parse_args()


def make_typeshed_path(typeshed_location, python_version):
    """Get the names of all modules in typeshed and pytype/pytd/builtins."""
    major = python_version[0]
    subdirs = ["stdlib/%d" % major,
               "stdlib/2and3",
              ]
    if major == 3:
      for i in range(0, python_version[1] + 1):
        # iterate over 3.0, 3.1, 3.2, ...
        subdirs.append("stdlib/3.%d" % i)
    return [fs.PYIFileSystem(fs.OSFileSystem(os.path.join(typeshed_location, subdir)))
            for subdir in subdirs]


class ImportGraph(object):
    def __init__(self, path, typeshed_location):
        self.path = path
        self.typeshed_location = typeshed_location
        self.deps = collections.defaultdict(set)

    def get_file_deps(self, filename):
        r = resolve.Resolver(self.path, filename)
        imports = parsepy.scan_file(filename)
        return [imported_filename
                for imported_filename in r.resolve_all(imports)
                if not imported_filename.endswith(".so")]

    def add_file(self, filename):
        for imported_filename in self.get_file_deps(filename):
            self.deps[filename].add(imported_filename)

    def add_file_recursive(self, filename):
        queue = collections.deque([filename])
        while queue:
            filename = queue.popleft()
            deps = self.get_file_deps(filename)
            for f in deps:
                self.deps[filename].add(f)
                if not f in self.deps and f.endswith(".py"):
                    queue.append(f)

    def print_edges(self):
        keys = self.deps.keys()
        prefix = os.path.commonprefix(keys)
        if not os.path.isdir(prefix):
            prefix = os.path.dirname(prefix)

        print prefix
        for key in sorted(keys):
            for value in sorted(self.deps[key]):
                k = os.path.relpath(key, prefix)
                if value.startswith(self.typeshed_location):
                    v = "[%s]" % os.path.relpath(value, self.typeshed_location)
                else:
                    v = os.path.relpath(value, prefix)
                print "  %s -> %s" % (k, v)

    def print_tree(self):
       pass


def main():
    args = parse_args()
    typeshed_location = args.typeshed or os.path.join(os.path.abspath(
        os.path.dirname(__file__)), "typeshed")
    python_version = [int(v) for v in args.python_version.split(".")]
    path = [fs.OSFileSystem(path) for path in args.pythonpath.split(".")]
    path += make_typeshed_path(typeshed_location, python_version)
    graph = ImportGraph(path, typeshed_location)
    for filename in args.filenames:
        graph.add_file(filename)

    graph.print_edges()



if __name__ == "__main__":
  sys.exit(main())
