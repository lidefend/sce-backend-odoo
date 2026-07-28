#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
TOOL_VERSION = "um_p3_core035_s07ac_confirmation_generate/v1"
S07A_COMMIT = "da25c8afc903b0358b8a3e5ef59b77c4646848ad"
EXPECTED_SOURCE_HASHES = {
    "分包合同": "134f1bd4694ae8a6649b3ee3d264388dd65e19592312dd61f1cd744650642bda",
    "分包方单": "f2309baab8fff14a02e3e559f3e575a44f969a4e02878816461ed42adb75a510",
    "分包结算单": "c4f28d77388ed8ea7f0df4f5a38ca206ce4728a9f134508fcd1846a4e83a15ff",
}
EVIDENCE_FIELDS = (
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
)


def canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical(value).encode("utf-8"))


def anonymized_anchor(kind: str, value: Any) -> str:
    if value in (None, ""):
        return "NOT_AVAILABLE_WITH_SOURCE_EVIDENCE"
    digest = sha256_bytes(f"{kind}\0{value}".encode("utf-8"))
    return f"{kind.upper()}_SHA256:{digest}"


def record_ref(kind: str, row: dict[str, Any]) -> str:
    return f"LEGACY_SOURCE_B-{kind}-{sha256_json(row)[:24].upper()}"


def evidence_digest(item: dict[str, Any]) -> str:
    payload = {field: item[field] for field in EVIDENCE_FIELDS}
    return f"sha256:{sha256_json(payload)}"


def first(row: dict[str, Any], *fields: str) -> Any:
    for field in fields:
        value = row.get(field)
        if value not in (None, ""):
            return value
    return None


def comparable(value: Any) -> str | None:
    if value in (None, ""):
        return None
    try:
        return format(float(value), ".12g")
    except (TypeError, ValueError):
        return str(value).strip() or None


def equality(left: Any, right: Any) -> str:
    left_value = comparable(left)
    right_value = comparable(right)
    if left_value is None or right_value is None:
        return "NOT_AVAILABLE"
    return "MATCH" if left_value == right_value else "DIFFERENT"


def date_order(left: Any, right: Any) -> str:
    if left in (None, "") or right in (None, ""):
        return "NOT_AVAILABLE"
    try:
        left_value = datetime.fromisoformat(str(left).replace("Z", "+00:00"))
        right_value = datetime.fromisoformat(str(right).replace("Z", "+00:00"))
    except ValueError:
        return "NOT_COMPARABLE"
    if left_value < right_value:
        return "REGISTER_BEFORE_SETTLEMENT"
    if left_value > right_value:
        return "REGISTER_AFTER_SETTLEMENT"
    return "SAME_RECORDED_TIME"


def load_capture(source_root: Path, label: str) -> tuple[Path, list[dict[str, Any]]]:
    paths = sorted(source_root.glob(f"{label}__*.json"))
    if len(paths) != 1:
        raise RuntimeError(f"{label}: expected exactly one capture, found {len(paths)}")
    path = paths[0]
    actual_hash = sha256_bytes(path.read_bytes())
    if actual_hash != EXPECTED_SOURCE_HASHES[label]:
        raise RuntimeError(f"{label}: source SHA-256 mismatch")
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("rows")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise RuntimeError(f"{label}: invalid rows")
    return path, rows


def build_candidate_evidence(
    settlement: dict[str, Any],
    register: dict[str, Any],
) -> dict[str, Any]:
    contract_left = settlement.get("FBHTID")
    contract_right = register.get("FBHTID")
    return {
        "candidate_register_ref": record_ref("REGISTER", register),
        "candidate_basis": "EXACT_PROJECT_AND_COUNTERPARTY_ATTRIBUTE_FILTER_ONLY",
        "company_consistency": "SAME_LEGACY_SOURCE_B_CAPTURE_CONTEXT",
        "project_consistency": equality(
            settlement.get("XMID"),
            register.get("XMID"),
        ),
        "counterparty_consistency": equality(
            settlement.get("JSDWID"),
            register.get("FBSID"),
        ),
        "contract_consistency": equality(contract_left, contract_right),
        "business_number_consistency": "NOT_A_RELATION_KEY",
        "currency_consistency": "NOT_AVAILABLE_WITH_SOURCE_EVIDENCE",
        "amount_consistency": equality(
            first(settlement, "ZJE", "DZJE", "LJJSJE"),
            first(
                register,
                "BYGZJE$SGGL_FBGL_FBFD_CB",
                "JEHJ",
            ),
        ),
        "business_date_order": date_order(
            first(register, "JSZZRQ", "JSQSRQ", "LRSJ"),
            first(settlement, "JSRQ", "QSJSRQ", "LRSJ"),
        ),
        "authoritative_relation_proven": False,
    }


def generate_items(
    registers: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    attribute_index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    row_index: dict[str, dict[str, Any]] = {}
    for register in registers:
        project = register.get("XMID")
        counterparty = register.get("FBSID")
        if project not in (None, "") and counterparty not in (None, ""):
            attribute_index.setdefault(
                (str(project), str(counterparty)),
                [],
            ).append(register)
        if register.get("RowIndex") not in (None, ""):
            row_index[str(register["RowIndex"])] = register

    ordered_settlements = sorted(
        settlements,
        key=lambda row: sha256_json(row),
    )
    items: list[dict[str, Any]] = []
    for sequence, settlement in enumerate(ordered_settlements, start=1):
        false_link = row_index.get(str(settlement.get("pid")))
        project_conflict = False
        counterparty_conflict = False
        contract_conflict = False
        if false_link:
            project_conflict = (
                equality(settlement.get("XMID"), false_link.get("XMID"))
                == "DIFFERENT"
            )
            counterparty_conflict = (
                equality(settlement.get("JSDWID"), false_link.get("FBSID"))
                == "DIFFERENT"
            )
            contract_conflict = (
                equality(settlement.get("FBHTID"), false_link.get("FBHTID"))
                == "DIFFERENT"
            )
        is_conflicting = bool(
            false_link
            and (project_conflict or counterparty_conflict or contract_conflict)
        )

        key = None
        if (
            settlement.get("XMID") not in (None, "")
            and settlement.get("JSDWID") not in (None, "")
        ):
            key = (
                str(settlement["XMID"]),
                str(settlement["JSDWID"]),
            )
        candidates = sorted(
            attribute_index.get(key, []) if key else [],
            key=lambda row: record_ref("REGISTER", row),
        )
        candidate_evidence = [
            build_candidate_evidence(settlement, candidate)
            for candidate in candidates
        ]
        candidate_refs = [
            evidence["candidate_register_ref"]
            for evidence in candidate_evidence
        ]

        conflict_flags: list[str] = []
        if project_conflict:
            conflict_flags.append("PROJECT_CONFLICT")
        if counterparty_conflict:
            conflict_flags.append("COUNTERPARTY_CONFLICT")
        if contract_conflict:
            conflict_flags.append("CONTRACT_CONFLICT")
        prohibited_flags = [
            "NO_NAME_INFERENCE",
            "NO_AMOUNT_INFERENCE",
            "NO_NEAREST_DATE_INFERENCE",
            "NO_ROW_ORDER_INFERENCE",
            "NO_PROJECT_CONTRACT_COUNTERPARTY_COMPOSITE_INFERENCE",
        ]
        prohibited_link_evidence: list[dict[str, Any]] = []
        if false_link:
            prohibited_flags.append("PID_ROWINDEX_PROHIBITED")
            prohibited_link_evidence.append(
                {
                    "relation": "SETTLEMENT_PID_TO_REGISTER_ROWINDEX",
                    "candidate_register_ref": record_ref(
                        "REGISTER",
                        false_link,
                    ),
                    "project_conflict": project_conflict,
                    "counterparty_conflict": counterparty_conflict,
                    "contract_conflict": contract_conflict,
                    "usable_as_relation": False,
                }
            )

        item: dict[str, Any] = {
            "review_item_id": f"CORE035-S07AC-{sequence:04d}",
            "source_settlement_ref": record_ref("SETTLEMENT", settlement),
            "source_settlement_fingerprint": f"sha256:{sha256_json(settlement)}",
            "source_contract_ref": anonymized_anchor(
                "contract",
                settlement.get("FBHTID"),
            ),
            "company_anchor": anonymized_anchor(
                "company_context",
                "LEGACY_SOURCE_B_DIRECT_PROJECT_CAPTURE",
            ),
            "project_anchor": anonymized_anchor(
                "project",
                settlement.get("XMID"),
            ),
            "counterparty_anchor": anonymized_anchor(
                "counterparty",
                settlement.get("JSDWID"),
            ),
            "business_number_anchor": anonymized_anchor(
                "business_number",
                settlement.get("DJBH"),
            ),
            "currency_anchor": "NOT_AVAILABLE_WITH_SOURCE_EVIDENCE",
            "amount_anchor": anonymized_anchor(
                "tax_basis_unproven_amount",
                first(settlement, "ZJE", "DZJE", "LJJSJE"),
            ),
            "business_date_anchor": anonymized_anchor(
                "business_date",
                first(settlement, "JSRQ", "QSJSRQ", "LRSJ"),
            ),
            "candidate_register_refs": candidate_refs,
            "candidate_count": len(candidate_refs),
            "candidate_evidence": candidate_evidence,
            "conflict_flags": conflict_flags,
            "prohibited_inference_flags": prohibited_flags,
            "prohibited_link_evidence": prohibited_link_evidence,
            "source_classification": (
                "CONFLICTING"
                if is_conflicting
                else "ATTRIBUTE_CANDIDATE_ONLY"
            ),
            "reviewer_decision": (
                "REQUIRE_SOURCE_DOCUMENT" if is_conflicting else ""
            ),
            "confirmed_register_ref": "",
            "authoritative_source_document_ref": "",
            "rejection_reason": "",
            "reviewer_comment": "",
            "reviewed_by": "",
            "reviewed_at": "",
            "authorization_evidence_id": "",
            "second_review_by": "",
            "second_review_at": "",
            "decision_status": "ESCALATED" if is_conflicting else "PENDING",
        }
        item["evidence_digest"] = evidence_digest(item)
        items.append(item)
    return items


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--generated-at", required=True)
    args = parser.parse_args()

    source_meta: dict[str, dict[str, Any]] = {}
    loaded: dict[str, list[dict[str, Any]]] = {}
    for label in EXPECTED_SOURCE_HASHES:
        path, rows = load_capture(args.source_root, label)
        source_meta[label] = {
            "source_id": path.name,
            "sha256": EXPECTED_SOURCE_HASHES[label],
            "row_count": len(rows),
        }
        loaded[label] = rows
    if {
        label: len(rows) for label, rows in loaded.items()
    } != {"分包合同": 86, "分包方单": 721, "分包结算单": 88}:
        raise RuntimeError("source counts do not match S07A")

    items = generate_items(loaded["分包方单"], loaded["分包结算单"])
    items_payload = {
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "TASK": "UM-P3-CORE-035-S07A-C-PREPARE-AUDITED-MANUAL-CONFIRMATION-SET",
        "S07A_COMMIT": S07A_COMMIT,
        "S07B_APPROVED": False,
        "MIGRATION_EXECUTED": False,
        "RELATION_REMEDIATION_EXECUTED": False,
        "AUTHORIZED_MAPPINGS": [],
        "REVIEW_ITEMS": items,
    }
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)
    items_path = (
        output_root / "um_p3_core_035_s07ac_confirmation_items_v1.json"
    )
    write_json(items_path, items_payload)
    items_sha = sha256_bytes(items_path.read_bytes())
    classification = {
        key: sum(item["source_classification"] == key for item in items)
        for key in ("ATTRIBUTE_CANDIDATE_ONLY", "CONFLICTING")
    }
    manifest = {
        "SCHEMA_VERSION": SCHEMA_VERSION,
        "TASK": "UM-P3-CORE-035-S07A-C-PREPARE-AUDITED-MANUAL-CONFIRMATION-SET",
        "S07A_COMMIT": S07A_COMMIT,
        "SOURCE_ID": "LEGACY_SOURCE_B_DIRECT_PROJECT_STRICT_PARITY_CAPTURE_20260601T130457Z",
        "SOURCE_CAPTURE_FILES": source_meta,
        "REVIEW_ITEM_COUNT": len(items),
        "ATTRIBUTE_CANDIDATE_COUNT": classification[
            "ATTRIBUTE_CANDIDATE_ONLY"
        ],
        "CONFLICTING_COUNT": classification["CONFLICTING"],
        "PENDING_REVIEW_COUNT": sum(
            item["decision_status"] == "PENDING" for item in items
        ),
        "ESCALATED_REVIEW_COUNT": sum(
            item["decision_status"] == "ESCALATED" for item in items
        ),
        "AUTHORIZED_FINAL_COUNT": 0,
        "GENERATED_AT": args.generated_at,
        "GENERATOR_VERSION": TOOL_VERSION,
        "CONFIRMATION_ITEMS_SHA256": items_sha,
        "AUTOMATIC_MAPPING_PROHIBITED": True,
        "PID_ROWINDEX_PROHIBITED": True,
        "MIGRATION_EXECUTION_ALLOWED": False,
        "S07B_APPROVED": False,
        "REQUIRED_REVIEW_ROLES": [
            "HISTORICAL_SUBCONTRACT_BUSINESS_OWNER",
            "DATA_STEWARD",
            "INDEPENDENT_SECOND_REVIEWER",
        ],
        "REVIEW_PACKAGE_EXPIRY_AT": "2026-09-30T15:59:59Z",
        "RESPONSIBLE_OWNER_ROLE": "DATA_STEWARD",
        "RESULT": "READY_FOR_AUTHORIZED_DUAL_REVIEW",
    }
    write_json(
        output_root / "um_p3_core_035_s07ac_confirmation_manifest_v1.json",
        manifest,
    )


if __name__ == "__main__":
    main()
