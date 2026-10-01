#!/usr/bin/env python3
"""Self-test for scripts/verify/page_pattern_reference_ledger_guard.py.

The ledger states its own completion rule and nothing executed it, so a gap
could be filed with no owner and no next action.  A guard that accepts anything
would recreate that hole, so this test proves it rejects an ownerless or
actionless contract gap, a surviving needs_work item, an unknown status and a
duplicate key, while accepting a ledger that does say who owns each gap.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

GUARD_PATH = Path(__file__).resolve().with_name("page_pattern_reference_ledger_guard.py")
_spec = importlib.util.spec_from_file_location("page_pattern_reference_ledger_guard", GUARD_PATH)
assert _spec and _spec.loader
guard = importlib.util.module_from_spec(_spec)
sys.modules["page_pattern_reference_ledger_guard"] = guard
_spec.loader.exec_module(guard)


def ledger(details: list[dict]) -> dict:
    return {
        "statusVocabulary": ["aligned", "needs_work", "contract_gap", "not_applicable"],
        "completionRule": "Contract gaps require an owner, evidence and a follow-up target.",
        "details": details,
    }


ALIGNED = {
    "key": "collection.pagination",
    "surface": "collection",
    "detail": "one footer",
    "status": "aligned",
    "authority": "pagination contract",
    "gap": None,
}

OWNED_GAP = {
    "key": "detail.container",
    "surface": "readonly-detail",
    "detail": "drawer authority",
    "status": "contract_gap",
    "authority": "record-entry disposition contract",
    "gap": "no standalone_page | contextual_drawer authority",
    "owner": "P0 smart_core",
    "followUp": "extend the record-entry contract to authorize the drawer, or drop the reference control",
}


class LedgerGuardTests(unittest.TestCase):
    def test_aligned_only_ledger_passes(self):
        self.assertEqual(guard.audit(ledger([ALIGNED])), [])

    def test_owned_gap_passes(self):
        self.assertEqual(guard.audit(ledger([OWNED_GAP])), [])

    def test_evidence_owner_is_accepted_for_an_evidence_gap(self):
        entry = {
            "key": "responsive.reference-mobile",
            "surface": "responsive",
            "detail": "mobile parity",
            "status": "contract_gap",
            "authority": "reference evidence",
            "gap": "no authenticated 390px reference screenshot",
            "owner": "evidence",
            "followUp": "capture the authenticated 390px reference screenshot before claiming parity",
        }
        self.assertEqual(guard.audit(ledger([entry])), [])

    def test_contract_gap_without_owner_fails(self):
        entry = {**OWNED_GAP, "owner": ""}
        findings = guard.audit(ledger([entry]))
        self.assertTrue(any("authoritative owner" in item for item in findings), findings)

    def test_contract_gap_with_invented_owner_fails(self):
        entry = {**OWNED_GAP, "owner": "frontend-team"}
        findings = guard.audit(ledger([entry]))
        self.assertTrue(any("authoritative owner" in item for item in findings), findings)

    def test_contract_gap_without_follow_up_fails(self):
        entry = {**OWNED_GAP, "followUp": "later"}
        findings = guard.audit(ledger([entry]))
        self.assertTrue(any("follow-up target" in item for item in findings), findings)

    def test_contract_gap_without_authority_fails(self):
        entry = {**OWNED_GAP, "authority": ""}
        findings = guard.audit(ledger([entry]))
        self.assertTrue(any("its authority" in item for item in findings), findings)

    def test_surviving_needs_work_fails(self):
        entry = {**OWNED_GAP, "status": "needs_work"}
        findings = guard.audit(ledger([entry]))
        self.assertTrue(any("needs_work" in item for item in findings), findings)

    def test_unknown_status_fails(self):
        entry = {**OWNED_GAP, "status": "maybe"}
        findings = guard.audit(ledger([entry]))
        self.assertTrue(any("declared vocabulary" in item for item in findings), findings)

    def test_duplicate_key_fails(self):
        findings = guard.audit(ledger([OWNED_GAP, OWNED_GAP]))
        self.assertTrue(any("duplicate key" in item for item in findings), findings)

    def test_unknown_surface_fails(self):
        entry = {**OWNED_GAP, "surface": "desktop"}
        findings = guard.audit(ledger([entry]))
        self.assertTrue(any("unknown surface" in item for item in findings), findings)

    def test_missing_completion_rule_fails(self):
        broken = ledger([ALIGNED])
        broken["completionRule"] = ""
        findings = guard.audit(broken)
        self.assertTrue(any("completionRule" in item for item in findings), findings)

    def test_non_object_ledger_fails(self):
        self.assertTrue(guard.audit([]))


if __name__ == "__main__":
    unittest.main()
