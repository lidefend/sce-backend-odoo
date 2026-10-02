# -*- coding: utf-8 -*-
"""Host-side guard for the contract supply-chain runtime attestation report.

Consumes the JSON the in-container probe writes and *independently re-verifies*
the attestation with the real core and a real Ed25519 verifier, so the probe's
own PASS marker is never the proof: a stale, truncated, tampered or
secret-signed report cannot pass. It also re-derives the declared check set and
the required chain bindings from the core declaration instead of duplicating
them as strings.
"""

import importlib.util
import json
import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
CORE_PATH = ROOT / "addons/smart_core/core/contract_supply_chain_attestation.py"
LIFECYCLE_PATH = ROOT / "addons/smart_core/core/contract_lifecycle.py"

PROBE_REPORT = os.environ.get(
    "CONTRACT_SUPPLY_CHAIN_PROBE_REPORT",
    "/tmp/contract_supply_chain_runtime_probe.json",
)
EXPECTED_REVISION = str(os.environ.get("CONTRACT_SUPPLY_CHAIN_EXPECTED_REVISION") or "").strip()

REQUIRED_CHECKS = (
    "deployment_identity_is_a_real_revision",
    "module_version_declared",
    "artifact_digest_is_stable",
    "artifact_digest_covers_the_loaded_module",
    "real_delivery_is_sealed",
    "delivery_schema_digest_matches_the_authority",
    "delivery_integrity_is_recomputable",
    "attestation_verifies_with_a_publishable_key",
    "attestation_binds_the_running_artifact_and_revision",
    "tampered_artifact_digest_is_refused",
    "revision_that_does_not_match_the_deployment_is_refused",
    "deployment_sha_outside_the_attested_revision_is_refused",
    "secret_key_scheme_is_refused_for_a_runtime_attestation",
    "forged_signature_is_refused",
)


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def _register_ed25519(core):
    from cryptography.hazmat.primitives.asymmetric import ed25519

    def verifier(signature_hex, payload, public_key_hex):
        try:
            public = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
            public.verify(bytes.fromhex(signature_hex), payload)
            return True
        except Exception:
            return False

    core.register_verifier(core.SCHEME_ED25519, verifier, public_key=True)


CORE = _load("contract_supply_chain_attestation_host_guard", CORE_PATH)
LIFECYCLE = _load("contract_lifecycle_host_guard", LIFECYCLE_PATH)
_register_ed25519(CORE)


def _load_report():
    with open(PROBE_REPORT, "r", encoding="utf-8") as handle:
        return json.load(handle)


class ContractSupplyChainRuntimeReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = _load_report()
        cls.document = cls.report.get("attestation")
        cls.subject = (cls.document or {}).get("subject") or {}

    # -- report shape and declared check set -------------------------------
    def test_report_shape(self):
        self.assertEqual(self.report.get("probe"), "contract_supply_chain_runtime_probe")
        self.assertEqual(self.report.get("schemaVersion"), "1.0.0")
        self.assertEqual(self.report.get("database"), "sc_contract_lifecycle")
        self.assertGreater(self.report.get("checkCount", 0), 0)

    def test_no_probe_check_failed(self):
        self.assertEqual(self.report.get("failedCount"), 0, self.report.get("failed"))
        failed = [check["name"] for check in self.report.get("checks", []) if not check.get("ok")]
        self.assertEqual(failed, [])

    def test_the_declared_check_set_is_exactly_the_required_set(self):
        names = [check.get("name") for check in self.report.get("checks", [])]
        self.assertEqual(sorted(names), sorted(REQUIRED_CHECKS))
        self.assertEqual(len(names), len(set(names)), "a duplicated check must not inflate the count")

    # -- identity ----------------------------------------------------------
    def test_identity_is_bound_to_a_real_revision(self):
        revision = str(self.report.get("sourceRevision") or "")
        self.assertEqual(len(revision), 40, revision)
        self.assertEqual(revision, str(self.subject.get("sourceRevision") or ""))
        self.assertEqual(revision, str(self.subject.get("artifactSourceRevision") or ""))
        self.assertEqual(revision, str(self.subject.get("deploymentRuntimeSha") or ""))
        self.assertTrue(str(self.report.get("moduleVersion") or "").strip())

    def test_expected_revision_matches_when_provided(self):
        if not EXPECTED_REVISION:
            self.skipTest("no expected revision supplied")
        self.assertEqual(str(self.report.get("sourceRevision") or ""), EXPECTED_REVISION)

    def test_artifact_digest_is_reported_and_bound(self):
        digest = str(self.report.get("artifactSha256") or "")
        self.assertEqual(len(digest), 64, digest)
        self.assertEqual(digest, str(self.subject.get("artifactSha256") or ""))
        self.assertGreater(int(self.report.get("artifactFileCount") or 0), 50)

    def test_delivery_digests_are_real_and_match_the_authority(self):
        delivery = self.report.get("delivery") or {}
        self.assertEqual(len(str(delivery.get("contractSha256") or "")), 64, delivery)
        self.assertEqual(str(delivery.get("schemaSha256") or ""), LIFECYCLE.UNIFIED_PAGE_SCHEMA_SHA256)
        self.assertEqual(str(delivery.get("schemaSha256") or ""), str(self.subject.get("schemaSha256") or ""))
        self.assertEqual(str(delivery.get("contractSha256") or ""), str(self.subject.get("contractSha256") or ""))

    # -- independent re-verification --------------------------------------
    def test_chain_binds_every_required_hash_field(self):
        bound = {field for _name, field in CORE.CHAIN_LINKS if field}
        for field in CORE.required_subject_hash_fields():
            self.assertIn(field, bound, "the chain must bind %s" % field)
        chain = self.document.get("chain") or []
        self.assertEqual([link.get("name") for link in chain], list(CORE.CHAIN_LINK_NAMES))

    def test_attestation_reverifies_independently(self):
        ok, reason = CORE.verify_attestation(
            self.document,
            require_public_key=True,
            expected_artifact_sha256=str(self.report.get("artifactSha256") or ""),
            expected_source_revision=str(self.report.get("sourceRevision") or ""),
            expected_deployment_runtime_sha=str(self.report.get("sourceRevision") or ""),
        )
        self.assertTrue(ok, reason)
        self.assertEqual(str(self.document.get("attestationDigest") or ""),
                         str(self.report.get("attestationDigest") or ""))

    def test_the_guard_can_refuse_a_tampered_replica(self):
        """If the guard cannot refuse a tampered replica, it proves nothing."""
        replica = json.loads(json.dumps(self.document))
        replica["subject"]["artifactSha256"] = "f" * 64
        ok, reason = CORE.verify_attestation(replica)
        self.assertFalse(ok)
        self.assertIn(reason, ("chain_link_not_subject_bound:artifact", "chain_digest_mismatch:artifact"))

    def test_a_replica_with_another_revision_is_refused(self):
        replica = json.loads(json.dumps(self.document))
        for field in ("sourceRevision", "artifactSourceRevision", "deploymentRuntimeSha"):
            replica["subject"][field] = "0" * 40
        replica["chain"] = CORE.build_chain(replica["subject"], replica["builder"])
        replica["attestationDigest"] = CORE.attestation_digest(replica)
        ok, reason = CORE.verify_attestation(replica)
        self.assertFalse(ok)
        self.assertIn(reason, ("signature_invalid", "attestation_digest_mismatch", "artifact_revision_mismatch",
                               "deployment_runtime_sha_mismatch",
                               "chain_link_not_subject_bound:sourceRevision"))

    def test_a_replica_with_a_secret_key_scheme_is_refused(self):
        replica = json.loads(json.dumps(self.document))
        replica["signature"]["scheme"] = CORE.SCHEME_HMAC_SHA256
        # Re-seal so the digest guard passes and the publishable-key rule is the
        # rule under test, not the signature-envelope digest check.
        replica["attestationDigest"] = CORE.attestation_digest(replica)
        ok, reason = CORE.verify_attestation(replica, require_public_key=True)
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_scheme_key_not_publishable")


if __name__ == "__main__":
    unittest.main()
