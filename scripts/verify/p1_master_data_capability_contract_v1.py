#!/usr/bin/env python3
"""Fail closed when the P1 master-data product capability loses its boundary."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "config/p1_master_data_capability_contract_v1.json"


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    errors: list[str] = []
    if contract.get("schema_version") != "p1_master_data_capability_contract.v1":
        errors.append("unexpected schema version")
    if contract.get("product_stage") != "P1_construction_industry_standard_product":
        errors.append("master-data work left the P1 standard-product stage")
    if contract.get("specific_customer_or_tenant_scope") != "forbidden":
        errors.append("specific customer or tenant scope is not forbidden")

    representative = contract.get("representative_object", {})
    if representative.get("meaning") != "system_business_role_view_of_counterparty_master_data":
        errors.append("customer master-data object meaning drifted")
    if representative.get("not_meaning") != "specific_customer_delivery_or_customization":
        errors.append("customer delivery/customization ambiguity returned")

    capabilities = contract.get("capabilities", [])
    capability_keys = [row.get("key") for row in capabilities]
    if len(capability_keys) != len(set(capability_keys)):
        errors.append("capability keys must be unique")
    required = {
        "identity_and_role", "contact_and_address", "tax_bank_and_settlement_profile",
        "evidence_and_notes", "lifecycle_and_reference_protection",
        "permission_and_risk_governance", "duplicate_identification",
        "transaction_eligibility_control", "related_business_trace",
        "task_first_native_form", "search_and_recovery",
    }
    if set(capability_keys) != required:
        errors.append("master-data capability set drifted")
    for row in capabilities:
        if not row.get("evidence"):
            errors.append(f"{row.get('key')} has no source evidence")
        if row.get("status") in {"partial", "source_gap", "runtime_verification_required"} and not row.get("gap"):
            errors.append(f"{row.get('key')} has an unexplained gap")

    assessment = contract.get("benchmark_assessment", {})
    scores = [*assessment.get("information_completeness", {}).values(), *assessment.get("handling_convenience", {}).values()]
    if not scores or any(not isinstance(score, int) or score < 0 or score > 2 for score in scores):
        errors.append("source-only benchmark scores must stay in the 0..2 range")
    if assessment.get("runtime_level_three_forbidden_without_authenticated_browser_evidence") is not True:
        errors.append("runtime level 3 must remain browser-evidence gated")

    sequence = contract.get("implementation_sequence", [])
    if [row.get("id") for row in sequence] != ["P1-MD-001", "P1-MD-002", "P1-MD-003", "P1-MD-004", "P1-MD-005"]:
        errors.append("implementation sequence drifted")
    if not sequence or sequence[-1].get("priority") != "blocked_until_business_acceptance":
        errors.append("component evaluation is no longer blocked by business acceptance")

    corpus_paths = [
        ROOT / "addons/smart_construction_core/models/support/partner_business.py",
        ROOT / "addons/smart_construction_core/views/support/account_extend_views.xml",
        ROOT / "addons/smart_construction_core/views/menu_business_taxonomy.xml",
        ROOT / "addons/smart_construction_core/models/support/partner_business_fact_line.py",
        ROOT / "addons/smart_construction_core/views/support/partner_business_fact_line_views.xml",
    ]
    corpus = "\n".join(path.read_text(encoding="utf-8") for path in corpus_paths)
    for anchor in ("class ResPartner", 'id="view_sc_customer_partner_form"', 'id="action_sc_customer_partner"', "class ScPartnerBusinessFactLine", 'id="action_sc_partner_business_fact_line"'):
        if anchor not in corpus:
            errors.append(f"unresolved repository anchor: {anchor}")

    if errors:
        for error in errors:
            print(f"[p1-master-data-capability] FAIL {error}", file=sys.stderr)
        return 1
    gaps = sum(row.get("status") != "implemented" for row in capabilities)
    print(f"[p1-master-data-capability] PASS capabilities={len(capabilities)} open_gaps={gaps} component=blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
