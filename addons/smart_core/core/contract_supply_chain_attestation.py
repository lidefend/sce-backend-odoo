# -*- coding: utf-8 -*-
"""Contract supply-chain attestation core.

The second L5 gap of the backend contract lifecycle is the missing unified
supply-chain proof: a single signed artifact that binds the protocol schema, the
governed contract definition, the built artifact, the source revision and the
*deployed runtime SHA* together, so "what is running" can be tied to "what was
built from which revision" without trusting a narrative.

This module owns the pure half of that feature. It builds and verifies a
canonical, digest-linked attestation document with a pluggable signature scheme:

* ``build_attestation`` assembles ``subject`` + ``builder`` + an ordered
  ``chain`` and signs it;
* ``verify_attestation`` recomputes every digest, re-derives the chain, enforces
  the unification invariants and verifies the signature, failing closed with a
  specific reason code;
* ``register_verifier`` lets a caller contribute a scheme (for example an
  asymmetric ``ed25519`` verifier that keeps the core dependency-free).

It imports nothing from Odoo so the semantics stay offline-verifiable.

Trust model (declared, not implied). The attestation is self-signed: the
signature proves the document was produced by the holder of the signing key and
that no digest, chain link or bound field was altered afterwards. It does not
prove *who* built the artifact, because no external identity/trust root is
consulted, and it does not make the deployment tamper-proof. A scheme whose key
material is a secret (``hmac-sha256``) is marked non-publishable and is only
meant for offline tests; a runtime attestation should use an asymmetric scheme
whose public key is safe to embed.
"""
from __future__ import annotations

import hmac
import json
import re
from hashlib import sha256
from typing import Any, Callable, Sequence


ATTESTATION_VERSION = "1.0.0"
DIGEST_ALGORITHM = "sha256"

SCHEME_HMAC_SHA256 = "hmac-sha256"
SCHEME_ED25519 = "ed25519"

# A scheme is publishable when its key material is a public key: embedding it in
# the document leaks nothing. A secret-key scheme is intentionally not
# publishable, so a runtime attestation cannot silently degrade to a shared
# secret that every verifier would need to hold.
_SCHEME_KEY_PUBLIC = {
    SCHEME_HMAC_SHA256: False,
    SCHEME_ED25519: True,
}

# Ordered provenance links. Each link binds one subject field, so the chain and
# the subject cannot disagree; ``builder`` binds the builder descriptor digest.
CHAIN_LINKS = (
    ("schema", "schemaSha256"),
    ("contract", "contractSha256"),
    ("artifact", "artifactSha256"),
    ("sourceRevision", "sourceRevision"),
    ("deploymentRuntime", "deploymentRuntimeSha"),
    ("builder", None),
)
CHAIN_LINK_NAMES = tuple(name for name, _field in CHAIN_LINKS)

REQUIRED_SUBJECT_FIELDS = (
    "schemaId",
    "schemaVersion",
    "schemaSha256",
    "contractSha256",
    "sourceRevision",
    "artifactSourceRevision",
    "artifactSha256",
    "moduleVersion",
    "productVersion",
    "deploymentDatabase",
    "deploymentRuntimeSha",
)
REQUIRED_BUILDER_FIELDS = ("generator", "generatorVersion", "builtAt")

REASON_OK = "ok"

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")

_VERIFIERS: dict[str, Callable[[str, bytes, str], bool]] = {}


class AttestationError(ValueError):
    """Raised when an attestation cannot be assembled from the given inputs."""


def canonical_json(value: Any) -> str:
    """Deterministic JSON the digest is taken over (sorted keys, no padding)."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_of(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def register_verifier(
    scheme: str,
    verifier: Callable[[str, bytes, str], bool],
    *,
    public_key: bool = False,
) -> None:
    """Register ``verifier(signature_hex, payload_bytes, public_key_hex) -> bool``.

    ``public_key`` declares whether the scheme's embedded key material is safe to
    publish; it is what ``require_public_key`` is checked against.
    """

    if not callable(verifier):
        raise AttestationError("verifier must be callable")
    name = str(scheme).strip()
    if not name:
        raise AttestationError("scheme name must be non-empty")
    _VERIFIERS[name] = verifier
    _SCHEME_KEY_PUBLIC[name] = bool(public_key)


def registered_schemes() -> tuple[str, ...]:
    return tuple(sorted(_VERIFIERS))


def _hmac_verifier(signature_hex: str, payload: bytes, key_hex: str) -> bool:
    try:
        key = bytes.fromhex(key_hex)
    except ValueError:
        return False
    expected = hmac.new(key, payload, sha256).hexdigest()
    return hmac.compare_digest(expected, signature_hex)


register_verifier(SCHEME_HMAC_SHA256, _hmac_verifier)


def scheme_key_is_public(scheme: str) -> bool:
    return bool(_SCHEME_KEY_PUBLIC.get(str(scheme).strip(), False))


def hmac_signer(secret: bytes, *, key_id: str) -> "HmacSigner":
    """Deterministic, stdlib-only signer for offline verification."""

    return HmacSigner(secret, key_id=key_id)


class HmacSigner:
    """Signs with a shared secret; not publishable, intended for offline tests."""

    scheme = SCHEME_HMAC_SHA256

    def __init__(self, secret: bytes, *, key_id: str):
        if not isinstance(secret, (bytes, bytearray)) or not secret:
            raise AttestationError("hmac signer requires non-empty key bytes")
        self._secret = bytes(secret)
        self._key_id = str(key_id or "").strip() or "hmac.local"

    def sign(self, payload: bytes) -> dict[str, str]:
        return {
            "scheme": self.scheme,
            "keyId": self._key_id,
            "publicKey": self._secret.hex(),
            "signature": hmac.new(self._secret, payload, sha256).hexdigest(),
        }


def signature_payload(document: dict[str, Any]) -> bytes:
    """Bytes the signature covers: the document without its signature envelope."""

    body = {key: value for key, value in document.items() if key != "signature"}
    body.pop("attestationDigest", None)
    return canonical_json(body).encode("utf-8")


def attestation_digest(document: dict[str, Any]) -> str:
    body = {key: value for key, value in document.items() if key != "attestationDigest"}
    return digest_of(body)


def append_link(chain: Sequence[dict[str, Any]], name: str, value: str) -> list[dict[str, Any]]:
    previous = str(chain[-1]["digest"]) if chain else ""
    link = {"name": str(name), "value": str(value), "previous": previous}
    link["digest"] = digest_of(link)
    return [*chain, link]


def build_chain(subject: dict[str, Any], builder: dict[str, Any]) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    for name, field in CHAIN_LINKS:
        value = digest_of(builder) if field is None else str(subject.get(field) or "")
        chain = append_link(chain, name, value)
    return chain


def chain_digest(chain: Sequence[dict[str, Any]]) -> str:
    return digest_of(list(chain))


def build_attestation(
    *,
    subject: dict[str, Any],
    builder: dict[str, Any],
    signer: Any,
) -> dict[str, Any]:
    """Assemble and sign the attestation document."""

    if not isinstance(subject, dict) or not isinstance(builder, dict):
        raise AttestationError("subject and builder must be objects")
    missing = [field for field in REQUIRED_SUBJECT_FIELDS if not str(subject.get(field) or "").strip()]
    if missing:
        raise AttestationError("subject missing fields: " + ",".join(missing))
    missing_builder = [field for field in REQUIRED_BUILDER_FIELDS if not str(builder.get(field) or "").strip()]
    if missing_builder:
        raise AttestationError("builder missing fields: " + ",".join(missing_builder))
    if not hasattr(signer, "sign"):
        raise AttestationError("signer must expose sign(payload) -> signature envelope")
    document = {
        "attestationVersion": ATTESTATION_VERSION,
        "digestAlgorithm": DIGEST_ALGORITHM,
        "subject": dict(subject),
        "builder": dict(builder),
        "chain": build_chain(subject, builder),
    }
    envelope = signer.sign(signature_payload(document))
    envelope = dict(envelope) if isinstance(envelope, dict) else {}
    for field in ("scheme", "keyId", "signature"):
        if not str(envelope.get(field) or "").strip():
            raise AttestationError("signer envelope missing " + field)
    envelope.setdefault("publicKey", "")
    document["signature"] = envelope
    document["attestationDigest"] = attestation_digest(document)
    return document


def _verify_chain(document: dict[str, Any]) -> str:
    chain = document.get("chain")
    if not isinstance(chain, list) or not chain:
        return "chain_missing"
    names = [str(link.get("name") or "") for link in chain if isinstance(link, dict)]
    if len(names) != len(chain):
        return "chain_link_not_object"
    for name in CHAIN_LINK_NAMES:
        if name not in names:
            return "chain_link_missing:" + name
    for name in names:
        if name not in CHAIN_LINK_NAMES:
            return "chain_link_unexpected:" + name
    if names != list(CHAIN_LINK_NAMES):
        return "chain_order_mismatch"
    subject = document.get("subject") if isinstance(document.get("subject"), dict) else {}
    builder = document.get("builder") if isinstance(document.get("builder"), dict) else {}
    expected_values = {
        name: (digest_of(builder) if field is None else str(subject.get(field) or ""))
        for name, field in CHAIN_LINKS
    }
    previous = ""
    for link in chain:
        name = str(link["name"])
        if str(link.get("value") or "") != expected_values[name]:
            return "chain_link_not_subject_bound:" + name
        if str(link.get("previous") or "") != previous:
            return "chain_predecessor_mismatch:" + name
        recomputed = digest_of({"name": name, "value": link.get("value"), "previous": link.get("previous")})
        if recomputed != str(link.get("digest") or ""):
            return "chain_digest_mismatch:" + name
        previous = recomputed
    return REASON_OK


def verify_attestation(
    document: Any,
    *,
    require_public_key: bool = False,
    expected_artifact_sha256: str = "",
    expected_source_revision: str = "",
    expected_deployment_runtime_sha: str = "",
) -> tuple[bool, str]:
    """Fail-closed verification. Returns ``(ok, reason_code)``.

    ``require_public_key`` rejects a secret-key scheme, so a runtime attestation
    cannot be accepted when it is not independently verifiable.
    """

    if not isinstance(document, dict):
        return False, "attestation_not_object"
    if str(document.get("attestationVersion") or "") != ATTESTATION_VERSION:
        return False, "unsupported_attestation_version"
    if str(document.get("digestAlgorithm") or "") != DIGEST_ALGORITHM:
        return False, "unsupported_digest_algorithm"
    subject = document.get("subject")
    builder = document.get("builder")
    if not isinstance(subject, dict):
        return False, "subject_not_object"
    if not isinstance(builder, dict):
        return False, "builder_not_object"
    for field in REQUIRED_SUBJECT_FIELDS:
        if not str(subject.get(field) or "").strip():
            return False, "subject_missing:" + field
    for field in REQUIRED_BUILDER_FIELDS:
        if not str(builder.get(field) or "").strip():
            return False, "builder_missing:" + field
    if not _HEX40.fullmatch(str(subject.get("sourceRevision") or "")):
        return False, "invalid_source_revision"
    if not _HEX40.fullmatch(str(subject.get("artifactSourceRevision") or "")):
        return False, "invalid_artifact_source_revision"
    if not _HEX40.fullmatch(str(subject.get("deploymentRuntimeSha") or "")):
        return False, "invalid_digest:deploymentRuntimeSha"
    for field in ("schemaSha256", "contractSha256", "artifactSha256"):
        if not _HEX64.fullmatch(str(subject.get(field) or "")):
            return False, "invalid_digest:" + field
    # Unification invariants: one revision built the artifact and is what runs.
    if str(subject["artifactSourceRevision"]) != str(subject["sourceRevision"]):
        return False, "artifact_revision_mismatch"
    if str(subject["deploymentRuntimeSha"]) != str(subject["sourceRevision"]):
        return False, "deployment_runtime_sha_mismatch"
    if expected_artifact_sha256 and str(expected_artifact_sha256) != str(subject["artifactSha256"]):
        return False, "expected_artifact_sha256_mismatch"
    if expected_source_revision and str(expected_source_revision) != str(subject["sourceRevision"]):
        return False, "expected_source_revision_mismatch"
    if expected_deployment_runtime_sha and str(expected_deployment_runtime_sha) != str(subject["deploymentRuntimeSha"]):
        return False, "expected_deployment_runtime_sha_mismatch"
    chain_reason = _verify_chain(document)
    if chain_reason != REASON_OK:
        return False, chain_reason
    if str(document.get("attestationDigest") or "") != attestation_digest(document):
        return False, "attestation_digest_mismatch"
    envelope = document.get("signature")
    if not isinstance(envelope, dict):
        return False, "signature_missing"
    scheme = str(envelope.get("scheme") or "").strip()
    if scheme not in _SCHEME_KEY_PUBLIC:
        return False, "unsupported_signature_scheme"
    if require_public_key and not scheme_key_is_public(scheme):
        return False, "signature_scheme_key_not_publishable"
    verifier = _VERIFIERS.get(scheme)
    if verifier is None:
        return False, "signature_verifier_unregistered:" + scheme
    if verifier(str(envelope.get("signature") or ""), signature_payload(document), str(envelope.get("publicKey") or "")):
        return True, REASON_OK
    return False, "signature_invalid"


def required_subject_hash_fields() -> tuple[str, ...]:
    """Declaration consumed by the runtime guard instead of a duplicated list.

    Three 64-hex content digests plus the 40-hex deployed revision: the runtime
    guard asserts the chain binds exactly these, so a chain that silently drops
    the deployment identity cannot pass.
    """

    return ("schemaSha256", "contractSha256", "artifactSha256", "deploymentRuntimeSha")
