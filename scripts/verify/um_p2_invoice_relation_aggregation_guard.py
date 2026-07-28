#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/audit/um_p2/um_p2_s04_invoice_relation_aggregation_v1.json"


def fail(message):
    raise SystemExit(f"UM_P2_INVOICE_RELATION_GUARD=FAIL: {message}")


def main():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected = {
        "SLICE_ID": "UM-P2-S04-INVOICE-RELATION-AGGREGATION",
        "BUSINESS_CLASSIFICATION": (
            "SOURCE_KIND_SPECIFIC_INVOICE_RELATION_AGGREGATION"
        ),
        "CONTRACT_DERIVATION_POLICY": (
            "UNIQUE_CONTRACT_FROM_COMPLETE_VALID_BASIS_SET_ONLY"
        ),
        "UNLINKED_CONTRACT_POLICY": (
            "ALLOW_EMPTY_WITHOUT_HEURISTIC_MATCHING"
        ),
        "TAX_DEDUCTION_INCLUDED": False,
        "TAX_DEDUCTION_NEW_RELATION_FIELD_ADDED": False,
        "TAX_DEDUCTION_TEXT_MATCHING_USED": False,
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

    if data.get("INVOICE_SOURCE_KIND_ENUM") != [
        "invoice_registration",
        "input_invoice_tax",
        "output_invoice_tax",
        "prepaid_tax",
    ]:
        fail("source_kind enum does not match the product model")

    acceptance = data.get("ACCEPTANCE", {})
    required_passes = (
        "SOURCE_KIND_ENUM_AND_DISPATCH",
        "INPUT_UNIQUE_SETTLEMENT_CONTRACT",
        "OUTPUT_UNIQUE_SETTLEMENT_CONTRACT",
        "EXPLICIT_CONTRACT_AND_COUNTERPARTY_CONFLICT",
        "PREPAID_TAX_WITHOUT_CONTRACT",
        "SOURCE_KIND_CHANGE_REVALIDATION",
        "RECEIPT_APPLICATION_CHAIN",
        "CROSS_COMPANY_UNAUTHORIZED_NONEXISTENT_EQUIVALENCE",
        "TAX_DEDUCTION_TEXT_NUMBER_NON_RELATION",
    )
    for key in required_passes:
        if acceptance.get(key) != "PASS":
            fail(f"{key} is not PASS")
    if not acceptance.get("TEMP_DATABASE_REMOVED"):
        fail("temporary database cleanup is not confirmed")
    if acceptance.get("TEMP_RESOURCE_RESIDUE_COUNT") != 0:
        fail("temporary resource residue is not zero")
    print("UM_P2_INVOICE_RELATION_GUARD=PASS")
    print(f"NEXT_SLICE={data['NEXT_SLICE']}")


if __name__ == "__main__":
    main()
