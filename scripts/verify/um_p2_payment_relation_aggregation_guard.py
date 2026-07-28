#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/audit/um_p2/um_p2_s02_payment_relation_aggregation_v1.json"


def fail(message):
    raise SystemExit(f"UM_P2_PAYMENT_RELATION_GUARD=FAIL: {message}")


def main():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected = {
        "SLICE_ID": "UM-P2-S02-PAYMENT-RELATION-AGGREGATION",
        "BUSINESS_CLASSIFICATION": "PAYMENT_EXECUTION_RELATION_AGGREGATION",
        "BASIS_AUTHORITY": (
            "PAYMENT_REQUEST_DETAIL_SET_WHEN_PRESENT_OTHERWISE_EXCLUSIVE_"
            "STANDARD_OR_MATERIAL_HEADER"
        ),
        "CONTRACT_DERIVATION_POLICY": (
            "DERIVE_FROM_COMPLETE_VALID_BASIS_SET_AND_WRITE_SCALAR_ONLY_WHEN_UNIQUE"
        ),
        "APPLICATION_COUNTERPARTY_ROLE": "BUSINESS_TRANSACTION_COUNTERPARTY",
        "ACTUAL_PAYEE_ROLE": "EXECUTION_LEVEL_FUNDS_RECIPIENT",
        "ACTUAL_PAYEE_DIFFERENCE_ALLOWED": True,
        "MULTI_CONTRACT_POLICY": (
            "PRESERVE_DETAIL_RELATIONS_AND_KEEP_EXECUTION_CONTRACT_EMPTY"
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
        "UNIQUE_STANDARD_CONTRACT",
        "MATERIAL_NO_CONTRACT_UNAGGREGATED",
        "MULTI_SOURCE_SAME_CONTRACT",
        "MULTI_CONTRACT_PRESERVATION",
        "CONTRACT_WITHOUT_BASIS_REJECTION",
        "EXPLICIT_CONTRACT_CONFLICT_REJECTION",
        "HEADER_DETAIL_CONFLICT_REJECTION",
        "SAME_ACTUAL_PAYEE",
        "DIFFERENT_ACTUAL_PAYEE",
        "ACTUAL_PAYEE_NON_OVERRIDE",
        "WRITE_REVALIDATION",
    )
    for key in required_passes:
        if acceptance.get(key) != "PASS":
            fail(f"{key} is not PASS")
    if not acceptance.get("TEMP_DATABASE_REMOVED"):
        fail("temporary database cleanup is not confirmed")
    if acceptance.get("TEMP_RESOURCE_RESIDUE_COUNT") != 0:
        fail("temporary resource residue is not zero")
    print("UM_P2_PAYMENT_RELATION_GUARD=PASS")
    print(f"NEXT_SLICE={data['NEXT_SLICE']}")


if __name__ == "__main__":
    main()
