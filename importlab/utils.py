"""Utility functions."""

import logging
import os


def setup_logging(name, log_file, level=logging.INFO):
    formatter = logging.Formatter(
            fmt='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


def expand_path(path):
    return os.path.realpath(os.path.expanduser(path))


def expand_paths(paths):
  return [expand_path(x) for x in paths]
