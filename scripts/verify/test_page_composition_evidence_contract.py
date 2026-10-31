#!/usr/bin/env python3
"""Tests for the page composition Evidence Contract and independent Collector."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFY_DIR = ROOT / "scripts/verify"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


CONTRACT = _load("page_composition_evidence_contract", VERIFY_DIR / "page_composition_evidence_contract.py")
COLLECTOR = _load("page_composition_evidence_collector", VERIFY_DIR / "page_composition_evidence_collector.py")
GUARD = _load("page_composition_integrity_guard", VERIFY_DIR / "page_composition_integrity_guard.py")

TARGET = {"model": "payment.request", "action_id": 649, "view_id": 1773}
SHA = "a9cd2fd5879d8a5358c2ad737602e0ae72644555"
COLLECTED_AT = "2026-10-31T00:00:00+00:00"


def _sha256_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _item(evidence_id, evidence_type, applies_to_rule, **overrides):
    item = {
        "evidence_id": evidence_id,
        "evidence_type": evidence_type,
        "source_type": "artifact",
        "collection_method": "auto_verify",
        "collected_at": COLLECTED_AT,
        "repository_sha": SHA,
        "model": "payment.request",
        "action_id": 649,
        "view_id": 1773,
        "contract_version": "2.2.0",
        "applies_to_rule": applies_to_rule,
    }
    if evidence_type == "HUMAN_REVIEW":
        item["review_basis"] = "owner review 2026-10-31"
    item.update(overrides)
    return item


def _guard_page(overrides=None):
    page = {
        "model": "payment.request",
        "action_id": 649,
        "view_id": 1773,
        "pageComposition": {"class": "unclassified_historical"},
        "formStructureContract": {"slots": []},
        "fieldGroups": {"groups": []},
        "fieldOwnership": {},
    }
    if overrides:
        page.update(overrides)
    return page


class EvidenceContractTests(unittest.TestCase):
    def test_valid_static_source_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src.txt"
            source.write_text("field:project_code", encoding="utf-8")
            item = _item("e1", "SOURCE_STATIC", "PC-008", source_location=str(source), content_digest=_sha256_file(str(source)))
            result = CONTRACT.validate_evidence_item(item, TARGET, SHA)
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertEqual(result["evidence_grade"], "SOURCE_VERIFIED")

    def test_valid_test_execution_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "test-result.json"
            source.write_text('{"passed": 3}', encoding="utf-8")
            item = _item("e2", "TEST_EXECUTION", "PC-009", source_location=str(source), content_digest=_sha256_file(str(source)))
            result = CONTRACT.validate_evidence_item(item, TARGET, SHA)
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertEqual(result["evidence_grade"], "STATIC_CHAIN_VERIFIED")

    def test_valid_runtime_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "runtime-artifact.json"
            source.write_text('{"consumer": "NativeFormTreeRenderer"}', encoding="utf-8")
            item = _item("e3", "RUNTIME_OBSERVATION", "PC-007", source_location=str(source), content_digest=_sha256_file(str(source)))
            result = CONTRACT.validate_evidence_item(item, TARGET, SHA)
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertEqual(result["evidence_grade"], "RUNTIME_VERIFIED")

    def test_human_review_cannot_masquerade_as_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "review.md"
            source.write_text("reviewed", encoding="utf-8")
            item = _item("e4", "HUMAN_REVIEW", "PC-008", source_location=str(source), content_digest=_sha256_file(str(source)))
            result = CONTRACT.validate_evidence_item(item, TARGET, SHA)
        self.assertEqual(result["verification_status"], "UNVERIFIED")
        self.assertEqual(result["evidence_grade"], "NOT_VERIFIED")

    def test_scope_mismatch(self):
        item = _item("e5", "SOURCE_STATIC", "PC-008", source_location="/tmp/x", content_digest="deadbeef")
        item["model"] = "project.project"
        result = CONTRACT.validate_evidence_item(item, TARGET, SHA)
        self.assertEqual(result["verification_status"], "SCOPE_MISMATCH")

    def test_repository_sha_mismatch_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src.txt"
            source.write_text("x", encoding="utf-8")
            item = _item("e6", "SOURCE_STATIC", "PC-008", source_location=str(source), content_digest=_sha256_file(str(source)), repository_sha="old-sha")
            result = CONTRACT.validate_evidence_item(item, TARGET, SHA)
        self.assertEqual(result["verification_status"], "STALE")

    def test_duplicate_evidence_id_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src.txt"
            source.write_text("x", encoding="utf-8")
            item = _item("dup", "SOURCE_STATIC", "PC-008", source_location=str(source), content_digest=_sha256_file(str(source)))
            bundle = COLLECTOR.collect({"target_page": TARGET, "items": [item, dict(item)]}, SHA)
        statuses = [r["verification_status"] for r in bundle["items"]]
        self.assertEqual(statuses.count("VERIFIED"), 1)
        self.assertEqual(statuses.count("INVALID"), 1)

    def test_content_digest_mismatch_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src.txt"
            source.write_text("actual", encoding="utf-8")
            item = _item("e8", "SOURCE_STATIC", "PC-008", source_location=str(source), content_digest="0" * 64)
            result = CONTRACT.validate_evidence_item(item, TARGET, SHA)
        self.assertEqual(result["verification_status"], "INVALID")

    def test_expired_evidence_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "src.txt"
            source.write_text("x", encoding="utf-8")
            item = _item("e9", "SOURCE_STATIC", "PC-008", source_location=str(source), content_digest=_sha256_file(str(source)), expires_at="2020-01-01T00:00:00+00:00")
            result = CONTRACT.validate_evidence_item(item, TARGET, SHA)
        self.assertEqual(result["verification_status"], "STALE")

    def test_empty_evidence_bundle(self):
        bundle = COLLECTOR.collect({"target_page": TARGET, "items": []}, SHA)
        self.assertEqual(bundle["summary"]["total"], 0)
        self.assertEqual(bundle["guard_evidence"]["permission_evidence"], [])

    def test_handwritten_json_does_not_become_trusted(self):
        item = _item("e11", "SOURCE_STATIC", "PC-008", content="claimed evidence")
        item.pop("content_digest", None)
        bundle = COLLECTOR.collect({"target_page": TARGET, "items": [item]}, SHA)
        self.assertEqual(bundle["summary"]["VERIFIED"], 0)
        self.assertIn("e11", bundle["untrusted"])

    def test_missing_collection_source(self):
        item = _item("e12", "SOURCE_STATIC", "PC-008", content="x", content_digest=_sha256_text("x"))
        result = CONTRACT.validate_evidence_item(item, TARGET, SHA)
        self.assertEqual(result["verification_status"], "INVALID")

    def test_historical_reference_without_original_basis(self):
        item = _item("e13", "HISTORICAL_REFERENCE", "PC-010", content="x", content_digest=_sha256_text("x"))
        result = CONTRACT.validate_evidence_item(item, TARGET, SHA)
        self.assertNotEqual(result["verification_status"], "VERIFIED")

    def test_cross_page_evidence_rejected(self):
        item = _item("e14", "SOURCE_STATIC", "PC-008", source_location="/tmp/x", content_digest="deadbeef")
        item["action_id"] = 999
        bundle = COLLECTOR.collect({"target_page": TARGET, "items": [item]}, SHA)
        self.assertEqual(bundle["summary"]["SCOPE_MISMATCH"], 1)

    def test_collector_invalid_input_handled(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bad = tmp_path / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            out = tmp_path / "out.json"
            sys_argv_save = sys.argv
            sys.argv = [
                "page_composition_evidence_collector.py",
                "--input", str(bad),
                "--repository-sha", SHA,
                "--output", str(out),
            ]
            try:
                exit_code = COLLECTOR.main()
            finally:
                sys.argv = sys_argv_save
            self.assertEqual(exit_code, 2)
            self.assertFalse(out.exists())


class GuardEvidenceTrustTests(unittest.TestCase):
    def test_unverified_evidence_does_not_pass(self):
        report = GUARD.evaluate(
            {
                "repository_sha": SHA,
                "contract_version": "2.2.0",
                "page": _guard_page(),
                "evidence": {
                    "permission_evidence": [
                        {"evidence_id": "x", "model": "payment.request", "action_id": 649, "view_id": 1773}
                    ]
                },
            }
        )
        pc008 = next(r for r in report["rule_results"] if r["rule_id"] == "PC-008")
        self.assertEqual(pc008["status"], "NOT_VERIFIED")

    def test_verified_scope_matched_evidence_passes(self):
        report = GUARD.evaluate(
            {
                "repository_sha": SHA,
                "contract_version": "2.2.0",
                "page": _guard_page(),
                "evidence": {
                    "permission_evidence": [
                        {
                            "evidence_id": "x",
                            "verification_status": "VERIFIED",
                            "evidence_type": "TEST_EXECUTION",
                            "coverage": [
                                "server_permission_mechanism",
                                "authorized_access",
                                "unauthorized_denied",
                            ],
                            "model": "payment.request",
                            "action_id": 649,
                            "view_id": 1773,
                        }
                    ]
                },
            }
        )
        pc008 = next(r for r in report["rule_results"] if r["rule_id"] == "PC-008")
        self.assertEqual(pc008["status"], "PASS")

    def test_verified_but_insufficient_permission_evidence_does_not_pass(self):
        report = GUARD.evaluate(
            {
                "repository_sha": SHA,
                "contract_version": "2.2.0",
                "page": _guard_page(),
                "evidence": {
                    "permission_evidence": [
                        {
                            "evidence_id": "x",
                            "verification_status": "VERIFIED",
                            "evidence_type": "TEST_EXECUTION",
                            "coverage": ["smoke"],
                            "model": "payment.request",
                            "action_id": 649,
                            "view_id": 1773,
                        }
                    ]
                },
            }
        )
        pc008 = next(r for r in report["rule_results"] if r["rule_id"] == "PC-008")
        self.assertEqual(pc008["status"], "NOT_VERIFIED")

    def test_verified_wrong_page_evidence_does_not_pass(self):
        report = GUARD.evaluate(
            {
                "repository_sha": SHA,
                "contract_version": "2.2.0",
                "page": _guard_page(),
                "evidence": {
                    "permission_evidence": [
                        {
                            "evidence_id": "x",
                            "verification_status": "VERIFIED",
                            "model": "project.project",
                            "action_id": 590,
                            "view_id": 1776,
                        }
                    ]
                },
            }
        )
        pc008 = next(r for r in report["rule_results"] if r["rule_id"] == "PC-008")
        self.assertEqual(pc008["status"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
