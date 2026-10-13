#!/usr/bin/env python3
"""Unit tests for the archived list-surface evidence binding guard.

The guard exists because two page-pattern ledger entries once cited a mutable
``.runtime/final-acceptance/list-surface-structure.json`` path as ``316/316 gated``
after that path had been overwritten by a payment.request create/edit run
(``records 12/12``, ``gated 0/0``) — and because the guard itself read that
machine-local file, so it could not run at all on a checkout that lacked it.

Claims now bind to a tracked, hash-verified archive. The tests lock the accepted
direction (an archived identity that supports the claim) and every unsupported
binding: unarchived path, overwritten local copy, non-surface schema,
gates-nothing document, count mismatch, no path at all. They also lock
machine-independence: an archived claim with no local copy still resolves.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/verify/list_surface_evidence_binding_guard.py"
SPEC = importlib.util.spec_from_file_location("list_surface_evidence_binding_guard", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SURFACE_SCHEMA = MODULE.SURFACE_SCHEMA
ARCHIVE_RELATIVE = MODULE.ARCHIVE_RELATIVE


def surface_document(passed: int, total: int, schema: str = SURFACE_SCHEMA) -> dict:
    return {
        "schema": schema,
        "summary": {"gated": {"passed": passed, "total": total, "failed": total - passed}},
    }


class ListSurfaceEvidenceBindingGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.index = self.root / "docs/frontend_productization/rendering-detail"
        self.index.mkdir(parents=True)
        self._saved_root = MODULE.ROOT
        MODULE.ROOT = self.root

    def tearDown(self) -> None:
        MODULE.ROOT = self._saved_root
        self._tmp.cleanup()

    # -- fixtures -----------------------------------------------------------
    def _write_surface(self, relative: str, passed: int, total: int, schema: str = SURFACE_SCHEMA) -> None:
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(surface_document(passed, total, schema)), encoding="utf-8")

    def _archive_entry(self, relative: str, sha: str | None = None, schema: str = SURFACE_SCHEMA,
                       passed: int = 108, total: int = 108) -> dict:
        target = self.root / relative
        if sha is not None:
            digest = sha
        elif target.is_file():
            digest = MODULE.sha256(target)
        else:
            digest = "f" * 64
        return {
            "artifact": relative,
            "sha256": digest,
            "bytes": target.stat().st_size if target.is_file() else 0,
            "schema": schema,
            "gated": {"passed": passed, "total": total, "failed": total - passed},
        }

    def _write_archive(self, entries: list[dict]) -> None:
        target = self.root / ARCHIVE_RELATIVE
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps({"schema": MODULE.ARCHIVE_SCHEMA, "entries": entries}), encoding="utf-8"
        )

    def _write_ledger(self, claim: str, name: str = "ledger.json") -> None:
        (self.index / name).write_text(json.dumps({"evidence": claim}), encoding="utf-8")

    # -- accepted direction -------------------------------------------------
    def test_repository_index_is_bound_to_supporting_evidence(self) -> None:
        # The repository index must resolve against the real tree, not the fixture.
        MODULE.ROOT = self._saved_root
        self.assertEqual(MODULE.audit(), [])

    def test_supported_claim_passes(self) -> None:
        relative = ".runtime/final-acceptance/list-surface-all-deadbeef.json"
        self._write_surface(relative, 108, 108)
        self._write_archive([self._archive_entry(relative)])
        self._write_ledger(
            f"Bound evidence: {relative} gates 108/108 checks over 1440/390 x normal/batch/empty"
        )
        self.assertEqual(MODULE.audit(self.index), [])

    def test_archived_claim_resolves_without_a_local_copy(self) -> None:
        # Machine independence: the archived identity adjudicates even when the
        # working path is absent, so no executor's leftover file is required.
        relative = ".runtime/final-acceptance/list-surface-all-deadbeef.json"
        self._write_archive([self._archive_entry(relative, sha="a" * 64)])
        self._write_ledger(f"Bound evidence: {relative} gates 108/108 checks")
        self.assertEqual(MODULE.audit(self.index), [])

    # -- rejected direction -------------------------------------------------
    def test_overwritten_local_copy_is_rejected(self) -> None:
        # The exact real defect: the path exists but now holds another run's data.
        relative = ".runtime/final-acceptance/list-surface-structure.json"
        self._write_archive([self._archive_entry(relative, sha="b" * 64)])
        self._write_surface(relative, 0, 0)
        self._write_ledger(f"Bound evidence: {relative} gates 316/316 checks")
        problems = MODULE.audit(self.index)
        self.assertTrue(any("was overwritten after archiving" in problem for problem in problems), problems)

    def test_unarchived_path_is_rejected(self) -> None:
        relative = ".runtime/final-acceptance/list-surface-structure.json"
        self._write_surface(relative, 108, 108)
        self._write_archive([self._archive_entry(".runtime/final-acceptance/other.json", sha="a" * 64)])
        self._write_ledger(f"Bound evidence: {relative} gates 108/108 checks")
        problems = MODULE.audit(self.index)
        self.assertTrue(
            any("cites no artifact bound to an archived identity" in problem for problem in problems),
            problems,
        )

    def test_gates_nothing_document_is_rejected(self) -> None:
        relative = ".runtime/final-acceptance/list-surface-structure.json"
        self._write_surface(relative, 0, 0)
        self._write_archive([self._archive_entry(relative, passed=0, total=0)])
        self._write_ledger(f"Bound evidence: {relative} gates 108/108 checks")
        problems = MODULE.audit(self.index)
        self.assertTrue(any("gates nothing" in problem for problem in problems), problems)

    def test_count_mismatch_is_rejected(self) -> None:
        relative = ".runtime/final-acceptance/list-surface-all-deadbeef.json"
        self._write_surface(relative, 50, 50)
        self._write_archive([self._archive_entry(relative, passed=50, total=50)])
        self._write_ledger(f"Bound evidence: {relative} gates 108/108 checks")
        problems = MODULE.audit(self.index)
        self.assertTrue(any("does not match the archived" in problem for problem in problems), problems)

    def test_claim_without_artifact_path_is_rejected(self) -> None:
        self._write_archive([self._archive_entry(".runtime/final-acceptance/x.json", sha="c" * 64)])
        self._write_ledger("Observed 108/108 gated during closure")
        problems = MODULE.audit(self.index)
        self.assertTrue(any("names no artifact path" in problem for problem in problems), problems)

    def test_archive_entry_with_a_non_surface_schema_is_a_manifest_problem(self) -> None:
        relative = ".runtime/final-acceptance/other.json"
        self._write_archive([self._archive_entry(relative, schema="something.else.v1")])
        problems = MODULE.audit(self.index)
        self.assertTrue(any("does not declare" in problem for problem in problems), problems)

    def test_a_duplicated_archive_artifact_is_a_manifest_problem(self) -> None:
        relative = ".runtime/final-acceptance/dup.json"
        entry = self._archive_entry(relative, sha="d" * 64)
        self._write_archive([entry, dict(entry)])
        problems = MODULE.audit(self.index)
        self.assertTrue(any("more than once" in problem for problem in problems), problems)

    def test_a_missing_archive_refuses(self) -> None:
        self._write_ledger("Bound evidence: .runtime/final-acceptance/x.json gates 108/108 checks")
        with self.assertRaises(MODULE.BindingError):
            MODULE.audit(self.index)

    def test_cli_reports_failure_for_unbound_index(self) -> None:
        relative = ".runtime/final-acceptance/list-surface-structure.json"
        self._write_archive([self._archive_entry(relative, sha="e" * 64)])
        self._write_surface(relative, 0, 0)
        self._write_ledger(f"Bound evidence: {relative} gates 316/316 checks")
        self.assertEqual(MODULE.main([str(self.index)]), 2)


if __name__ == "__main__":
    unittest.main()
