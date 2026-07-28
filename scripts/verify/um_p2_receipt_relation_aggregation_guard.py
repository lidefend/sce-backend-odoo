#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/audit/um_p2/um_p2_s01_receipt_relation_aggregation_v1.json"


def fail(message):
    raise SystemExit(f"UM_P2_RECEIPT_RELATION_GUARD=FAIL: {message}")


def main():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected = {
        "SLICE_ID": "UM-P2-S01-RECEIPT-RELATION-AGGREGATION",
        "BUSINESS_CLASSIFICATION": "RECEIPT_RELATION_AGGREGATION",
        "CONFLICT_POLICY": "REJECT_EXPLICIT_VALUES_THAT_DIFFER_FROM_UPSTREAM_RELATION",
        "UNLINKED_RECORD_POLICY": "KEEP_UNAGGREGATED_WITHOUT_HEURISTIC_MATCHING",
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
    if data.get("PRIMARY_RELATION_ANCHOR") != (
        "payment.request via sc.receipt.income.payment_request_id"
    ):
        fail("receipt application is not the primary relation anchor")
    if data.get("COUNTERPARTY_SOURCE") != "construction.contract.partner_id":
        fail("contract counterparty is not authoritative")
    acceptance = data.get("ACCEPTANCE", {})
    required_passes = (
        "AUTHORIZED_APPLICATION_CHAIN",
        "CONTRACT_SECONDARY_CHAIN",
        "CONTRACT_CONFLICT_REJECTION",
        "COUNTERPARTY_CONFLICT_REJECTION",
        "WRITE_REVALIDATION",
        "UNLINKED_NO_HEURISTIC",
        "UNAUTHORIZED_NONEXISTENT_EQUIVALENCE",
    )
    for key in required_passes:
        if acceptance.get(key) != "PASS":
            fail(f"{key} is not PASS")
    if not acceptance.get("TEMP_DATABASE_REMOVED"):
        fail("temporary database cleanup is not confirmed")
    print("UM_P2_RECEIPT_RELATION_GUARD=PASS")
    print(f"NEXT_SLICE={data['NEXT_SLICE']}")


if __name__ == "__main__":
    main()
