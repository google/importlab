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
import sys
import os

import fs
import parsepy
import resolve


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', metavar='filename', type=str, nargs='+',
                        help='input file(s)')
    parser.add_argument('--tree', dest='tree', action='store_true',
                        default=False,
                        help='')
    parser.add_argument('-p', "--pythonpath", dest='pythonpath', action='store',
                        default='',
                        help='PYTHONPATH')
    parser.add_argument('-t', "--tarfile", dest='tarfile', action='store',
                        default=None,
                        help='PYTHONPATH')
    return parser.parse_args()


def main():
    args = parse_args()
    path = [fs.OSFileSystem(path) for path in args.pythonpath.split(".")]
    for filename in args.filenames:
      r = resolve.Resolver(path, filename)
      for imported_filename in r.resolve_all(parsepy.scan_file(filename)):
        if not imported_filename.endswith(".so"):
          print filename, "->", imported_filename


if __name__ == "__main__":
  sys.exit(main())
