# -*- coding: utf-8 -*-
"""Runtime half of the contract supply-chain attestation gap.

Run with:
  make verify.backend.contract_supply_chain.runtime

Executed by ``odoo shell`` against the isolated contract-lifecycle profile. It
builds a real attestation for the *running* deployment:

* the protocol schema digest and a real ``ui.contract.v2`` delivery's contract
  digest come from the production handler on this database;
* the artifact digest is recomputed from the module source the container
  actually loaded, so it cannot be asserted from a narrative;
* the deployment runtime SHA comes from the deployed runtime identity, which the
  governed profile declares through ``SC_SOURCE_REVISION``;
* the document is signed with an ephemeral, in-process Ed25519 key pair whose
  public key is embedded, so the attestation is verifiable without any shared
  secret and without minting a stored credential.

Baseline first: the honest attestation must verify before any tampering is
treated as detected. Every negative then tampers exactly one binding and must be
refused with the owning reason code.

Trust boundary: this is a self-signed attestation. It proves artifact/schema/
contract/revision/runtime consistency and tamper-evidence; it does not prove
*who* built the artifact, because no external identity or trust root is
consulted.
"""

import json
from hashlib import sha256
from pathlib import Path

from odoo.addons.smart_core.core import contract_lifecycle as lifecycle
from odoo.addons.smart_core.core import contract_supply_chain_attestation as attest
from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler
from odoo.addons.smart_core.utils.product_release import runtime_release_identity


PROBE_PATH = "/tmp/contract_supply_chain_runtime_probe.json"
PROBE_NAME = "contract_supply_chain_runtime_probe"
PROBE_SCHEMA_VERSION = "1.0.0"
MODULE_NAME = "smart_core"
OTHER_REVISION = "0" * 40


def _env():
    return globals()["env"]


def _module_version():
    _env().cr.execute(
        "SELECT latest_version FROM ir_module_module WHERE name = %s", [MODULE_NAME]
    )
    row = _env().cr.fetchone()
    return str(row[0] or "").strip() if row else ""


def _module_root():
    import odoo.addons.smart_core as module

    return Path(module.__file__).resolve().parent


def _artifact_digest(root):
    """Content digest of the module the container actually loaded."""

    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        entries.append([str(path.relative_to(root)), sha256(path.read_bytes()).hexdigest()])
    return sha256(attest.canonical_json(entries).encode("utf-8")).hexdigest(), len(entries)


def _ed25519_signer():
    """Register a real, publicly verifiable scheme from the optional dependency."""

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ed25519

    def verifier(signature_hex, payload, public_key_hex):
        try:
            public = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
            public.verify(bytes.fromhex(signature_hex), payload)
            return True
        except Exception:
            return False

    attest.register_verifier(attest.SCHEME_ED25519, verifier, public_key=True)

    class _Signer:
        scheme = attest.SCHEME_ED25519

        def __init__(self):
            self._key = ed25519.Ed25519PrivateKey.generate()

        def sign(self, payload):
            public = self._key.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
            return {
                "scheme": self.scheme,
                "keyId": "contract.supplychain.ephemeral",
                "publicKey": public.hex(),
                "signature": self._key.sign(payload).hex(),
            }

    return _Signer()


def _deliver(request):
    handler = UiContractV2Handler(env=_env(), su_env=_env())
    result = handler.handle(payload={"params": dict(request)}, ctx=dict(_env().context or {}))
    envelope = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
    return envelope if isinstance(envelope, dict) else {}


def _delivered_lifecycle(envelope):
    data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    lifecycle_evidence = meta.get("lifecycle") if isinstance(meta.get("lifecycle"), dict) else {}
    return data, lifecycle_evidence


def _run():
    checks = []
    identity = runtime_release_identity(_env().cr.dbname)
    deployed_revision = str(identity.get("source_revision") or "").strip()
    module_version = _module_version()

    checks.append(("deployment_identity_is_a_real_revision",
                   deployed_revision != "unknown" and len(deployed_revision) == 40,
                   {"sourceRevision": deployed_revision}))
    checks.append(("module_version_declared", bool(module_version), {"moduleVersion": module_version}))

    root = _module_root()
    artifact_sha256, file_count = _artifact_digest(root)
    again, _count = _artifact_digest(root)
    checks.append(("artifact_digest_is_stable", artifact_sha256 == again, {"artifactSha256": artifact_sha256}))
    checks.append(("artifact_digest_covers_the_loaded_module", file_count > 50,
                   {"fileCount": file_count, "root": str(root)}))

    request = {
        "model": "res.partner",
        "view_type": "form",
        "source_type": "ui.contract",
        "client_type": "web_pc",
        "delivery_profile": "full",
        "force_refresh": True,
    }
    envelope = _deliver(request)
    contract, evidence = _delivered_lifecycle(envelope)
    definition = evidence.get("definition") if isinstance(evidence.get("definition"), dict) else {}
    integrity = evidence.get("integrity") if isinstance(evidence.get("integrity"), dict) else {}
    contract_sha256 = str(integrity.get("contractSha256") or "")
    schema_sha256 = str(definition.get("schemaSha256") or "")
    checks.append(("real_delivery_is_sealed", bool(envelope.get("ok")) and bool(contract_sha256),
                   {"ok": bool(envelope.get("ok")), "contractSha256": contract_sha256}))
    checks.append(("delivery_schema_digest_matches_the_authority",
                   schema_sha256 == lifecycle.UNIFIED_PAGE_SCHEMA_SHA256,
                   {"schemaSha256": schema_sha256,
                    "authority": lifecycle.UNIFIED_PAGE_SCHEMA_SHA256}))
    reseal_ok, reseal_reason = lifecycle.verify_unified_page_contract_integrity(contract)
    checks.append(("delivery_integrity_is_recomputable", bool(reseal_ok), {"reason": reseal_reason}))

    signer = _ed25519_signer()
    subject = {
        "schemaId": lifecycle.UNIFIED_PAGE_SCHEMA_ID,
        "schemaVersion": lifecycle.UNIFIED_PAGE_SCHEMA_VERSION,
        "schemaSha256": schema_sha256,
        "contractSha256": contract_sha256,
        "sourceRevision": deployed_revision,
        "artifactSourceRevision": deployed_revision,
        "artifactSha256": artifact_sha256,
        "moduleVersion": module_version,
        "productVersion": str(identity.get("product_version") or ""),
        "deploymentDatabase": str(identity.get("database") or ""),
        "deploymentRuntimeSha": deployed_revision,
    }
    builder = {
        "generator": PROBE_NAME,
        "generatorVersion": PROBE_SCHEMA_VERSION,
        "builtAt": _timestamp(),
    }
    document = attest.build_attestation(subject=subject, builder=builder, signer=signer)

    ok, reason = attest.verify_attestation(document, require_public_key=True)
    checks.append(("attestation_verifies_with_a_publishable_key", bool(ok), {"reason": reason}))
    ok_bind, reason_bind = attest.verify_attestation(
        document,
        require_public_key=True,
        expected_artifact_sha256=artifact_sha256,
        expected_source_revision=deployed_revision,
        expected_deployment_runtime_sha=deployed_revision,
    )
    checks.append(("attestation_binds_the_running_artifact_and_revision",
                   bool(ok_bind), {"reason": reason_bind}))

    # Negative 1: an artifact digest that does not match the running code.
    tampered = _resign(document, {"artifactSha256": "f" * 64}, signer)
    ok_t, reason_t = attest.verify_attestation(tampered, expected_artifact_sha256=artifact_sha256)
    checks.append(("tampered_artifact_digest_is_refused",
                   (not ok_t) and reason_t == "expected_artifact_sha256_mismatch",
                   {"reason": reason_t}))

    # Negative 2: the artifact was built from a different revision than the one
    # that is deployed. Chain and seal are consistent, so only the unification
    # rule can catch it.
    tampered = _resign(document, {
        "artifactSourceRevision": OTHER_REVISION,
        "deploymentRuntimeSha": OTHER_REVISION,
    }, signer)
    ok_t, reason_t = attest.verify_attestation(tampered)
    checks.append(("revision_that_does_not_match_the_deployment_is_refused",
                   (not ok_t) and reason_t == "artifact_revision_mismatch",
                   {"reason": reason_t}))

    # Negative 3: a deployment SHA that is not the attested revision.
    tampered = _resign(document, {"deploymentRuntimeSha": OTHER_REVISION}, signer)
    ok_t, reason_t = attest.verify_attestation(tampered)
    checks.append(("deployment_sha_outside_the_attested_revision_is_refused",
                   (not ok_t) and reason_t == "deployment_runtime_sha_mismatch",
                   {"reason": reason_t}))

    # Negative 4: a secret-key scheme must not be accepted as a runtime proof.
    secret_document = attest.build_attestation(
        subject=subject, builder=builder, signer=attest.hmac_signer(b"probe-secret", key_id="probe.hmac")
    )
    ok_t, reason_t = attest.verify_attestation(secret_document, require_public_key=True)
    checks.append(("secret_key_scheme_is_refused_for_a_runtime_attestation",
                   (not ok_t) and reason_t == "signature_scheme_key_not_publishable",
                   {"reason": reason_t}))

    # Negative 5: a signature that no longer covers the (re-sealed) document.
    forged = json.loads(json.dumps(document))
    forged["signature"]["signature"] = "0" * 128
    forged["attestationDigest"] = attest.attestation_digest(forged)
    ok_t, reason_t = attest.verify_attestation(forged)
    checks.append(("forged_signature_is_refused",
                   (not ok_t) and reason_t == "signature_invalid", {"reason": reason_t}))

    failed = [name for name, ok, _detail in checks if not ok]
    return {
        "probe": PROBE_NAME,
        "schemaVersion": PROBE_SCHEMA_VERSION,
        "database": _env().cr.dbname,
        "moduleVersion": module_version,
        "sourceRevision": deployed_revision,
        "artifactSha256": artifact_sha256,
        "artifactFileCount": file_count,
        "delivery": {"model": request["model"], "viewType": request["view_type"],
                     "contractSha256": contract_sha256, "schemaSha256": schema_sha256},
        "attestationDigest": document.get("attestationDigest"),
        "attestation": document,
        "checkCount": len(checks),
        "failedCount": len(failed),
        "failed": failed,
        "checks": [{"name": name, "ok": ok, "detail": _detail} for name, ok, _detail in checks],
    }


def _timestamp():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resign(document, overrides, signer):
    """Rebuild a *consistent* forgery: overrides, re-chained, re-signed."""

    body = json.loads(json.dumps(document))
    body["subject"].update(overrides)
    body["chain"] = attest.build_chain(body["subject"], body["builder"])
    body.pop("attestationDigest", None)
    body["signature"] = signer.sign(attest.signature_payload(body))
    body["attestationDigest"] = attest.attestation_digest(body)
    return body


def main():
    report = _run()
    with open(PROBE_PATH, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
    print("CONTRACT_SUPPLY_CHAIN_RUNTIME_PROBE=%s checks=%d failed=%d"
          % ("PASS" if report["failedCount"] == 0 else "FAIL",
             report["checkCount"], report["failedCount"]))
    if report["failedCount"]:
        print("CONTRACT_SUPPLY_CHAIN_RUNTIME_PROBE_FAILED=" + ",".join(report["failed"]))


main()
