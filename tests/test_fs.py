"""Tests for fs.py."""

import unittest

from importlab import fs
from importlab import utils

FILES = {
        "a.py": "contents of a",
        "b.py": "contents of b",
        "foo/c.py": "contents of c",
        "foo/d.py": "contents of d",
        "bar/e.py": "contents of e"
}


class TestStoredFileSystem(unittest.TestCase):
    """Tests for StoredFileSystem."""

    def setUp(self):
        self.fs = fs.StoredFileSystem(FILES)

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
        for f in FILES:
            self.tempdir.create_file(f, FILES[f])
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


class LowercasingFileSystem(fs.RemappingFileSystem):
    """Remapping file system subclass for tests."""

    def map_path(self, path):
        return path.lower()


class TestRemappingFileSystem(unittest.TestCase):
    """Tests for RemappingFileSystem."""

    def setUp(self):
        self.tempdir = utils.Tempdir()
        self.tempdir.setup()
        for f in FILES:
            self.tempdir.create_file(f, FILES[f])
        self.fs = LowercasingFileSystem(
                fs.OSFileSystem(self.tempdir.path))

    def tearDown(self):
        self.tempdir.teardown()

    def testIsFile(self):
        self.assertTrue(self.fs.isfile("A.py"))
        self.assertTrue(self.fs.isfile("FOO/c.py"))
        self.assertFalse(self.fs.isfile("foO/B.py"))

    def testIsDir(self):
        self.assertTrue(self.fs.isdir("fOO"))
        self.assertTrue(self.fs.isdir(""))
        self.assertFalse(self.fs.isdir("FOO/C.PY"))
        self.assertFalse(self.fs.isdir("a.PY"))


class TestPYIFileSystem(unittest.TestCase):
    """Tests for PYIFileSystem (also tests ExtensionRemappingFileSystem)."""

    def setUp(self):
        self.tempdir = utils.Tempdir()
        self.tempdir.setup()
        for f in FILES:
            self.tempdir.create_file(f + "i", FILES[f])
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

    def testFullPath(self):
        self.assertEqual(self.fs.refer_to("foo/c.py"),
                         self.tempdir["foo/c.pyi"])


if __name__ == "__main__":
    unittest.main()
