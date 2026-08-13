#!/usr/bin/env python3
"""Fail closed when the P1 income-contract capability loses its product boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "config/p1_income_contract_capability_contract_v1.json"


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    if contract.get("schema_version") != "p1_income_contract_capability_contract.v1":
        errors.append("unexpected schema version")
    if contract.get("product_stage") != "P1_construction_industry_standard_product":
        errors.append("income-contract work left the P1 standard-product stage")
    if contract.get("specific_customer_or_tenant_scope") != "forbidden":
        errors.append("specific customer or tenant scope is not forbidden")
    boundary = contract.get("business_boundary", {})
    if "frontend_component_selection" not in boundary.get("excluded", []):
        errors.append("component selection is no longer excluded")
    capabilities = contract.get("capabilities", [])
    keys = [row.get("key") for row in capabilities]
    if len(keys) != len(set(keys)) or len(keys) != 10:
        errors.append("income-contract capability set must contain ten unique keys")
    for row in capabilities:
        if not row.get("evidence"):
            errors.append(f"{row.get('key')} has no evidence")
        if row.get("status") != "implemented" and not row.get("gap"):
            errors.append(f"{row.get('key')} has an unexplained gap")
    sequence = contract.get("implementation_sequence", [])
    if not sequence or sequence[-1].get("status") != "blocked_until_business_acceptance":
        errors.append("component evaluation is no longer business-acceptance gated")

    corpus = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "addons/smart_construction_core/models/support/contract_center.py",
            "addons/smart_construction_core/models/support/contract_professional.py",
            "addons/smart_construction_core/views/core/contract_views.xml",
        )
    )
    for anchor in (
        "_sc_assert_transaction_eligible",
        "action_open_settlements",
        "action_open_payment_requests",
        "action_open_invoice_registrations",
        "action_open_receipt_incomes",
    ):
        if anchor not in corpus:
            errors.append(f"missing source anchor: {anchor}")
    if errors:
        for error in errors:
            print(f"[p1-income-contract-capability] FAIL {error}", file=sys.stderr)
        return 1
    gaps = sum(row.get("status") != "implemented" for row in capabilities)
    print(f"[p1-income-contract-capability] PASS capabilities={len(capabilities)} open_gaps={gaps} component=blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
