#!/usr/bin/env python3
"""Offline lock for the contract supply-chain attestation core.

The suite pins the unification invariants (one revision built the artifact and
is what runs), the digest-linked chain, the signature boundary and the
fail-closed reason codes. Baseline passes first; every negative then tampers
exactly one binding and must be refused with the owning reason code.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_PATH = ROOT / "addons/smart_core/core/contract_supply_chain_attestation.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


CHAIN = load_module("contract_supply_chain_attestation", CORE_PATH)

REVISION = "1" * 40
OTHER_REVISION = "2" * 40


def _subject(**overrides):
    subject = {
        "schemaId": "smart_core.unified_page_contract_v2",
        "schemaVersion": "2.2.0",
        "schemaSha256": "a" * 64,
        "contractSha256": "b" * 64,
        "sourceRevision": REVISION,
        "artifactSourceRevision": REVISION,
        "artifactSha256": "c" * 64,
        "moduleVersion": "17.0.1.1.14",
        "productVersion": "1.0.0",
        "deploymentDatabase": "sc_contract_lifecycle",
        "deploymentRuntimeSha": REVISION,
    }
    subject.update(overrides)
    return subject


def _builder():
    return {
        "generator": "contract_supply_chain_runtime_probe",
        "generatorVersion": "1.0.0",
        "builtAt": "2026-10-02T00:00:00+00:00",
    }


def _attestation(**overrides):
    signer = CHAIN.hmac_signer(b"offline-test-key", key_id="offline.test")
    return CHAIN.build_attestation(subject=_subject(**overrides), builder=_builder(), signer=signer)


def _reseal(document):
    """Recompute only the document digest, to isolate the signature path.

    The seal covers the signature envelope, so a naive tamper is caught by the
    digest first. Re-sealing is the honest forgery case ("tamper plus a
    consistent seal") and is what makes a ``signature_*`` reason reachable.
    """

    document["attestationDigest"] = CHAIN.attestation_digest(document)
    return document


class AttestationBaselineTest(unittest.TestCase):
    def test_baseline_attestation_verifies(self):
        document = _attestation()
        ok, reason = CHAIN.verify_attestation(document)
        self.assertTrue(ok, reason)
        self.assertEqual(reason, CHAIN.REASON_OK)

    def test_attestation_digest_is_stable_for_the_same_input(self):
        self.assertEqual(_attestation()["attestationDigest"], _attestation()["attestationDigest"])

    def test_chain_binds_every_required_subject_digest(self):
        bound = {field for _name, field in CHAIN.CHAIN_LINKS if field}
        for field in CHAIN.required_subject_hash_fields():
            self.assertIn(field, bound, "chain must bind %s" % field)
        self.assertIn("sourceRevision", bound)

    def test_expectations_match_the_attested_values(self):
        document = _attestation()
        ok, reason = CHAIN.verify_attestation(
            document,
            expected_artifact_sha256="c" * 64,
            expected_source_revision=REVISION,
            expected_deployment_runtime_sha=REVISION,
        )
        self.assertTrue(ok, reason)


class AttestationNegativeTest(unittest.TestCase):
    def test_artifact_built_from_another_revision_is_refused(self):
        ok, reason = CHAIN.verify_attestation(_attestation(artifactSourceRevision=OTHER_REVISION))
        self.assertFalse(ok)
        self.assertEqual(reason, "artifact_revision_mismatch")

    def test_deployed_runtime_sha_not_matching_the_revision_is_refused(self):
        ok, reason = CHAIN.verify_attestation(_attestation(deploymentRuntimeSha=OTHER_REVISION))
        self.assertFalse(ok)
        self.assertEqual(reason, "deployment_runtime_sha_mismatch")

    def test_truncated_source_revision_is_refused(self):
        ok, reason = CHAIN.verify_attestation(_attestation(sourceRevision=REVISION[:12],
                                                          artifactSourceRevision=REVISION[:12],
                                                          deploymentRuntimeSha=REVISION[:12]))
        self.assertFalse(ok)
        self.assertEqual(reason, "invalid_source_revision")

    def test_missing_subject_field_is_refused_by_name(self):
        document = _attestation()
        document["subject"].pop("artifactSha256")
        ok, reason = CHAIN.verify_attestation(document)
        self.assertFalse(ok)
        self.assertEqual(reason, "subject_missing:artifactSha256")

    def test_tampered_chain_link_is_refused(self):
        document = _attestation()
        document["chain"][2]["value"] = "d" * 64
        ok, reason = CHAIN.verify_attestation(document)
        self.assertFalse(ok)
        self.assertIn(reason, ("chain_link_not_subject_bound:artifact", "chain_digest_mismatch:artifact",
                               "chain_predecessor_mismatch:deploymentRuntime"))

    def test_reordered_chain_is_refused(self):
        document = _attestation()
        document["chain"] = [document["chain"][0], *reversed(document["chain"][1:])]
        ok, reason = CHAIN.verify_attestation(document)
        self.assertFalse(ok)
        self.assertIn(reason, ("chain_order_mismatch", "chain_predecessor_mismatch:sourceRevision"))

    def test_tampered_subject_without_reseal_is_refused(self):
        document = _attestation()
        document["subject"]["moduleVersion"] = "17.0.1.1.99"
        ok, reason = CHAIN.verify_attestation(document)
        self.assertFalse(ok)
        self.assertEqual(reason, "attestation_digest_mismatch")

    def test_wrong_signature_is_refused(self):
        document = _attestation()
        document["signature"]["signature"] = "0" * 64
        _reseal(document)
        ok, reason = CHAIN.verify_attestation(document)
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_invalid")

    def test_expected_artifact_mismatch_is_refused(self):
        ok, reason = CHAIN.verify_attestation(_attestation(), expected_artifact_sha256="e" * 64)
        self.assertFalse(ok)
        self.assertEqual(reason, "expected_artifact_sha256_mismatch")

    def test_empty_document_is_refused(self):
        ok, reason = CHAIN.verify_attestation({})
        self.assertFalse(ok)
        self.assertEqual(reason, "unsupported_attestation_version")

    def test_missing_signature_is_refused(self):
        document = _attestation()
        document.pop("signature")
        _reseal(document)
        ok, reason = CHAIN.verify_attestation(document)
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_missing")

    def test_tampering_the_signature_alone_is_caught_by_the_seal(self):
        document = _attestation()
        document["signature"]["signature"] = "0" * 64
        ok, reason = CHAIN.verify_attestation(document)
        self.assertFalse(ok)
        self.assertEqual(reason, "attestation_digest_mismatch")


class AttestationSchemeBoundaryTest(unittest.TestCase):
    def test_secret_scheme_is_refused_when_a_public_key_is_required(self):
        document = _attestation()
        ok, reason = CHAIN.verify_attestation(document, require_public_key=True)
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_scheme_key_not_publishable")

    def test_an_asymmetric_scheme_can_be_registered_and_consumed(self):
        def verifier(signature_hex: str, payload: bytes, public_key_hex: str) -> bool:
            expected = CHAIN.digest_of([public_key_hex, payload.decode("utf-8")])
            return expected == signature_hex

        CHAIN.register_verifier("test-asymmetric", verifier, public_key=True)

        class Signer:
            scheme = "test-asymmetric"

            def sign(self, payload: bytes) -> dict:
                return {
                    "scheme": self.scheme,
                    "keyId": "test.public",
                    "publicKey": "9" * 64,
                    "signature": CHAIN.digest_of(["9" * 64, payload.decode("utf-8")]),
                }

        document = CHAIN.build_attestation(subject=_subject(), builder=_builder(), signer=Signer())
        ok, reason = CHAIN.verify_attestation(document, require_public_key=True)
        self.assertTrue(ok, reason)
        document["signature"]["signature"] = "8" * 64
        _reseal(document)
        ok, reason = CHAIN.verify_attestation(document)
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_invalid")


class AttestationCoreBoundaryTest(unittest.TestCase):
    def test_core_imports_no_odoo(self):
        tree = ast.parse(CORE_PATH.read_text(encoding="utf-8"))
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        self.assertNotIn("odoo", roots, "the attestation core must stay offline-verifiable")


if __name__ == "__main__":
    unittest.main()
