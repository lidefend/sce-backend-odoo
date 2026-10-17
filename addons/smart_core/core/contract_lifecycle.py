# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
from typing import Any


LIFECYCLE_VERSION = "1.0.0"
HASH_ALGORITHM = "sha256"
UNIFIED_PAGE_SCHEMA_ID = "smart_core.unified_page_contract_v2"
UNIFIED_PAGE_SCHEMA_VERSION = "2.2.0"
UNIFIED_PAGE_SCHEMA_SHA256 = "708dc5ed8da9959d91a84b8c6976d708983f47c73b92a32859727bbccc285071"
UNIFIED_PAGE_NORMATIVE_STATUS = "stable"
_PROTOCOL_ID_INVALID = re.compile(r"[^a-zA-Z0-9_.:-]+")
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _delivery_default(value: Any) -> Any:
    """Serialize a non JSON-native value the way the delivery layer does.

    The integrity digest must stay recomputable from the bytes the client
    receives.  Odoo shrinks datetimes to whole seconds on delivery
    (``fields.Datetime.to_string``), so hashing the raw in-memory value, which
    can carry microseconds, would make the seal unverifiable from the response.
    Delegate to the delivery serializer when it is importable and keep a
    dependency-free fallback for standalone use.
    """
    try:
        from odoo.tools import date_utils

        return date_utils.json_default(value)
    except Exception:
        pass
    if isinstance(value, datetime):
        return value.strftime(DATETIME_FORMAT)
    return str(value)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=_delivery_default,
    )


def payload_sha256(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def protocol_id(value: Any, *, prefix: str) -> str:
    normalized = _PROTOCOL_ID_INVALID.sub(".", str(value or "").strip()).strip(".")
    if not normalized:
        normalized = prefix
    if not normalized[0].isalpha():
        normalized = f"{prefix}.{normalized}"
    return normalized


# A delivered contract echoes the live request context (``dataContract.dataMeta.
# sourceContext.context`` and ``dataSource.primary.params.context``), and that
# context carries the request transport identity the intent dispatcher injects
# (``intent_dispatcher`` sets ``context_in["trace_id"]``). Business context is
# authoritative and stays in the delivered payload, but a per-request transport
# identifier must not enter the sealed semantic payload: otherwise
# ``contractSha256``, ``etag`` and ``snapshotId`` change on every read and the
# seal stops identifying a contract (no version aggregation, no reproducible
# acceptance receipt). Transport identity remains available under
# ``meta.lifecycle.runtime``.
REQUEST_TRANSPORT_CONTEXT_KEYS = ("trace_id", "request_id")


def strip_request_transport_identity(value: Any) -> Any:
    """Return ``value`` with transport identity removed from ``context`` containers.

    The result is copy-on-write: any subtree that contains no transport key is
    returned by reference because the only consumer (canonical JSON hashing)
    never mutates it.  The previous unconditional deep-copy walked and allocated
    the whole delivered contract on every seal, which was a material part of the
    record-form hot path.  Callers that mutate the result must copy the object
    they own; ``contract_semantic_payload`` does exactly that before dropping
    ``meta``.
    """
    if isinstance(value, dict):
        changed = False
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key == "context" and isinstance(item, dict):
                context_changed = False
                context_out: dict[str, Any] = {}
                for sub_key, sub_value in item.items():
                    if sub_key in REQUEST_TRANSPORT_CONTEXT_KEYS:
                        context_changed = True
                        continue
                    child = strip_request_transport_identity(sub_value)
                    if child is not sub_value:
                        context_changed = True
                    context_out[sub_key] = child
                if context_changed:
                    changed = True
                    out[key] = context_out
                else:
                    out[key] = item
                continue
            child = strip_request_transport_identity(item)
            if child is not item:
                changed = True
            out[key] = child
        return out if changed else value
    if isinstance(value, list):
        out_list: list[Any] = []
        changed = False
        for item in value:
            child = strip_request_transport_identity(item)
            if child is not item:
                changed = True
            out_list.append(child)
        return out_list if changed else value
    return value


# Source-envelope identity
# ------------------------
# The source envelope's ``source_meta`` is part of the payload that
# ``build_lifecycle_evidence`` hashes into ``sourceSha256``, so every key in it
# is part of the source identity. Transport identity and per-request measurements
# describe the request, not the source: keeping them made the digest change
# between processes (and between requests) for byte-identical source content.
# ``elapsed_ms`` is the projection's own duration; ``trace_id``/``request_id`` are
# the request's transport identity.
SOURCE_META_PER_REQUEST_KEYS = REQUEST_TRANSPORT_CONTEXT_KEYS + ("elapsed_ms",)


def source_meta_for_identity(meta: Any) -> dict[str, Any]:
    """The source envelope meta with per-request identity and measurements removed.

    Returns a new dict; the caller's ``meta`` is never mutated. A non-dict value
    yields ``{}`` so an unreadable envelope contributes no identity rather than
    an accidental one.
    """
    if not isinstance(meta, dict):
        return {}
    return {
        key: value
        for key, value in meta.items()
        if key not in SOURCE_META_PER_REQUEST_KEYS
    }


def contract_semantic_payload(contract: dict[str, Any]) -> dict[str, Any]:
    payload = strip_request_transport_identity(contract if isinstance(contract, dict) else {})
    # ``strip_request_transport_identity`` may return the caller's own object by
    # reference, so isolate the top level before removing ``meta``.
    payload = dict(payload)
    payload.pop("meta", None)
    return payload


def _reusable_digest(reuse_digests: dict[str, Any] | None, key: str) -> str:
    """Return a caller-supplied digest only when it is a usable sha256 value.

    A missing, blank or non-string value is never accepted: the caller falls
    back to computing the digest from the payload it actually holds. The reuse
    is therefore a pure memo hint, never an authority: ``reuse_digests`` may
    only carry a digest that was produced by this same function over the same
    semantic payload, and ``verify_unified_page_contract_integrity`` still
    recomputes it from the delivered contract on every delivery.
    """
    if not isinstance(reuse_digests, dict):
        return ""
    value = reuse_digests.get(key)
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        return ""
    return value


def build_lifecycle_evidence(
    *,
    contract: dict[str, Any],
    source_payload: dict[str, Any],
    source_type: str,
    request_id: str,
    trace_id: str,
    client_type: str,
    stage: str,
    generator: str,
    generator_version: str,
    source_authority: dict[str, Any],
    published_version_ref: str = "",
    reuse_digests: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_request_id = protocol_id(request_id, prefix="request")
    normalized_trace_id = protocol_id(trace_id or request_id, prefix="trace")
    definition = {
        "schemaId": UNIFIED_PAGE_SCHEMA_ID,
        "schemaVersion": UNIFIED_PAGE_SCHEMA_VERSION,
        "schemaSha256": UNIFIED_PAGE_SCHEMA_SHA256,
        "contractVersion": UNIFIED_PAGE_SCHEMA_VERSION,
        "normativeStatus": UNIFIED_PAGE_NORMATIVE_STATUS,
    }
    # Additive: a delivery that was governed by a published business-config
    # contract version names it here, so runtime telemetry can aggregate per
    # published version. A delivery with no published version omits the field
    # entirely and stays unattributed rather than borrowing another's identity.
    normalized_published_version_ref = str(published_version_ref or "").strip()
    if normalized_published_version_ref:
        definition["publishedVersionRef"] = normalized_published_version_ref
    return {
        "lifecycleVersion": LIFECYCLE_VERSION,
        "stage": str(stage or "assembly"),
        "definition": definition,
        "generation": {
            "generator": str(generator or "unknown"),
            "generatorVersion": str(generator_version or UNIFIED_PAGE_SCHEMA_VERSION),
            "sourceType": str(source_type or "unknown"),
            "sourceSha256": _reusable_digest(reuse_digests, "sourceSha256")
            or payload_sha256(
                strip_request_transport_identity(source_payload if isinstance(source_payload, dict) else {})
            ),
        },
        "runtime": {
            "requestId": normalized_request_id,
            "traceId": normalized_trace_id,
            "clientType": str(client_type or "web_pc"),
            "traceSource": "request_context" if trace_id else "request_id_fallback",
        },
        "integrity": {
            "algorithm": HASH_ALGORITHM,
            "contractSha256": _reusable_digest(reuse_digests, "contractSha256")
            or payload_sha256(contract_semantic_payload(contract)),
        },
        "authority": deepcopy(source_authority if isinstance(source_authority, dict) else {}),
    }


def seal_unified_page_contract(
    contract: dict[str, Any],
    *,
    source_payload: dict[str, Any],
    source_type: str,
    request_id: str,
    trace_id: str = "",
    client_type: str = "web_pc",
    stage: str = "assembly",
    generator: str = "unified_page_contract_v2_assembler",
    generator_version: str = UNIFIED_PAGE_SCHEMA_VERSION,
    source_authority: dict[str, Any] | None = None,
    published_version_ref: str = "",
    reuse_digests: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(contract, dict):
        raise TypeError("contract must be a dict")
    meta = contract.get("meta") if isinstance(contract.get("meta"), dict) else {}
    meta = dict(meta)
    lifecycle = build_lifecycle_evidence(
        contract=contract,
        source_payload=source_payload,
        source_type=source_type,
        request_id=request_id,
        trace_id=trace_id,
        client_type=client_type,
        stage=stage,
        generator=generator,
        generator_version=generator_version,
        source_authority=source_authority or {},
        published_version_ref=published_version_ref,
        reuse_digests=reuse_digests,
    )
    digest = lifecycle["integrity"]["contractSha256"]
    normalized_request_id = lifecycle["runtime"]["requestId"]
    normalized_trace_id = lifecycle["runtime"]["traceId"]
    meta.update(
        {
            "etag": f"upc-v2-sha256-{digest}",
            "snapshotId": f"snapshot.upc.v2.{digest[:32]}",
            "traceId": normalized_trace_id,
            "requestId": normalized_request_id,
            "sourceType": str(source_type or meta.get("sourceType") or "unknown"),
            "lifecycle": lifecycle,
        }
    )
    contract["meta"] = meta
    return contract


def verify_unified_page_contract_integrity(contract: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(contract, dict):
        return False, "contract_not_object"
    meta = contract.get("meta") if isinstance(contract.get("meta"), dict) else {}
    lifecycle = meta.get("lifecycle") if isinstance(meta.get("lifecycle"), dict) else {}
    integrity = lifecycle.get("integrity") if isinstance(lifecycle.get("integrity"), dict) else {}
    if integrity.get("algorithm") != HASH_ALGORITHM:
        return False, "unsupported_integrity_algorithm"
    expected = str(integrity.get("contractSha256") or "")
    actual = payload_sha256(contract_semantic_payload(contract))
    if not expected or expected != actual:
        return False, "contract_sha256_mismatch"
    return True, "ok"
