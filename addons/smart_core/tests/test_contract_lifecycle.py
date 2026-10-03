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

    def test_request_transport_identity_is_not_part_of_semantic_payload(self):
        # The delivered contract echoes the live request context. Its business
        # context is authoritative, but the per-request transport identity must
        # not reach the sealed payload, or the digest would change on every read.
        contract = {
            "dataContract": {"dataMeta": {"sourceContext": {"context": {
                "lang": "en_US", "trace_id": "trace.one", "request_id": "request.one",
            }}}},
            "dataSource": {"primary": {"params": {"context": {
                "lang": "en_US", "trace_id": "trace.one",
            }}}},
        }
        payload = contract_semantic_payload(contract)
        self.assertEqual(payload["dataContract"]["dataMeta"]["sourceContext"]["context"], {"lang": "en_US"})
        self.assertEqual(payload["dataSource"]["primary"]["params"]["context"], {"lang": "en_US"})
        # The caller's contract object is never mutated: the delivered payload
        # keeps the echoed context, only the seal is normalized.
        self.assertEqual(contract["dataSource"]["primary"]["params"]["context"]["trace_id"], "trace.one")

    def test_only_the_request_trace_changes_the_semantic_digest(self):
        base = {"pageInfo": {"pageId": "payment.request.form"}, "dataContract": {"dataMeta": {"sourceContext": {
            "context": {"lang": "en_US", "trace_id": "trace.one"}}}}}
        other = {"pageInfo": {"pageId": "payment.request.form"}, "dataContract": {"dataMeta": {"sourceContext": {
            "context": {"lang": "en_US", "trace_id": "trace.two"}}}}}
        self.assertEqual(payload_sha256(contract_semantic_payload(base)),
                         payload_sha256(contract_semantic_payload(other)))
        # A business value that merely shares the name stays sealed: it does not
        # live under a transport ``context`` container.
        business = {"pageInfo": {"pageId": "payment.request.form"}, "mainData": {"trace_id": "trace.one"}}
        business_changed = {"pageInfo": {"pageId": "payment.request.form"}, "mainData": {"trace_id": "trace.two"}}
        self.assertNotEqual(payload_sha256(contract_semantic_payload(business)),
                            payload_sha256(contract_semantic_payload(business_changed)))

    def test_a_sealed_contract_is_stable_across_request_traces(self):
        def sealed(trace_id):
            contract = {"pageInfo": {"pageId": "payment.request.form"}, "dataContract": {"dataMeta": {
                "sourceContext": {"context": {"lang": "en_US", "trace_id": trace_id}}}}}
            return seal_unified_page_contract(
                contract,
                source_payload={"model": "payment.request", "context": {"trace_id": trace_id}},
                source_type="ui.contract",
                request_id=f"request.{trace_id}",
                trace_id=trace_id,
            )
        first, second = sealed("trace.one"), sealed("trace.two")
        self.assertEqual(first["meta"]["lifecycle"]["integrity"]["contractSha256"],
                         second["meta"]["lifecycle"]["integrity"]["contractSha256"])
        self.assertEqual(first["meta"]["etag"], second["meta"]["etag"])
        self.assertEqual(first["meta"]["lifecycle"]["generation"]["sourceSha256"],
                         second["meta"]["lifecycle"]["generation"]["sourceSha256"])
        # Identity is still per request and still verifiable.
        self.assertNotEqual(first["meta"]["lifecycle"]["runtime"]["traceId"],
                            second["meta"]["lifecycle"]["runtime"]["traceId"])
        self.assertEqual(verify_unified_page_contract_integrity(first), (True, "ok"))
        self.assertEqual(verify_unified_page_contract_integrity(second), (True, "ok"))

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

    def _seal(self, *, published_version_ref=""):
        return seal_unified_page_contract(
            self._contract(),
            source_payload={"model": "project.project"},
            source_type="ui.contract",
            request_id="request.one",
            published_version_ref=published_version_ref,
        )

    def test_an_unattributed_delivery_omits_the_published_version_ref(self):
        definition = self._seal()["meta"]["lifecycle"]["definition"]
        self.assertNotIn("publishedVersionRef", definition)
        self.assertEqual(sorted(definition), [
            "contractVersion", "normativeStatus", "schemaId", "schemaSha256", "schemaVersion",
        ])

    def test_a_blank_published_version_ref_is_not_recorded(self):
        definition = self._seal(published_version_ref="   ")["meta"]["lifecycle"]["definition"]
        self.assertNotIn("publishedVersionRef", definition)

    def test_a_published_version_ref_is_additive_to_the_semantic_digest(self):
        # ``meta`` is outside the semantic payload, so naming the applied
        # published version must not change the delivered contract digest.
        attributed = self._seal(published_version_ref="ui.business.config.contract:22@2")
        unattributed = self._seal()
        self.assertEqual(
            attributed["meta"]["lifecycle"]["definition"]["publishedVersionRef"],
            "ui.business.config.contract:22@2",
        )
        self.assertEqual(
            attributed["meta"]["lifecycle"]["integrity"]["contractSha256"],
            unattributed["meta"]["lifecycle"]["integrity"]["contractSha256"],
        )
        self.assertEqual(verify_unified_page_contract_integrity(attributed), (True, "ok"))


if __name__ == "__main__":
    unittest.main()
