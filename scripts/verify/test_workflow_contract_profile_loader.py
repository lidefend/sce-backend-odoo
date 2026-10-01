#!/usr/bin/env python3
"""Pin the workflow contract profile loader to a complete, fail-closed read.

The registry mixes inline literals with helper-built entries.  A reader that
only sees the inline half silently shrinks every consumer's scope, so the
loader must evaluate the whole mapping and must refuse -- not truncate -- when
it meets something it cannot read.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from workflow_contract_profile_loader import (
    ProfileSourceError,
    adopted_models,
    declared_methods,
    load_profiles,
)

PROFILE = 'PROFILE_BY_MODEL = {\n    "a.model": {"state_field": "state"},\n}\n'


def _write(source: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    with handle:
        handle.write(source)
    return Path(handle.name)


class WorkflowContractProfileLoaderTest(unittest.TestCase):
    def test_the_real_registry_reads_in_full(self) -> None:
        profiles = load_profiles()
        self.assertEqual(len(profiles), len(adopted_models(profiles)))
        self.assertGreater(len(profiles), 40)

    def test_helper_built_profiles_are_loaded(self) -> None:
        profiles = load_profiles()
        # sc.fund.account.operation arrives through **_confirm_done_profiles((...)), never as an
        # inline literal, so a pattern-matching reader would drop it.
        self.assertIn("sc.fund.account.operation", profiles)
        self.assertIn("state_phase", profiles["sc.fund.account.operation"])

    def test_declared_methods_include_helper_bindings(self) -> None:
        methods = declared_methods(load_profiles())
        self.assertIn("action_submit", methods)
        self.assertIn("action_done", methods)

    def test_a_helper_call_is_evaluated(self) -> None:
        source = (
            "def _profiles(names):\n"
            "    return {n: {'state_field': 'state'} for n in names}\n"
            "\n"
            "PROFILE_BY_MODEL = {**_profiles(('m.one', 'm.two'))}\n"
        )
        profiles = load_profiles(_write(source))
        self.assertEqual(sorted(profiles), ["m.one", "m.two"])

    def test_an_unsupported_expression_is_refused(self) -> None:
        source = (
            "import os\n"
            "PROFILE_BY_MODEL = {k: {'state_field': 'state'} for k in os.environ}\n"
        )
        with self.assertRaises(ProfileSourceError):
            load_profiles(_write(source))

    def test_a_missing_registry_is_refused(self) -> None:
        with self.assertRaises(ProfileSourceError):
            load_profiles(_write("OTHER = {}\n"))

    def test_an_empty_registry_is_refused(self) -> None:
        with self.assertRaises(ProfileSourceError):
            load_profiles(_write("PROFILE_BY_MODEL = {}\n"))

    def test_a_non_profile_entry_is_refused(self) -> None:
        with self.assertRaises(ProfileSourceError):
            load_profiles(_write('PROFILE_BY_MODEL = {"a.model": "not-a-profile"}\n'))


if __name__ == "__main__":
    unittest.main()
