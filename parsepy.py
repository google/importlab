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

from __future__ import google_type_annotations

import collections
import io

import google3

from lib2to3 import pgen2
from lib2to3 import pygram
from lib2to3 import pytree
from lib2to3 import refactor
from lib2to3.pgen2 import parse as parse2to3
from lib2to3.pgen2 import token
from lib2to3.pgen2 import tokenize as tokenize2to3
from lib2to3.pygram import python_symbols

import typing


class ParseError(Exception):
  pass


class ImportStatement(collections.namedtuple(
    "ImportStatement", ["name", "new_name", "is_from", "everything"])):
  """A Python import statement, such as "import foo as bar"."""

  def __new__(cls, name, new_name=None, is_from=False, everything=False):
    """Create a new ImportStatement.

    Args:
      name: Name of the module to be imported. E.g. "sys".
      new_name: What the module is renamed to. The "y" in
        "import x as y".
      is_from: If the last part of the name (the "z" in "x.y.z") can
      be an element within a module, instead of a module itself. Happens
      e.g. for "from sys import argv".
      everything: If this is an import of the form "from x import *".
    Returns:
      A new ImportStatement instance.
    """
    return super(ImportStatement, cls).__new__(
        cls, name, new_name or name, is_from, everything)

  def is_relative(self):
    return self.name.startswith(".")

  def __repr__(self):
    if self.everything:
      assert self.name == self.new_name
      assert self.is_from
      return "from " + self.name + " import *"
    if self.is_from:
      left, right = self.name.rsplit(".", 2)
      module = left + "[." + right + "]"
    else:
      module = self.name
    if self.new_name != self.name:
      return "import " + module + " as " + self.new_name
    else:
      return "import " + module


class Parser(object):
  """Wrapper for lib2to3's Python parser."""

  # Global variable, initialized when first instance is created
  _drivers = None

  def __init__(self):
    if Parser._drivers is None:
      Parser._drivers = {
          "no_print_statement": pgen2.driver.Driver(
              pygram.python_grammar_no_print_statement,
              convert=pytree.convert),
          "print_statement": pgen2.driver.Driver(
              pygram.python_grammar,
              convert=pytree.convert),
      }

  def parse_string(self, code_str):
    """Parse a program string and remove unwanted outer levels in AST."""
    # see lib2to3.tests.support.parse_string -- but we don't do the dedent
    # (support.reformat)
    if not isinstance(code_str, unicode):
      encoding, _ = tokenize2to3.detect_encoding(
          io.BytesIO(code_str).readline)
      code_str = unicode(code_str, encoding)
    features = refactor._detect_future_features(code_str)  # pylint: disable=protected-access
    if "print_function" in features:
      driver = self._drivers["no_print_statement"]
    else:
      driver = self._drivers["print_statement"]
    code_ast = driver.parse_string(code_str + "\n\n", debug=False)
    if code_ast:
      code_ast.parent = None
    return code_ast


def expand_ast(node):
  """Flatten an AST.

  Args:
    node: A lib2to3 AST node.

  Yields:
    One node at a time, for a depth-first preorder traversal.
  """
  yield node
  for c in node.children:
    for x in expand_ast(c):
      yield x


def _parse_as_names(nodes):
  """Parse a list of import_as_name statements.

  Args:
    nodes: Children of an import_from statement.

  Yields:
    Pairs (name, new_name).
    For example, "from abc import x as y, z" will return
    the pairs x, y and z, z. (z is imported as z)
  """
  for symbol in nodes:
    if symbol.type == python_symbols.import_as_names:
      # handle "from abc import a as x, b as y"
      for c in symbol.children:
        if c.type == token.COMMA:
          continue
        if c.type == python_symbols.import_as_name:
          assert c.children[1].value == "as"
          yield (c.children[0], c.children[2])
        else:
          assert c.type == token.NAME
          yield (c, c)
    elif symbol.type == python_symbols.import_as_name:
      assert symbol.children[1].value == "as"
      yield (symbol.children[0], symbol.children[2])
    elif symbol.type == token.NAME:
      yield (symbol, symbol)
    elif symbol.type == token.STAR:
      pass  # handled elsewhere


def _parse_package_name(node):
  """Helper function. Transform a lib2to3 node to a string and an index."""
  package_name = ""
  for i, n in enumerate(node.children[1:]):
    if n.type == token.NAME and n.value == "import":
      break
    elif n.type == token.NAME:
      package_name += n.value
    elif n.type == token.DOT:
      package_name += "."
    elif n.type == python_symbols.dotted_name:
      # support "a . b . c" as well as "a.b.c"
      # TODO(kramm): is . right-binding when it's a seperate token?
      package_name += str(n).replace(" ", "")
  assert node.children[i+1].value == "import"  # pylint: disable=undefined-loop-variable
  return package_name, i  # pylint: disable=undefined-loop-variable


def _parse_import_star(node):
  assert any(symbol.type == token.STAR for symbol in node.children)
  assert node.children[0].value == "from", repr(node)
  package_name, _ = _parse_package_name(node)
  return [ImportStatement(package_name, package_name, everything=True)]


def _parse_import_from(node):
  """Helper function for parsing 'from x import y'."""
  assert node.children[0].value == "from", repr(node)
  package_name, i = _parse_package_name(node)
  prefix = package_name
  if not prefix.endswith("."):
    prefix += "."
  imports = []
  for name_node, new_name in _parse_as_names(node.children[i+2:]):
    name = name_node.value.strip()
    new_name = new_name.value.strip()
    imports.append(ImportStatement(prefix + name, new_name, is_from=True))
  return imports


def _parse_import_name(node):
  """Helper function for parsing 'import x'."""
  assert node.children[0].value == "import", repr(node)
  imp = node.children[1]

  nodes = []
  if imp.type == python_symbols.dotted_as_names:
    # "import a [as x],b [as y],..."
    for ch in imp.children:
      if ch.type in [python_symbols.dotted_as_name,
                     python_symbols.dotted_name,
                     token.NAME]:
        nodes.append(ch)
      elif ch.type == token.COMMA:
        pass
      else:
        raise AssertionError("Unexpected: %r in %r" % (ch, node))
  else:
    # "import a [as b]"
    nodes = [imp]

  for imp in nodes:
    if imp.type == python_symbols.dotted_as_name:
      if len(imp.children) != 3 or imp.children[-2].value != "as":
        raise AssertionError(repr(imp))
      # "a.b.c as d"
      if imp.children[0].type == token.NAME:
        name = imp.children[0].value
      else:
        name = ".".join(ch.value for ch in imp.children[0].children
                        if ch.type == token.NAME)
      new_name = imp.children[-1].value
      yield ImportStatement(name, new_name)
    elif imp.type == python_symbols.dotted_name:
      # "a.b.c"
      name = ".".join(ch.value for ch in imp.children
                      if ch.type == token.NAME)
      yield ImportStatement(name)
    elif imp.type == token.NAME:
      name = imp.value
      yield ImportStatement(name)
    else:
      # "name"
      assert imp.type == token.NAME
      name = imp.value
      yield ImportStatement(name)


def is_import_node(node):
  return node.type in {python_symbols.import_from, python_symbols.import_name}


def parse_import_node(node):
  if node.type == python_symbols.import_name:
    return list(_parse_import_name(node))
  else:
    assert node.type == python_symbols.import_from
    if any(symbol.type == token.STAR for symbol in node.children):
      return _parse_import_star(node)
    else:
      return _parse_import_from(node)


class Module(object):
  """Represent a single Python file, loaded from a specified path."""

  def __init__(self, src):
    """Initialize.

    Args:
      src: The source string
    """
    self.src = src

  @staticmethod
  def main():
    """Generate a module representing a (nameless) script.

    Returns:
      The main module (__main__).

    This module corresponds to the start of execution of any Python
    program.
    """
    return Module("")

  def to_ast(self):
    """Parse this module and return the AST."""
    try:
      return Parser().parse_string(self.src)
    except parse2to3.ParseError as e:
      raise ParseError(e.message)
    except tokenize2to3.TokenError as e:
      raise ParseError(e.message)
    except UnicodeDecodeError as e:
      raise ParseError(e.message)
    except IndentationError as e:
      raise ParseError(e.message)

  def get_imports(self):
    ast = self.to_ast()
    if ast is not None:
      for node in expand_ast(ast):
        if is_import_node(node):
          for n in parse_import_node(node):
            yield n


def scan_string(src):
  return Module(src).get_imports()


def scan_file(filename):
  with open(filename, "rb") as fi:
    return Module(fi.read()).get_imports()
