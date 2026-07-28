#!/usr/bin/env python3
from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from frontend_release_ci_guard import ROOT, findings


class FrontendReleaseCIGuardTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        (root / ".github/workflows").mkdir(parents=True)
        (root / "config/ci").mkdir(parents=True)
        (root / "make").mkdir(parents=True)
        shutil.copy(ROOT / ".github/workflows/frontend_release_gate.yml", root / ".github/workflows/")
        shutil.copy(ROOT / "config/ci/frontend_release_gate_v1.json", root / "config/ci/")
        shutil.copy(ROOT / "make/runtime_ops.mk", root / "make/")
        return temporary, root

    def test_repository_contract_passes(self):
        self.assertEqual(findings(), [])

    def test_dynamic_matrix_and_duplicate_check_are_rejected(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/frontend_release_gate.yml"
        workflow.write_text(workflow.read_text() + "\n    strategy:\n      matrix: {}\n", encoding="utf-8")
        (root / ".github/workflows/duplicate.yml").write_text(
            "permissions:\n  contents: read\njobs:\n  x:\n    name: frontend_release_gate\n",
            encoding="utf-8",
        )
        errors = findings(root)
        self.assertTrue(any(item.startswith("WORKFLOW_FORBIDDEN:matrix") for item in errors))
        self.assertTrue(any(item.startswith("CHECK_NAME_NOT_UNIQUE") for item in errors))

    def test_continue_on_error_and_historical_download_are_rejected(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        workflow = root / ".github/workflows/frontend_release_gate.yml"
        workflow.write_text(
            workflow.read_text()
            + "\n# continue-on-error: true\n# uses: actions/download-artifact@0000000000000000000000000000000000000000\n",
            encoding="utf-8",
        )
        errors = findings(root)
        self.assertIn("WORKFLOW_FORBIDDEN:continue-on-error:", errors)
        self.assertIn("WORKFLOW_FORBIDDEN:actions/download-artifact", errors)


if __name__ == "__main__":
    unittest.main()
