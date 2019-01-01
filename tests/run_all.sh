# This script must be run from the directory above tests.
set -ev
python -m tests.test_fs
python -m tests.test_graph
python -m tests.test_import_finder
python -m tests.test_output
python -m tests.test_parsepy
python -m tests.test_resolve
python -m tests.test_utils
