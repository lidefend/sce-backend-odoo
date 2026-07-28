#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import um_p3_core035_s07ac_confirmation_guard as core035_s07ac_guard


ROOT = Path(__file__).resolve().parents[2]
MATRIX = (
    ROOT
    / "docs/audit/um_p3/um_p3_s01_core_domain_authority_matrix_v1.json"
)
MAP_ZH = ROOT / "docs/audit/um_p3/um_p3_s01_core_domain_relation_map_v1.md"
MAP_EN = (
    ROOT / "docs/audit/um_p3/um_p3_s01_core_domain_relation_map_v1.en.md"
)
CORE_035_ENVIRONMENT = (
    ROOT / "docs/audit/um_p3/um_p3_core_035_s07a_environment_handoff_v1.json"
)
CORE_035_PROFILE = (
    ROOT / "docs/audit/um_p3/um_p3_core_035_s07a_source_profile_v1.json"
)
CORE_035_PLAN = (
    ROOT
    / "docs/audit/um_p3/um_p3_core_035_s07a_relation_remediation_plan_v1.json"
)
P2_AUDITS = {
    "S01": ROOT
    / "docs/audit/um_p2/um_p2_s01_receipt_relation_aggregation_v1.json",
    "S02": ROOT
    / "docs/audit/um_p2/um_p2_s02_payment_relation_aggregation_v1.json",
    "S03": ROOT
    / "docs/audit/um_p2/um_p2_s03_interfund_relation_aggregation_v1.json",
    "S04": ROOT
    / "docs/audit/um_p2/um_p2_s04_invoice_relation_aggregation_v1.json",
    "S05": ROOT
    / "docs/audit/um_p2/um_p2_s05_settlement_relation_aggregation_v1.json",
}

REQUIRED_RELATION_FIELDS = {
    "RELATION_ID",
    "SOURCE_MODEL",
    "TARGET_MODEL",
    "SOURCE_FIELD",
    "TARGET_FIELD",
    "BUSINESS_FACT",
    "AUTHORITY_SIDE",
    "PROJECTION_SIDE",
    "CARDINALITY",
    "REQUIREDNESS",
    "DERIVATION_POLICY",
    "CONFLICT_POLICY",
    "MULTI_VALUE_POLICY",
    "PROJECT_BOUNDARY",
    "COMPANY_BOUNDARY",
    "COUNTERPARTY_BOUNDARY",
    "CALLER_VISIBILITY_POLICY",
    "CREATE_REVALIDATION",
    "WRITE_REVALIDATION",
    "UNLINK_REVALIDATION",
    "GENERIC_CRUD_COVERAGE",
    "HEURISTIC_MATCHING_ALLOWED",
    "HISTORICAL_INFERENCE_ALLOWED",
    "IMPLEMENTATION_STATUS",
    "TEST_EVIDENCE",
    "AUDIT_EVIDENCE",
    "OPEN_GAP",
    "GAP_PRIORITY",
    "NEXT_SAFE_ACTION",
}
REQUIRED_MODELS = {
    "project.project",
    "construction.contract",
    "construction.contract.line",
    "purchase.order",
    "purchase.order.line",
    "sc.subcontract.register",
    "sc.subcontract.register.line",
    "sc.subcontract.settlement",
    "sc.subcontract.settlement.line",
    "sc.settlement.order",
    "sc.settlement.order.line",
    "sc.material.settlement",
    "sc.material.settlement.purchase.scope",
    "payment.request",
    "payment.request.line",
    "sc.payment.execution",
    "sc.receipt.income",
    "project.funding.baseline",
    "project.funding.baseline.line",
    "project.funding.actual.event.allocation",
    "payment.ledger",
    "sc.fund.account",
    "sc.fund.account.operation",
    "sc.invoice.registration",
    "sc.receipt.invoice.line",
    "sc.tax.deduction.registration",
    "res.partner",
    "res.company",
}
REQUIRED_CHAINS = {
    "CONTRACT_TO_SETTLEMENT",
    "SETTLEMENT_TO_PAYMENT_REQUEST",
    "PAYMENT_REQUEST_TO_PAYMENT_EXECUTION",
    "CONTRACT_TO_RECEIPT_REQUEST",
    "RECEIPT_REQUEST_TO_RECEIPT_EVENT",
    "SETTLEMENT_OR_CONTRACT_TO_INVOICE",
    "PROJECT_TO_FUND_PLAN",
    "FUND_PLAN_TO_ACTUAL_FUND_EVENT",
    "COUNTERPARTY_ACROSS_CONTRACT_SETTLEMENT_PAYMENT_INVOICE",
    "COMPANY_BOUNDARY_ACROSS_ALL_CHAINS",
    "SUBCONTRACT_REGISTER_TO_SETTLEMENT",
    "TAX_DEDUCTION_RELATION_MODELING",
}
CHAIN_SUMMARY_KEYS = {
    "CLOSED": "CLOSED_CHAINS",
    "PARTIAL": "PARTIAL_CHAINS",
    "BLOCKED_DECISION": "BLOCKED_DECISION_CHAINS",
    "BLOCKED_SCHEMA": "BLOCKED_SCHEMA_CHAINS",
    "OUT_OF_SCOPE": "OUT_OF_SCOPE_CHAINS",
}
PRIORITY = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "NONE": 4}
EXPECTED_FIXED_AUTHORITIES = {
    "RECEIPT_PRIMARY_RELATION_ANCHOR": (
        "payment.request via sc.receipt.income.payment_request_id"
    ),
    "RECEIPT_SECONDARY_RELATION_ANCHOR": (
        "construction.contract via sc.receipt.income.contract_id"
    ),
    "PAYMENT_BASIS_AUTHORITY": (
        "PAYMENT_REQUEST_DETAIL_SET_WHEN_PRESENT_OTHERWISE_EXCLUSIVE_"
        "STANDARD_OR_MATERIAL_HEADER"
    ),
    "PAYMENT_CONTRACT_DERIVATION_POLICY": (
        "DERIVE_FROM_COMPLETE_VALID_BASIS_SET_AND_WRITE_SCALAR_ONLY_WHEN_UNIQUE"
    ),
    "INTERFUND_PRIMARY_RELATION_ANCHORS": [
        "sc.fund.account.operation.source_account_id",
        "sc.fund.account.operation.target_account_id",
    ],
    "INTERFUND_PROJECT_DERIVATION_POLICY": (
        "SOURCE_AND_TARGET_PROJECTS_DERIVE_ONLY_FROM_THEIR_ACCOUNT_"
        "PROJECT_RELATIONS"
    ),
    "INVOICE_SOURCE_RELATION_POLICY": "TYPE_SPECIFIC_STRONG_RELATIONS",
    "INPUT_INVOICE_AUTHORITY": (
        "VISIBLE_SETTLEMENT_OR_FORMAL_INPUT_CONTRACT"
    ),
    "OUTPUT_INVOICE_AUTHORITY": (
        "VISIBLE_SETTLEMENT_OR_FORMAL_OUTPUT_CONTRACT"
    ),
    "PREPAID_TAX_AUTHORITY": (
        "PROJECT_AND_COUNTERPARTY_WITH_OPTIONAL_CONTRACT"
    ),
    "TAX_DEDUCTION_RELATION_MODELING": (
        "EXCLUDED_PENDING_SEPARATE_AUTHORITY"
    ),
    "SETTLEMENT_CONTRACT_AUTHORITY": "MULTI_CONTRACT_DETAIL_SET",
    "SETTLEMENT_HEADER_CONTRACT_ROLE": (
        "OPTIONAL_UNIQUE_CONTRACT_PROJECTION"
    ),
    "SETTLEMENT_DETAIL_CONTRACT_ROLE": "AUTHORITATIVE_BUSINESS_RELATION",
    "MULTI_CONTRACT_SETTLEMENT_ALLOWED": True,
    "SETTLEMENT_CONTRACT_DERIVATION_POLICY": (
        "COMPLETE_VALID_DETAIL_SET_UNIQUE_CONTRACT_ONLY"
    ),
    "FUND_PLAN_ROLE": "APPROVED_BUDGET_BASELINE",
    "FUND_PLAN_LINE_ROLE": "AUTHORITATIVE_PLANNED_BUDGET_BUCKET",
    "FUND_REQUEST_ROLE": "WORKFLOW_INTENT_NOT_FINAL_FUND_FACT",
    "ACTUAL_FUND_EVENT_MODEL": "payment.ledger",
    "ACTUAL_FUND_EVENT_ROLE": "AUTHORITATIVE_OCCURRED_FUND_FACT",
    "PLAN_EVENT_RELATION_MODEL": (
        "project.funding.actual.event.allocation"
    ),
    "PLAN_EVENT_RELATION_AUTHORITY": "EXPLICIT_ALLOCATION_RELATION",
    "PLAN_EVENT_CARDINALITY": (
        "MANY_TO_MANY_THROUGH_AMOUNT_BEARING_ALLOCATION"
    ),
    "CURRENT_ACTIVE_PLAN_AUTO_BINDING_ALLOWED": False,
    "PROJECT_ONLY_BINDING_ALLOWED": False,
    "MATERIAL_SETTLEMENT_ROLE": (
        "AUTHORITATIVE_SETTLED_QUANTITY_AND_AMOUNT_FACT"
    ),
    "PURCHASE_ORDER_ROLE": "AUTHORITATIVE_PROCUREMENT_COMMITMENT",
    "PURCHASE_ORDER_PROJECT_ROLE": (
        "AUTHORITATIVE_PROJECT_FOR_PROCURED_SCOPE"
    ),
    "PURCHASE_ORDER_SUPPLIER_ROLE": (
        "AUTHORITATIVE_SUPPLIER_FOR_PROCURED_SCOPE"
    ),
    "MATERIAL_SETTLEMENT_PURCHASE_RELATION_AUTHORITY": (
        "EXPLICIT_PURCHASE_RELATION_SET"
    ),
    "MATERIAL_SETTLEMENT_PURCHASE_RELATION_MODEL": (
        "sc.material.settlement.purchase.scope"
    ),
    "MATERIAL_SETTLEMENT_PURCHASE_CARDINALITY": (
        "ONE_SETTLEMENT_TO_ONE_OR_MORE_EXPLICIT_PURCHASE_SCOPES"
    ),
    "MULTI_PURCHASE_SETTLEMENT_ALLOWED": True,
    "PROJECT_ONLY_MATCHING_ALLOWED": False,
    "SUPPLIER_ONLY_MATCHING_ALLOWED": False,
    "SUBCONTRACT_CONTRACT_ROLE": (
        "AUTHORITATIVE_SUBCONTRACT_COMMITMENT_AND_SCOPE"
    ),
    "SUBCONTRACT_REGISTER_ROLE": (
        "AUTHORITATIVE_OCCURRED_PERFORMANCE_QUANTITY_OR_WORKLOAD_FACT"
    ),
    "SUBCONTRACT_SETTLEMENT_ROLE": (
        "AUTHORITATIVE_SETTLED_QUANTITY_AMOUNT_AND_STATUS_FACT"
    ),
    "REGISTER_SETTLEMENT_RELATION_AUTHORITY": (
        "EXPLICIT_REGISTER_RELATION_SET"
    ),
    "REGISTER_SETTLEMENT_RELATION_GRAIN": (
        "SUBCONTRACT_SETTLEMENT_LINE_TO_SUBCONTRACT_REGISTER_LINE"
    ),
    "REGISTER_SETTLEMENT_CARDINALITY": (
        "ONE_SETTLEMENT_TO_ONE_OR_MORE_EXPLICIT_REGISTER_SCOPES"
    ),
    "MULTI_REGISTER_SETTLEMENT_ALLOWED": True,
    "SPLIT_SETTLEMENT_OF_REGISTER_ALLOWED": True,
    "MULTI_CONTRACT_SUBCONTRACT_SETTLEMENT_ALLOWED": False,
    "CUMULATIVE_SETTLEMENT_POLICY": (
        "HARD_LIMIT_ON_FORMALLY_COMPARABLE_REGISTERED_QUANTITY"
    ),
    "CUMULATIVE_LIMIT_PRIMARY_DIMENSION": "QUANTITY_OR_FORMAL_WORKLOAD",
    "CUMULATIVE_INCLUDED_STATE_SEMANTICS": (
        "EFFECTIVE_APPROVED_OR_COMPLETED_SETTLEMENT"
    ),
    "CUMULATIVE_EFFECTIVE_STATE": "confirmed",
    "CUMULATIVE_AMOUNT_LIMIT_POLICY": (
        "HARD_LIMIT_ON_EFFECTIVE_TAX_INCLUDED_AMOUNT_IN_SUBCONTRACT_CONTRACT_CURRENCY"
    ),
    "COMMON_VALUATION_CURRENCY": "SUBCONTRACT_CONTRACT_CURRENCY",
    "COMMON_TAX_BASIS": "TAX_INCLUDED",
    "IMPLICIT_FX_CONVERSION_ALLOWED": False,
    "CROSS_CURRENCY_EFFECTIVE_RECORD_ALLOWED": False,
    "ROUNDING_BASIS": "AUTHORITATIVE_CURRENCY_ROUNDING",
    "CANCELLED_OR_VOID_SETTLEMENT_INCLUDED": False,
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_p2_authorities(data: dict, errors: list[str]) -> None:
    fixed = data.get("FIXED_AUTHORITIES", {})
    for key, expected in EXPECTED_FIXED_AUTHORITIES.items():
        if fixed.get(key) != expected:
            errors.append(f"FIXED_AUTHORITIES.{key} is not frozen")

    audits = {key: load_json(path) for key, path in P2_AUDITS.items()}
    comparisons = (
        ("S01", "PRIMARY_RELATION_ANCHOR", "RECEIPT_PRIMARY_RELATION_ANCHOR"),
        (
            "S01",
            "SECONDARY_RELATION_ANCHOR",
            "RECEIPT_SECONDARY_RELATION_ANCHOR",
        ),
        ("S02", "BASIS_AUTHORITY", "PAYMENT_BASIS_AUTHORITY"),
        (
            "S02",
            "CONTRACT_DERIVATION_POLICY",
            "PAYMENT_CONTRACT_DERIVATION_POLICY",
        ),
        (
            "S03",
            "PRIMARY_RELATION_ANCHORS",
            "INTERFUND_PRIMARY_RELATION_ANCHORS",
        ),
        (
            "S03",
            "PROJECT_DERIVATION_POLICY",
            "INTERFUND_PROJECT_DERIVATION_POLICY",
        ),
        (
            "S05",
            "SETTLEMENT_CONTRACT_AUTHORITY",
            "SETTLEMENT_CONTRACT_AUTHORITY",
        ),
        (
            "S05",
            "SETTLEMENT_HEADER_CONTRACT_ROLE",
            "SETTLEMENT_HEADER_CONTRACT_ROLE",
        ),
        (
            "S05",
            "SETTLEMENT_DETAIL_CONTRACT_ROLE",
            "SETTLEMENT_DETAIL_CONTRACT_ROLE",
        ),
        (
            "S05",
            "MULTI_CONTRACT_SETTLEMENT_ALLOWED",
            "MULTI_CONTRACT_SETTLEMENT_ALLOWED",
        ),
        (
            "S05",
            "CONTRACT_DERIVATION_POLICY",
            "SETTLEMENT_CONTRACT_DERIVATION_POLICY",
        ),
    )
    for slice_id, audit_key, fixed_key in comparisons:
        if audits[slice_id].get(audit_key) != fixed.get(fixed_key):
            errors.append(
                f"{slice_id}.{audit_key} diverges from {fixed_key}"
            )

    s04 = audits["S04"]
    if s04.get("SOURCE_KIND_RELATION_POLICY") != {
        "invoice_registration": (
            "USE_EXPLICIT_FORMAL_SETTLEMENT_OR_CONTRACT_RELATION_WITH_"
            "DIRECTION_SPECIFIC_CONTRACT_TYPE"
        ),
        "input_invoice_tax": "INPUT_SETTLEMENT_OR_FORMAL_INPUT_CONTRACT",
        "output_invoice_tax": "OUTPUT_SETTLEMENT_OR_FORMAL_OUTPUT_CONTRACT",
        "prepaid_tax": (
            "PROJECT_AND_TAXPAYER_AUTHORITY_WITH_OPTIONAL_FORMAL_CONTRACT"
        ),
    }:
        errors.append("S04 source-kind dispatch evidence changed")
    if s04.get("INPUT_INVOICE_BASIS_AUTHORITY") != (
        "CALLER_VISIBLE_SETTLEMENT_OR_EXPLICIT_FORMAL_INPUT_CONTRACT"
    ):
        errors.append("S04 input invoice authority evidence changed")
    if s04.get("OUTPUT_INVOICE_BASIS_AUTHORITY") != (
        "CALLER_VISIBLE_SETTLEMENT_OR_EXPLICIT_FORMAL_OUTPUT_CONTRACT"
    ):
        errors.append("S04 output invoice authority evidence changed")
    if s04.get("PREPAID_TAX_BASIS_AUTHORITY") != (
        "PROJECT_AND_COUNTERPARTY_WITHOUT_AUTOMATIC_CONTRACT"
    ):
        errors.append("S04 prepaid tax authority evidence changed")
    if s04.get("TAX_DEDUCTION_INCLUDED") is not False:
        errors.append("S04 tax deduction exclusion evidence changed")


def validate(data: dict, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if data.get("PHASE_ID") != "UM-P3-BUSINESS-CLOSURE":
        errors.append("PHASE_ID mismatch")
    if data.get("SLICE_ID") != (
        "UM-P3-S01-CORE-DOMAIN-AUTHORITY-BASELINE"
    ):
        errors.append("SLICE_ID mismatch")
    source = data.get("SOURCE_BASELINE", {})
    if source.get("HEAD") != "3af4f0e312155cf837fe2c9b2228526011f898e4":
        errors.append("source HEAD mismatch")
    if source.get("TREE") != "2081a02e72e98fecab77b84e6e7313c98d19f978":
        errors.append("source TREE mismatch")

    policies = data.get("GLOBAL_POLICIES", {})
    if policies.get("HEURISTIC_MATCHING_ALLOWED") is not False:
        errors.append("global heuristic matching must be false")
    if policies.get("HISTORICAL_INFERENCE_ALLOWED") is not False:
        errors.append("global historical inference must be false")

    declared_fields = set(data.get("REQUIRED_RELATION_FIELDS", []))
    if declared_fields != REQUIRED_RELATION_FIELDS:
        errors.append("required relation field declaration mismatch")
    models = set(data.get("DOMAIN_MODELS_COVERED", []))
    missing_models = REQUIRED_MODELS - models
    if missing_models:
        errors.append(f"missing domain models: {sorted(missing_models)}")

    relations = data.get("RELATIONS", [])
    ids = [relation.get("RELATION_ID") for relation in relations]
    if len(ids) != len(set(ids)):
        errors.append("relation identifiers are not unique")
    for relation in relations:
        relation_id = relation.get("RELATION_ID", "<missing>")
        missing = REQUIRED_RELATION_FIELDS - set(relation)
        if missing:
            errors.append(f"{relation_id} missing fields: {sorted(missing)}")
        if relation.get("HEURISTIC_MATCHING_ALLOWED") is not False:
            errors.append(f"{relation_id} permits heuristic matching")
        if relation.get("HISTORICAL_INFERENCE_ALLOWED") is not False:
            errors.append(f"{relation_id} permits historical inference")
        if relation.get("GAP_PRIORITY") not in PRIORITY:
            errors.append(f"{relation_id} has invalid gap priority")
        for evidence_key in ("TEST_EVIDENCE", "AUDIT_EVIDENCE"):
            for evidence in relation.get(evidence_key, []):
                if not (root / evidence).is_file():
                    errors.append(
                        f"{relation_id} missing {evidence_key}: {evidence}"
                    )

    chains = data.get("CHAINS", [])
    chain_ids = {chain.get("CHAIN_ID") for chain in chains}
    if chain_ids != REQUIRED_CHAINS:
        errors.append("required business closure chain set mismatch")
    counts = Counter(chain.get("STATUS") for chain in chains)
    summary = data.get("SUMMARY", {})
    for status, summary_key in CHAIN_SUMMARY_KEYS.items():
        if summary.get(summary_key) != counts.get(status, 0):
            errors.append(f"{summary_key} does not match chain statuses")
    if summary.get("RELATIONS_RECORDED") != len(relations):
        errors.append("RELATIONS_RECORDED does not match matrix")
    if summary.get("BUSINESS_LOGIC_CHANGED") is not True:
        errors.append("SUMMARY.BUSINESS_LOGIC_CHANGED must record S06")
    for key in ("ACL_CHANGED", "DATA_MIGRATION_REQUIRED"):
        if summary.get(key) is not False:
            errors.append(f"SUMMARY.{key} must remain false")
    if summary.get("RECORD_RULE_CHANGED") is not True:
        errors.append("SUMMARY.RECORD_RULE_CHANGED must record CORE-020")

    gaps = [
        chain
        for chain in chains
        if chain.get("GAP_PRIORITY") in PRIORITY
        and chain.get("GAP_PRIORITY") != "NONE"
    ]
    selected = data.get("GAP_SELECTION", {})
    if gaps:
        highest_rank = min(PRIORITY[chain["GAP_PRIORITY"]] for chain in gaps)
        highest = [
            chain
            for chain in gaps
            if PRIORITY[chain["GAP_PRIORITY"]] == highest_rank
        ]
        if selected.get("HIGHEST_PRIORITY_GAP") not in {
            chain["CHAIN_ID"] for chain in highest
        }:
            errors.append("selected gap is not a highest-priority chain")
    selected_relation = next(
        (
            relation
            for relation in relations
            if relation.get("RELATION_ID")
            == selected.get("HIGHEST_PRIORITY_RELATION")
        ),
        None,
    )
    if selected_relation is None:
        errors.append("selected gap relation does not exist")
    elif selected_relation.get("GAP_PRIORITY") != (
        next(
            (
                chain.get("GAP_PRIORITY")
                for chain in chains
                if chain.get("CHAIN_ID")
                == selected.get("HIGHEST_PRIORITY_GAP")
            ),
            None,
        )
    ):
        errors.append("selected relation and chain priorities diverge")
    if selected.get("SAFE_TO_IMPLEMENT") is not False:
        errors.append("selected historical remediation gap requires evidence")
    if selected.get("NEXT_TASK") != (
        "OBTAIN_AUTHORIZED_DUAL_REVIEWED_SETTLEMENT_TO_REGISTER_"
        "CONFIRMATION_SET"
    ):
        errors.append("selected next task mismatch")
    core_035 = next(
        (
            relation
            for relation in relations
            if relation.get("RELATION_ID")
            == "CORE-035-SUBCONTRACT-HISTORICAL-REGISTER-RELATION-REMEDIATION"
        ),
        {},
    )
    for key, expected in {
        "EXECUTION_STATE": "S07AC_CONFIRMATION_SET_READY",
        "POLICY_STATE": "OPEN",
        "PRIORITY_PRESERVED": True,
        "SKIPPED_FOR_CURRENT_EXECUTION_ONLY": False,
        "S07A_READY_TO_RESUME": False,
        "S07A_STATUS": "COMPLETE_NO_SOURCE_PROVEN_LINE_RELATION",
        "S07AC_STATUS": "READY_FOR_AUTHORIZED_REVIEW",
        "SOURCE_RELATION_EVIDENCE_FOUND": False,
        "DETERMINISTIC_MAPPING_AVAILABLE": False,
        "AUTOMATIC_MIGRATION_CANDIDATE_COUNT": 0,
        "AMBIGUOUS_COUNT": 76,
        "CONFLICTING_COUNT": 12,
        "REVIEW_ITEM_COUNT": 88,
        "AUTHORIZED_FINAL_COUNT": 0,
        "S07B_APPROVED": False,
        "S07B_READY_FOR_APPROVAL": False,
        "MIGRATION_EXECUTED": False,
    }.items():
        if core_035.get(key) != expected:
            errors.append(f"CORE-035 {key} source evidence drift")

    execution = data.get("EXECUTION_GAP_SELECTION", {})
    if execution.get("SAFE_CANDIDATE_COUNT") != 0:
        errors.append("execution matrix must have zero safe candidates")
    if execution.get("HIGHEST_REMAINING_RELATION") != "NONE":
        errors.append("execution matrix highest remaining relation mismatch")
    if execution.get("SAFE_TO_IMPLEMENT") is not False:
        errors.append("execution matrix must not invent a safe candidate")
    if execution.get("UNIQUE_NEXT_DECISION") != (
        "ASSIGN_AUTHORIZED_BUSINESS_OWNER_DATA_STEWARD_AND_SECOND_REVIEWER"
    ):
        errors.append("execution matrix unique next decision mismatch")

    for audit_path in (
        CORE_035_ENVIRONMENT,
        CORE_035_PROFILE,
        CORE_035_PLAN,
    ):
        if not audit_path.is_file():
            errors.append(
                f"missing CORE-035 S07A audit: {audit_path.relative_to(root)}"
            )
    if all(
        path.is_file()
        for path in (CORE_035_ENVIRONMENT, CORE_035_PROFILE, CORE_035_PLAN)
    ):
        environment = load_json(CORE_035_ENVIRONMENT)
        profile = load_json(CORE_035_PROFILE)
        plan = load_json(CORE_035_PLAN)
        for key, expected in {
            "S07A_READY_TO_RESUME": True,
            "S07A_STATUS": "SOURCE_PROFILING_COMPLETED",
            "S07B_APPROVED": False,
            "MIGRATION_EXECUTED": False,
            "RELATION_REMEDIATION_EXECUTED": False,
        }.items():
            if environment.get(key) != expected:
                errors.append(f"CORE-035 environment {key} drift")
        classification = profile.get("RELATION_CLASSIFICATION", {})
        for key, expected in {
            "TOTAL_SETTLEMENT_RECORDS": 88,
            "EXACT_AUTHORITATIVE_KEY_COUNT": 0,
            "UNIQUE_COMPOSITE_BUSINESS_KEY_COUNT": 0,
            "AMBIGUOUS_COUNT": 76,
            "UNMATCHED_COUNT": 0,
            "CONFLICTING_COUNT": 12,
            "AUTOMATIC_MIGRATION_CANDIDATE_COUNT": 0,
        }.items():
            if classification.get(key) != expected:
                errors.append(f"CORE-035 profile {key} drift")
        for key, expected in {
            "SOURCE_RELATION_EVIDENCE_FOUND": False,
            "DETERMINISTIC_MAPPING_AVAILABLE": False,
            "HEURISTIC_MATCHING_USED": False,
            "MIGRATION_EXECUTED": False,
            "S07B_READY_FOR_APPROVAL": False,
        }.items():
            if profile.get(key) != expected:
                errors.append(f"CORE-035 profile {key} drift")
        if plan.get("CURRENT_AUTOMATIC_MIGRATION_CANDIDATE_COUNT") != 0:
            errors.append("CORE-035 remediation plan invented candidates")
        if plan.get("S07B_READY_FOR_APPROVAL") is not False:
            errors.append("CORE-035 remediation plan prematurely approves S07B")
        s07ac_errors = core035_s07ac_guard.validate(
            core035_s07ac_guard.load_json(core035_s07ac_guard.MANIFEST),
            core035_s07ac_guard.load_json(core035_s07ac_guard.ITEMS),
            core035_s07ac_guard.load_json(core035_s07ac_guard.AUTHORIZATION),
            profile,
            core035_s07ac_guard.file_sha256(core035_s07ac_guard.ITEMS),
        )
        errors.extend(
            f"CORE-035 S07A-C {error}" for error in s07ac_errors
        )
    core_034 = next(
        (
            relation
            for relation in relations
            if relation.get("RELATION_ID")
            == "CORE-034-SUBCONTRACT-REGISTER-CUMULATIVE-AMOUNT-POLICY"
        ),
        {},
    )
    for key, expected in {
        "IMPLEMENTATION_STATUS": "VERIFIED",
        "OPEN_GAP": "NONE",
        "FORMAL_APPROVAL_ID": (
            "UM_P3_CORE_034_SUBCONTRACT_CUMULATIVE_AMOUNT_VALUATION_BASIS"
        ),
        "FORMAL_APPROVAL_APPLIED": True,
        "COMMON_VALUATION_CURRENCY": "SUBCONTRACT_CONTRACT_CURRENCY",
        "COMMON_TAX_BASIS": "TAX_INCLUDED",
        "IMPLICIT_FX_CONVERSION_ALLOWED": False,
        "CROSS_CURRENCY_EFFECTIVE_RECORD_ALLOWED": False,
    }.items():
        if core_034.get(key) != expected:
            errors.append(f"CORE-034 {key} closure drift")
    core_020 = next(
        (
            relation
            for relation in relations
            if relation.get("RELATION_ID")
            == "CORE-020-PAYMENT-LEDGER-REQUEST"
        ),
        {},
    )
    for key, expected in {
        "IMPLEMENTATION_STATUS": "VERIFIED",
        "OPEN_GAP": "NONE",
        "FORMAL_APPROVAL_ID": (
            "UM_P3_CORE_020_PAYMENT_LEDGER_ALLOWED_COMPANY_RECORD_RULE"
        ),
        "FORMAL_APPROVAL_APPLIED": True,
        "PAYMENT_REQUEST_REQUIRED": True,
        "ORPHAN_LEDGER_POLICY_REQUIRED": False,
        "ALLOWED_COMPANY_RULE": (
            "payment_request_id.company_id in company_ids"
        ),
        "RECORD_RULE_CHANGED": True,
        "OTHER_RECORD_RULES_CHANGED": False,
        "PUBLIC_PERMISSION_FRAMEWORK_REFACTORED": False,
        "PUBLIC_PERMISSION_FRAMEWORK_CHANGE_REQUIRED": False,
    }.items():
        if core_020.get(key) != expected:
            errors.append(f"CORE-020 {key} closure drift")

    _check_p2_authorities(data, errors)
    for path in (MAP_ZH, MAP_EN):
        if not path.is_file():
            errors.append(f"missing relation map: {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        for token in (
            "FUND_PLAN_TO_ACTUAL_FUND_EVENT",
            "OPTIONAL_UNIQUE_CONTRACT_PROJECTION",
            "MULTI_CONTRACT_DETAIL_SET",
            "sc.material.settlement.purchase.scope",
            "EXPLICIT_REGISTER_RELATION_SET",
            "HARD_LIMIT_ON_FORMALLY_COMPARABLE_REGISTERED_QUANTITY",
            "HARD_LIMIT_ON_EFFECTIVE_TAX_INCLUDED_AMOUNT_IN_SUBCONTRACT_CONTRACT_CURRENCY",
            "COMMON_VALUATION_CURRENCY=SUBCONTRACT_CONTRACT_CURRENCY",
            "COMMON_TAX_BASIS=TAX_INCLUDED",
            "CORE_035_EXECUTION_STATE=S07AC_CONFIRMATION_SET_READY",
            "UM_P3_CORE_020_PAYMENT_LEDGER_ALLOWED_COMPANY_RECORD_RULE",
            "PAYMENT_REQUEST_COMPANY_IN_ALLOWED_COMPANY_IDS",
            "ASSIGN_AUTHORIZED_BUSINESS_OWNER_DATA_STEWARD_AND_SECOND_REVIEWER",
        ):
            if token not in text:
                errors.append(f"{path.name} missing frozen token {token}")
    return errors


def main() -> None:
    data = load_json(MATRIX)
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"UM_P3_CORE_DOMAIN_AUTHORITY_BASELINE_GUARD=FAIL: {error}")
        raise SystemExit(1)
    summary = data["SUMMARY"]
    gap = data["GAP_SELECTION"]
    print("UM_P3_CORE_DOMAIN_AUTHORITY_BASELINE_GUARD=PASS")
    print(f"RELATIONS_RECORDED={summary['RELATIONS_RECORDED']}")
    for summary_key in CHAIN_SUMMARY_KEYS.values():
        print(f"{summary_key}={summary[summary_key]}")
    print(f"NEXT_GAP={gap['HIGHEST_PRIORITY_GAP']}")
    print(
        "NEXT_GAP_SAFE_TO_IMPLEMENT="
        f"{str(gap['SAFE_TO_IMPLEMENT']).lower()}"
    )
    print(f"NEXT_TASK={gap['NEXT_TASK']}")
    execution = data["EXECUTION_GAP_SELECTION"]
    print(
        "SAFE_CANDIDATE_COUNT="
        f"{execution['SAFE_CANDIDATE_COUNT']}"
    )
    print(
        "UNIQUE_NEXT_DECISION="
        f"{execution['UNIQUE_NEXT_DECISION']}"
    )


if __name__ == "__main__":
    main()
