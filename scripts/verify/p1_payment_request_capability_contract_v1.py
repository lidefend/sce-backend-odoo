#!/usr/bin/env python3
"""Fail closed when the P1 payment-request capability boundary drifts."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config/p1_payment_request_capability_contract_v1.json"


def main() -> int:
    contract = json.loads(PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    if contract.get("schema_version") != "p1_payment_request_capability_contract.v1":
        errors.append("unexpected schema version")
    if contract.get("product_stage") != "P1_construction_industry_standard_product":
        errors.append("payment-request work left P1 standard product")
    if contract.get("specific_customer_or_tenant_scope") != "forbidden":
        errors.append("specific customer or tenant scope is not forbidden")
    capabilities = contract.get("capabilities", [])
    if len(capabilities) != 11 or len({row.get("key") for row in capabilities}) != 11:
        errors.append("capability set must contain eleven unique keys")
    for row in capabilities:
        if not row.get("evidence"):
            errors.append(f"{row.get('key')} has no evidence")
        if row.get("status") != "implemented" and not row.get("gap"):
            errors.append(f"{row.get('key')} has an unexplained gap")
    if contract.get("implementation_sequence", [])[-1].get("status") != "blocked_until_business_acceptance":
        errors.append("component evaluation is no longer acceptance gated")
    corpus = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "addons/smart_construction_core/models/core/payment_request.py",
            "addons/smart_construction_core/models/core/payment_execution.py",
            "addons/smart_construction_core/views/core/payment_request_views.xml",
        )
    )
    for anchor in (
        "_check_contract_business_identity",
        "_sc_assert_transaction_eligible",
        "payee_account_completeness",
        "_business_fact_fields",
        "合同本身是预付款",
        "_assert_payment_relation_anchors_immutable",
        "history_surface_sync",
        "self.env.su",
    ):
        if anchor not in corpus:
            errors.append(f"missing payment capability anchor: {anchor}")
    if errors:
        for error in errors:
            print(f"[p1-payment-request-capability] FAIL {error}", file=sys.stderr)
        return 1
    gaps = sum(row.get("status") != "implemented" for row in capabilities)
    print(
        f"[p1-payment-request-capability] PASS capabilities={len(capabilities)} "
        f"open_gaps={gaps} component=blocked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
