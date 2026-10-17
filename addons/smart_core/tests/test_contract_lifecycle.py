#!/usr/bin/env python3
from __future__ import annotations

import hashlib
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
    def test_published_schema_digest_matches_authoritative_file(self):
        schema = Path(__file__).resolve().parents[3] / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
        self.assertEqual(contract_lifecycle.UNIFIED_PAGE_SCHEMA_SHA256, hashlib.sha256(schema.read_bytes()).hexdigest())

    def _contract(self):
        return {"pageInfo": {"pageId": "project.list", "contractVersion": "2.2.0"}}

    def test_canonical_digest_is_order_independent(self):
        self.assertEqual(payload_sha256({"b": 2, "a": 1}), payload_sha256({"a": 1, "b": 2}))

    def test_meta_is_not_part_of_semantic_payload(self):
        contract = {"pageInfo": {"pageId": "project.list"}, "meta": {"traceId": "trace.one"}}
        self.assertEqual(contract_semantic_payload(contract), {"pageInfo": {"pageId": "project.list"}})

    def test_semantic_payload_never_mutates_a_caller_without_transport_keys(self):
        # ``strip_request_transport_identity`` is copy-on-write so a payload with
        # no transport identity is returned by reference.  The semantic payload
        # must still isolate the top level before dropping ``meta``, or sealing
        # would delete the caller's metadata.
        contract = {
            "pageInfo": {"pageId": "project.list"},
            "meta": {"traceId": "trace.one", "etag": "etag.one"},
        }
        payload = contract_semantic_payload(contract)
        self.assertEqual(payload, {"pageInfo": {"pageId": "project.list"}})
        self.assertEqual(contract["meta"], {"traceId": "trace.one", "etag": "etag.one"})

    def test_transport_strip_is_copy_on_write_and_keeps_unchanged_subtrees(self):
        stable = {"pageInfo": {"pageId": "project.list"}, "rows": [{"id": 1}, {"id": 2}]}
        payload = {
            "stable": stable,
            "context": {"lang": "en_US", "trace_id": "trace.one", "request_id": "request.one"},
        }
        stripped = contract_lifecycle.strip_request_transport_identity(payload)
        self.assertEqual(stripped["context"], {"lang": "en_US"})
        self.assertIs(stripped["stable"], stable)
        self.assertEqual(payload["context"]["trace_id"], "trace.one")

    def test_transport_strip_reuses_the_whole_object_when_nothing_moves(self):
        payload = {"pageInfo": {"pageId": "project.list"}, "context": {"lang": "en_US"}, "rows": [{"id": 1}]}
        self.assertIs(contract_lifecycle.strip_request_transport_identity(payload), payload)

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

    def test_a_bound_digest_is_reused_without_recomputation(self):
        contract = self._contract()
        source = {"model": "project.project"}
        baseline = contract_lifecycle.build_lifecycle_evidence(
            contract=contract, source_payload=source, source_type="ui.contract",
            request_id="request.one", trace_id="trace.one", client_type="web_pc",
            stage="runtime_delivery", generator="test", generator_version="1",
            source_authority={},
        )
        digests = {
            "contractSha256": baseline["integrity"]["contractSha256"],
            "sourceSha256": baseline["generation"]["sourceSha256"],
        }
        calls = {"n": 0}
        original = contract_lifecycle.payload_sha256

        def _refuse(*args, **kwargs):
            calls["n"] += 1
            return original(*args, **kwargs)

        contract_lifecycle.payload_sha256 = _refuse
        try:
            reused = contract_lifecycle.build_lifecycle_evidence(
                contract=contract, source_payload=source, source_type="ui.contract",
                request_id="request.two", trace_id="trace.two", client_type="web_pc",
                stage="runtime_delivery", generator="test", generator_version="1",
                source_authority={}, reuse_digests=digests,
            )
        finally:
            contract_lifecycle.payload_sha256 = original
        self.assertEqual(calls["n"], 0)
        self.assertEqual(reused["integrity"]["contractSha256"], digests["contractSha256"])
        self.assertEqual(reused["generation"]["sourceSha256"], digests["sourceSha256"])
        # The reused seal is still a genuine per-request identity.
        self.assertEqual(reused["runtime"]["traceId"], "trace.two")

    def test_reuse_fails_closed_on_a_missing_or_malformed_digest(self):
        contract = self._contract()
        for reuse in (None, {}, {"contractSha256": "", "sourceSha256": ""},
                      {"contractSha256": "x" * 64, "sourceSha256": "y" * 64},
                      {"contractSha256": 1234, "sourceSha256": "z" * 64},
                      {"contractSha256": "a" * 64}):
            evidence = contract_lifecycle.build_lifecycle_evidence(
                contract=contract, source_payload={"model": "project.project"},
                source_type="ui.contract", request_id="request.one", trace_id="trace.one",
                client_type="web_pc", stage="runtime_delivery", generator="test",
                generator_version="1", source_authority={}, reuse_digests=reuse,
            )
            self.assertEqual(len(evidence["integrity"]["contractSha256"]), 64)
            self.assertEqual(len(evidence["generation"]["sourceSha256"]), 64)
            if isinstance(reuse, dict) and reuse.get("contractSha256") in ("x" * 64,):
                self.assertNotEqual(evidence["integrity"]["contractSha256"], reuse["contractSha256"])

    def test_a_wrong_bound_digest_is_caught_by_the_per_request_reverification(self):
        # The reuse is a memo, not an authority: if the bound digest did not
        # describe the delivered contract, the delivery-time re-verification
        # must reject it instead of shipping a silently wrong etag.
        contract = seal_unified_page_contract(
            self._contract(),
            source_payload={"model": "project.project"},
            source_type="ui.contract",
            request_id="request.one",
            trace_id="trace.one",
            reuse_digests={"contractSha256": "b" * 64, "sourceSha256": "a" * 64},
        )
        self.assertEqual(contract["meta"]["etag"], "upc-v2-sha256-" + "b" * 64)
        ok, reason = verify_unified_page_contract_integrity(contract)
        self.assertFalse(ok)
        self.assertEqual(reason, "contract_sha256_mismatch")

    def test_a_correct_bound_digest_still_verifies(self):
        contract = self._contract()
        source = {"model": "project.project"}
        evidence = contract_lifecycle.build_lifecycle_evidence(
            contract=contract, source_payload=source, source_type="ui.contract",
            request_id="request.one", trace_id="trace.one", client_type="web_pc",
            stage="runtime_delivery", generator="test", generator_version="1",
            source_authority={},
        )
        sealed = seal_unified_page_contract(
            contract,
            source_payload=source,
            source_type="ui.contract",
            request_id="request.two",
            trace_id="trace.two",
            reuse_digests={
                "contractSha256": evidence["integrity"]["contractSha256"],
                "sourceSha256": evidence["generation"]["sourceSha256"],
            },
        )
        self.assertEqual(verify_unified_page_contract_integrity(sealed), (True, "ok"))

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


class SourceMetaIdentityTests(unittest.TestCase):
    """``source_meta`` is inside the hashed source payload.

    ``build_lifecycle_evidence`` hashes ``strip_request_transport_identity(source_payload)``
    into ``sourceSha256``, so every key the source envelope meta carries is part of
    the source identity. A per-request measurement there makes the same source
    content produce a different identity in every process.
    """

    def _identity(self, source_payload):
        return payload_sha256(contract_lifecycle.strip_request_transport_identity(source_payload))

    def test_per_request_measurements_and_transport_identity_are_dropped(self):
        meta = {
            "intent": "ui.contract",
            "model": "res.partner",
            "op": "action_open",
            "elapsed_ms": 1234,
            "trace_id": "trace.one",
            "request_id": "request.one",
        }
        self.assertEqual(
            contract_lifecycle.source_meta_for_identity(meta),
            {"intent": "ui.contract", "model": "res.partner", "op": "action_open"},
        )
        # The caller's meta is never mutated: only the hashed copy is normalized.
        self.assertEqual(meta["elapsed_ms"], 1234)
        self.assertEqual(meta["trace_id"], "trace.one")

    def test_a_non_dict_meta_contributes_no_identity(self):
        self.assertEqual(contract_lifecycle.source_meta_for_identity(None), {})
        self.assertEqual(contract_lifecycle.source_meta_for_identity("ui.contract"), {})
        self.assertEqual(contract_lifecycle.source_meta_for_identity([("intent", "ui.contract")]), {})

    def _source_payload(self, *, elapsed_ms, model="res.partner", op="action_open"):
        return {
            "model": model,
            "source_meta": contract_lifecycle.source_meta_for_identity({
                "intent": "ui.contract",
                "model": model,
                "op": op,
                "elapsed_ms": elapsed_ms,
                "trace_id": "trace.one",
                "request_id": "request.one",
            }),
        }

    def test_source_identity_is_stable_across_projection_duration(self):
        # Two projections of the same source that differ only in how long they
        # took are the same source; the identity must not move with the clock.
        self.assertEqual(
            self._identity(self._source_payload(elapsed_ms=1)),
            self._identity(self._source_payload(elapsed_ms=9999)),
        )

    def test_source_identity_still_moves_when_a_source_fact_changes(self):
        # Negative control: the filter is narrow. A changed source fact still
        # changes the identity, both outside and inside the envelope meta.
        baseline = self._identity(self._source_payload(elapsed_ms=7))
        self.assertNotEqual(baseline, self._identity(self._source_payload(elapsed_ms=7, model="project.project")))
        self.assertNotEqual(baseline, self._identity(self._source_payload(elapsed_ms=7, op="action_other")))


if __name__ == "__main__":
    unittest.main()
