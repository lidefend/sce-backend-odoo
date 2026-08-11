#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "core" / "contract_lifecycle.py"
SPEC = importlib.util.spec_from_file_location("contract_lifecycle", MODULE_PATH)
contract_lifecycle = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(contract_lifecycle)
contract_semantic_payload = contract_lifecycle.contract_semantic_payload
payload_sha256 = contract_lifecycle.payload_sha256
protocol_id = contract_lifecycle.protocol_id
seal_unified_page_contract = contract_lifecycle.seal_unified_page_contract
verify_unified_page_contract_integrity = contract_lifecycle.verify_unified_page_contract_integrity


class ContractLifecycleTests(unittest.TestCase):
    def _contract(self):
        return {"pageInfo": {"pageId": "project.list", "contractVersion": "2.2.0"}}

    def test_canonical_digest_is_order_independent(self):
        self.assertEqual(payload_sha256({"b": 2, "a": 1}), payload_sha256({"a": 1, "b": 2}))

    def test_meta_is_not_part_of_semantic_payload(self):
        contract = {"pageInfo": {"pageId": "project.list"}, "meta": {"traceId": "trace.one"}}
        self.assertEqual(contract_semantic_payload(contract), {"pageInfo": {"pageId": "project.list"}})

    def test_seal_binds_request_trace_and_sha256(self):
        contract = seal_unified_page_contract(
            self._contract(),
            source_payload={"model": "project.project"},
            source_type="ui.contract",
            request_id="request/123",
            trace_id="trace/456",
            source_authority={"kind": "test"},
        )
        lifecycle = contract["meta"]["lifecycle"]
        self.assertEqual(lifecycle["runtime"]["requestId"], "request.123")
        self.assertEqual(lifecycle["runtime"]["traceId"], "trace.456")
        self.assertEqual(lifecycle["integrity"]["algorithm"], "sha256")
        self.assertEqual(len(lifecycle["integrity"]["contractSha256"]), 64)
        self.assertEqual(verify_unified_page_contract_integrity(contract), (True, "ok"))

    def test_tampering_fails_integrity_verification(self):
        contract = seal_unified_page_contract(
            self._contract(),
            source_payload={},
            source_type="ui.contract",
            request_id="request.one",
        )
        contract["pageInfo"]["pageId"] = "tampered"
        self.assertEqual(
            verify_unified_page_contract_integrity(contract),
            (False, "contract_sha256_mismatch"),
        )

    def test_protocol_id_is_stable_and_schema_safe(self):
        self.assertEqual(protocol_id("123 / abc", prefix="trace"), "trace.123.abc")


if __name__ == "__main__":
    unittest.main()
