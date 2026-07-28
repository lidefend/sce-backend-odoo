#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/audit/um_p2/um_p2_s03_interfund_relation_aggregation_v1.json"


def fail(message):
    raise SystemExit(f"UM_P2_INTERFUND_RELATION_GUARD=FAIL: {message}")


def main():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected = {
        "SLICE_ID": "UM-P2-S03-INTERFUND-RELATION-AGGREGATION",
        "BUSINESS_CLASSIFICATION": (
            "INTERFUND_ACCOUNT_PROJECT_COUNTERPARTY_AGGREGATION"
        ),
        "PROJECT_DERIVATION_POLICY": (
            "SOURCE_AND_TARGET_PROJECTS_DERIVE_ONLY_FROM_THEIR_ACCOUNT_"
            "PROJECT_RELATIONS"
        ),
        "OPERATION_PROJECT_ROLE": (
            "OPTIONAL_BUSINESS_ATTRIBUTION_NOT_AN_ENDPOINT_AUTHORITY"
        ),
        "CONFLICT_POLICY": (
            "REJECT_ACCOUNTS_OUTSIDE_OPERATION_COMPANY_OR_WITH_MISMATCHED_"
            "PROJECT_COMPANY"
        ),
        "HEURISTIC_MATCHING_USED": False,
        "HISTORICAL_INFERENCE_USED": False,
        "ACL_CHANGED": False,
        "RECORD_RULE_CHANGED": False,
        "DATA_MIGRATION_REQUIRED": False,
        "STATUS": "IMPLEMENTED_AND_VERIFIED",
    }
    for key, value in expected.items():
        if data.get(key) != value:
            fail(f"{key} expected {value!r}, got {data.get(key)!r}")

    acceptance = data.get("ACCEPTANCE", {})
    required_passes = (
        "PROJECT_TO_PROJECT_ENDPOINTS",
        "PROJECT_COMPANY_COUNTERPARTY",
        "COMPANY_PROJECT_COUNTERPARTY",
        "SAME_PROJECT_INTERNAL_COUNTERPARTY",
        "CROSS_COMPANY_ACCOUNT_REJECTION",
        "ACCOUNT_PROJECT_COMPANY_REJECTION",
        "WRITE_REVALIDATION",
        "UNAUTHORIZED_NONEXISTENT_EQUIVALENCE",
    )
    for key in required_passes:
        if acceptance.get(key) != "PASS":
            fail(f"{key} is not PASS")
    if not acceptance.get("TEMP_DATABASE_REMOVED"):
        fail("temporary database cleanup is not confirmed")
    if acceptance.get("TEMP_RESOURCE_RESIDUE_COUNT") != 0:
        fail("temporary resource residue is not zero")
    print("UM_P2_INTERFUND_RELATION_GUARD=PASS")
    print(f"NEXT_SLICE={data['NEXT_SLICE']}")


if __name__ == "__main__":
    main()
