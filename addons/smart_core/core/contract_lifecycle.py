# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from copy import deepcopy
from hashlib import sha256
from typing import Any


LIFECYCLE_VERSION = "1.0.0"
HASH_ALGORITHM = "sha256"
UNIFIED_PAGE_SCHEMA_ID = "smart_core.unified_page_contract_v2"
UNIFIED_PAGE_SCHEMA_VERSION = "2.2.0"
UNIFIED_PAGE_SCHEMA_SHA256 = "e6a28e9b7a406fe1002f79c0502129cfa10cda2c8a3600d81c38c5dbd1a83ba4"
UNIFIED_PAGE_NORMATIVE_STATUS = "stable"
_PROTOCOL_ID_INVALID = re.compile(r"[^a-zA-Z0-9_.:-]+")


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
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


def contract_semantic_payload(contract: dict[str, Any]) -> dict[str, Any]:
    payload = deepcopy(contract if isinstance(contract, dict) else {})
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
) -> dict[str, Any]:
    normalized_request_id = protocol_id(request_id, prefix="request")
    normalized_trace_id = protocol_id(trace_id or request_id, prefix="trace")
    return {
        "lifecycleVersion": LIFECYCLE_VERSION,
        "stage": str(stage or "assembly"),
        "definition": {
            "schemaId": UNIFIED_PAGE_SCHEMA_ID,
            "schemaVersion": UNIFIED_PAGE_SCHEMA_VERSION,
            "schemaSha256": UNIFIED_PAGE_SCHEMA_SHA256,
            "contractVersion": UNIFIED_PAGE_SCHEMA_VERSION,
            "normativeStatus": UNIFIED_PAGE_NORMATIVE_STATUS,
        },
        "generation": {
            "generator": str(generator or "unknown"),
            "generatorVersion": str(generator_version or UNIFIED_PAGE_SCHEMA_VERSION),
            "sourceType": str(source_type or "unknown"),
            "sourceSha256": payload_sha256(source_payload if isinstance(source_payload, dict) else {}),
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
