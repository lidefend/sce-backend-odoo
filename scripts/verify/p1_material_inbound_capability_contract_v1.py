#!/usr/bin/env python3
"""Fail closed when P1 material-inbound source rules drift."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config/p1_material_inbound_capability_contract_v1.json"


def main() -> int:
    contract = json.loads(PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    if contract.get("schema_version") != "p1_material_inbound_capability_contract.v1":
        errors.append("unexpected schema version")
    if contract.get("product_stage") != "P1_construction_industry_standard_product":
        errors.append("material-inbound work left P1 standard product")
    if contract.get("specific_customer_or_tenant_scope") != "forbidden":
        errors.append("specific customer or tenant scope is not forbidden")
    source_types = contract.get("source_types", {})
    if set(source_types) != {
        "contract_execution", "spot_purchase", "site_variation",
        "provisional_pending_contract", "adjustment_reversal", "internal_transfer",
    }:
        errors.append("source type set drifted")
    if source_types.get("contract_execution", {}).get("contract_required") is not True:
        errors.append("contract execution no longer requires a contract")
    if any(source_types[key].get("contract_required") for key in source_types if key != "contract_execution"):
        errors.append("non-contract source incorrectly requires a contract")
    capabilities = contract.get("capabilities", [])
    if len(capabilities) != 10 or len({row.get("key") for row in capabilities}) != 10:
        errors.append("capability set must contain ten unique keys")
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
            "addons/smart_construction_core/models/core/material_acceptance.py",
            "addons/smart_construction_core/views/core/material_acceptance_views.xml",
        )
    )
    for anchor in ("source_type", "contract_execution", "_validate_source_relationships", "_sc_assert_transaction_eligible"):
        if anchor not in corpus:
            errors.append(f"missing source anchor: {anchor}")
    if errors:
        for error in errors:
            print(f"[p1-material-inbound-capability] FAIL {error}", file=sys.stderr)
        return 1
    gaps = sum(row.get("status") != "implemented" for row in capabilities)
    print(f"[p1-material-inbound-capability] PASS capabilities={len(capabilities)} open_gaps={gaps} component=blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
