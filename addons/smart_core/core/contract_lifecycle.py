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
UNIFIED_PAGE_SCHEMA_SHA256 = "28be508e6488a72a35d4c128834d14b4a182af53bdab65ee9f728e5e791edf83"
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
    """Copy ``value``, dropping transport identity from ``context`` containers."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if key == "context" and isinstance(item, dict):
                out[key] = {
                    sub_key: strip_request_transport_identity(sub_value)
                    for sub_key, sub_value in item.items()
                    if sub_key not in REQUEST_TRANSPORT_CONTEXT_KEYS
                }
                continue
            out[key] = strip_request_transport_identity(item)
        return out
    if isinstance(value, list):
        return [strip_request_transport_identity(item) for item in value]
    return value


def contract_semantic_payload(contract: dict[str, Any]) -> dict[str, Any]:
    payload = strip_request_transport_identity(contract if isinstance(contract, dict) else {})
    payload.pop("meta", None)
    return payload


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
            "sourceSha256": payload_sha256(
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
            "contractSha256": payload_sha256(contract_semantic_payload(contract)),
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
