#!/usr/bin/env python3
"""Focused behaviour tests for the reuse-first business-entry matrix entry.

They lock the evidence-locality contract: the governed Make target forwards
``SC_ACCEPTANCE_OUTPUT_DIR`` even when the caller left it unset, so the entry
must treat an empty or blank value as "unset" and keep writing evidence into the
declared default directory instead of resolving to the repository root
(``Path('') == '.'``) and leaking ``summary.json`` into the worktree.

They also lock the immutability contract: the ledger records the ``summary.json``
each unit was folded from, so the default must be a per-run subdirectory of the
declared location. A fixed default would let a later, narrower run overwrite an
earlier run's evidence and break the ledger's source pointers, which is precisely
the failure a targeted reverification would otherwise cause.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from scripts.verify import business_entry_matrix_incremental as incremental


class OutputDirResolutionTests(unittest.TestCase):
    def test_missing_env_falls_back_under_the_default_directory(self) -> None:
        resolved = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='a,b')
        self.assertEqual(resolved.parent, Path(incremental.DEFAULT_OUTPUT_DIR))

    def test_empty_env_falls_back_under_the_default_directory(self) -> None:
        self.assertEqual(
            incremental.resolve_output_dir({'SC_ACCEPTANCE_OUTPUT_DIR': ''}, stamp='20260101T000000Z', selection='').parent,
            Path(incremental.DEFAULT_OUTPUT_DIR),
        )

    def test_blank_env_falls_back_under_the_default_directory(self) -> None:
        self.assertEqual(
            incremental.resolve_output_dir({'SC_ACCEPTANCE_OUTPUT_DIR': '   '}, stamp='20260101T000000Z', selection='').parent,
            Path(incremental.DEFAULT_OUTPUT_DIR),
        )

    def test_explicit_env_is_used_verbatim(self) -> None:
        self.assertEqual(
            incremental.resolve_output_dir({'SC_ACCEPTANCE_OUTPUT_DIR': 'artifacts/x'}),
            Path('artifacts/x'),
        )

    def test_default_directory_is_not_the_repository_root(self) -> None:
        self.assertNotEqual(incremental.resolve_output_dir({}, stamp='20260101T000000Z'), Path('.'))

    def test_default_is_never_the_shared_directory_itself(self) -> None:
        resolved = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='a,b')
        self.assertNotEqual(resolved, Path(incremental.DEFAULT_OUTPUT_DIR))

    def test_distinct_runs_resolve_to_distinct_directories(self) -> None:
        first = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='a,b')
        second = incremental.resolve_output_dir({}, stamp='20260101T000001Z', selection='a,b')
        self.assertNotEqual(first, second)

    def test_distinct_selections_at_one_stamp_stay_distinct(self) -> None:
        first = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='a')
        second = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='b')
        self.assertNotEqual(first, second)

    def test_recorded_evidence_of_an_earlier_run_is_not_overwritten(self) -> None:
        first = incremental.resolve_output_dir({}, stamp='20260101T000000Z', selection='a,b')
        second = incremental.resolve_output_dir({}, stamp='20260102T000000Z', selection='c')
        self.assertNotEqual(first / 'summary.json', second / 'summary.json')


if __name__ == '__main__':
    unittest.main()
