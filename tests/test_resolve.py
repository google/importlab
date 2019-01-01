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
        "baz/__init__.py": "contents of init",
        "baz/f.py": "contents of f"
}

PYI_FILES = {
        "x.pyi": "contents of x",
        "y.pyi": "contents of y",
}


class TestResolver(unittest.TestCase):
    """Tests for Resolver."""

    def setUp(self):
        self.py_fs = fs.StoredFileSystem(FILES)
        self.pyi_fs = fs.PYIFileSystem(fs.StoredFileSystem(PYI_FILES))
        self.path = [self.pyi_fs, self.py_fs]

    def make_resolver(self, filename, module_name):
        module = resolve.Local(filename, module_name, self.py_fs)
        return resolve.Resolver(self.path, module)

    def testResolveWithFilesystem(self):
        imp = parsepy.ImportStatement("a")
        r = self.make_resolver("b.py", "b")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.Local))
        self.assertEqual(f.fs, self.py_fs)
        self.assertEqual(f.path, "a.py")
        self.assertEqual(f.module_name, "a")

    def testResolveTopLevel(self):
        imp = parsepy.ImportStatement("a")
        r = self.make_resolver("b.py", "b")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "a.py")
        self.assertEqual(f.module_name, "a")

    def testResolvePackageFile(self):
        imp = parsepy.ImportStatement("foo.c")
        r = self.make_resolver("b.py", "b")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "foo/c.py")
        self.assertEqual(f.module_name, "foo.c")

    def testResolveSamePackageFile(self):
        imp = parsepy.ImportStatement(".c")
        r = self.make_resolver("foo/d.py", "foo.d")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "foo/c.py")

    def testResolveParentPackageFile(self):
        imp = parsepy.ImportStatement("..a")
        r = self.make_resolver("foo/d.py", "foo.d")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "a.py")
        self.assertTrue(isinstance(f, resolve.Local))
        self.assertEqual(f.module_name, "..a")

    def testResolveParentPackageFileWithModule(self):
        imp = parsepy.ImportStatement("..a")
        r = self.make_resolver("foo/d.py", "bar.foo.d")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "a.py")
        self.assertTrue(isinstance(f, resolve.Local))
        self.assertEqual(f.module_name, "bar.a")

    def testResolveSiblingPackageFile(self):
        # This is an invalid import, since we are trying to resolve a relative
        # import beyond the top-level package. The file resolver does not figure
        # out that we are moving beyond the top-level, but the module name does
        # not get qualified and remains relative.
        imp = parsepy.ImportStatement("..bar.e")
        r = self.make_resolver("foo/d.py", "foo.d")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "bar/e.py")
        self.assertEqual(f.module_name, "..bar.e")

    def testResolveInitFile(self):
        imp = parsepy.ImportStatement("baz")
        r = self.make_resolver("b.py", "b")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "baz/__init__.py")
        self.assertEqual(f.module_name, "baz")

    def testResolveInitFileRelative(self):
        imp = parsepy.ImportStatement("..baz")
        r = self.make_resolver("foo/d.py", "foo.d")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.Local))
        self.assertEqual(f.path, "baz/__init__.py")
        self.assertEqual(f.module_name, "..baz")

    def testResolveRelativeFromInitFileWithModule(self):
        parent = resolve.Direct("baz/__init__.py", "baz")
        imp = parsepy.ImportStatement(".f")
        r = resolve.Resolver(self.path, parent)
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.Local))
        self.assertEqual(f.path, "baz/f.py")
        self.assertEqual(f.module_name, "baz.f")

    def testResolveRelativeSymbol(self):
        # importing the Symbol object from baz/__init__.py while in baz/f.py
        parent = resolve.Direct("baz/f.py", "baz.f")
        imp = parsepy.ImportStatement(".Symbol", is_from=True)
        r = resolve.Resolver(self.path, parent)
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.Local))
        self.assertEqual(f.path, "baz/__init__.py")
        self.assertEqual(f.module_name, "baz")

    def testResolveModuleFromFile(self):
        # from foo import c
        imp = parsepy.ImportStatement("foo.c", is_from=True)
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "foo/c.py")
        self.assertEqual(f.module_name, "foo.c")

    def testResolveSymbolFromFile(self):
        # from foo.c import X
        imp = parsepy.ImportStatement("foo.c.X", is_from=True)
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "foo/c.py")
        self.assertEqual(f.module_name, "foo.c")

    def testOverrideSource(self):
        imp = parsepy.ImportStatement("foo.c", source="/system/c.py")
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "foo/c.py")
        self.assertEqual(f.module_name, "foo.c")

    def testFallBackToSource(self):
        imp = parsepy.ImportStatement("f", source="/system/f.py")
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.System))
        self.assertEqual(f.path, "/system/f.py")
        self.assertEqual(f.module_name, "f")

    def testResolveSystemSymbol(self):
        imp = parsepy.ImportStatement("argparse.ArgumentParser",
                                      source="/system/argparse.pyc",
                                      is_from=True)
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.System))
        self.assertEqual(f.module_name, "argparse")

    def testResolveSystemSymbolNameClash(self):
        # from foo.foo import foo
        imp = parsepy.ImportStatement("foo.foo.foo",
                                      source="/system/bar/foo/foo.pyc",
                                      is_from=True)
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.System))
        self.assertEqual(f.module_name, "foo.foo")

    def testResolveSystemFileNameClash(self):
        # `import a` in a.py should get the system a.py
        sys_file = "/system/a.py"
        imp = parsepy.ImportStatement("a", source=sys_file)
        r = self.make_resolver("a.py", "a")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.System))
        self.assertEqual(f.path, sys_file)
        self.assertEqual(f.module_name, "a")

    def testResolveSystemInitFile(self):
        # from foo.foo import foo
        imp = parsepy.ImportStatement("foo.bar.X",
                                      source="/system/foo/bar/__init__.pyc",
                                      is_from=True)
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.System))
        self.assertEqual(f.module_name, "foo.bar")

    def testResolveSystemPackageDir(self):
        with utils.Tempdir() as d:
            py_file = d.create_file("foo/__init__.py")
            imp = parsepy.ImportStatement("foo",
                                          source=d["foo"],
                                          is_from=True)
            r = self.make_resolver("x.py", "x")
            f = r.resolve_import(imp)
            self.assertTrue(isinstance(f, resolve.System))
            self.assertEqual(f.module_name, "foo")
            self.assertEqual(f.path, py_file)

    def testGetPyFromPycSource(self):
        # Override a source pyc file with the corresponding py file if it exists
        # in the native filesystem.
        with utils.Tempdir() as d:
            py_file = d.create_file("f.py")
            pyc_file = d.create_file("f.pyc")
            imp = parsepy.ImportStatement("f", source=pyc_file)
            r = self.make_resolver("x.py", "x")
            f = r.resolve_import(imp)
            self.assertEqual(f.path, py_file)
            self.assertEqual(f.module_name, "f")

    def testPycSourceWithoutPy(self):
        imp = parsepy.ImportStatement("f", source="/system/f.pyc")
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "/system/f.pyc")
        self.assertEqual(f.module_name, "f")

    def testResolveBuiltin(self):
        imp = parsepy.ImportStatement("sys")
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.Builtin))
        self.assertEqual(f.path, "sys.so")
        self.assertEqual(f.module_name, "sys")

    def testResolveStarImport(self):
        # from foo.c import *
        imp = parsepy.ImportStatement("foo.c", is_from=True, is_star=True)
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "foo/c.py")
        self.assertEqual(f.module_name, "foo.c")

    def testResolveStarImportBuiltin(self):
        imp = parsepy.ImportStatement("sys", is_from=True, is_star=True)
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.Builtin))
        self.assertEqual(f.path, "sys.so")
        self.assertEqual(f.module_name, "sys")

    def testResolveStarImportSystem(self):
        imp = parsepy.ImportStatement("f", is_from=True, is_star=True,
                                      source="/system/f.py")
        r = self.make_resolver("x.py", "x")
        f = r.resolve_import(imp)
        self.assertEqual(f.path, "/system/f.py")
        self.assertEqual(f.module_name, "f")

    def testResolvePyiFile(self):
        imp = parsepy.ImportStatement("x")
        r = self.make_resolver("b.py", "b")
        f = r.resolve_import(imp)
        self.assertTrue(isinstance(f, resolve.Local))
        self.assertEqual(f.fs, self.pyi_fs)
        self.assertEqual(f.path, "x.pyi")
        self.assertEqual(f.module_name, "x")

    def testResolveSystemRelative(self):
        with utils.Tempdir() as d:
            os_fs = fs.OSFileSystem(d.path)
            fspath = [os_fs]
            d.create_file("foo/x.py")
            d.create_file("foo/y.py")
            imp = parsepy.ImportStatement(".y")
            module = resolve.System(d["foo/x.py"], "foo.x")
            r = resolve.Resolver(fspath, module)
            f = r.resolve_import(imp)
            self.assertEqual(f.path, d["foo/y.py"])
            self.assertTrue(isinstance(f, resolve.System))
            self.assertEqual(f.module_name, "foo.y")

    def testResolveRelativeInNonPackage(self):
        r = self.make_resolver("a.py", "a")
        imp = parsepy.ImportStatement(".b", is_from=True)
        with self.assertRaises(resolve.ImportException):
            r.resolve_import(imp)


class TestResolverUtils(unittest.TestCase):
    """Tests for utility functions."""

    def testInferModuleName(self):
        with utils.Tempdir() as d:
            os_fs = fs.OSFileSystem(d.path)
            fspath = [os_fs]
            py_file = d.create_file("foo/bar.py")
            self.assertEqual(
                    resolve.infer_module_name(py_file, fspath),
                    "foo.bar")
            # Standalone Python scripts often don't have extensions.
            self.assertEqual(
                    resolve.infer_module_name(d["foo/baz"], fspath),
                    "foo.baz")
            self.assertEqual(
                    resolve.infer_module_name(d["random/src.py"], fspath),
                    "random.src")
            self.assertEqual(
                    resolve.infer_module_name("/some/random/file", fspath),
                    "")

    def testInferInitModuleName(self):
        with utils.Tempdir() as d:
            os_fs = fs.OSFileSystem(d.path)
            fspath = [os_fs]
            py_file = d.create_file("foo/__init__.py")
            self.assertEqual(
                    resolve.infer_module_name(py_file, fspath),
                    "foo")

    def testGetAbsoluteName(self):
        test_cases = [
                ("x.y", "a.b", "x.y.a.b"),
                ("", "a.b", "a.b"),
                ("x.y", ".a.b", "x.y.a.b"),
                ("x.y", "..a.b", "x.a.b"),
                ("x.y", "...a.b", "...a.b"),
        ]
        for parent, name, expected in test_cases:
            self.assertEqual(
                    resolve.get_absolute_name(parent, name),
                    expected)


if __name__ == "__main__":
    unittest.main()
