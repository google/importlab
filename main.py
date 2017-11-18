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

"""importlab executable."""

import os
import sys

import argparse
import parsepy
import resolve
import tarfile
import utils


def parse_args():
    parser = argparse.ArgumentParser()
    #parser.add_argument('filenames', metavar='filename', type=str, nargs='+',
    #                    help='input file(s)')
    parser.add_argument('--tree', dest='tree', action='store_true',
                        default=False,
                        help='')
    parser.add_argument('-P', dest='pythonpath', action='store',
                        default=None,
                        help='PYTHONPATH')
    parser.add_argument('-t', dest='tarfile', action='store',
                        default=None,
                        help='PYTHONPATH')
    return parser.parse_args()


def read_tar_gz(archive_filename):
    tar = tarfile.open(archive_filename)
    fs = utils.FileSystem()
    fs.attach(utils.TarFileSystem(tar))
    fs.attach(utils.PYIFileSystem("../typeshed"))
    for m in tar.getmembers():
      if m.isfile() and m.name.endswith(".py"):
        _, filename = m.name.split(os.path.sep, 1)
        data = tar.extractfile(m).read()
        r = resolve.Resolver(fs, filename)
        for imported_filename in r.resolve_all(parsepy.scan_string(data)):
          pass  # print imported_filename


def main():
    args = parse_args()
    if False and args.filenames:
      for filename in args.filenames:
        r = resolve.Resolver(utils.OSFileSystem(), filename, args.pythonpath)
        for imported_filename in r.resolve_all(parsepy.scan_file(filename)):
          if not imported_filename.endswith(".so"):
            print filename, imported_filename
    elif args.tarfile:
      read_tar_gz(args.tarfile)


if __name__ == "__main__":
  sys.exit(main())
