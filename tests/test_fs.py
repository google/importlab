"""Tests for fs.py."""

import unittest

from importlab import fs
from importlab import utils

FILES = [
        ("a.py", "contents of a"),
        ("b.py", "contents of b"),
        ("foo/c.py", "contents of c"),
        ("foo/d.py", "contents of d"),
        ("bar/e.py", "contents of e")
]


class TestStoredFileSystem(unittest.TestCase):
  """Tests for StoredFileSystem."""

  def setUp(self):
      files = ["a.py", "b.py", "foo/c.py", "foo/d.py", "bar/e.py"]
      self.fs = fs.StoredFileSystem({f: True for f in files})

  def testIsFile(self):
      self.assertTrue(self.fs.isfile("a.py"))
      self.assertTrue(self.fs.isfile("foo/c.py"))
      self.assertFalse(self.fs.isfile("foo/b.py"))

  def testIsDir(self):
      self.assertTrue(self.fs.isdir("foo"))
      self.assertTrue(self.fs.isdir(""))
      self.assertFalse(self.fs.isdir("foo/c.py"))
      self.assertFalse(self.fs.isdir("a.py"))

  def testNoTrivialEmptyDir(self):
      f = fs.StoredFileSystem({"foo/a.py": True, "bar/b.py": True})
      self.assertTrue(f.isdir("foo"))
      self.assertTrue(f.isdir("bar"))
      self.assertFalse(f.isdir(""))


class TestOSFileSystem(unittest.TestCase):
  """Tests for OSFileSystem."""

  def setUp(self):
      self.tempdir = utils.Tempdir()
      self.tempdir.setup()
      for f, contents in FILES:
          f = self.tempdir.create_file(f, contents)
      self.fs = fs.OSFileSystem(self.tempdir.path)

  def tearDown(self):
      self.tempdir.teardown()

  def testIsFile(self):
      self.assertTrue(self.fs.isfile("a.py"))
      self.assertTrue(self.fs.isfile("foo/c.py"))
      self.assertFalse(self.fs.isfile("foo/b.py"))

  def testIsDir(self):
      self.assertTrue(self.fs.isdir("foo"))
      self.assertTrue(self.fs.isdir(""))
      self.assertFalse(self.fs.isdir("foo/c.py"))
      self.assertFalse(self.fs.isdir("a.py"))


class TestPyiFileSystem(unittest.TestCase):
  """Tests for OSFileSystem."""

  def setUp(self):
      self.tempdir = utils.Tempdir()
      self.tempdir.setup()
      for f, contents in FILES:
          f = self.tempdir.create_file(f + "i", contents)
      self.fs = fs.PYIFileSystem(
              fs.OSFileSystem(self.tempdir.path))

  def tearDown(self):
      self.tempdir.teardown()

  def testIsFile(self):
      self.assertTrue(self.fs.isfile("a.py"))
      self.assertTrue(self.fs.isfile("foo/c.py"))
      self.assertFalse(self.fs.isfile("foo/b.py"))

  def testIsDir(self):
      self.assertTrue(self.fs.isdir("foo"))
      self.assertTrue(self.fs.isdir(""))
      self.assertFalse(self.fs.isdir("foo/c.py"))
      self.assertFalse(self.fs.isdir("a.py"))


if __name__ == "__main__":
    unittest.main()
