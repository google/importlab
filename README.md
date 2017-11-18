## importlab - https://github.com/google/importlab/

Importlab is a build system for Python that automatically infers dependencies.

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

For example, if you have http://github.com/google/pytype installed, you can do

```
importlab -m pytype ./
```

to run static analysis on all your code.
