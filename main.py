#!/usr/bin/env python3.6

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
import graph
import parsepy
import pytype
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


def process_pythonpath(pythonpath):
    dirs = pythonpath.split(os.pathsep)
    out = []
    for d in dirs:
        d = os.path.expanduser(d)
        d = os.path.realpath(d)
        out.append(d)
    return ":".join(out)


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


def recursive_import(args, path, typeshed_location):
    imports = graph.ImportGraph(path, typeshed_location)
    for filename in args.filenames:
        imports.add_file_recursive(os.path.abspath(filename))
    imports.build()
    imports.print_deps_list()
    return imports


def main():
    args = parse_args()
    args.pythonpath = process_pythonpath(args.pythonpath)
    typeshed_location = args.typeshed or os.path.join(os.path.abspath(
        os.path.dirname(__file__)), "typeshed")
    python_version = [int(v) for v in args.python_version.split(".")]
    path = [fs.OSFileSystem(path) for path in args.pythonpath.split(os.pathsep)]
    path += make_typeshed_path(typeshed_location, python_version)
    #---------------------------------------
    imports = recursive_import(args, path, typeshed_location)
    runner = pytype.Runner(imports, {
        'python_version': args.python_version,
        'pythonpath': args.pythonpath,
    })
    runner.run()


if __name__ == "__main__":
  sys.exit(main())
