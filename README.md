## importlab - https://github.com/google/importlab/

Importlab is a tool for Python that automatically infers dependencies.

Importlab works with static analysis tools that process one file at a time,
ensuring that a file's dependencies are analysed before it is.

The initial release of importlab works with
[pytype](https://github.com/google/pytype); integration with other tools is
planned for future versions.

(This is not an official Google product.)

## License
Apache 2.0

## Installation

```
git clone https://github.com/google/importlab.git
cd importlab
python3 setup.py install
```

## Usage

### Prerequisites
Importlab requires [pytype](https://github.com/google/pytype) and [typeshed](https://github.com/python/typeshed) to be locally available.

* `pytype`: Needs to be installed and in your executable path. (Note that
  `pytype` depends on Python 2.7, whereas `importlab` depends on Python 3.6,
  making them difficult to install in the same virtualenv.)
* `typeshed`: Needs to be checked out from git, and pointed to via
  the `TYPESHED_HOME` environment variable, or via the `--typeshed_location`
  argument

### Usage

Importlab takes one or more python files as arguments, and runs pytype over
them. Typechecking errors and `.pyi` files are generated in `./importlab_output/`

```
usage: importlab [-h] [--tree] [-V PYTHON_VERSION] [-T TYPESHED_LOCATION]
                 [--quiet] [--cfg CFG] [--generate-config GENERATE_CONFIG]
                 [filename [filename ...]]

positional arguments:
  filename              input file(s)

optional arguments:
  -h, --help            show this help message and exit
  --tree                Display import tree.
  -V PYTHON_VERSION, --python-version PYTHON_VERSION
                        Python version for the project you're analyzing
  -T TYPESHED_LOCATION, --typeshed-location TYPESHED_LOCATION
                        Location of typeshed. Will use the TYPESHED_HOME
                        environment variable if this argument is not
                        specified.
  --quiet               Don't print errors to stdout.
  --cfg CFG             Configuration file.
  --generate-config GENERATE_CONFIG
                        Write out a dummy configuration file.
```

### Config File

Importlab uses a config file to set up per-project input, dependency and output
directories. The config file is a python file defining configuration variables
as top-level constants.

Start off by generating a sample config file:
```
$ importlab --generate-config my-project.cfg
```

Now customise each section based on your local setup. Directories may be
relative to the location of the config file, which is useful if you want to
check in the config file as part of your project.

Here is an example of a filled-in config file for a project with files split
across two directories, `~/code/foo` and `~/code/bar`, and the config file at
`~/code/foo/foo.cfg`

```
# NOTE: All relative paths are relative to the location of this file.

# Dependencies within these directories will be checked for type errors.
projects = [
  ".",
  "~/code/bar"
]

# Dependencies within these directories will have type inference
# run on them, but will not be checked for errors.
deps = [
  "~/code/some_dependency",
  "/usr/local/lib/python3.6/dist-packages/project.egg/"
]

# All importlab output goes here.
output_dir = "importlab_output"
```

### Example

A complete set of steps to check out the `requests` project and run `pytype` over it. We will assume a ~/github toplevel directory in which everything gets checked out:

```
# Install pytype
$ cd ~/github
$ git clone https://github.com/google/pytype
$ cd pytype
$ sudo python2 setup.py install
$ cd ..

# Install typeshed
$ git clone https://github.com/python/typeshed
$ export TYPESHED_HOME=`pwd`/typeshed

# Install importlab
$ git clone https://github.com/google/importlab.git
$ cd importlab
$ sudo python3 setup.py install
$ cd ..

# Check out and analyze requests
$ git clone https://github.com/requests/requests
$ cd requests
# Generate a config file
$ importlab --generate-config requests.conf
# and edit it to point to your toplevel directory
$ cat requests.conf

  # Dependencies within these directories will be checked for type errors.
  projects = [
    "."  # "~/github/requests" would work too
  ]

  # Dependencies within these directories will have type inference
  # run on them, but will not be checked for errors.
  deps = [
  ]

$ importlab -V 2.7 --cfg=requests.conf requests/*.py
```

This will generate the following tree:

```
importlab_output/
├── pyi
│   └── requests
│       ├── auth.pyi
│       ├── certs.pyi
│       ├── compat.py.errors
│       ├── compat.pyi
│       ├── cookies.py.errors
│       ├── cookies.pyi
│       ├── ...
└── pytype.log
```

So for example to see the pytype errors generated for `requests/compat.py`, run

```
$ cat importlab_output/pyi/requests/compat.py.errors
```

or to see all the errors at once,

```
less importlab_output/pytype.log
```

You will notice a set of import errors for urllib3; this can be fixed by
checking out the urllib3 source as well, and adding it to your config file.
Since we are analysing `requests`, and not `urllib3`, we add it to `deps` rather
than `projects`:

```
$ cd ..
$ git clone https://github.com/shazow/urllib3
$ cd requests

# edit file
$ cat requests.conf
  # Dependencies within these directories will be checked for type errors.
  projects = [
    "."
  ]

  # Dependencies within these directories will have type inference
  # run on them, but will not be checked for errors.
  deps = [
    "~/github/urllib3"
  ]

# run importlab again
$ importlab -V 2.7 --cfg=requests.conf requests/*.py
```

## Roadmap

* `Makefile` generation, to take advantage of `make`'s incremental update and
  parallel execution features

* `libimportlab`, to let other projects use importlab as an internal library

* Integration with other static analysis tools
