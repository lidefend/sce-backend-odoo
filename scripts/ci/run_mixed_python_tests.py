#!/usr/bin/env python3
"""Run specific pure-Python test files with the correct module identity.

``python3 <file> -v`` imports the file as ``__main__`` and emits
``__main__.Class.method`` identities, and ``python3 -m unittest <file>`` first
imports the package ``tests/__init__.py`` (which may import Odoo and fail
offline).  Both are wrong for the changed-test-coverage verifier.

Discover each file with its own directory as both start and top-level dir so
the module is named ``<filename>``, the package ``__init__.py`` is never
imported, and the verbose output carries ``<filename>.Class.method``.

Verbose ``... ok`` text is not a reliable result record: a method docstring
breaks the ``... ok`` suffix onto its own line, and a test that prints or logs
between start and success separates the method identity from ``ok``.  Instead,
every test's full ``test.id()`` (``<filename>.<Class>.<method>``) and its exact
outcome are recorded into one structured ``SC_BACKEND_TEST_RESULTS`` line; the
coverage verifier matches the same identity and never reparses wrapped text.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

RESULTS_MARKER = "SC_BACKEND_TEST_RESULTS="


class _RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes: dict[str, str] = {}

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes[test.id()] = "passed"

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes[test.id()] = "skipped"

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes[test.id()] = "failed"

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes[test.id()] = "error"

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.outcomes[test.id()] = "expected_failure"

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.outcomes[test.id()] = "unexpected_success"


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
    result = unittest.TextTestRunner(verbosity=2, resultclass=_RecordingResult).run(suite)
    marker = {
        "schema": "backend-python-test-results/v1",
        "results": result.outcomes,
        "run": result.testsRun,
        "skipped": len(result.skipped),
        "failures": len(result.failures),
        "errors": len(result.errors),
    }
    print(RESULTS_MARKER + json.dumps(marker, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
