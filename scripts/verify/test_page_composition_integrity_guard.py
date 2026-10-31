#!/usr/bin/env python3
"""Regression tests for page_composition_integrity_guard PC-005 (_text) repair.

These tests lock the P0 fix for the undefined ``_text`` helper: any page with
non-empty ``formStructureContract.slots`` must evaluate without raising
``NameError``. Precise PC-005 PASS/FAIL semantics for multi-slot fields with
ownership are deferred to Phase 4G-02C; here we assert the guard executes and
returns a valid, deterministic report.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/verify/page_composition_integrity_guard.py"
SPEC = importlib.util.spec_from_file_location("page_composition_integrity_guard", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

evaluate = MODULE.evaluate

VALID_STATUSES = {"PASS", "FAIL", "WARNING", "NOT_VERIFIED", "NOT_APPLICABLE"}
AUX_ROLES = ["summary", "context", "relation", "detail", "activity", "audit"]


def _build(slots=None, ownership=None, groups=None, page_class="unclassified_historical", evidence=None):
    page = {
        "model": "payment.request",
        "action_id": 649,
        "view_id": 1773,
        "pageComposition": {"class": page_class},
        "formStructureContract": {"slots": slots if slots is not None else []},
        "fieldGroups": {"groups": groups if groups is not None else []},
        "fieldOwnership": ownership if ownership is not None else {},
    }
    return {
        "repository_sha": "test",
        "contract_version": "2.2.0",
        "page": page,
        "evidence": evidence or {},
    }


def _pc005(report):
    return next(r for r in report["rule_results"] if r["rule_id"] == "PC-005")


def _pc006(report):
    return next(r for r in report["rule_results"] if r["rule_id"] == "PC-006")


class PC005TextRepairTests(unittest.TestCase):
    def test_empty_slots(self):
        report = evaluate(_build(slots=[]))
        self.assertEqual(_pc005(report)["status"], "NOT_VERIFIED")

    def test_single_field_slot(self):
        slots = [{"id": "identity", "role": "identity", "fieldRefs": ["field:project_code"]}]
        report = evaluate(_build(slots=slots))
        self.assertEqual(_pc005(report)["status"], "PASS")

    def test_multiple_slots_each_single_field(self):
        slots = [
            {"id": "identity", "role": "identity", "fieldRefs": ["field:project_code"]},
            {"id": "basic_information", "role": "section", "fieldRefs": ["field:owner_id"]},
        ]
        report = evaluate(_build(slots=slots))
        self.assertEqual(_pc005(report)["status"], "PASS")

    def test_same_field_multiple_slots_without_ownership(self):
        slots = [
            {"id": "identity", "role": "identity", "fieldRefs": ["field:user_id"]},
            {"id": "summary", "role": "summary", "fieldRefs": ["field:user_id"]},
        ]
        report = evaluate(_build(slots=slots, ownership={}))
        self.assertEqual(_pc005(report)["status"], "NOT_VERIFIED")
        self.assertTrue(any("no ownership" in f for f in _pc005(report)["scope"].get("fields", [])))

    def test_invalid_auxiliary_role_fails(self):
        slots = [
            {"id": "identity", "role": "identity", "fieldRefs": ["field:user_id"]},
            {"id": "basic_information", "role": "section", "fieldRefs": ["field:user_id"]},
        ]
        ownership = {"field:user_id": {"ownerSlotRef": "slot:identity", "ownerGroupRef": "group:identity"}}
        report = evaluate(_build(slots=slots, ownership=ownership, evidence={"allowed_slot_roles": AUX_ROLES}))
        # A non-auxiliary second projection must be judged ambiguous (FAIL),
        # regardless of the slot-ref prefix reconciliation deferred to 4G-02C.
        self.assertEqual(_pc005(report)["status"], "FAIL")

    def test_auxiliary_role_executes_without_name_error(self):
        slots = [
            {"id": "identity", "role": "identity", "fieldRefs": ["field:user_id"]},
            {"id": "summary", "role": "summary", "fieldRefs": ["field:user_id"]},
        ]
        ownership = {"field:user_id": {"ownerSlotRef": "slot:identity", "ownerGroupRef": "group:identity"}}
        report = evaluate(_build(slots=slots, ownership=ownership, evidence={"allowed_slot_roles": AUX_ROLES}))
        # With the prefix fixed and schema roles provided, an auxiliary projection
        # remains NOT_VERIFIED until its runtime semantics are proven.
        self.assertEqual(_pc005(report)["status"], "NOT_VERIFIED")

    def test_owner_slot_ref_valid_and_invalid_execute(self):
        slots = [
            {"id": "identity", "role": "identity", "fieldRefs": ["field:user_id"]},
            {"id": "summary", "role": "summary", "fieldRefs": ["field:user_id"]},
        ]
        evidence = {"allowed_slot_roles": AUX_ROLES}
        valid_ownership = {"field:user_id": {"ownerSlotRef": "slot:identity", "ownerGroupRef": "group:identity"}}
        report = evaluate(_build(slots=slots, ownership=valid_ownership, evidence=evidence))
        self.assertEqual(_pc005(report)["status"], "NOT_VERIFIED")

        invalid_ownership = {"field:user_id": {"ownerSlotRef": "slot:nonexistent", "ownerGroupRef": "group:identity"}}
        report = evaluate(_build(slots=slots, ownership=invalid_ownership, evidence=evidence))
        self.assertEqual(_pc005(report)["status"], "FAIL")

    def test_null_field_values(self):
        for field_refs in (None, [None]):
            slots = [{"id": "identity", "role": "identity", "fieldRefs": field_refs}]
            report = evaluate(_build(slots=slots))
            self.assertIn(_pc005(report)["status"], VALID_STATUSES)

    def test_unexpected_input_types(self):
        # Top-level slots must degrade to empty without raising.
        report = evaluate(_build(slots="not-a-list"))
        self.assertEqual(_pc005(report)["status"], "NOT_VERIFIED")

        # Field-ref entries of unexpected scalar types flow through _text safely.
        slots = [{"id": "s1", "role": "section", "fieldRefs": [123, True, {"field": "x"}]}]
        report = evaluate(_build(slots=slots))
        self.assertIn(_pc005(report)["status"], VALID_STATUSES)

    def test_payment_request_nine_slots_executes(self):
        slots = []
        for index in range(1, 10):
            slots.append(
                {
                    "id": f"slot_{index}",
                    "role": "identity" if index == 1 else "section",
                    "fieldRefs": [f"field:field_{index}"],
                }
            )
        # A second projection across two slots exercises the previously-crashing path.
        slots[0]["fieldRefs"].append("field:shared")
        slots[1]["fieldRefs"].append("field:shared")
        ownership = {"field:shared": {"ownerSlotRef": "slot:slot_1", "ownerGroupRef": "group:g1"}}
        report = evaluate(_build(slots=slots, ownership=ownership))
        self.assertIn(report["overall_status"], VALID_STATUSES)
        self.assertIn(_pc005(report)["status"], VALID_STATUSES)

    def test_pc006_unaffected(self):
        report = evaluate(_build(slots=[], page_class="formal"))
        self.assertEqual(_pc006(report)["status"], "PASS")

    def test_main_writes_reports_and_returns_zero(self):
        payload = _build(slots=[])
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            in_file = tmp_path / "input.json"
            out_json = tmp_path / "report.json"
            out_md = tmp_path / "report.md"
            in_file.write_text(json.dumps(payload), encoding="utf-8")
            sys_argv_save = None
            import sys
            sys_argv_save = sys.argv
            sys.argv = [
                "page_composition_integrity_guard.py",
                "--input",
                str(in_file),
                "--output-json",
                str(out_json),
                "--output-markdown",
                str(out_md),
            ]
            try:
                exit_code = MODULE.main()
            finally:
                sys.argv = sys_argv_save
            self.assertEqual(exit_code, 0)
            report = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertIn(report["overall_status"], VALID_STATUSES)
            markdown = out_md.read_text(encoding="utf-8")
            self.assertIn("PC-001", markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
