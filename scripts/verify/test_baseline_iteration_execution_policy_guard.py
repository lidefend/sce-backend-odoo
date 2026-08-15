#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import baseline_iteration_execution_policy_guard as guard


class BaselineIterationExecutionPolicyGuardTests(unittest.TestCase):
    def fixture(self, root: Path) -> None:
        for relative, fragments in guard.DOCUMENT_REQUIREMENTS.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join((guard.MARKER, *fragments)), encoding="utf-8")
        for relative, targets in guard.MAKE_TARGET_REQUIREMENTS.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(f"{target}:" for target in targets), encoding="utf-8")

    def test_complete_policy_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            self.assertEqual(guard.validate(root), [])

    def test_missing_rule_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "AGENTS.md"
            path.write_text(guard.MARKER, encoding="utf-8")
            self.assertTrue(any("missing locked rule" in error for error in guard.validate(root)))

    def test_missing_authoritative_target_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            path = root / "make/runtime_ops.mk"
            path.write_text("acceptance.module.upgrade:\n", encoding="utf-8")
            self.assertTrue(any("authoritative target missing" in error for error in guard.validate(root)))


if __name__ == "__main__":
    unittest.main()
