"""Tests for resolve.py."""

import unittest

from importlab import fs
from importlab import parsepy
from importlab import resolve
from importlab import utils


FILES = {
        "a.py": "contents of a",
        "b.py": "contents of b",
        "foo/c.py": "contents of c",
        "foo/d.py": "contents of d",
        "bar/e.py": "contents of e",
        "baz/__init__.py": "contents of init"
}


class TestResolver(unittest.TestCase):
    """Tests for Resolver."""

    def setUp(self):
        self.path = [fs.StoredFileSystem(FILES)]

    def testResolveWithFilesystem(self):
        imp = parsepy.ImportStatement("a")
        r = resolve.Resolver(self.path, "b.py")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.Local))
        self.assertEqual(f.fs, self.path[0])
        self.assertEqual(f.path, "a.py")
        self.assertEqual(f.module_name, "a")

    def testResolveTopLevel(self):
        imp = parsepy.ImportStatement("a")
        r = resolve.Resolver(self.path, "b.py")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "a.py")
        self.assertEqual(f.module_name, "a")

    def testResolvePackageFile(self):
        imp = parsepy.ImportStatement("foo.c")
        r = resolve.Resolver(self.path, "b.py")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "foo/c.py")
        self.assertEqual(f.module_name, "foo.c")

    def testResolveSamePackageFile(self):
        imp = parsepy.ImportStatement(".c")
        r = resolve.Resolver(self.path, "foo/d.py")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "foo/c.py")

    def testResolveParentPackageFile(self):
        imp = parsepy.ImportStatement("..a")
        r = resolve.Resolver(self.path, "foo/d.py")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "a.py")
        self.assertTrue(isinstance(f, resolve.Relative))
        self.assertEqual(f.module_name, "..a")

    def testResolveSiblingPackageFile(self):
        imp = parsepy.ImportStatement("..bar.e")
        r = resolve.Resolver(self.path, "foo/d.py")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "bar/e.py")
        self.assertEqual(f.module_name, "..bar.e")

    def testResolveInitFile(self):
        imp = parsepy.ImportStatement("baz")
        r = resolve.Resolver(self.path, "b.py")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "baz/__init__.py")
        self.assertEqual(f.module_name, "baz")

    def testResolveInitFileRelative(self):
        imp = parsepy.ImportStatement("..baz")
        r = resolve.Resolver(self.path, "foo/d.py")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.Relative))
        self.assertEqual(f.path, "baz/__init__.py")
        self.assertEqual(f.module_name, "..baz")

    def testResolveModuleFromFile(self):
        # from foo import c
        imp = parsepy.ImportStatement("foo.c", is_from=True)
        r = resolve.Resolver(self.path, "x.py")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "foo/c.py")
        self.assertEqual(f.module_name, "foo.c")

    def testResolveSymbolFromFile(self):
        # from foo.c import X
        imp = parsepy.ImportStatement("foo.c.X", is_from=True)
        r = resolve.Resolver(self.path, "x.py")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "foo/c.py")
        self.assertEqual(f.module_name, "foo.c")

    def testOverrideSource(self):
        imp = parsepy.ImportStatement("foo.c", source="/system/c.py")
        r = resolve.Resolver(self.path, "x.py")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "foo/c.py")
        self.assertEqual(f.module_name, "foo.c")

    def testFallBackToSource(self):
        imp = parsepy.ImportStatement("f", source="/system/f.py")
        r = resolve.Resolver(self.path, "x.py")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.System))
        self.assertEqual(f.path, "/system/f.py")
        self.assertEqual(f.module_name, "f")

    def testGetPyFromPycSource(self):
        # Override a source pyc file with the corresponding py file if it exists
        # in the native filesystem.
        with utils.Tempdir() as d:
            py_file = d.create_file('f.py')
            pyc_file = d.create_file('f.pyc')
            imp = parsepy.ImportStatement("f", source=pyc_file)
            r = resolve.Resolver(self.path, "x.py")
            f = r.resolve_import(imp)
            self.assertEqual(f.path, py_file)
            self.assertEqual(f.module_name, "f")

    def testPycSourceWithoutPy(self):
        imp = parsepy.ImportStatement("f", source="/system/f.pyc")
        r = resolve.Resolver(self.path, "x.py")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "/system/f.pyc")
        self.assertEqual(f.module_name, "f")

    def testResolveBuiltin(self):
        imp = parsepy.ImportStatement("sys")
        r = resolve.Resolver(self.path, "x.py")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.Builtin))
        self.assertEqual(f.path, "sys.so")
        self.assertEqual(f.module_name, "sys")


if __name__ == "__main__":
    unittest.main()
