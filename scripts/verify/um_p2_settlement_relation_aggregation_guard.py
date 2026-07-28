#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/audit/um_p2/um_p2_s05_settlement_relation_aggregation_v1.json"


def fail(message):
    raise SystemExit(f"UM_P2_SETTLEMENT_RELATION_GUARD=FAIL: {message}")


def main():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    expected = {
        "SLICE_ID": "UM-P2-S05-SETTLEMENT-RELATION-AGGREGATION",
        "SETTLEMENT_CONTRACT_AUTHORITY": "MULTI_CONTRACT_DETAIL_SET",
        "SETTLEMENT_HEADER_CONTRACT_ROLE": "OPTIONAL_UNIQUE_CONTRACT_PROJECTION",
        "SETTLEMENT_DETAIL_CONTRACT_ROLE": "AUTHORITATIVE_BUSINESS_RELATION",
        "MULTI_CONTRACT_SETTLEMENT_ALLOWED": True,
        "CONTRACT_DERIVATION_POLICY": (
            "COMPLETE_VALID_DETAIL_SET_UNIQUE_CONTRACT_ONLY"
        ),
        "HEURISTIC_MATCHING_USED": False,
        "HISTORICAL_INFERENCE_USED": False,
        "ACL_CHANGED": False,
        "RECORD_RULE_CHANGED": False,
        "DATA_MIGRATION_REQUIRED": False,
        "STATUS": "IMPLEMENTED_AND_VERIFIED",
        "P2_FORMAL_RELATION_SEQUENCE_COMPLETE": True,
    }
    for key, value in expected.items():
        if data.get(key) != value:
            fail(f"{key} expected {value!r}, got {data.get(key)!r}")

    acceptance = data.get("ACCEPTANCE", {})
    required_passes = (
        "STANDARD_SETTLEMENT_SINGLE_CONTRACT",
        "MULTI_LINE_SAME_CONTRACT",
        "MULTI_CONTRACT_PRESERVATION",
        "MULTI_CONTRACT_HEADER_EMPTY",
        "EXPLICIT_HEADER_CONTRACT_CONFLICT",
        "HEADER_NON_OVERRIDE",
        "LINE_CREATE_REVALIDATION",
        "LINE_WRITE_REVALIDATION",
        "LINE_UNLINK_REVALIDATION",
        "ONE2MANY_COMMAND_REVALIDATION",
        "CROSS_PROJECT_RELATION",
        "CROSS_COMPANY_RELATION",
        "COUNTERPARTY_CONFLICT",
        "UNAUTHORIZED_AND_NONEXISTENT_EQUIVALENCE",
    )
    for key in required_passes:
        if acceptance.get(key) != "PASS":
            fail(f"{key} is not PASS")
    if acceptance.get("MATERIAL_SETTLEMENT_SINGLE_CONTRACT") != (
        "NOT_APPLICABLE_NO_CONTRACT_BEARING_DETAIL"
    ):
        fail("material settlement must remain outside contract aggregation")
    if not acceptance.get("TEMP_DATABASE_REMOVED"):
        fail("temporary database cleanup is not confirmed")
    if acceptance.get("TEMP_RESOURCE_RESIDUE_COUNT") != 0:
        fail("temporary resource residue is not zero")
    print("UM_P2_SETTLEMENT_RELATION_GUARD=PASS")
    print(f"NEXT_SLICE={data['NEXT_SLICE']}")
    print(f"NEXT_SLICE_BLOCKER={data['NEXT_SLICE_BLOCKER']}")


if __name__ == "__main__":
    main()
