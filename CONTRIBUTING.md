Want to contribute? Great! First, read this page (including the small print at
the end).

### Before you contribute
Before we can use your code, you must sign the
[Google Individual Contributor License Agreement](https://developers.google.com/open-source/cla/individual?csw=1)
(CLA), which you can do online. The CLA is necessary mainly because you own the
copyright to your changes, even after your contribution becomes part of our
codebase, so we need your permission to use and distribute your code. We also
need to be sure of various other things -- for instance that you'll tell us if you
know that your code infringes on other people's patents. You don't have to sign
the CLA until after you've submitted your code for review and a member has
approved it, but you must do it before we can put your code into our codebase.
Before you start working on a larger contribution, you should get in touch with
us first through the issue tracker with your idea so that we can help out and
possibly guide you. Coordinating up front makes it much easier to avoid
frustration later on.

### Code reviews
All submissions, including submissions by project members, require review. We
use Github pull requests for this purpose.

### Releasing to PyPI

To release to PyPI:

1. (Optional) We recommend that you release from within a virtualenv:
   ```console
   $ python3 -m venv .venv_release
   $ source .venv_release/bin/activate
   ```
1. Make sure that `wheel` and `twine` are installed:
   ```console
   $ pip install wheel twine
   ```
1. Navigate into the top-level `importlab` directory and build a source
   distribution and a wheel:
   ```console
   $ cd importlab
   $ python3 setup.py sdist bdist_wheel
   ```
   The build command puts the distributions in a `dist` subdirectory and also
   creates `build` and `importlab.egginfo` subdirectories as side effects.
1. Upload the distributions to (Test)PyPI:
   ```console
   $ twine upload --repository testpypi dist/*
   ```
   Remove the `--repository testpypi` to upload to PyPI proper.
1. (Optional) If you've uploaded to TestPyPI, you can install your new version
   for testing like so:
   ```console
   $ pip install -U --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple importlab
   ```
   If you've uploaded to PyPI proper, install with `pip install -U importlab`
   as usual.
1. Clean up the subdirectories created by the build command:
   ```console
   $ rm -rf build/ dist/ importlab.egg-info/
   ```

### The small print
Contributions made by corporations are covered by a different agreement than
the one mentioned above; they're covered by the the Software Grant and
Corporate Contributor License Agreement.
