#!/usr/bin/env python3
"""Page Composition Evidence Contract.

Defines the evidence schema and validation rules that turn raw evidence into
verifiable, scope-bound, grade-bearing items. Provenance integrity (digest,
scope, freshness) is verified here; the collector never promotes handwritten
or human-provided declarations into trusted evidence.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

COLLECTOR_VERSION = "1.0.0"

EVIDENCE_TYPES = {
    "SOURCE_STATIC",
    "TEST_EXECUTION",
    "RUNTIME_OBSERVATION",
    "HISTORICAL_REFERENCE",
    "HUMAN_REVIEW",
}

EVIDENCE_GRADES = {
    "SOURCE_VERIFIED",
    "STATIC_CHAIN_VERIFIED",
    "RUNTIME_VERIFIED",
    "NOT_VERIFIED",
}

COLLECTION_METHODS = {"auto_collect", "auto_verify", "human_provided", "unverifiable"}

VERIFICATION_STATUSES = {
    "VERIFIED",
    "UNVERIFIED",
    "SCOPE_MISMATCH",
    "STALE",
    "INVALID",
}

RULE_TARGETS = {"PC-007", "PC-008", "PC-009", "PC-010"}

REQUIRED_COMMON = {
    "evidence_id",
    "evidence_type",
    "source_type",
    "collection_method",
    "collected_at",
    "repository_sha",
    "model",
    "action_id",
    "view_id",
    "contract_version",
    "applies_to_rule",
}

REQUIRED_BY_TYPE = {
    "SOURCE_STATIC": {"source_location"},
    "TEST_EXECUTION": {"source_location"},
    "RUNTIME_OBSERVATION": {"source_location"},
    "HISTORICAL_REFERENCE": {"source_location"},
    "HUMAN_REVIEW": {"review_basis"},
}

_GRADE_BY_TYPE = {
    "SOURCE_STATIC": "SOURCE_VERIFIED",
    "TEST_EXECUTION": "STATIC_CHAIN_VERIFIED",
    "RUNTIME_OBSERVATION": "RUNTIME_VERIFIED",
    "HISTORICAL_REFERENCE": "SOURCE_VERIFIED",
    "HUMAN_REVIEW": "NOT_VERIFIED",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_timestamp(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def validate_evidence_item(
    item: dict[str, Any],
    target_page: dict[str, Any],
    repository_sha: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    out = dict(item)
    structural_errors: list[str] = []

    for key in REQUIRED_COMMON:
        if out.get(key) in (None, ""):
            structural_errors.append(f"missing required field: {key}")

    evidence_type = _text(out.get("evidence_type"))
    if evidence_type not in EVIDENCE_TYPES:
        structural_errors.append(f"invalid evidence_type: {out.get('evidence_type')!r}")
    else:
        for key in REQUIRED_BY_TYPE[evidence_type]:
            if out.get(key) in (None, ""):
                structural_errors.append(f"missing type-required field: {key}")

    if _text(out.get("collection_method")) not in COLLECTION_METHODS:
        structural_errors.append(f"invalid collection_method: {out.get('collection_method')!r}")

    applies_to_rule = _text(out.get("applies_to_rule"))
    if applies_to_rule not in RULE_TARGETS:
        structural_errors.append(f"invalid applies_to_rule: {out.get('applies_to_rule')!r}")

    collected_at = _parse_timestamp(out.get("collected_at"))
    if collected_at is None:
        structural_errors.append("collected_at not parseable")
    elif collected_at > now + timedelta(minutes=5):
        structural_errors.append("collected_at is in the future")

    scope_ok = all(
        _text(out.get(key)) == _text(target_page.get(key)) and _text(target_page.get(key))
        for key in ("model", "action_id", "view_id")
    )

    stale = False
    if _text(out.get("repository_sha")) != _text(repository_sha):
        stale = True
    expires_at = _parse_timestamp(out.get("expires_at"))
    if expires_at is not None and expires_at <= now:
        stale = True

    integrity_state = "unavailable"
    if evidence_type != "HUMAN_REVIEW" and not structural_errors:
        content_digest = _text(out.get("content_digest"))
        source_location = _text(out.get("source_location"))
        content = out.get("content")
        if content_digest:
            actual: str | None = None
            if source_location and Path(source_location).exists():
                actual = sha256_file(source_location)
            elif content is not None:
                actual = sha256_text(str(content))
            if actual is None:
                integrity_state = "unavailable"
            elif actual == content_digest:
                integrity_state = "verified"
            else:
                integrity_state = "mismatch"

    if structural_errors:
        status = "INVALID"
    elif not scope_ok:
        status = "SCOPE_MISMATCH"
    elif stale:
        status = "STALE"
    elif evidence_type == "HUMAN_REVIEW":
        status = "UNVERIFIED"
    elif integrity_state == "verified":
        status = "VERIFIED"
    elif integrity_state == "mismatch":
        status = "INVALID"
    else:
        status = "UNVERIFIED"

    grade = _GRADE_BY_TYPE.get(evidence_type, "NOT_VERIFIED") if status == "VERIFIED" else "NOT_VERIFIED"

    out["verification_status"] = status
    out["evidence_grade"] = grade
    out["collector_version"] = COLLECTOR_VERSION
    return {
        "item": out,
        "verification_status": status,
        "evidence_grade": grade,
        "structural_errors": structural_errors,
        "scope_matched": scope_ok,
        "stale": stale,
    }
