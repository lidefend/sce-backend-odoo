#!/usr/bin/env python3
"""Run specific pure-Python test files with the correct module identity.

``python3 <file> -v`` imports the file as ``__main__`` and emits
``__main__.Class.method`` identities, and ``python3 -m unittest <file>`` first
imports the package ``tests/__init__.py`` (which may import Odoo and fail
offline).  Both are wrong for the changed-test-coverage verifier.

Discover each file with its own directory as both start and top-level dir so
the module is named ``<filename>``, the package ``__init__.py`` is never
imported, and the verbose output carries ``<filename>.Class.method ... ok``.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


def main() -> int:
    files = [Path(f) for f in sys.argv[1:] if str(f).strip()]
    if not files:
        raise SystemExit("no mixed pure-python test files provided")
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for path in files:
        test_dir = str(path.resolve().parent)
        suite.addTests(loader.discover(
            start_dir=test_dir,
            top_level_dir=test_dir,
            pattern=path.name,
        ))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
