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
python setup.py install
```

## Usage

### Prerequisites
Importlab [pytype](https://github.com/google/pytype) and [typeshed](https://github.com/python/typeshed) to be locally available.

* `pytype`: Needs to be installed and in your executable path. (Note that
  `pytype` depends on Python 2.7, whereas `importlab` depends on Python 3.6,
  making them difficult to install in the same virtualenv.)
* `typeshed`: Needs to be checked out from git, and pointed to via
  the `TYPESHED_HOME` environment variable, or via the --typeshed_location
  argument

### Usage

Importlab takes one or more python files as arguments, and runs pytype over
them. Typechecking errors and `.pyi` files are generated in `./importlab_output/`

```
importlab [-h] [--tree] [-P PYTHON_VERSION] [-p PYTHONPATH]
                 [-T TYPESHED_LOCATION]
                 filename [filename ...]

positional arguments:
  filename              input file(s)

optional arguments:
  -h, --help            show this help message and exit
  --tree                Display import tree.
  -P PYTHON_VERSION, --python-version PYTHON_VERSION
                        Python version for the project you"re analyzing
  -p PYTHONPATH, --pythonpath PYTHONPATH
                        PYTHONPATH
  -T TYPESHED_LOCATION, --typeshed-location TYPESHED_LOCATION
                        Location of typeshed. Will use the TYPESHED_HOME
                        environment variable if this argument is not
                        specified.
```

### Example

To check out the `requests` project and run `pytype` over it:

```
$ export TYPESHED_HOME=/path/to/typeshed
$ git clone https://github.com/requests/requests
$ importlab -P 3.6 --pythonpath=./requests requests/requests/*.py
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
