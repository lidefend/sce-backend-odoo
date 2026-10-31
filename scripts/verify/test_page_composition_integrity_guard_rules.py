#!/usr/bin/env python3
"""Rule-alignment tests for the Page Composition Integrity Guard (PC-001..PC-011)."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "page_composition_integrity_guard", ROOT / "scripts/verify/page_composition_integrity_guard.py"
)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
sys.modules["page_composition_integrity_guard"] = GUARD
SPEC.loader.exec_module(GUARD)

AUX_ROLES = ["summary", "context", "relation", "detail", "activity", "audit"]


def _page(slots=None, ownership=None, groups=None, page_class="unclassified_historical", container_tree=None):
    page = {
        "model": "payment.request",
        "action_id": 649,
        "view_id": 1773,
        "pageComposition": {"class": page_class},
        "formStructureContract": {"slots": slots or []},
        "fieldGroups": {"groups": groups or []},
        "fieldOwnership": ownership or {},
    }
    if container_tree is not None:
        page["layoutContract"] = {"containerTree": container_tree}
    return page


def _trusted(evidence_type, coverage=None, grade=None):
    item = {
        "verification_status": "VERIFIED",
        "evidence_type": evidence_type,
        "model": "payment.request",
        "action_id": 649,
        "view_id": 1773,
    }
    if coverage is not None:
        item["coverage"] = coverage
    if grade is not None:
        item["evidence_grade"] = grade
    return item


def _run(page, evidence=None):
    return GUARD.evaluate(
        {"repository_sha": "sha", "contract_version": "2.2.0", "page": page, "evidence": evidence or {}}
    )


def _status(report, rule_id):
    return next(r for r in report["rule_results"] if r["rule_id"] == rule_id)["status"]


class PC001Tests(unittest.TestCase):
    def test_two_layers_pass(self):
        report = _run(_page(slots=[{"id": "identity", "role": "identity"}], container_tree=[{"id": "root"}]))
        self.assertEqual(_status(report, "PC-001"), "PASS")

    def test_slots_only_not_verified(self):
        report = _run(_page(slots=[{"id": "identity", "role": "identity"}]))
        self.assertEqual(_status(report, "PC-001"), "NOT_VERIFIED")

    def test_container_tree_cannot_substitute_slots(self):
        report = _run(_page(container_tree=[{"id": "root"}]))
        self.assertEqual(_status(report, "PC-001"), "NOT_VERIFIED")


class PC002Tests(unittest.TestCase):
    def test_identity_bound_pass(self):
        slots = [{"id": "identity", "role": "identity", "fieldRefs": ["field:project_code"]}]
        ownership = {"field:project_code": {"ownerSlotRef": "slot:identity"}}
        report = _run(_page(slots=slots, ownership=ownership, container_tree=[{"id": "r"}]))
        self.assertEqual(_status(report, "PC-002"), "PASS")

    def test_identity_slot_without_owned_field_not_verified(self):
        slots = [{"id": "identity", "role": "identity", "fieldRefs": ["field:project_code"]}]
        report = _run(_page(slots=slots, container_tree=[{"id": "r"}]))
        self.assertEqual(_status(report, "PC-002"), "NOT_VERIFIED")


class PC003Tests(unittest.TestCase):
    def test_section_binding_pass(self):
        slots = [
            {"id": "identity", "role": "identity", "fieldRefs": ["field:project_code"]},
            {"id": "basic_information", "role": "section", "fieldRefs": ["field:owner_id"]},
        ]
        groups = [{"id": "basic_information"}]
        ownership = {
            "field:project_code": {"ownerSlotRef": "slot:identity"},
            "field:owner_id": {"ownerSlotRef": "slot:basic_information", "ownerGroupRef": "group:basic_information"},
        }
        report = _run(_page(slots=slots, groups=groups, ownership=ownership, container_tree=[{"id": "r"}]))
        self.assertEqual(_status(report, "PC-003"), "PASS")

    def test_business_field_without_group_not_verified(self):
        slots = [
            {"id": "identity", "role": "identity", "fieldRefs": ["field:project_code"]},
            {"id": "basic_information", "role": "section", "fieldRefs": ["field:owner_id"]},
        ]
        ownership = {
            "field:owner_id": {"ownerSlotRef": "slot:basic_information", "ownerGroupRef": "group:missing"},
        }
        report = _run(_page(slots=slots, ownership=ownership, container_tree=[{"id": "r"}]))
        self.assertEqual(_status(report, "PC-003"), "NOT_VERIFIED")


class PC004Tests(unittest.TestCase):
    def test_valid_ownership_pass(self):
        slots = [{"id": "identity", "role": "identity", "fieldRefs": ["field:project_code"]}]
        ownership = {"field:project_code": {"ownerSlotRef": "slot:identity"}}
        report = _run(_page(slots=slots, ownership=ownership, container_tree=[{"id": "r"}]))
        self.assertEqual(_status(report, "PC-004"), "PASS")

    def test_dangling_owner_slot_fails(self):
        slots = [{"id": "identity", "role": "identity", "fieldRefs": ["field:project_code"]}]
        ownership = {"field:project_code": {"ownerSlotRef": "slot:nonexistent"}}
        report = _run(_page(slots=slots, ownership=ownership, container_tree=[{"id": "r"}]))
        self.assertEqual(_status(report, "PC-004"), "FAIL")

    def test_duplicate_json_key_detected(self):
        text = (
            '{"page":{"model":"payment.request","action_id":649,"view_id":1773,'
            '"pageComposition":{"class":"formal"},'
            '"formStructureContract":{"slots":[{"id":"identity"}]},'
            '"fieldOwnership":{'
            '"field:project_code":{"ownerSlotRef":"slot:a"},'
            '"field:project_code":{"ownerSlotRef":"slot:b"}}}}'
        )
        payload, duplicates = GUARD._load_json_detect_duplicates(text)
        self.assertEqual([d["key"] for d in duplicates], ["field:project_code"])
        report = GUARD.evaluate(payload, parse_diagnostics={"duplicate_keys": duplicates})
        self.assertEqual(_status(report, "PC-004"), "FAIL")


class PC005Tests(unittest.TestCase):
    def test_non_list_field_refs_fails_structured(self):
        slots = [{"id": "identity", "role": "identity", "fieldRefs": 123}]
        report = _run(_page(slots=slots, container_tree=[{"id": "r"}]))
        self.assertEqual(_status(report, "PC-005"), "FAIL")

    def test_two_primary_entries_fail(self):
        slots = [
            {"id": "identity", "role": "identity", "fieldRefs": ["field:user_id"]},
            {"id": "basic_information", "role": "section", "fieldRefs": ["field:user_id"]},
        ]
        ownership = {"field:user_id": {"ownerSlotRef": "slot:identity"}}
        report = _run(_page(slots=slots, ownership=ownership, container_tree=[{"id": "r"}], ), evidence={"allowed_slot_roles": AUX_ROLES})
        self.assertEqual(_status(report, "PC-005"), "FAIL")


class PC007Tests(unittest.TestCase):
    def test_formal_runtime_fallback_fails(self):
        report = _run(
            _page(page_class="formal", container_tree=[{"id": "r"}]),
            evidence={"legacy_fallback_sources": [_trusted("RUNTIME_OBSERVATION", grade="RUNTIME_VERIFIED")]},
        )
        self.assertEqual(_status(report, "PC-007"), "FAIL")

    def test_unclassified_runtime_fallback_warns(self):
        report = _run(
            _page(container_tree=[{"id": "r"}]),
            evidence={"legacy_fallback_sources": [_trusted("RUNTIME_OBSERVATION", grade="RUNTIME_VERIFIED")]},
        )
        self.assertEqual(_status(report, "PC-007"), "WARNING")

    def test_source_only_fallback_not_verified(self):
        report = _run(
            _page(container_tree=[{"id": "r"}]),
            evidence={"legacy_fallback_sources": [_trusted("SOURCE_STATIC", grade="SOURCE_VERIFIED")]},
        )
        self.assertEqual(_status(report, "PC-007"), "NOT_VERIFIED")


class PC008To010Tests(unittest.TestCase):
    def test_permission_runtime_observation_pass(self):
        item = _trusted(
            "RUNTIME_OBSERVATION",
            coverage=["server_permission_mechanism", "authorized_access", "unauthorized_denied"],
        )
        report = _run(_page(container_tree=[{"id": "r"}]), evidence={"permission_evidence": [item]})
        self.assertEqual(_status(report, "PC-008"), "PASS")

    def test_version_regression_pass(self):
        report = _run(
            _page(container_tree=[{"id": "r"}]),
            evidence={"version_compatibility_evidence": [_trusted("TEST_EXECUTION", coverage=["old_consumer_regression"])]},
        )
        self.assertEqual(_status(report, "PC-009"), "PASS")

    def test_historical_mapping_pass(self):
        report = _run(
            _page(container_tree=[{"id": "r"}]),
            evidence={"historical_node_identity_evidence": [_trusted("HISTORICAL_REFERENCE", coverage=["before_after_mapping"])]},
        )
        self.assertEqual(_status(report, "PC-010"), "PASS")


class PC011Tests(unittest.TestCase):
    def test_dangling_reference_fails(self):
        report = _run(_page(slots=[{"id": "identity", "role": "identity"}], container_tree=[{"id": "root", "children": ["missing"]}]))
        self.assertEqual(_status(report, "PC-011"), "FAIL")

    def test_mapping_consistent_pass(self):
        slots = [{"id": "identity", "role": "identity", "fieldRefs": ["field:a"]}]
        tree = [{"id": "c1", "fieldRefs": ["field:a"]}]
        report = _run(
            _page(slots=slots, container_tree=tree),
            evidence={"slot_container_mapping": [{"slot_ref": "slot:identity", "container_id": "c1"}]},
        )
        self.assertEqual(_status(report, "PC-011"), "PASS")

    def test_missing_mapping_not_verified(self):
        report = _run(_page(slots=[{"id": "identity", "role": "identity"}], container_tree=[{"id": "c1"}]))
        self.assertEqual(_status(report, "PC-011"), "NOT_VERIFIED")

    def test_container_assigns_ownership_conflict_fails(self):
        slots = [{"id": "identity", "role": "identity", "fieldRefs": ["field:a"]}]
        ownership = {"field:a": {"ownerSlotRef": "slot:identity"}}
        tree = [{"id": "c1", "businessRegionRef": "slot:basic_information", "fieldRefs": ["field:a"]}]
        report = _run(_page(slots=slots, ownership=ownership, container_tree=tree))
        self.assertEqual(_status(report, "PC-011"), "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
