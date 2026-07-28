#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from um_p3_core035_s07ac_confirmation_generate import evidence_digest


ROOT = Path(__file__).resolve().parents[2]
AUDIT_ROOT = ROOT / "docs/audit/um_p3"
MANIFEST = AUDIT_ROOT / "um_p3_core_035_s07ac_confirmation_manifest_v1.json"
ITEMS = AUDIT_ROOT / "um_p3_core_035_s07ac_confirmation_items_v1.json"
AUTHORIZATION = (
    AUDIT_ROOT / "um_p3_core_035_s07ac_authorization_template_v1.json"
)
S07A_PROFILE = AUDIT_ROOT / "um_p3_core_035_s07a_source_profile_v1.json"
ALLOWED_DECISIONS = {
    "",
    "CONFIRM_ONE",
    "CONFIRM_NONE",
    "REQUIRE_SOURCE_DOCUMENT",
    "REQUIRE_BUSINESS_OWNER_DECISION",
    "INVALID_SOURCE_RECORD",
}
ALLOWED_STATUSES = {
    "PENDING",
    "FIRST_REVIEW_COMPLETED",
    "SECOND_REVIEW_COMPLETED",
    "AUTHORIZED_FINAL",
    "REJECTED",
    "ESCALATED",
}
REQUIRED_ITEM_FIELDS = {
    "review_item_id",
    "source_settlement_ref",
    "source_settlement_fingerprint",
    "source_contract_ref",
    "company_anchor",
    "project_anchor",
    "counterparty_anchor",
    "business_number_anchor",
    "currency_anchor",
    "amount_anchor",
    "business_date_anchor",
    "candidate_register_refs",
    "candidate_count",
    "candidate_evidence",
    "conflict_flags",
    "prohibited_inference_flags",
    "prohibited_link_evidence",
    "source_classification",
    "reviewer_decision",
    "confirmed_register_ref",
    "authoritative_source_document_ref",
    "rejection_reason",
    "reviewer_comment",
    "reviewed_by",
    "reviewed_at",
    "authorization_evidence_id",
    "second_review_by",
    "second_review_at",
    "decision_status",
    "evidence_digest",
}
ANCHOR_PATTERN = re.compile(
    r"^(?:[A-Z_]+_SHA256:[0-9a-f]{64}|NOT_AVAILABLE_WITH_SOURCE_EVIDENCE)$"
)
SETTLEMENT_REF_PATTERN = re.compile(r"^LEGACY_SOURCE_B-SETTLEMENT-[0-9A-F]{24}$")
REGISTER_REF_PATTERN = re.compile(r"^LEGACY_SOURCE_B-REGISTER-[0-9A-F]{24}$")
FINGERPRINT_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"postgres(?:ql)?://", re.IGNORECASE),
    re.compile(r"(?:password|passwd|token|secret|cookie)\s*[:=]", re.IGNORECASE),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY", re.IGNORECASE),
)
FORBIDDEN_RAW_KEYS = {
    "XMMC",
    "FBS",
    "GYDW",
    "LRR",
    "PersonName",
    "CompanyName",
    "ProjectName",
    "UserName",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)
    elif isinstance(value, str):
        yield value


def validate(
    manifest: dict[str, Any],
    payload: dict[str, Any],
    authorization: dict[str, Any],
    profile: dict[str, Any],
    items_sha256: str,
) -> list[str]:
    errors: list[str] = []
    classification = profile.get("RELATION_CLASSIFICATION", {})
    if classification.get("TOTAL_SETTLEMENT_RECORDS") != 88:
        errors.append("S07A settlement count drift")
    if classification.get("AMBIGUOUS_COUNT") != 76:
        errors.append("S07A ambiguous count drift")
    if classification.get("CONFLICTING_COUNT") != 12:
        errors.append("S07A conflicting count drift")
    if classification.get("EXACT_AUTHORITATIVE_KEY_COUNT") != 0:
        errors.append("S07A authoritative key count drift")
    if classification.get("UNIQUE_COMPOSITE_BUSINESS_KEY_COUNT") != 0:
        errors.append("S07A immutable key count drift")

    if manifest.get("S07A_COMMIT") != (
        "da25c8afc903b0358b8a3e5ef59b77c4646848ad"
    ):
        errors.append("manifest S07A commit mismatch")
    if manifest.get("CONFIRMATION_ITEMS_SHA256") != items_sha256:
        errors.append("confirmation items SHA-256 mismatch")
    for key, expected in {
        "REVIEW_ITEM_COUNT": 88,
        "ATTRIBUTE_CANDIDATE_COUNT": 76,
        "CONFLICTING_COUNT": 12,
        "PENDING_REVIEW_COUNT": 76,
        "ESCALATED_REVIEW_COUNT": 12,
        "AUTHORIZED_FINAL_COUNT": 0,
        "AUTOMATIC_MAPPING_PROHIBITED": True,
        "PID_ROWINDEX_PROHIBITED": True,
        "MIGRATION_EXECUTION_ALLOWED": False,
        "S07B_APPROVED": False,
    }.items():
        if manifest.get(key) != expected:
            errors.append(f"manifest {key} drift")

    for key in (
        "S07B_APPROVED",
        "MIGRATION_EXECUTED",
        "RELATION_REMEDIATION_EXECUTED",
    ):
        if payload.get(key) is not False:
            errors.append(f"payload {key} must remain false")

    review_items = payload.get("REVIEW_ITEMS")
    if not isinstance(review_items, list) or len(review_items) != 88:
        errors.append("confirmation set must contain 88 review items")
        return errors
    expected_ids = [f"CORE035-S07AC-{index:04d}" for index in range(1, 89)]
    actual_ids = [item.get("review_item_id") for item in review_items]
    if actual_ids != expected_ids:
        errors.append("review item identifiers are missing duplicated or unstable")
    settlement_refs = [item.get("source_settlement_ref") for item in review_items]
    if len(set(settlement_refs)) != 88:
        errors.append("source settlement coverage is not one-to-one")

    attribute_count = 0
    conflicting_count = 0
    counterparty_conflict_count = 0
    authorized_items: list[dict[str, Any]] = []
    for item in review_items:
        item_id = item.get("review_item_id", "<missing>")
        missing = REQUIRED_ITEM_FIELDS - set(item)
        if missing:
            errors.append(f"{item_id} missing fields: {sorted(missing)}")
            continue
        if not SETTLEMENT_REF_PATTERN.fullmatch(item["source_settlement_ref"]):
            errors.append(f"{item_id} invalid settlement reference")
        if not FINGERPRINT_PATTERN.fullmatch(
            item["source_settlement_fingerprint"]
        ):
            errors.append(f"{item_id} invalid settlement fingerprint")
        for anchor in (
            "source_contract_ref",
            "company_anchor",
            "project_anchor",
            "counterparty_anchor",
            "business_number_anchor",
            "currency_anchor",
            "amount_anchor",
            "business_date_anchor",
        ):
            if not ANCHOR_PATTERN.fullmatch(item[anchor]):
                errors.append(f"{item_id} exposes or corrupts {anchor}")
        candidate_refs = item["candidate_register_refs"]
        if not isinstance(candidate_refs, list):
            errors.append(f"{item_id} candidate references must be a list")
            candidate_refs = []
        if len(candidate_refs) != len(set(candidate_refs)):
            errors.append(f"{item_id} duplicates candidate references")
        if not all(REGISTER_REF_PATTERN.fullmatch(ref) for ref in candidate_refs):
            errors.append(f"{item_id} invalid candidate reference")
        if item["candidate_count"] != len(candidate_refs):
            errors.append(f"{item_id} candidate count mismatch")
        evidence_refs = [
            evidence.get("candidate_register_ref")
            for evidence in item["candidate_evidence"]
        ]
        if evidence_refs != candidate_refs:
            errors.append(f"{item_id} candidate evidence is incomplete or reordered")
        if any(
            evidence.get("authoritative_relation_proven") is not False
            for evidence in item["candidate_evidence"]
        ):
            errors.append(f"{item_id} candidate evidence claims authority")
        if item["reviewer_decision"] not in ALLOWED_DECISIONS:
            errors.append(f"{item_id} invalid reviewer decision")
        if item["decision_status"] not in ALLOWED_STATUSES:
            errors.append(f"{item_id} invalid decision status")
        if item["evidence_digest"] != evidence_digest(item):
            errors.append(f"{item_id} evidence digest mismatch")

        classification_value = item["source_classification"]
        if classification_value == "ATTRIBUTE_CANDIDATE_ONLY":
            attribute_count += 1
            if item["reviewer_decision"] or item["decision_status"] != "PENDING":
                errors.append(f"{item_id} attribute candidate is pre-confirmed")
        elif classification_value == "CONFLICTING":
            conflicting_count += 1
            if "PROJECT_CONFLICT" not in item["conflict_flags"]:
                errors.append(f"{item_id} conflicting item lacks project conflict")
            if "COUNTERPARTY_CONFLICT" in item["conflict_flags"]:
                counterparty_conflict_count += 1
            if item["reviewer_decision"] != "REQUIRE_SOURCE_DOCUMENT":
                errors.append(f"{item_id} conflict silently confirms a candidate")
            if item["decision_status"] != "ESCALATED":
                errors.append(f"{item_id} conflict must remain escalated")
            if "PID_ROWINDEX_PROHIBITED" not in item[
                "prohibited_inference_flags"
            ]:
                errors.append(f"{item_id} omits pid to RowIndex prohibition")
            if not item["prohibited_link_evidence"]:
                errors.append(f"{item_id} omits false-link evidence")
        else:
            errors.append(f"{item_id} invalid source classification")

        if any(
            link.get("usable_as_relation") is not False
            for link in item["prohibited_link_evidence"]
        ):
            errors.append(f"{item_id} uses pid to RowIndex as a relation")

        if item["decision_status"] == "AUTHORIZED_FINAL":
            authorized_items.append(item)
            if item["reviewer_decision"] != "CONFIRM_ONE":
                errors.append(f"{item_id} final decision is not CONFIRM_ONE")
            confirmed = item["confirmed_register_ref"]
            if (
                confirmed not in candidate_refs
                and not item["authoritative_source_document_ref"]
            ):
                errors.append(f"{item_id} confirms a non-candidate without evidence")
            for field in (
                "reviewed_by",
                "reviewed_at",
                "authorization_evidence_id",
                "second_review_by",
                "second_review_at",
            ):
                if not item[field]:
                    errors.append(f"{item_id} final decision lacks {field}")
            if item["reviewed_by"] == item["second_review_by"]:
                errors.append(f"{item_id} uses one person for dual review")
        elif item["confirmed_register_ref"]:
            errors.append(f"{item_id} unconfirmed item emits a mapping")

    if attribute_count != 76:
        errors.append("attribute candidate classification must equal 76")
    if conflicting_count != 12:
        errors.append("conflicting classification must equal 12")
    if counterparty_conflict_count != 11:
        errors.append("counterparty conflict count must equal 11")

    expected_mappings = [
        {
            "review_item_id": item["review_item_id"],
            "source_settlement_ref": item["source_settlement_ref"],
            "confirmed_register_ref": item["confirmed_register_ref"],
            "evidence_digest": item["evidence_digest"],
        }
        for item in authorized_items
    ]
    if payload.get("AUTHORIZED_MAPPINGS") != expected_mappings:
        errors.append("migration mapping output includes unconfirmed or missing items")
    if authorized_items:
        errors.append("initial S07A-C package must have zero authorized final items")

    for key in (
        "AUTHORIZED_BY",
        "AUTHORIZED_AT",
        "AUTHORIZATION_EVIDENCE_ID",
        "BUSINESS_OWNER",
        "DATA_STEWARD",
        "SECOND_REVIEWER",
    ):
        if authorization.get(key) != "":
            errors.append(f"authorization template must leave {key} unsigned")
    if authorization.get("CONFIRMATION_MANIFEST_SHA256") != file_sha256(
        MANIFEST
    ):
        errors.append("authorization template manifest digest mismatch")
    if authorization.get("CONFIRMATION_ITEMS_SHA256") != items_sha256:
        errors.append("authorization template items digest mismatch")
    if authorization.get("SIGNED_STATUS") != "UNSIGNED":
        errors.append("authorization template must remain unsigned")
    if authorization.get("S07B_REVIEW_REQUESTED") is not False:
        errors.append("authorization template prematurely requests S07B")

    all_values = list(walk({"items": payload, "authorization": authorization}))
    if any(value in FORBIDDEN_RAW_KEYS for value in all_values):
        errors.append("confirmation package contains forbidden raw source fields")
    for value in all_values:
        if isinstance(value, str) and any(
            pattern.search(value) for pattern in FORBIDDEN_VALUE_PATTERNS
        ):
            errors.append("confirmation package contains a credential-like value")
            break
    return errors


def main() -> None:
    manifest = load_json(MANIFEST)
    payload = load_json(ITEMS)
    authorization = load_json(AUTHORIZATION)
    profile = load_json(S07A_PROFILE)
    errors = validate(
        manifest,
        payload,
        authorization,
        profile,
        file_sha256(ITEMS),
    )
    if errors:
        for error in errors:
            print(f"UM_P3_CORE035_S07AC_CONFIRMATION_GUARD=FAIL: {error}")
        raise SystemExit(1)
    print("UM_P3_CORE035_S07AC_CONFIRMATION_GUARD=PASS")
    print("REVIEW_ITEM_COUNT=88")
    print("ATTRIBUTE_CANDIDATE_COUNT=76")
    print("CONFLICTING_COUNT=12")
    print("AUTHORIZED_FINAL_COUNT=0")
    print("S07B_APPROVED=false")
    print("MIGRATION_EXECUTED=false")


if __name__ == "__main__":
    main()
