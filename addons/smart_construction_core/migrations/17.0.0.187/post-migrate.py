# -*- coding: utf-8 -*-
"""Retire superseded standard process scenarios, then add current scenarios."""
from __future__ import annotations

import json

from odoo import SUPERUSER_ID, api


LEGACY_STANDARD_BINDINGS = {
    "governance.organization": {
        "smart_construction_core.menu_sc_organization_department",
        "smart_construction_core.menu_sc_product_job_management_v1",
    },
    "project.management": {
        "smart_construction_core.menu_sc_construction_diary",
        "smart_construction_core.menu_sc_construction_progress",
        "smart_construction_core.menu_sc_customer_partner",
        "smart_construction_core.menu_sc_plan",
        "smart_construction_core.menu_sc_plan_report",
        "smart_construction_core.menu_sc_product_project_lifecycle_v1",
        "smart_construction_core.menu_sc_product_site_variation_v1",
        "smart_construction_core.menu_sc_product_tender_document_v1",
        "smart_construction_core.menu_sc_product_tender_information_v1",
        "smart_construction_core.menu_sc_project_documents",
        "smart_construction_core.menu_sc_project_initiation",
        "smart_construction_core.menu_sc_project_project",
        "smart_construction_core.menu_sc_project_quick_create",
        "smart_construction_core.menu_sc_project_tender",
        "smart_construction_core.menu_sc_tender_guarantee",
        "smart_construction_core.menu_sc_tender_won",
    },
    "contract.performance": {
        "smart_construction_core.menu_sc_p1_contract_change",
        "smart_construction_core.menu_sc_p1_daily_contract",
        "smart_construction_core.menu_sc_p1_expense_contract",
        "smart_construction_core.menu_sc_p1_expense_settlement",
        "smart_construction_core.menu_sc_p1_income_contract",
        "smart_construction_core.menu_sc_p1_income_settlement",
        "smart_construction_core.menu_sc_product_general_contract_settlement_v1",
        "smart_construction_core.menu_sc_settlement_order",
        "smart_construction_core.menu_sc_tender_opening",
        "smart_construction_core.menu_sc_tender_registration_fee",
    },
    "cost.budget": {
        "smart_construction_core.menu_sc_p1_cost_ledger",
        "smart_construction_core.menu_sc_p1_cost_plan",
        "smart_construction_core.menu_sc_p1_project_budget",
    },
    "procurement.supplier": {
        "smart_construction_core.menu_sc_product_partner_blacklist_v1",
        "smart_construction_core.menu_sc_supplier_partner",
    },
    "material.management": {
        "smart_construction_core.menu_project_material_plan",
        "smart_construction_core.menu_sc_material_acceptance",
        "smart_construction_core.menu_sc_material_inbound",
        "smart_construction_core.menu_sc_material_loss",
        "smart_construction_core.menu_sc_material_outbound",
        "smart_construction_core.menu_sc_material_purchase_request",
        "smart_construction_core.menu_sc_material_rental_order",
        "smart_construction_core.menu_sc_material_rental_plan",
        "smart_construction_core.menu_sc_material_rental_settlement",
        "smart_construction_core.menu_sc_material_rfq",
        "smart_construction_core.menu_sc_material_settlement",
        "smart_construction_core.menu_sc_material_transfer",
        "smart_construction_core.menu_sc_product_material_return_v1",
    },
    "subcontract.management": {
        "smart_construction_core.menu_sc_product_subcontract_cost_v1",
        "smart_construction_core.menu_sc_product_subcontract_variation_v1",
        "smart_construction_core.menu_sc_subcontract_plan",
        "smart_construction_core.menu_sc_subcontract_request",
        "smart_construction_core.menu_sc_subcontract_settlement",
    },
    "labor.management": {
        "smart_construction_core.menu_sc_labor_plan",
        "smart_construction_core.menu_sc_labor_request",
        "smart_construction_core.menu_sc_labor_settlement",
        "smart_construction_core.menu_sc_product_labor_cost_v1",
        "smart_construction_core.menu_sc_product_labor_deduction_v1",
        "smart_construction_core.menu_sc_product_labor_realname_v1",
    },
    "quality.management": {
        "smart_construction_core.menu_sc_product_quality_acceptance_v1",
        "smart_construction_core.menu_sc_quality_issue",
        "smart_construction_core.menu_sc_quality_recheck",
        "smart_construction_core.menu_sc_quality_rectification",
        "smart_construction_core.menu_sc_quality_site_photo_v2",
        "smart_construction_core.menu_sc_quality_standard_v2",
    },
    "safety.management": {
        "smart_construction_core.menu_sc_safety_disclosure_v2",
        "smart_construction_core.menu_sc_safety_hazard_source_v2",
        "smart_construction_core.menu_sc_safety_issue",
        "smart_construction_core.menu_sc_safety_patrol_v2",
        "smart_construction_core.menu_sc_safety_plan_v2",
        "smart_construction_core.menu_sc_safety_recheck",
        "smart_construction_core.menu_sc_safety_rectification",
        "smart_construction_core.menu_sc_safety_risk_library_v2",
    },
    "payment.capital": {
        "smart_construction_core.menu_sc_advance_fund",
        "smart_construction_core.menu_sc_company_finance_expense",
        "smart_construction_core.menu_sc_deduction_bill",
        "smart_construction_core.menu_sc_engineering_progress_income",
        "smart_construction_core.menu_sc_payment_execution",
        "smart_construction_core.menu_sc_product_company_project_refund_v1",
        "smart_construction_core.menu_sc_product_current_account_v1",
        "smart_construction_core.menu_sc_product_team_loan_deduction_v1",
        "smart_construction_core.menu_sc_receipt_income",
        "smart_construction_core.menu_sc_reimbursement_request",
        "smart_construction_core.menu_sc_user_income",
        "smart_construction_core.menu_sc_user_payment_apply",
    },
    "receipt.payment.ledger": {
        "smart_construction_core.menu_payment_ledger",
        "smart_construction_core.menu_sc_funding_plan_summary",
        "smart_construction_core.menu_sc_treasury_ledger",
    },
    "tax.management": {
        "smart_construction_core.menu_sc_invoice_application_user",
        "smart_construction_core.menu_sc_invoice_input",
        "smart_construction_core.menu_sc_invoice_prepaid_tax_user",
        "smart_construction_core.menu_sc_invoice_registration_user",
        "smart_construction_core.menu_sc_output_invoice_change_registration",
        "smart_construction_core.menu_sc_product_project_tax_deduction_v1",
        "smart_construction_core.menu_sc_product_tax_filing_v1",
        "smart_construction_core.menu_sc_tax_certificate_registration_user",
        "smart_construction_core.menu_sc_tax_deduction_registration_user",
    },
    "accounting.management": {
        "account.menu_action_account_form",
        "account.menu_action_account_moves_all",
        "account.menu_action_move_journal_line_form",
        "smart_construction_core.menu_sc_account_journal_foundation",
        "smart_construction_core.menu_sc_analytic_account_foundation",
        "smart_construction_core.menu_sc_analytic_distribution_foundation",
    },
    "analytics.decision": {
        "smart_construction_core.menu_sc_comprehensive_cost_statistics_report",
        "smart_construction_core.menu_sc_fund_daily_summary",
        "smart_construction_core.menu_sc_p1_profit_analysis",
        "smart_construction_core.menu_sc_product_labor_subcontract_report_v1",
        "smart_construction_core.menu_sc_product_tax_report_v1",
        "smart_construction_core.menu_sc_project_operation_statistics_report",
    },
    "equipment.management": {
        "smart_construction_core.menu_sc_equipment_plan",
        "smart_construction_core.menu_sc_equipment_request",
        "smart_construction_core.menu_sc_equipment_settlement",
        "smart_construction_core.menu_sc_product_equipment_shift_v1",
    },
    "administration.office": {
        "smart_construction_core.menu_sc_certificate_registration",
        "smart_construction_core.menu_sc_payroll_management",
        "smart_construction_core.menu_sc_product_office_asset_v1",
        "smart_construction_core.menu_sc_product_policy_document_v1",
        "smart_construction_core.menu_sc_product_project_payroll_v1",
        "smart_construction_core.menu_sc_product_project_salary_payment_v1",
        "smart_construction_core.menu_sc_product_social_fund_v1",
    },
}


def migrate(cr, version):
    if not version:
        return {"skipped": "fresh_install"}
    env = api.Environment(cr, SUPERUSER_ID, {})
    scenario_model = env["sc.product.scenario"].sudo()
    legacy = scenario_model.with_context(active_test=False).search([
        ("code", "in", tuple(LEGACY_STANDARD_BINDINGS)),
    ])
    unexpected = {}
    for scenario in legacy:
        current_bindings = set()
        for entry in scenario.entry_ids:
            menu = entry.menu_id
            xmlid = menu.get_external_id().get(menu.id) or "menu:%s" % menu.id
            current_bindings.add(xmlid)
        extra = current_bindings - LEGACY_STANDARD_BINDINGS[scenario.code]
        if extra:
            unexpected[scenario.code] = sorted(extra)
    if unexpected:
        raise RuntimeError(
            "LEGACY_SCENARIO_CUSTOM_BINDING_DETECTED:"
            + json.dumps(unexpected, ensure_ascii=False, sort_keys=True)
        )
    retired_codes = sorted(legacy.mapped("code"))
    legacy.mapped("entry_ids").unlink()
    legacy.unlink()
    result = scenario_model.import_scenario_product_surface(force=True)
    scenario_model.initialize_navigation_entry_exemptions()
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import (
        load_surface,
    )
    current_codes = {
        str(scenario.get("key") or "").strip()
        for scenario in load_surface().get("scenarios") or []
        if str(scenario.get("key") or "").strip()
    }
    current_scenarios = scenario_model.with_context(active_test=False).search([
        ("code", "in", tuple(current_codes)),
    ])
    missing = current_codes - set(current_scenarios.mapped("code"))
    if missing:
        raise RuntimeError(
            "LEGACY_SCENARIO_MIGRATION_INCOMPLETE:"
            + json.dumps(sorted(missing), ensure_ascii=False)
        )
    current_entries = current_scenarios.mapped("entry_ids")
    unique_menu_count = len(set(current_entries.mapped("menu_id").ids))
    if unique_menu_count != 132:
        raise RuntimeError(
            "LEGACY_SCENARIO_BINDING_COUNT_INVALID:%s" % unique_menu_count
        )
    env.registry.clear_cache()
    return {
        "retired_legacy_scenarios": retired_codes,
        "unique_standard_menu_count": unique_menu_count,
        **result,
    }
