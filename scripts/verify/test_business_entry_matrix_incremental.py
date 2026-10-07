#!/usr/bin/env python3
"""Focused behaviour tests for the reuse-first business-entry matrix entry.

They lock the evidence-locality contract: the governed Make target forwards
``SC_ACCEPTANCE_OUTPUT_DIR`` even when the caller left it unset, so the entry
must treat an empty or blank value as "unset" and keep writing evidence into the
declared default directory instead of resolving to the repository root
(``Path('') == '.'``) and leaking ``summary.json`` into the worktree.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from scripts.verify import business_entry_matrix_incremental as incremental


class OutputDirResolutionTests(unittest.TestCase):
    def test_missing_env_falls_back_to_the_default_directory(self) -> None:
        self.assertEqual(incremental.resolve_output_dir({}), Path(incremental.DEFAULT_OUTPUT_DIR))

    def test_empty_env_falls_back_to_the_default_directory(self) -> None:
        self.assertEqual(
            incremental.resolve_output_dir({'SC_ACCEPTANCE_OUTPUT_DIR': ''}),
            Path(incremental.DEFAULT_OUTPUT_DIR),
        )

    def test_blank_env_falls_back_to_the_default_directory(self) -> None:
        self.assertEqual(
            incremental.resolve_output_dir({'SC_ACCEPTANCE_OUTPUT_DIR': '   '}),
            Path(incremental.DEFAULT_OUTPUT_DIR),
        )

    def test_explicit_env_is_used_verbatim(self) -> None:
        self.assertEqual(
            incremental.resolve_output_dir({'SC_ACCEPTANCE_OUTPUT_DIR': 'artifacts/x'}),
            Path('artifacts/x'),
        )

    def test_default_directory_is_not_the_repository_root(self) -> None:
        self.assertNotEqual(incremental.resolve_output_dir({}), Path('.'))


if __name__ == '__main__':
    unittest.main()
