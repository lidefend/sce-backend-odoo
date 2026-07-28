#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/audit/um_p1/um_p1_s01_ownership_visibility_contract_v1.json"
PLAN = ROOT / "docs/audit/user_business_data_portrait_productization_plan_2026-06-10.md"
RULES = ROOT / "addons/smart_construction_core/security/sc_record_rules.xml"
ACL = ROOT / "addons/smart_construction_core/security/ir.model.access.csv"

EXPECTED_ORDER = [
    "UM-P1-ENTRY-01-PROJECT-RECEIPT",
    "UM-P1-ENTRY-02-PAYMENT-REQUEST-EXECUTION",
    "UM-P1-ENTRY-03-INVOICE-DEDUCTION",
    "UM-P1-ENTRY-04-INTERFUND-TRANSFER",
    "UM-P1-ENTRY-05-CONTRACT-SETTLEMENT",
    "UM-P1-ENTRY-06-COST-LEDGER",
]
EXPECTED_NAMES = [
    "项目收款登记",
    "付款申请/付款执行",
    "发票登记/抵扣登记",
    "资金往来/账户调拨",
    "合同结算",
    "成本台账",
]
MODEL_SOURCES = {
    "sc.receipt.income": "addons/smart_construction_core/models/core/receipt_income.py",
    "payment.request": "addons/smart_construction_core/models/core/payment_request.py",
    "sc.payment.execution": "addons/smart_construction_core/models/core/payment_execution.py",
    "sc.invoice.registration": "addons/smart_construction_core/models/core/invoice_registration.py",
    "sc.tax.deduction.registration": "addons/smart_construction_core/models/core/tax_deduction_registration.py",
    "sc.fund.account.operation": "addons/smart_construction_core/models/core/fund_account_operation.py",
    "sc.financing.loan": "addons/smart_construction_core/models/core/financing_loan.py",
    "sc.settlement.order": "addons/smart_construction_core/models/core/settlement_order.py",
    "project.cost.ledger": "addons/smart_construction_core/models/core/cost_domain.py",
}
REQUIRED_FIELDS = {
    "sc.receipt.income": {"project_id", "company_id"},
    "payment.request": {"project_id", "company_id"},
    "sc.payment.execution": {"project_id", "company_id"},
    "sc.invoice.registration": {"project_id", "company_id"},
    "sc.tax.deduction.registration": {"project_id", "company_id"},
    "sc.fund.account.operation": {"project_id", "company_id"},
    "sc.financing.loan": {"project_id", "company_id"},
    "sc.settlement.order": {"project_id", "company_id", "entry_user_id"},
    "project.cost.ledger": {"project_id", "company_id"},
}
MODEL_REFS = {
    "sc.receipt.income": "model_sc_receipt_income",
    "payment.request": "model_payment_request",
    "sc.payment.execution": "model_sc_payment_execution",
    "sc.invoice.registration": "model_sc_invoice_registration",
    "sc.tax.deduction.registration": "model_sc_tax_deduction_registration",
    "sc.fund.account.operation": "model_sc_fund_account_operation",
    "sc.financing.loan": "model_sc_financing_loan",
    "sc.settlement.order": "model_sc_settlement_order",
    "project.cost.ledger": "model_project_cost_ledger",
}
EXPECTED_RULES = {
    "UM-P1-ENTRY-01-PROJECT-RECEIPT": {
        "rule_sc_business_initiator_receipt_income",
        "rule_sc_finance_read_receipt_income",
        "rule_sc_finance_user_receipt_income",
        "rule_sc_finance_manager_receipt_income",
    },
    "UM-P1-ENTRY-02-PAYMENT-REQUEST-EXECUTION": {
        "rule_sc_business_initiator_payment_request",
        "rule_sc_finance_read_payment_request",
        "rule_sc_finance_user_payment_request",
        "rule_sc_finance_manager_payment_request",
        "rule_sc_executive_payment_request",
        "rule_sc_config_admin_payment_request",
        "rule_sc_business_initiator_payment_execution",
        "rule_sc_finance_read_payment_execution",
        "rule_sc_finance_user_payment_execution",
        "rule_sc_finance_manager_payment_execution",
    },
    "UM-P1-ENTRY-03-INVOICE-DEDUCTION": {
        "rule_sc_invoice_registration_company",
        "rule_sc_finance_read_invoice_registration",
        "rule_sc_finance_user_invoice_registration",
        "rule_sc_finance_manager_invoice_registration",
        "rule_sc_business_initiator_invoice_registration",
        "rule_sc_tax_deduction_registration_company",
        "rule_sc_finance_read_tax_deduction_registration",
        "rule_sc_finance_user_tax_deduction_registration",
        "rule_sc_finance_manager_tax_deduction_registration",
        "rule_sc_config_admin_tax_deduction_registration",
        "rule_sc_business_initiator_tax_deduction_registration",
    },
    "UM-P1-ENTRY-04-INTERFUND-TRANSFER": {
        "rule_sc_fund_account_operation_company",
        "rule_sc_finance_read_fund_account_operation",
        "rule_sc_finance_user_fund_account_operation",
        "rule_sc_finance_manager_fund_account_operation",
        "rule_sc_business_initiator_fund_account_operation",
        "rule_sc_financing_loan_company",
        "rule_sc_finance_read_financing_loan",
        "rule_sc_finance_user_financing_loan",
        "rule_sc_finance_manager_financing_loan",
        "rule_sc_business_initiator_financing_loan",
    },
    "UM-P1-ENTRY-05-CONTRACT-SETTLEMENT": {
        "rule_sc_settlement_read_order",
        "rule_sc_settlement_user_order",
        "rule_sc_settlement_manager_order",
        "rule_sc_config_admin_settlement_order_all",
    },
    "UM-P1-ENTRY-06-COST-LEDGER": {
        "rule_sc_project_cost_ledger_company",
        "rule_sc_cost_read_project_cost_ledger",
        "rule_sc_cost_user_project_cost_ledger",
        "rule_sc_cost_manager_project_cost_ledger",
    },
}
REQUIRED_ENTRY_FIELDS = {
    "ENTRY_ID",
    "ENTRY_NAME",
    "SOURCE_LOCATION",
    "AFFECTED_ENTRYPOINT",
    "AFFECTED_MODEL",
    "OWNERSHIP_FIELD",
    "COMPANY_FIELD",
    "PROJECT_OR_BUSINESS_SCOPE_FIELD",
    "ORDINARY_USER_ALLOWED_SCOPE",
    "CROSS_USER_BEHAVIOR",
    "CROSS_COMPANY_BEHAVIOR",
    "ADMINISTRATOR_BEHAVIOR",
    "MISSING_IDENTIFIER_BEHAVIOR",
    "UNAUTHORIZED_IDENTIFIER_BEHAVIOR",
    "UNAUTHORIZED_AND_NONEXISTENT_EQUIVALENCE",
    "NO_SCOPE_OR_DEFAULT_BEHAVIOR",
    "CURRENT_PRODUCT_IMPLEMENTATION_STATUS",
    "REQUIRED_FUTURE_PRODUCT_SLICE",
    "CONTRACT_EVIDENCE",
    "PRODUCT_GAP",
    "EXPECTED_RECORD_RULE_IDS",
}


def _class_fields(path: Path, model_name: str) -> set[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        declared_name = None
        fields: set[str] = set()
        for statement in node.body:
            if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                continue
            target = statement.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if target.id == "_name":
                try:
                    declared_name = ast.literal_eval(statement.value)
                except (ValueError, TypeError):
                    declared_name = None
            elif (
                isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Attribute)
                and isinstance(statement.value.func.value, ast.Name)
                and statement.value.func.value.id == "fields"
            ):
                fields.add(target.id)
        if declared_name == model_name:
            return fields
    raise AssertionError(f"model declaration not found: {model_name} in {path.relative_to(ROOT)}")


def _rule_inventory() -> dict[str, set[str]]:
    inventory = {model: set() for model in MODEL_REFS}
    refs_to_models = {ref: model for model, ref in MODEL_REFS.items()}
    root = ET.parse(RULES).getroot()
    for record in root.iter("record"):
        fields = {field.get("name"): field for field in record.findall("field")}
        model_field = fields.get("model_id")
        model_ref = model_field.get("ref") if model_field is not None else None
        if model_ref in refs_to_models:
            inventory[refs_to_models[model_ref]].add(str(record.get("id") or ""))
    return inventory


def _entry_rules(entry: dict, inventory: dict[str, set[str]]) -> set[str]:
    return {
        rule_id
        for model in entry["AFFECTED_MODEL"]
        for rule_id in inventory.get(model, set())
        if rule_id in set(entry["EXPECTED_RECORD_RULE_IDS"])
    }


def main() -> int:
    failures: list[str] = []
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except Exception as exc:
        print("[um_p1_ownership_visibility_contract_guard] FAIL")
        print(f"- cannot load contract: {exc}")
        return 1

    if contract.get("SCHEMA_VERSION") != "um_p1_ownership_visibility_contract.v1":
        failures.append("schema version mismatch")
    if contract.get("SLICE_ID") != "UM-P1-S01-OWNERSHIP-VISIBILITY-CONTRACT-BASELINE":
        failures.append("slice ID mismatch")
    approval = contract.get("APPROVAL") or {}
    if approval.get("STATUS") != "FORMALLY_APPROVED":
        failures.append("formal approval is missing")
    if approval.get("SOURCE") != "USER_DECISION_2026-07-25":
        failures.append("approval source mismatch")
    if approval.get("FULL_USER_MANAGEMENT_PRODUCTIZATION") != "DEFERRED":
        failures.append("full user-management productization must remain deferred")
    if contract.get("P1_ENTRY_COUNT") != 6:
        failures.append("P1 entry count must be 6")
    if contract.get("P1_ENTRY_ORDER") != EXPECTED_ORDER:
        failures.append("P1 entry order differs from the approved document order")

    entries = contract.get("ENTRIES")
    if not isinstance(entries, list) or len(entries) != 6:
        failures.append("contract must contain exactly six entry records")
        entries = []
    ids = [entry.get("ENTRY_ID") for entry in entries]
    names = [entry.get("ENTRY_NAME") for entry in entries]
    if ids != EXPECTED_ORDER:
        failures.append("entry IDs are not unique and ordered")
    if names != EXPECTED_NAMES:
        failures.append("entry names are not in the approved document order")

    plan = PLAN.read_text(encoding="utf-8")
    p1_start = plan.find("P1：建立统一业务办理入口")
    p1_end = plan.find("P2：建立关系口径和非侵入式事实归集", p1_start)
    p1_plan = plan[p1_start:p1_end] if p1_start >= 0 and p1_end > p1_start else ""
    positions = [p1_plan.find(name) for name in EXPECTED_NAMES]
    if any(position < 0 for position in positions):
        failures.append("the source plan does not contain all six approved entry names")
    elif positions != sorted(positions):
        failures.append("the source plan entry order changed")

    inventory = _rule_inventory()
    acl_source = ACL.read_text(encoding="utf-8")
    for entry in entries:
        missing = REQUIRED_ENTRY_FIELDS - set(entry)
        if missing:
            failures.append(f"{entry.get('ENTRY_ID')} missing fields: {sorted(missing)}")
            continue
        if not entry["CONTRACT_EVIDENCE"]:
            failures.append(f"{entry['ENTRY_ID']} has no positive evidence")
        if entry["PRODUCT_GAP"]:
            failures.append(f"{entry['ENTRY_ID']} retains a product gap after the approved P1 sequence")
        expected_rules = EXPECTED_RULES[entry["ENTRY_ID"]]
        if set(entry["EXPECTED_RECORD_RULE_IDS"]) != expected_rules:
            failures.append(f"{entry['ENTRY_ID']} expected rule list drifted")
        if _entry_rules(entry, inventory) != expected_rules:
            failures.append(f"{entry['ENTRY_ID']} committed record-rule topology drifted")

        for model_name in entry["AFFECTED_MODEL"]:
            source_rel = MODEL_SOURCES.get(model_name)
            if not source_rel:
                failures.append(f"{entry['ENTRY_ID']} has unregistered model source: {model_name}")
                continue
            source_path = ROOT / source_rel
            if not source_path.exists():
                failures.append(f"{entry['ENTRY_ID']} model source missing: {source_rel}")
                continue
            try:
                actual_fields = _class_fields(source_path, model_name)
            except AssertionError as exc:
                failures.append(str(exc))
                continue
            expected_fields = REQUIRED_FIELDS[model_name]
            if not expected_fields.issubset(actual_fields):
                failures.append(
                    f"{model_name} ownership/company field topology drifted: "
                    f"missing {sorted(expected_fields - actual_fields)}"
                )
            model_ref = MODEL_REFS.get(model_name)
            if model_ref and model_ref not in acl_source:
                failures.append(f"{model_name} has no committed ACL reference")

    next_slice = contract.get("NEXT_DOCUMENT_ORDER_SLICE") or {}
    if next_slice.get("SLICE_ID") != "UM-P1-DOCUMENT-ORDER-COMPLETE":
        failures.append("all six approved P1 document-order entries must be complete")
    if next_slice.get("IMPLEMENTATION_GATE") != "NO_REMAINING_P1_ENTRY":
        failures.append("the completed P1 sequence must not invent a seventh entry")
    if contract.get("S01_PRODUCT_FILES_CHANGED") != []:
        failures.append("S01 must not record product-file changes")
    if contract.get("S01_BUSINESS_LOGIC_CHANGED") is not False:
        failures.append("S01 must not record business-logic changes")
    s02_verification = contract.get("S02_VERIFICATION") or {}
    if s02_verification.get("RESULT") != "PASS":
        failures.append("S02 real-ORM verification result must be PASS")
    if not all(
        s02_verification.get(field) is True
        for field in (
            "REAL_ODOO_REGISTRY_USED",
            "REAL_ORM_USED",
            "TEMP_DATABASE_REMOVED",
            "TEMP_RESOURCES_REMOVED",
            "DATABASE_BASELINE_RESTORED",
            "CONTAINER_BASELINE_RESTORED",
            "NETWORK_BASELINE_RESTORED",
            "VOLUME_BASELINE_RESTORED",
        )
    ):
        failures.append("S02 real-ORM evidence or exact resource cleanup is incomplete")
    if s02_verification.get("CONTROLLED_ORM_DOUBLES_USED") is not False:
        failures.append("S02 authorization evidence must not use controlled ORM doubles")
    if s02_verification.get("NEW_OR_WORSENED_FAILURES") != []:
        failures.append("S02 must not introduce or worsen quality-gate failures")
    s03_verification = contract.get("S03_VERIFICATION") or {}
    if s03_verification.get("RESULT") != "PASS":
        failures.append("S03 real-ORM verification result must be PASS")
    if s03_verification.get("PRODUCT_FILES_CHANGED") != []:
        failures.append("S03 must remain a verification-only slice")
    if not all(
        s03_verification.get(field) is True
        for field in (
            "REAL_ODOO_REGISTRY_USED",
            "REAL_ORM_USED",
            "FIRST_RUN_TEMP_DATABASE_REMOVED",
            "FIRST_RUN_TEMP_RESOURCES_REMOVED",
            "FINAL_TEMP_DATABASE_REMOVED",
            "FINAL_TEMP_RESOURCES_REMOVED",
            "DATABASE_BASELINE_RESTORED",
            "CONTAINER_BASELINE_RESTORED",
            "NETWORK_BASELINE_RESTORED",
            "VOLUME_BASELINE_RESTORED",
        )
    ):
        failures.append("S03 real-ORM evidence or exact resource cleanup is incomplete")
    if s03_verification.get("CONTROLLED_ORM_DOUBLES_USED") is not False:
        failures.append("S03 authorization evidence must not use controlled ORM doubles")
    if s03_verification.get("NEW_OR_WORSENED_FAILURES") != []:
        failures.append("S03 must not introduce or worsen quality-gate failures")
    s04_verification = contract.get("S04_VERIFICATION") or {}
    if s04_verification.get("RESULT") != "PASS":
        failures.append("S04 real-ORM verification result must be PASS")
    if not all(
        s04_verification.get(field) is True
        for field in (
            "REAL_ODOO_REGISTRY_USED",
            "REAL_ORM_USED",
            "FIRST_RUN_TEMP_DATABASE_REMOVED",
            "FIRST_RUN_TEMP_RESOURCES_REMOVED",
            "FINAL_TEMP_DATABASE_REMOVED",
            "FINAL_TEMP_RESOURCES_REMOVED",
            "DATABASE_BASELINE_RESTORED",
            "CONTAINER_BASELINE_RESTORED",
            "NETWORK_BASELINE_RESTORED",
            "VOLUME_BASELINE_RESTORED",
        )
    ):
        failures.append("S04 real-ORM evidence or exact resource cleanup is incomplete")
    if s04_verification.get("CONTROLLED_ORM_DOUBLES_USED") is not False:
        failures.append("S04 authorization evidence must not use controlled ORM doubles")
    if s04_verification.get("NEW_OR_WORSENED_FAILURES") != []:
        failures.append("S04 must not introduce or worsen quality-gate failures")
    s05_verification = contract.get("S05_VERIFICATION") or {}
    if s05_verification.get("RESULT") != "PASS":
        failures.append("S05 real-ORM verification result must be PASS")
    if not all(
        s05_verification.get(field) is True
        for field in (
            "REAL_ODOO_REGISTRY_USED",
            "REAL_ORM_USED",
            "FIRST_RUN_TEMP_DATABASE_REMOVED",
            "FIRST_RUN_TEMP_RESOURCES_REMOVED",
            "FINAL_TEMP_DATABASE_REMOVED",
            "FINAL_TEMP_RESOURCES_REMOVED",
            "DATABASE_BASELINE_RESTORED",
            "CONTAINER_BASELINE_RESTORED",
            "NETWORK_BASELINE_RESTORED",
            "VOLUME_BASELINE_RESTORED",
        )
    ):
        failures.append("S05 real-ORM evidence or exact resource cleanup is incomplete")
    if s05_verification.get("CONTROLLED_ORM_DOUBLES_USED") is not False:
        failures.append("S05 authorization evidence must not use controlled ORM doubles")
    if s05_verification.get("NEW_OR_WORSENED_FAILURES") != []:
        failures.append("S05 must not introduce or worsen quality-gate failures")
    s06_verification = contract.get("S06_VERIFICATION") or {}
    if s06_verification.get("RESULT") != "PASS":
        failures.append("S06 real-ORM verification result must be PASS")
    if s06_verification.get("PRODUCT_FILES_CHANGED") != []:
        failures.append("S06 must remain a verification-only slice")
    if not all(
        s06_verification.get(field) is True
        for field in (
            "REAL_ODOO_REGISTRY_USED",
            "REAL_ORM_USED",
            "FIRST_RUN_TEMP_DATABASE_REMOVED",
            "FIRST_RUN_TEMP_RESOURCES_REMOVED",
            "FINAL_TEMP_DATABASE_REMOVED",
            "FINAL_TEMP_RESOURCES_REMOVED",
            "DATABASE_BASELINE_RESTORED",
            "CONTAINER_BASELINE_RESTORED",
            "NETWORK_BASELINE_RESTORED",
            "VOLUME_BASELINE_RESTORED",
        )
    ):
        failures.append("S06 real-ORM evidence or exact resource cleanup is incomplete")
    if s06_verification.get("CONTROLLED_ORM_DOUBLES_USED") is not False:
        failures.append("S06 authorization evidence must not use controlled ORM doubles")
    if s06_verification.get("NEW_OR_WORSENED_FAILURES") != []:
        failures.append("S06 must not introduce or worsen quality-gate failures")
    s07_verification = contract.get("S07_VERIFICATION") or {}
    if s07_verification.get("RESULT") != "PASS":
        failures.append("S07 real-ORM verification result must be PASS")
    if not all(
        s07_verification.get(field) is True
        for field in (
            "REAL_ODOO_REGISTRY_USED",
            "REAL_ORM_USED",
            "FINAL_TEMP_DATABASE_REMOVED",
            "FINAL_TEMP_RESOURCES_REMOVED",
            "DATABASE_BASELINE_RESTORED",
            "CONTAINER_BASELINE_RESTORED",
            "NETWORK_BASELINE_RESTORED",
            "VOLUME_BASELINE_RESTORED",
        )
    ):
        failures.append("S07 real-ORM evidence or exact resource cleanup is incomplete")
    if s07_verification.get("CONTROLLED_ORM_DOUBLES_USED") is not False:
        failures.append("S07 authorization evidence must not use controlled ORM doubles")
    if s07_verification.get("NEW_OR_WORSENED_FAILURES") != []:
        failures.append("S07 must not introduce or worsen quality-gate failures")

    if failures:
        print("[um_p1_ownership_visibility_contract_guard] FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("[um_p1_ownership_visibility_contract_guard] PASS")
    print("P1_ENTRY_COUNT=6")
    print("CONTRACT_CONFLICTS=0")
    print(f"PRODUCT_GAPS={len(contract.get('PRODUCT_GAPS') or [])}")
    print("NEXT_SLICE=UM-P1-DOCUMENT-ORDER-COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
