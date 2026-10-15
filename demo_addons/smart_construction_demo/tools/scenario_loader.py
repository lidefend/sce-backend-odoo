# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from odoo.tools import convert
from odoo.tools.misc import file_path

from ..hooks import apply_demo_user_passwords, guard_demo_scope, guard_demo_data_space


BASE_SEED_FILES: List[str] = [
    "data/demo/sc_demo_users.xml",
    "data/base/00_dictionary.xml",
    "data/base/dictionary_demo.xml",
    "data/base/cost_demo.xml",
    "data/base/10_partners.xml",
    "data/base/12_departments.xml",
    "data/base/20_projects.xml",
    "data/base/25_project_tasks.xml",
]


# Scenario registry: scenario_name -> ordered xml file list (relative under module root)
SCENARIOS: Dict[str, List[str]] = {
    # S00 is "default baseline" (usually already loaded by manifest, but loader can load too)
    "s00_min_path": [
        "data/scenario/s00_min_path/10_project_boq.xml",
        "data/scenario/s00_min_path/20_project_links.xml",
        "data/scenario/s00_min_path/30_project_revenue.xml",
    ],
    # S10 contract payment path (optional scenario)
    "s10_contract_payment": [
        "data/scenario/s10_contract_payment/10_contracts.xml",
        "data/scenario/s10_contract_payment/20_payment_requests.xml",
        "data/scenario/s10_contract_payment/30_invoices.xml",
    ],
    "s20_settlement_clearing": {
        "sequence": 20,
        "files": [
            "data/scenario/s20_settlement_clearing/10_payments.xml",
            "data/scenario/s20_settlement_clearing/30_settlement.xml",
            "data/scenario/s20_settlement_clearing/20_clearing.xml",
        ],
    },
    "s30_settlement_workflow": {
        "sequence": 30,
        "files": [
            "data/scenario/s30_settlement_workflow/10_settlement_seed.xml",
            "data/scenario/s30_settlement_workflow/20_settlement_actions.xml",
            "data/scenario/s30_settlement_workflow/30_assert_state.xml",
        ],
    },
    "s40_failure_paths": {
        "sequence": 40,
        "files": [
            "data/scenario/s40_failure_paths/10_invalid_settlement.xml",
            "data/scenario/s40_failure_paths/20_invalid_amounts.xml",
            "data/scenario/s40_failure_paths/30_invalid_links.xml",
        ],
    },
    "s50_repairable_paths": {
        "sequence": 50,
        "files": [
            "data/scenario/s50_repairable_paths/10_bad_seed.xml",
            "data/scenario/s50_repairable_paths/20_fix_patch.xml",
            "data/scenario/s50_repairable_paths/30_assert_state.xml",
        ],
    },
    "s60_project_cockpit": {
        "sequence": 60,
        "files": [
            "data/scenario/s60_project_cockpit/10_cockpit_business_facts.xml",
        ],
    },
    "s65_cost_budget_funding_surface": {
        "sequence": 65,
        "files": [
            "data/scenario/s65_cost_budget_funding_surface/10_cost_budget_funding_records.xml",
        ],
    },
    "s66_ledger_entity_surface": {
        "sequence": 66,
        "files": [
            "data/scenario/s66_ledger_entity_surface/10_ledger_entity_records.xml",
        ],
    },
    "s67_scene_pack_surface": {
        "sequence": 67,
        "files": [
            "data/scenario/s67_scene_pack_surface/10_scene_pack_records.xml",
        ],
    },
    "s68_cockpit_workbench_surface": {
        "sequence": 68,
        "files": [
            "data/scenario/s68_cockpit_workbench_surface/10_cockpit_workbench_records.xml",
        ],
    },
    "s69_payment_ledger_surface": {
        "sequence": 69,
        "files": [
            "data/scenario/s69_payment_ledger_surface/10_payment_ledger_records.xml",
        ],
    },
    "s70_daily_business_surface": {
        "sequence": 70,
        "files": [
            "data/scenario/s70_daily_business_surface/10_daily_business_records.xml",
        ],
    },
    "s71_governance_audit_surface": {
        "sequence": 71,
        "files": [
            "data/scenario/s71_governance_audit_surface/10_governance_audit_records.xml",
        ],
    },
    "s72_project_governance_surface": {
        "sequence": 72,
        "files": [
            "data/scenario/s72_project_governance_surface/10_project_governance_records.xml",
        ],
    },
    "s73_risk_settlement_surface": {
        "sequence": 73,
        "files": [
            "data/scenario/s73_risk_settlement_surface/10_risk_settlement_records.xml",
        ],
    },
    "s74_partner_supplier_surface": {
        "sequence": 74,
        "files": [
            "data/scenario/s74_partner_supplier_surface/10_partner_supplier_records.xml",
        ],
    },
    "s75_summary_projection_surface": {
        "sequence": 75,
        "files": [],
    },
    "s76_workflow_compat_surface": {
        "sequence": 76,
        "files": [
            "data/scenario/s76_workflow_compat_surface/10_workflow_compat_records.xml",
        ],
    },
    "s77_data_dictionary_surface": {
        "sequence": 77,
        "files": [
            "data/scenario/s77_data_dictionary_surface/10_data_dictionary_records.xml",
        ],
    },
    "s78_project_document_wbs_surface": {
        "sequence": 78,
        "files": [
            "data/scenario/s78_project_document_wbs_surface/10_project_document_wbs_records.xml",
        ],
    },
    "s79_execution_structure_surface": {
        "sequence": 79,
        "files": [
            "data/scenario/s79_execution_structure_surface/10_execution_structure_records.xml",
        ],
    },
    "s80_execution_management_surface": {
        "sequence": 80,
        "files": [
            "data/scenario/s80_execution_management_surface/10_execution_management_records.xml",
        ],
    },
    "s85_admin_finance_surface": {
        "sequence": 85,
        "files": [
            "data/scenario/s85_admin_finance_surface/10_admin_finance_records.xml",
        ],
    },
    "s86_tender_rental_finance_surface": {
        "sequence": 86,
        "files": [
            "data/scenario/s86_tender_rental_finance_surface/10_tender_rental_finance_records.xml",
        ],
    },
    "s87_resource_contract_surface": {
        "sequence": 87,
        "files": [
            "data/scenario/s87_resource_contract_surface/10_resource_contract_records.xml",
        ],
    },
    "s88_output_invoice_surface": {
        "sequence": 88,
        "files": [
            "data/scenario/s88_output_invoice_surface/10_output_invoice_records.xml",
        ],
    },
    "s89_quality_safety_surface": {
        "sequence": 89,
        "files": [
            "data/scenario/s89_quality_safety_surface/10_quality_safety_records.xml",
        ],
    },
    "s90_users_roles": {
        "sequence": 90,
        "files": [
            "data/scenario/s90_users_roles/10_users.xml",
        ],
    },
}

SCENARIO_ALIASES = {
    "project_normal": "s60_project_cockpit",
    "project_over_budget": "s60_project_cockpit",
    "project_payment_delay": "s60_project_cockpit",
}

SCENARIO_PROFILES: Dict[str, Dict[str, object]] = {
    "project_normal": {
        "label": "正常项目",
        "release_ready": True,
        "showcase_project": "展厅-智慧园区运营中心",
        "expected_risk": "EXECUTION_COST_MISSING",
    },
    "project_over_budget": {
        "label": "超预算项目",
        "release_ready": True,
        "showcase_project": "展厅-产线升级改造工程",
        "expected_risk": "PAYMENT_EXCEEDS_COST",
    },
    "project_payment_delay": {
        "label": "付款风险项目",
        "release_ready": True,
        "showcase_project": "展厅-装配式住宅试点",
        "expected_risk": "PAYMENT_MISSING",
    },
}


RELEASE_SCENARIOS: List[str] = [
    "s00_min_path",
    "s10_contract_payment",
    "s20_settlement_clearing",
    "s30_settlement_workflow",
    "s60_project_cockpit",
    "s65_cost_budget_funding_surface",
    "s66_ledger_entity_surface",
    "s68_cockpit_workbench_surface",
    "s69_payment_ledger_surface",
    "s70_daily_business_surface",
    "s72_project_governance_surface",
    "s73_risk_settlement_surface",
    "s74_partner_supplier_surface",
    "s75_summary_projection_surface",
    "s77_data_dictionary_surface",
    "s78_project_document_wbs_surface",
    "s79_execution_structure_surface",
    "s80_execution_management_surface",
    "s85_admin_finance_surface",
    "s86_tender_rental_finance_surface",
    "s87_resource_contract_surface",
    "s88_output_invoice_surface",
    "s89_quality_safety_surface",
    "s90_users_roles",
]


def _normalize_registry() -> Dict[str, Dict[str, List[str] | int]]:
    """
    Normalize SCENARIOS to:
      {name: {"sequence": int, "files": List[str]}}
    Backward compatible with legacy list-only entries.
    """
    normalized: Dict[str, Dict[str, List[str] | int]] = {}
    for name, spec in SCENARIOS.items():
        if isinstance(spec, dict):
            files = spec.get("files") or []
            seq = int(spec.get("sequence", 0))
        else:
            files = spec
            seq = 0
        normalized[name] = {
            "sequence": seq,
            "files": files,
        }
    return normalized


def _filter_files(files: List[str], step: str | None) -> List[str]:
    if not step or step == "all":
        return files
    step = step.strip().lower()
    if step == "bad":
        prefixes = ("10_",)
    elif step == "fix":
        prefixes = ("20_", "30_")
    else:
        raise ValueError(f"unknown step '{step}'. use bad|fix|all")

    filtered = [
        relpath for relpath in files if Path(relpath).name.startswith(prefixes)
    ]
    if not filtered:
        raise ValueError(f"no files matched step '{step}'")
    return filtered


# ---------------------------------------------------------------------------
# Demo lifecycle alignment (DEMO-SCENARIO-PRODUCT-DRIFT-01)
#
# The product reserves terminal document states for official办理动作
# (create() only accepts draft). The release seed therefore declares each
# record in its legal initial state and this table names the governed
# action chain that carries it to the state the scenario is meant to show.
# The driver below never writes a status field directly and never opens a
# guard bypass: it calls the model's own public actions (approval-bearing
# transitions are performed by the configured reviewer role).
# ---------------------------------------------------------------------------

# 少数记录在通用办理链到达 target 后，还会由场景专用 finalizer 继续推进
# （例如 s86 租赁结算由 _ensure_s86_rental_settlement_payment 送到 paid）。
# 重载时这些记录已经越过 target，必须按“已完成”处理，否则会再次调用只接受
# 草稿的提交动作并被产品守卫拒绝。
_DEMO_LIFECYCLE_BEYOND_TARGET = {
    ("sc.material.rental.settlement", "confirmed"): frozenset({"paid"}),
}

# (scenario, xmlid-without-module) -> intended terminal state.
_DEMO_LIFECYCLE_TARGETS = {
    "s73_risk_settlement_surface": {
        "sc_demo_project_settlement_073_risk": "confirmed",
        "sc_demo_project_risk_action_073_cost": "claimed",
        "sc_demo_project_risk_action_073_schedule": "escalated",
    },
    "s68_cockpit_workbench_surface": {
        "sc_demo_dashboard_fact_068_fund": "in_progress",
        "sc_demo_dashboard_fact_068_cost": "done",
        "sc_demo_workbench_item_068_todo": "in_progress",
        "sc_demo_workbench_item_068_recent": "done",
    },
    "s60_project_cockpit": {
        "sc_demo_tender_060_001": "submitted",
    },
    "s66_ledger_entity_surface": {
        "sc_demo_general_contract_066_income": "signed",
        "sc_demo_general_contract_066_expense": "signed",
    },
    "s65_cost_budget_funding_surface": {
        "sc_demo_material_outbound_065_rebar": "issued",
    },
    "s70_daily_business_surface": {
        "sc_demo_receipt_income_070_progress": "received",
        "sc_demo_payment_execution_070_material": "paid",
        "sc_demo_treasury_reconciliation_070_daily": "confirmed",
        "sc_demo_invoice_registration_070_input": "registered",
        "sc_demo_tax_deduction_070_input": "deducted",
        "sc_demo_construction_diary_070_daily": "confirmed",
    },
    "s78_project_document_wbs_surface": {
        "sc_demo_document_078_safety_review": "approved",
        "sc_demo_document_078_quality_archive": "done",
    },
    "s80_execution_management_surface": {
        "sc_demo_quality_issue_080_rebar": "closed",
        "sc_demo_hazard_source_080_lifting": "controlled",
        "sc_demo_safety_issue_080_guardrail": "closed",
        "sc_demo_safety_patrol_080_weekly": "done",
        "sc_demo_material_purchase_request_080_steel": "approved",
        "sc_demo_material_rfq_080_steel": "selected",
        "sc_demo_material_acceptance_080_steel": "accepted",
        "sc_demo_material_inbound_080_steel": "received",
        "sc_demo_material_outbound_080_steel": "issued",
        "sc_demo_material_settlement_080_steel": "confirmed",
        "sc_demo_plan_080_master": "in_progress",
        "sc_demo_plan_line_080_rebar": "in_progress",
        "sc_demo_plan_report_080_weekly": "accepted",
        "sc_demo_safety_plan_080_lifting": "approved",
        "sc_demo_safety_disclosure_080_lifting": "approved",
        "sc_demo_labor_plan_080_rebar": "approved",
        "sc_demo_labor_request_080_rebar": "approved",
        "sc_demo_attendance_checkin_080_rebar": "confirmed",
        "sc_demo_equipment_plan_080_crane": "approved",
        "sc_demo_equipment_request_080_crane": "approved",
        "sc_demo_equipment_usage_080_crane": "confirmed",
    },
    "s85_admin_finance_surface": {
        "sc_demo_document_admin_085_certificate": "done",
        "sc_demo_document_admin_085_borrow": "done",
        "sc_demo_office_admin_085_leave": "done",
        "sc_demo_office_admin_085_seal": "done",
        "sc_demo_financing_loan_085_bank": "confirmed",
        "sc_demo_hr_payroll_085_salary": "done",
        "sc_demo_hr_payroll_085_bonus": "done",
        "sc_demo_subcontract_plan_085_fitout": "approved",
        "sc_demo_subcontract_request_085_fitout": "approved",
        "sc_demo_subcontract_register_085_fitout": "active",
        "sc_demo_subcontract_settlement_085_fitout": "confirmed",
    },
    "s86_tender_rental_finance_surface": {
        "sc_demo_tender_bid_086_complex": "won",
        "sc_demo_fund_operation_086_transfer": "done",
        "sc_demo_fund_operation_086_daily": "confirmed",
        "sc_demo_tender_doc_purchase_086": "approved",
        "sc_demo_expense_claim_086_deposit_pay": "done",
        "sc_demo_expense_claim_086_deposit_refund": "done",
        "sc_demo_material_rental_plan_086_scaffold": "approved",
        "sc_demo_material_rental_order_086_scaffold": "settled",
        # 租赁结算的终态 paid 由 _ensure_s86_rental_settlement_payment 在付款
        # 台账入账后推进；通用办理链只负责把结算送达到付款依据态 confirmed。
        "sc_demo_material_rental_settlement_086_scaffold": "confirmed",
        "sc_demo_settlement_adjustment_086_deduction": "confirmed",
    },
    "s87_resource_contract_surface": {
        "sc_demo_general_contract_087_service": "signed",
        "sc_demo_labor_usage_087_masonry": "confirmed",
        "sc_demo_labor_settlement_087_masonry": "confirmed",
        "sc_demo_equipment_settlement_087_pump": "confirmed",
        "sc_demo_contract_event_087_design_change": "approved",
        "sc_demo_contract_event_087_output_value": "done",
    },
    "s88_output_invoice_surface": {
        "sc_demo_invoice_registration_088_output": "registered",
    },
    "s89_quality_safety_surface": {
        "sc_demo_quality_issue_089_rebar": "closed",
        "sc_demo_hazard_source_089_high_support": "controlled",
        "sc_demo_safety_issue_089_high_support": "closed",
        "sc_demo_safety_patrol_task_089_high_support": "done",
        "sc_demo_safety_plan_089_dangerous": "approved",
        "sc_demo_safety_disclosure_089_dangerous": "approved",
    },
}

# (model, intended terminal state) -> ordered public action methods.
# When a model carries no approval rule the submission action completes the
# approval inline (one-step handling), so the chain is just the submit.
_DEMO_LIFECYCLE_CHAINS = {
    ("sc.receipt.income", "confirmed"): ("action_confirm",),
    ("sc.receipt.income", "received"): ("action_confirm", "action_received"),
    ("sc.payment.execution", "confirmed"): ("action_confirm",),
    ("sc.payment.execution", "paid"): ("action_confirm", "action_paid"),
    ("sc.tax.deduction.registration", "deducted"): ("action_confirm", "action_deduct"),
    ("sc.treasury.reconciliation", "confirmed"): ("action_confirm",),
    ("sc.invoice.registration", "registered"): ("action_confirm", "action_register"),
    ("sc.construction.diary", "confirmed"): ("action_confirm",),
    ("sc.project.document", "approved"): ("action_submit",),
    ("sc.project.document", "done"): ("action_submit", "action_archive"),
    ("sc.material.purchase.request", "approved"): ("action_submit",),
    ("sc.material.rfq", "selected"): ("action_submit", "action_select"),
    ("sc.material.acceptance", "accepted"): ("action_submit", "action_accept"),
    ("sc.material.inbound", "received"): ("action_submit", "action_receive"),
    ("sc.material.outbound", "issued"): ("action_issue",),
    ("sc.material.settlement", "confirmed"): ("action_confirm",),
    ("sc.plan", "in_progress"): ("action_confirm", "action_start"),
    ("sc.plan.report", "accepted"): ("action_submit",),
    ("sc.safety.plan", "approved"): ("action_submit",),
    ("sc.safety.disclosure", "approved"): ("action_submit",),
    ("sc.labor.plan", "approved"): ("action_submit",),
    ("sc.labor.request", "approved"): ("action_submit",),
    ("sc.attendance.checkin", "confirmed"): ("action_submit", "action_confirm"),
    ("sc.equipment.plan", "approved"): ("action_submit",),
    ("sc.equipment.request", "approved"): ("action_submit",),
    ("sc.equipment.usage", "confirmed"): ("action_confirm",),
    ("sc.financing.loan", "confirmed"): ("action_confirm",),
    ("sc.hr.payroll.document", "done"): ("action_submit", "action_done"),
    ("sc.subcontract.plan", "approved"): ("action_submit",),
    ("sc.subcontract.request", "approved"): ("action_submit",),
    ("sc.subcontract.register", "active"): ("action_register",),
    ("sc.subcontract.settlement", "confirmed"): ("action_confirm",),
    ("tender.doc.purchase", "approved"): ("action_submit",),
    ("sc.expense.claim", "done"): ("action_submit", "action_approve", "action_done"),
    ("sc.material.rental.plan", "approved"): ("action_submit",),
    ("sc.material.rental.order", "settled"): ("action_submit", "action_activate", "action_return", "action_settle"),
    ("sc.material.rental.settlement", "confirmed"): ("action_submit", "action_confirm"),
    ("sc.settlement.adjustment", "confirmed"): ("action_confirm",),
    ("sc.labor.usage", "confirmed"): ("action_submit", "action_confirm"),
    ("sc.labor.settlement", "confirmed"): ("action_submit", "action_confirm"),
    ("sc.equipment.settlement", "confirmed"): ("action_submit", "action_confirm"),
    ("sc.contract.event", "approved"): ("action_submit",),
    ("sc.contract.event", "done"): ("action_submit", "action_done"),
    ('sc.general.contract', 'signed'): ('action_confirm', 'action_signed'),
    ('sc.quality.issue', 'submitted'): ('action_submit',),
    ('sc.hazard.source', 'controlled'): ('action_report', 'action_control'),
    ('sc.safety.issue', 'submitted'): ('action_submit',),
    ('sc.safety.patrol.task', 'done'): ('action_plan', 'action_done'),
    ('sc.document.admin.document', 'done'): ('action_submit', 'action_done'),
    ('sc.office.admin.document', 'done'): ('action_submit', 'action_done'),
    ('sc.fund.account.operation', 'done'): ('action_confirm', 'action_done'),
    ('sc.fund.account.operation', 'confirmed'): ('action_confirm',),
    ('tender.bid', 'submitted'): ('action_to_submitted',),
    ('tender.bid', 'won'): ('action_to_submitted', 'action_mark_won'),
    ('project.settlement', 'confirmed'): ('action_confirm',),
    ('project.risk.action', 'claimed'): ('action_claim',),
    ('project.risk.action', 'escalated'): ('action_escalate',),
    ('sc.dashboard.cockpit.fact', 'in_progress'): ('action_submit',),
    ('sc.dashboard.cockpit.fact', 'done'): ('action_submit', 'action_done'),
    ('sc.workbench.item', 'in_progress'): ('action_submit',),
    ('sc.workbench.item', 'done'): ('action_submit', 'action_done'),
}

# These terminal states are produced by role-bound XML orchestration, not by
# a generic state action. Missing closure must fail rather than fabricate it.
_DEMO_LIFECYCLE_XML_ACTIONS = {
    "sc_demo_quality_issue_080_rebar": "sc_demo_close_issue",
    "sc_demo_safety_issue_080_guardrail": "sc_demo_close_issue",
    "sc_demo_quality_issue_089_rebar": "sc_demo_close_issue",
    "sc_demo_safety_issue_089_high_support": "sc_demo_close_issue",
}

# Records whose execution facts belong to a governed write API rather than an
# action (sc.plan.line exposes the execution fields through write() while the
# parent plan is in progress). Values mirror the scenario's intended snapshot.
_DEMO_LIFECYCLE_FACT_WRITES = {
    "sc_demo_plan_line_080_rebar": {
        "state": "in_progress",
        "actual_start": "2025-04-08",
        "progress_rate": 65.0,
    },
}

# Record-specific operational seats: project salary and company bonus have
# different native permission requirements. Pending approval seats are resolved
# separately from the actual review instance, never from these overrides.
_DEMO_LIFECYCLE_REVIEWER = {
    ("sc_demo_hr_payroll_085_salary", "action_submit"): "smart_construction_demo.user_sc_project_user",
    ("sc_demo_hr_payroll_085_salary", "action_done"): "smart_construction_demo.user_sc_project_manager_cap",
    ("sc_demo_hr_payroll_085_bonus", "action_submit"): "smart_construction_demo.user_demo_role_project_a_member",
    ("sc_demo_hr_payroll_085_bonus", "action_done"): "smart_construction_demo.user_sc_business_config_demo",
}

# Approval tier seat map: reviewer group -> the demo account that owns that
# seat. The product ships its user-visible approval templates with several
# tiers (付款/收款申请: 财务经办确认 -> 项目负责人审核 -> 财务审核 -> 管理层终审),
# and each tier may only be decided by a member of its own group. Declaring the
# seat once means the generic driver below can walk any chain for any model, so
# a scenario that adds an approval-bearing document needs no tier-specific code.
_DEMO_APPROVAL_ACTORS = {
    "smart_construction_core.group_sc_role_operation_user": "smart_construction_demo.user_sc_operation_demo",
    "smart_construction_core.group_sc_cap_cost_manager": "smart_construction_demo.user_sc_cost_manager_cap",
    "smart_construction_core.group_sc_role_contract_admin": "smart_construction_demo.user_sc_contract_01",
    "smart_construction_core.group_sc_cap_contract_manager": "smart_construction_demo.user_sc_contract_manager_cap",
    "smart_construction_core.group_sc_role_finance_user":
        "smart_construction_demo.user_sc_fin_01",
    "smart_construction_core.group_sc_cap_project_manager":
        "smart_construction_demo.user_demo_project_manager",
    "smart_construction_core.group_sc_cap_finance_manager":
        "smart_construction_demo.user_sc_fin_mgr_01",
    "smart_construction_core.group_sc_role_executive":
        "smart_construction_demo.user_demo_role_executive",
    "smart_construction_core.group_sc_cap_settlement_manager": "smart_construction_demo.user_sc_settlement_manager_cap",
    "smart_construction_core.group_sc_role_settlement_user": "smart_construction_demo.user_sc_settlement_user_cap",
    "smart_construction_core.group_sc_cap_material_manager": "smart_construction_demo.user_sc_material_mgr_01",
    "smart_construction_core.group_sc_cap_purchase_manager": "smart_construction_demo.user_sc_purchase_manager_cap",
    "smart_construction_core.group_sc_role_project_user": "smart_construction_demo.user_sc_project_user",
    "smart_construction_core.group_sc_cap_project_user": "smart_construction_demo.user_sc_project_user",
    "smart_construction_core.group_sc_cap_business_config_admin": "smart_construction_demo.user_sc_business_config_demo",
}

# The project-side operator who raises the payment/receipt request. It holds the
# 业务发起 capability, so the request is submitted by the business side and the
# first approval tier (财务经办确认) stays a different seat, as in real use.
_DEMO_DOCUMENT_SUBMITTER = "smart_construction_demo.user_demo_role_project_a_member"

# Seats whose payment-request record rule is scoped to "project manager or
# project follower": the business initiator who raises the request and the
# 财务经办 who takes the first tier. The rules are domain-required, so these
# demo seats must follow the project their request belongs to; the driver wires
# that org fact instead of every scenario repeating it.
_DEMO_PAYMENT_SCOPED_SEATS = (
    _DEMO_DOCUMENT_SUBMITTER,
    _DEMO_APPROVAL_ACTORS["smart_construction_core.group_sc_role_finance_user"],
)


def _demo_project_members(env, project, user_xmlids) -> None:
    """Subscribe demo operators to a project.

    The payment-request record rules scope a plain finance user to the projects
    they manage or follow, so the clerk/drafter who works a project must be a
    project member - a real business fact, not a permission change.
    Idempotent: partners already following the project are skipped.
    """
    if not project:
        return
    project = project.sudo()
    partners = env["res.partner"]
    for xmlid in user_xmlids:
        user = env.ref(xmlid, raise_if_not_found=False)
        if user and user.partner_id:
            partners |= user.partner_id
    missing = partners - project.message_partner_ids
    if missing:
        project.message_subscribe(partner_ids=missing.ids)


def _prepare_scenario_organization(env, scenario):
    """Install declared demo membership before business execution starts.

    Approval execution never changes its own visibility or membership.
    The declared projects include only their required operational seats.
    """
    project_xmlid = {
        "s73_risk_settlement_surface": "sc_demo_project_073_risk",
        "s65_cost_budget_funding_surface": "sc_demo_project_065_cost_funding",
        "s69_payment_ledger_surface": "sc_demo_project_069_payment_ledger",
        "s70_daily_business_surface": "sc_demo_project_001",
        "s86_tender_rental_finance_surface": "sc_demo_project_001",
        "s80_execution_management_surface": "sc_demo_project_001",
    }.get(scenario)
    if project_xmlid:
        project = env.ref("smart_construction_demo." + project_xmlid)
        seats = {
            "s69_payment_ledger_surface": _DEMO_PAYMENT_SCOPED_SEATS + (
                "smart_construction_demo.user_sc_settlement_user_cap",
                "smart_construction_demo.user_sc_project_user",
                "smart_construction_demo.user_sc_purchase_manager_cap",
                "smart_construction_demo.user_demo_project_manager",
                "smart_construction_demo.user_sc_cost_manager_cap",
                "smart_construction_demo.user_sc_settlement_manager_cap",
                "smart_construction_demo.user_sc_fin_mgr_01",
                "smart_construction_demo.user_demo_role_executive",
            ),
            "s80_execution_management_surface": ("smart_construction_demo.user_sc_material_01",),
            "s86_tender_rental_finance_surface": _DEMO_PAYMENT_SCOPED_SEATS + (
                "smart_construction_demo.user_sc_rental_payment_checker_demo",
                "smart_construction_demo.user_sc_project_user",
                "smart_construction_demo.user_sc_material_01",
            ),
            "s65_cost_budget_funding_surface": ("smart_construction_demo.user_sc_cost_user_cap",),
            "s73_risk_settlement_surface": ("smart_construction_demo.user_sc_project_user", "smart_construction_demo.user_sc_fin_01"),
        }.get(scenario, _DEMO_PAYMENT_SCOPED_SEATS)
        _demo_project_members(env, project, seats)


def _demo_drive_approval(env, record, submitter_xmlid: str | None = None):
    """Carry one seeded document from draft to its approved state.

    Every step is the model's own public action, taken as the demo account that
    owns that step: ``action_submit`` by the business submitter, then one
    ``action_approval_decision`` per pending tier by ``_DEMO_APPROVAL_ACTORS``.
    Nothing writes a state field and nothing runs as superuser, so the product's
    own access rules and approval gates stay in force. Idempotent: a document
    already approved (or beyond) is returned untouched.
    """
    record = record.sudo()
    if record.state in ("draft", "rejected"):
        _demo_action_record(env, record, "action_submit", submitter_xmlid or _DEMO_DOCUMENT_SUBMITTER).action_submit()
        record.invalidate_recordset()
    _demo_finish_reviews(env, record)
    return record


def _demo_finish_reviews(env, record):
    """Consume the actual pending review instance using its declared seat."""
    rounds = 0
    while "validation_status" in record._fields and record.validation_status in ("waiting", "pending"):
        rounds += 1
        if rounds > 20:
            raise ValueError("demo approval: %s did not converge" % record)
        pending = record.review_ids.filtered(
            lambda review: review.status in ("waiting", "pending")
        ).sorted("sequence")[:1]
        if not pending:
            raise ValueError("demo approval: %s has no pending review tier" % record)
        group = pending.reviewer_group_id
        group_xmlid = group.get_external_id().get(group.id) if group else None
        seat_xmlid = _DEMO_APPROVAL_ACTORS.get(group_xmlid)
        if not seat_xmlid:
            raise ValueError(
                "demo approval: no demo seat declared for reviewer group %s (%s)"
                % (group_xmlid, record)
            )
        action = "action_approval_decision" if record._name == "payment.request" else "validate_tier"
        acting = _demo_action_record(env, record, action, seat_xmlid)
        if not acting.can_review:
            raise ValueError("demo approval: declared seat cannot review %s" % seat_xmlid)
        getattr(acting, action)()
        record.invalidate_recordset()

# Operational seats belong to the demo, not product authorization. The product
# still checks every action. Unreviewed seats fail closed rather than using uid1.
_DEMO_LIFECYCLE_ACTION_ACTORS = {
    ("sc.material.purchase.request", "action_submit"): "user_sc_material_01",
    ("sc.material.rfq", "action_submit"): "user_sc_purchase_01",
    ("sc.material.rfq", "action_select"): "user_sc_material_mgr_01",
    ("sc.material.acceptance", "action_submit"): "user_sc_material_01",
    ("sc.material.acceptance", "action_accept"): "user_sc_material_mgr_01",
    ("sc.material.inbound", "action_submit"): "user_sc_material_01",
    ("sc.material.inbound", "action_receive"): "user_sc_material_mgr_01",
    ("sc.material.outbound", "action_issue"): "user_sc_material_mgr_01",
    ("sc.material.settlement", "action_confirm"): "user_sc_material_mgr_01",
    ("sc.labor.usage", "action_submit"): "user_demo_project_manager",
    ("sc.labor.usage", "action_confirm"): "user_demo_project_manager",
    ("sc.equipment.usage", "action_confirm"): "user_demo_project_manager",
    ("sc.subcontract.register", "action_register"): "user_demo_project_manager",
    ("sc.receipt.income", "action_confirm"): "user_sc_fin_01",
    ("sc.receipt.income", "action_received"): "user_sc_fin_mgr_01",
    ("sc.payment.execution", "action_confirm"): "user_sc_fin_01",
    ("sc.payment.execution", "action_paid"): "user_sc_fin_mgr_01",
    ("sc.tax.deduction.registration", "action_confirm"): "user_sc_fin_01",
    ("sc.tax.deduction.registration", "action_deduct"): "user_sc_fin_mgr_01",
    ("sc.treasury.reconciliation", "write"): "user_sc_fin_01",
    ("sc.treasury.reconciliation", "action_confirm"): "user_sc_fin_01",
    ("sc.invoice.registration", "action_confirm"): "user_sc_fin_01",
    ("sc.financing.loan", "action_confirm"): "user_sc_fin_01",
    ("sc.invoice.registration", "action_register"): "user_sc_fin_mgr_01",
    ("sc.expense.claim", "action_submit"): "user_sc_fin_01",
    ("sc.expense.claim", "action_approve"): "user_sc_fin_mgr_01",
    ("sc.expense.claim", "action_done"): "user_sc_fin_mgr_01",
    ("sc.plan", "action_confirm"): "user_sc_project_user",
    ("sc.plan", "action_start"): "user_sc_project_user",
    ("sc.plan.line", "write"): "user_sc_project_user",
    ("sc.project.document", "action_submit"): "user_sc_project_user",
    ("sc.project.document", "action_archive"): "user_sc_project_user",
    ("sc.construction.diary", "action_confirm"): "user_sc_project_user",
    ("sc.plan.report", "action_submit"): "user_sc_project_user",
    ("sc.safety.plan", "action_submit"): "user_sc_project_user",
    ("sc.safety.disclosure", "action_submit"): "user_sc_project_user",
    ("sc.labor.plan", "action_submit"): "user_sc_project_user",
    ("sc.labor.request", "action_submit"): "user_sc_project_user",
    ("sc.equipment.plan", "action_submit"): "user_sc_project_user",
    ("sc.equipment.request", "action_submit"): "user_sc_project_user",
    ("sc.subcontract.plan", "action_submit"): "user_sc_project_user",
    ("sc.subcontract.request", "action_submit"): "user_sc_project_user",
    ("tender.doc.purchase", "action_submit"): "user_sc_project_user",
    ("sc.attendance.checkin", "action_submit"): "user_sc_project_user",
    ("sc.attendance.checkin", "action_confirm"): "user_sc_project_user",
    ("sc.labor.settlement", "action_submit"): "user_sc_project_user",
    ("sc.labor.settlement", "action_confirm"): "user_sc_project_user",
    ("sc.equipment.settlement", "action_submit"): "user_sc_project_user",
    ("sc.equipment.settlement", "action_confirm"): "user_sc_project_user",
    ("sc.subcontract.settlement", "action_confirm"): "user_sc_project_user",
    ("sc.material.rental.plan", "action_submit"): "user_sc_material_01",
    ("sc.material.rental.order", "action_submit"): "user_sc_material_01",
    ("sc.material.rental.order", "action_activate"): "user_sc_material_01",
    ("sc.material.rental.order", "action_return"): "user_sc_material_01",
    ("sc.material.rental.order", "action_settle"): "user_sc_material_01",
    ("sc.material.rental.settlement", "action_submit"): "user_sc_material_01",
    ("sc.material.rental.settlement", "action_confirm"): "user_sc_material_01",
    ("sc.material.rental.settlement", "action_paid"): "user_sc_rental_payment_checker_demo",
    ("sc.contract.event", "action_submit"): "user_sc_contract_user_cap",
    ("sc.contract.event", "action_done"): "user_sc_contract_user_cap",
    ("sc.settlement.adjustment", "action_confirm"): "user_sc_settlement_user_cap",
    ("project.funding.baseline", "action_activate"): "user_sc_fin_mgr_01",
    ("tender.guarantee", "action_confirm"): "user_sc_project_user",
    ("sc.expense.claim", "write"): "user_sc_fin_01",
    ('sc.general.contract', 'action_confirm'): 'user_sc_contract_user_cap',
    ('sc.general.contract', 'action_signed'): 'user_sc_contract_user_cap',
    ('sc.quality.issue', 'action_submit'): 'user_sc_project_user',
    ('sc.safety.issue', 'action_submit'): 'user_sc_project_user',
    ('sc.hazard.source', 'action_report'): 'user_sc_project_user',
    ('sc.hazard.source', 'action_control'): 'user_sc_project_user',
    ('sc.safety.patrol.task', 'action_plan'): 'user_sc_project_user',
    ('sc.safety.patrol.task', 'action_done'): 'user_sc_project_user',
    ('sc.document.admin.document', 'action_submit'): 'user_sc_business_config_demo',
    ('sc.document.admin.document', 'action_done'): 'user_sc_business_config_demo',
    ('sc.office.admin.document', 'action_submit'): 'user_sc_business_config_demo',
    ('sc.office.admin.document', 'action_done'): 'user_sc_business_config_demo',
    ('sc.fund.account.operation', 'action_confirm'): 'user_sc_fin_01',
    ('sc.fund.account.operation', 'action_done'): 'user_sc_fin_01',
    ('tender.bid', 'action_to_submitted'): 'user_sc_project_user',
    ('tender.bid', 'action_mark_won'): 'user_sc_project_user',
    ('project.settlement', 'action_confirm'): 'user_sc_fin_01',
    ('project.risk.action', 'action_claim'): 'user_sc_project_user',
    ('project.risk.action', 'action_escalate'): 'user_sc_project_user',
    ('sc.dashboard.cockpit.fact', 'action_submit'): 'user_sc_project_user',
    ('sc.dashboard.cockpit.fact', 'action_done'): 'user_sc_project_user',
    ('sc.workbench.item', 'action_submit'): 'user_sc_project_user',
    ('sc.workbench.item', 'action_done'): 'user_sc_project_user',
    ('tender.bid', 'write'): 'user_sc_project_user',
}


def _demo_action_record(env, record, action, actor_xmlid=None):
    if not actor_xmlid:
        seat = _DEMO_LIFECYCLE_ACTION_ACTORS.get((record._name, action))
        if not seat:
            raise ValueError("demo actor declaration missing: %s.%s" % (record._name, action))
        actor_xmlid = "smart_construction_demo." + seat
    actor = env.ref(actor_xmlid, raise_if_not_found=False)
    if not actor or not actor.active or actor.id == 1:
        raise ValueError("demo requires an active non-superuser seat: %s" % actor_xmlid)
    acting = record.with_user(actor).sudo(False)
    if acting.env.su:
        raise ValueError("demo business action cannot run with superuser authority")
    return acting


def _advance_scenario_lifecycle(env, scenario: str) -> None:
    """Drive seeded records from their legal draft create() to the shown state.

    Each record is advanced only through the model's own public business
    actions (``_DEMO_LIFECYCLE_CHAINS``); nothing writes a state field behind a
    guard token. Idempotent: records already at (or beyond) the intended state
    are left untouched, so a reload does not replay approvals.
    """
    targets = _DEMO_LIFECYCLE_TARGETS.get(scenario)
    if not targets:
        return
    module = "smart_construction_demo"
    for xmlid, target in targets.items():
        record = env.ref(f"{module}.{xmlid}", raise_if_not_found=False)
        if not record:
            raise ValueError("demo lifecycle declared record missing: %s" % xmlid)
        state_field = getattr(record, "_state_field", "state")
        current_state = record[state_field]
        if current_state == target or current_state in _DEMO_LIFECYCLE_BEYOND_TARGET.get(
            (record._name, target), ()
        ):
            continue
        if xmlid in _DEMO_LIFECYCLE_XML_ACTIONS:
            raise ValueError("Demo XML business chain did not reach declared terminal: " + xmlid)
        if xmlid == "sc_demo_treasury_reconciliation_070_daily":
            _link_s70_generated_treasury_ledger(env, record)
        fact_values = _DEMO_LIFECYCLE_FACT_WRITES.get(xmlid)
        if fact_values is not None:
            _demo_action_record(env, record, "write", _DEMO_LIFECYCLE_REVIEWER.get((xmlid, "write"))).write(fact_values)
            record.invalidate_recordset()
        else:
            chain = _DEMO_LIFECYCLE_CHAINS.get((record._name, target))
            if not chain:
                raise ValueError(
                    f"demo lifecycle: no action chain for {record._name} -> {target} ({xmlid})"
                )
            for method_name in chain:
                if record[state_field] == target:
                    break
                acting = _demo_action_record(env, record, method_name, _DEMO_LIFECYCLE_REVIEWER.get((xmlid, method_name)))
                getattr(acting, method_name)()
                record.invalidate_recordset()
                _demo_finish_reviews(env, record)
        if record[state_field] != target:
            raise ValueError(
                "demo lifecycle: %s stayed at %s, expected %s after %s"
                % (xmlid, record[state_field], target, chain if fact_values is None else "fact write")
            )


def _link_s70_generated_treasury_ledger(env, reconciliation):
    """Link the native receipt result; outgoing payments own payment.ledger."""
    actor = env.ref("smart_construction_demo.user_sc_fin_mgr_01")
    receipt = env.ref("smart_construction_demo.sc_demo_receipt_income_070_progress").with_user(actor).sudo(False)
    ledgers = receipt.treasury_ledger_id
    if (receipt.state != "received" or len(ledgers) != 1 or ledgers.state != "posted"
            or ledgers.payment_request_id != receipt.payment_request_id or ledgers.direction != "in"):
        raise ValueError("S70 requires its native posted receipt treasury result")
    _bind_generated_demo_xmlid(env, "sc_demo_treasury_ledger_070_daily", ledgers)
    if reconciliation.treasury_ledger_id != ledgers:
        _demo_action_record(env, reconciliation, "write").write({"treasury_ledger_id": ledgers.id})


def _bind_generated_demo_xmlid(env, name, record):
    """Bind fixture metadata to a real result; never replace a conflicting fact."""
    record.ensure_one()
    existing = env.ref("smart_construction_demo." + name, raise_if_not_found=False)
    if existing:
        if existing._name != record._name or existing.id != record.id:
            raise ValueError("demo generated identity conflicts with existing seed: %s" % name)
        return
    env["ir.model.data"].sudo().create({
        "module": "smart_construction_demo", "name": name,
        "model": record._name, "res_id": record.id, "noupdate": True,
    })


def _bind_s65_generated_cost(env):
    source = env.ref("smart_construction_demo.sc_demo_material_outbound_065_rebar")
    actor = env.ref("smart_construction_demo.user_sc_cost_user_cap")
    ledger = env["project.cost.ledger"].with_user(actor).sudo(False).search([
        ("source_model", "=", source._name), ("source_id", "=", source.id),
    ])
    if len(ledger) != 1:
        raise ValueError("S65 requires exactly one cost result from its real material issue")
    _bind_generated_demo_xmlid(env, "sc_demo_cost_ledger_065_rebar", ledger)


def load_scenario(
    env,
    scenario: str,
    mode: str = "update",
    step: str | None = None,
    ensure_base: bool = True,
    apply_passwords: bool = True,
) -> None:
    """
    Load a demo scenario XML files into current DB using Odoo converter.
    - env: Odoo env from odoo shell
    - scenario: key in SCENARIOS
    - mode: 'init' or 'update'. Use update for idempotent reloads.
    """
    scenario = (scenario or "").strip()
    if not scenario:
        raise ValueError("scenario is required, e.g. 's10_contract_payment'")

    scenario = SCENARIO_ALIASES.get(scenario, scenario)

    if scenario not in SCENARIOS:
        known = ", ".join(sorted(SCENARIOS.keys()))
        raise ValueError(f"unknown scenario '{scenario}'. known: {known}")

    guard_demo_scope(env)
    if scenario == "s50_repairable_paths":
        _reset_s50_repairable_records(env)

    module = "smart_construction_demo"
    if ensure_base:
        load_base_seed(env, mode=mode)

    registry = _normalize_registry()
    files = registry[scenario]["files"]
    files = _filter_files(files, step)

    if scenario in ("s70_daily_business_surface", "s86_tender_rental_finance_surface"):
        _prepare_scenario_organization(env, scenario)

    # idref is used by Odoo converter to resolve xmlids in-file
    idref = {}

    for relpath in files:
        abspath = file_path(f"{module}/{relpath}")

        # convert_file will parse XML and create/update records.
        # mode='update' makes this idempotent-friendly for repeated loads.
        convert.convert_file(
            env,
            module,
            abspath,
            idref,
            mode=mode,
            noupdate=False,
            kind="data",
        )

    _prepare_scenario_organization(env, scenario)
    if scenario == "s00_min_path":
        _ensure_s00_boq_visibility(env)
    if scenario == "s65_cost_budget_funding_surface":
        _ensure_funding_baseline(env, "sc_demo_funding_baseline_065")
    if scenario == "s69_payment_ledger_surface":
        _ensure_funding_baseline(env, "sc_demo_funding_baseline_069_payment")
        _ensure_s69_settlement_lifecycle(env)
        _ensure_s69_payment_request_approved(env)
        _ensure_s69_payment_ledger(env)
    if scenario == "s78_project_document_wbs_surface":
        _ensure_s78_project_document_wbs(env)
    if scenario == "s86_tender_rental_finance_surface":
        _prepare_s86_award_source(env)
        _ensure_s86_tender_guarantee_lifecycle(env)
        _ensure_s86_deposit_payment_anchor(env)
    _advance_scenario_lifecycle(env, scenario)
    if scenario == "s65_cost_budget_funding_surface":
        _bind_s65_generated_cost(env)
    if scenario == "s86_tender_rental_finance_surface":
        # 租赁结算必须先是 confirmed 才能作为付款依据，因此付款链只能在通用
        # 办理链把结算送达到 confirmed 之后运行。
        _ensure_s86_rental_settlement_payment(env)

    if apply_passwords:
        apply_demo_user_passwords(env)
    env.cr.commit()


def load_base_seed(env, mode: str = "update") -> None:
    """
    Recreate shared demo base records that scenarios reference.

    Scenario replay restores shared records by their demo-owned XML-IDs.
    """
    guard_demo_scope(env)
    module = "smart_construction_demo"
    idref = {}
    for relpath in BASE_SEED_FILES:
        abspath = file_path(f"{module}/{relpath}")
        convert.convert_file(
            env,
            module,
            abspath,
            idref,
            mode=mode,
            noupdate=False,
            kind="data",
        )
    # Seat XML can introduce identities or replace their group membership.
    # Enroll them before any following scenario performs business actions.
    guard_demo_data_space(env)
    env.cr.commit()


def _import_demo_boq(env, project):
    """Consume the native upload/preflight/import workflow as the cost user."""
    import base64
    import hashlib

    raw = Path(file_path("smart_construction_demo/data/scenario/s00_min_path/contract_boq.csv")).read_bytes()
    actor = env.ref("smart_construction_demo.user_sc_cost_01")
    if actor.id == 1 or not actor.active:
        raise ValueError("demo BOQ import requires its active cost operator")
    Version = env["project.boq.version"].with_user(actor).sudo(False)
    versions = Version.search([
        ("project_id", "=", project.id), ("source_type", "=", "contract"),
        ("code", "=", "DEMO-CONTRACT-V1"),
    ])
    if not versions:
        wizard = env["project.boq.import.wizard"].with_user(actor).sudo(False).create({
            "project_id": project.id, "source_type": "contract", "version_code": "DEMO-CONTRACT-V1",
            "file": base64.b64encode(raw), "filename": "contract_boq.csv",
        })
        wizard.action_preflight()
        action = wizard.action_import()
        versions = Version.browse(action["res_id"]).exists()
    if len(versions) != 1:
        raise ValueError("demo BOQ version identity is ambiguous")
    batch = env["project.boq.import.batch"].with_user(actor).sudo(False).search([
        ("project_id", "=", project.id), ("version_id", "=", versions.id),
    ])
    if len(batch) != 1 or batch.file_digest != hashlib.sha256(raw).hexdigest() or batch.state != "imported":
        raise ValueError("demo BOQ existing result does not match the real import file")
    return versions, batch


def _ensure_s00_boq_visibility(env) -> None:
    """Make the S00 BOQ import batch visible to demo PM and cost users.

    The ``project.boq.import.batch`` "project member scope" record rule
    grants read access only to the project manager (``project_id.user_id``)
    or message followers. Both wirings live here rather than in the seed
    XML: ``data/base/20_projects.xml`` loads before ``sc_demo_users.xml``
    in the manifest data order (a ``user_id`` ref would fail install with
    Error 255), and ``<function>`` tags inside noupdate data blocks are
    silently skipped on update. The loader runs at seed time when the
    demo users already exist.
    Idempotent: skips an already-assigned manager and partners already
    following the project.
    """
    project = env.ref(
        "smart_construction_demo.sc_demo_project_001", raise_if_not_found=False
    )
    if not project:
        return
    project = project.sudo()
    pm_user = env.ref(
        "smart_construction_demo.user_sc_pm_01", raise_if_not_found=False
    )
    if pm_user and project.user_id != pm_user:
        project.write({"user_id": pm_user.id})
    cost_user = env.ref(
        "smart_construction_demo.user_sc_cost_01", raise_if_not_found=False
    )
    if cost_user:
        partner = cost_user.partner_id
        if partner and partner not in project.message_partner_ids:
            project.message_subscribe(partner_ids=[partner.id])


def _ensure_funding_baseline(env, xmlid: str) -> None:
    """Advance a demo funding baseline through the controlled lifecycle.

    Scenario XML only creates draft baselines (the model guards create()
    against non-draft states); activation must go through action_activate().
    Idempotent: skips baselines that are already active or beyond.
    """
    baseline = env.ref(
        f"smart_construction_demo.{xmlid}", raise_if_not_found=False
    )
    if not baseline:
        return
    if baseline.state == "draft":
        _demo_action_record(env, baseline, "action_activate").action_activate()


def _ensure_s69_payment_request_approved(env) -> None:
    """Carry the S69 source request to approved through the real tier chain.

    The request anchors an approved expenditure settlement, so it may only be
    approved after the settlement lifecycle has run; it must also be approved
    before the loader posts its payment ledger. Idempotent.
    """
    request = env.ref(
        "smart_construction_demo.sc_demo_payment_request_069_pay",
        raise_if_not_found=False,
    )
    if not request:
        return
    _demo_drive_approval(env, request)


def _ensure_s69_settlement_lifecycle(env) -> None:
    """Advance the S69 settlement through the controlled lifecycle.

    The settlement XML creates a draft header (its detail line must load
    while the parent is mutable); approval then goes through public submission and the actual review seats.
    Idempotent: skips settlements already approved or beyond.
    """
    settlement = env.ref(
        "smart_construction_demo.sc_demo_settlement_069_payment",
        raise_if_not_found=False,
    )
    if not settlement:
        return
    from ..seed.steps.step_40_contracts_demo import _ensure_purchase_order
    author = _demo_action_record(
        env, settlement, "action_submit", "smart_construction_demo.user_sc_settlement_user_cap"
    )
    _ensure_purchase_order(
        env, author, product=env.ref("smart_construction_demo.sc_demo_product_069_steel_batch")
    )
    if settlement.state == "draft":
        _demo_action_record(
            env, settlement, "action_submit",
            "smart_construction_demo.user_sc_settlement_user_cap",
        ).action_submit()
    _demo_finish_reviews(env, settlement)
    settlement.invalidate_recordset()
    if settlement.state not in ("approve", "done"):
        raise ValueError("demo settlement approval incomplete: %s" % settlement.state)


def _prepare_s86_award_source(env):
    bid = env.ref("smart_construction_demo.sc_demo_tender_bid_086_complex")
    if bid.award_confirmed_at:
        return
    opening = env.ref("smart_construction_demo.sc_demo_tender_opening_086")
    _demo_action_record(env, bid, "write").write({
        "award_opening_id": opening.id,
        "award_source_kind": "award_notice",
        "award_source_reference": "S86-DEMO-AWARD-NOTICE-001",
    })


def _ensure_s86_tender_guarantee_lifecycle(env) -> None:
    """Submit and review before native confirmation produces the treasury fact."""
    for xmlid in (
        "smart_construction_demo.sc_demo_tender_guarantee_086_out",
        "smart_construction_demo.sc_demo_tender_guarantee_086_return",
    ):
        guarantee = env.ref(xmlid)
        if guarantee.state != "confirmed":
            _demo_drive_approval(env, guarantee,
                                 "smart_construction_demo.user_sc_project_user")
            _demo_action_record(env, guarantee, "action_confirm").action_confirm()
        if guarantee.state != "confirmed" or not guarantee.treasury_ledger_id:
            raise ValueError("Demo guarantee did not produce its native treasury fact")


# Xmlid pairs whose evidence attachment must be joined to the claim. The
# business category declares ``attachment_policy = required``, so the seed
# ships the voucher as an ``ir.attachment`` and the relation is wired here:
# records inside a ``<data noupdate="1">`` block are created once and never
# rewritten on reload, so a second record for the same xmlid is a no-op.
_DEMO_CLAIM_ATTACHMENTS = {
    "sc_demo_expense_claim_086_deposit_pay":
        "sc_demo_attachment_086_deposit_pay",
    "sc_demo_expense_claim_086_deposit_refund":
        "sc_demo_attachment_086_deposit_refund",
}


def _demo_link_attachments(env) -> None:
    """Join each seeded claim to its evidence attachment. Idempotent."""
    module = "smart_construction_demo"
    for claim_xmlid, attachment_xmlid in _DEMO_CLAIM_ATTACHMENTS.items():
        claim = env.ref(f"{module}.{claim_xmlid}", raise_if_not_found=False)
        attachment = env.ref(f"{module}.{attachment_xmlid}", raise_if_not_found=False)
        if not claim or not attachment:
            continue
        if attachment not in claim.attachment_ids:
            _demo_action_record(env, claim, "write").write({"attachment_ids": [(4, attachment.id)]})


def _ensure_s86_deposit_payment_anchor(env) -> None:
    """Drive the S86 deposit payment/receipt requests through the real chain.

    A deposit claim is a cash 办理事实, so the product requires an approved
    payment/receipt request as its cash source, and a payment request is a
    four-tier approval document (财务经办确认 -> 项目负责人审核 -> 财务审核 ->
    管理层终审). The seed declares drafts only and the generic approval driver
    walks every tier with the demo seat that owns it. Project membership is
    prepared separately before the business chain starts. Idempotent.
    """
    module = "smart_construction_demo"
    _demo_link_attachments(env)
    for xmlid in (
        "sc_demo_payment_request_086_deposit_pay",
        "sc_demo_payment_request_086_deposit_refund",
    ):
        request = env.ref(f"{module}.{xmlid}", raise_if_not_found=False)
        if not request:
            continue
        request = _demo_drive_approval(env, request)
        if request.state not in ("approved", "done"):
            raise ValueError(
                "demo lifecycle: %s stayed at %s, expected an approved request"
                % (xmlid, request.state)
            )


def _ensure_s86_rental_settlement_payment(env) -> None:
    """Pay the S86 rental settlement through the real 付款登记 chain.

    A rental settlement only reaches ``paid`` once an attributed payment
    request has a fully posted payment ledger (``RENTAL_PAYMENT_ATTRIBUTION_
    MISSING``), and the request may only exist while the settlement is already
    ``confirmed`` (``_check_rental_settlement_consistency``), while neither
    document may be completed by a direct state write
    (``payment.request.action_done`` refuses both directions). The real product
    order is therefore settlement 提交/确认 -> 付款申请(金额取未预留额) ->
    四段审批 -> 付款登记 (``sc.payment.execution``) confirm/register -> 结算
    确认已支付, and this finalizer runs after the generic 办理链 has delivered
    the settlement to ``confirmed``. Idempotent.
    """
    module = "smart_construction_demo"
    settlement = env.ref(
        f"{module}.sc_demo_material_rental_settlement_086_scaffold",
        raise_if_not_found=False,
    )
    if not settlement:
        return
    settlement = settlement.sudo()
    if settlement.state == "paid":
        return
    if settlement.state != "confirmed":
        raise ValueError(
            "demo lifecycle: 租赁结算必须先在 confirmed 才能作为付款依据，实际为 %s"
            % settlement.state
        )

    request = env["payment.request"].sudo().search(
        [("rental_settlement_id", "=", settlement.id)], limit=1
    )
    if not request:
        amount = settlement._payment_unreserved_amount()
        if amount <= 0:
            raise ValueError("demo lifecycle: 租赁结算无可付余额，无法生成付款依据")
        # 付款申请必须由既能读取租赁结算、又有付款申请创建权的真实席位发起
        # （付款依据关系校验 _caller_visible_payment_relations 按发起人可见性
        # 复核来源单据）。demo 中该席位为财务经理，而非项目业务发起人。
        request = (
            env["payment.request"]
            .with_user(
                env.ref("smart_construction_demo.user_sc_fin_mgr_01")
            )
            .create(
                {
                    "type": "pay",
                    "project_id": settlement.project_id.id,
                    "rental_settlement_id": settlement.id,
                    "partner_id": settlement.supplier_id.id,
                    "contract_id": settlement.contract_id.id or False,
                    "currency_id": settlement.currency_id.id,
                    "amount": amount,
                    "date_request": "2025-07-12",
                    "actual_payee_unit": "德阳某某周转材料租赁有限公司（示例）",
                    "payment_account_name": "德阳某某周转材料租赁有限公司（示例）",
                    "payment_bank_name": "中国银行德阳示范支行",
                    "payment_account_no": "DEMO-ACCOUNT-RENTAL-086",
                    "note": "S86 周转材料租赁费支付申请。",
                }
            )
        )
    request = _demo_drive_approval(env, request)
    if request.state not in ("approved", "done"):
        raise ValueError(
            "demo lifecycle: %s stayed at %s, expected an approved request"
            % (request.name, request.state)
        )
    handler = env.ref(
        "smart_construction_demo.user_sc_fin_01", raise_if_not_found=False
    )
    # 付款登记创建会复核来源租赁结算额度并按发起人可见性读取结算单；demo 中
    # 同时具备“财务经办能力 + 租赁结算读取”的席位是财务经理，故由该席位创建，
    # 经办与确认仍按财务办理/财务确认两段职责推进。
    execution_creator = env.ref(
        "smart_construction_demo.user_sc_fin_mgr_01", raise_if_not_found=False
    )
    execution = env["sc.payment.execution"].sudo().search(
        [("payment_request_id", "=", request.id)], limit=1
    )
    if not execution:
        execution = (
            env["sc.payment.execution"]
            .with_user(execution_creator)
            .create(
                {
                    "payment_request_id": request.id,
                    "project_id": request.project_id.id,
                    "partner_id": request.partner_id.id,
                    "contract_id": request.contract_id.id,
                    "source_kind": "actual_outflow",
                    "payment_family": "周转材料租赁费",
                    "payment_method": "银行转账",
                    "date_payment": "2025-07-12",
                    "document_no": request.name,
                    "planned_amount": request.amount,
                    "paid_amount": request.amount,
                    "invoice_amount": request.amount,
                    "currency_id": request.currency_id.id,
                    "receipt_account_name": request.payment_account_name,
                    "receipt_bank_name": request.payment_bank_name,
                    "receipt_account_no": request.payment_account_no,
                    "handler_name": "测试-财务经办",
                    "note": "S86 周转材料租赁费付款登记样例。",
                }
            )
        )
    if execution.state == "draft":
        execution.with_user(handler).action_confirm()
    if execution.state == "confirmed":
        manager = env.ref(
            "smart_construction_demo.user_sc_fin_mgr_01", raise_if_not_found=False
        )
        execution.with_user(manager).action_paid()

    settlement.invalidate_recordset()
    if settlement.state == "confirmed":
        _demo_action_record(env, settlement, "action_paid").action_paid()
        settlement.invalidate_recordset()
    if settlement.state != "paid":
        raise ValueError(
            "demo lifecycle: 租赁结算付款后仍为 %s，预期 paid" % settlement.state
        )


def _ensure_s69_payment_ledger(env) -> None:
    """Post S69 through the same payment registration used by finance users."""
    request = env.ref("smart_construction_demo.sc_demo_payment_request_069_pay")
    creator = env.ref("smart_construction_demo.user_sc_fin_mgr_01")
    Execution = env["sc.payment.execution"].with_user(creator).sudo(False)
    execution = Execution.search([("payment_request_id", "=", request.id)])
    if len(execution) > 1:
        raise ValueError("demo payment execution identity is ambiguous")
    if not execution:
        execution = Execution.create({
            "payment_request_id": request.id,
            "project_id": request.project_id.id,
            "partner_id": request.partner_id.id,
            "contract_id": request.contract_id.id,
            "source_kind": "actual_outflow",
            "payment_method": "银行转账",
            "date_payment": "2025-08-24",
            "document_no": "S69-PAY-LEDGER-001",
            "planned_amount": request.amount,
            "paid_amount": request.amount,
            "invoice_amount": request.amount,
            "currency_id": request.currency_id.id,
            "receipt_account_name": request.payment_account_name,
            "receipt_bank_name": request.payment_bank_name,
            "receipt_account_no": request.payment_account_no,
            "handler_name": "Demo-财务经办",
            "note": "S69 支付台账样例。",
        })
    if execution.state == "draft":
        _demo_action_record(env, execution, "action_confirm").action_confirm()
    _demo_finish_reviews(env, execution)
    if execution.state == "confirmed":
        _demo_action_record(
            env, execution, "action_paid", "smart_construction_demo.user_sc_fin_mgr_01"
        ).action_paid()
    execution.invalidate_recordset()
    if execution.state != "paid":
        raise ValueError("demo payment registration incomplete: %s" % execution.state)


def _ensure_s78_project_document_wbs(env) -> None:
    """Keep XML-loaded S78 WBS levels and document attachment relations stable."""
    wbs_records = env["construction.work.breakdown"].sudo().search(
        [("code", "in", ("S78-SINGLE", "S78-UNIT", "S78-SUBDIV", "S78-INSP-001"))],
        order="id",
    )
    if wbs_records:
        wbs_records._compute_level()

    doc = env.ref(
        "smart_construction_demo.sc_demo_document_078_quality_archive",
        raise_if_not_found=False,
    )
    attachment = env.ref(
        "smart_construction_demo.sc_demo_attachment_078_quality_archive",
        raise_if_not_found=False,
    )
    if doc and attachment and attachment not in doc.attachment_ids:
        doc.sudo().write({"attachment_ids": [(4, attachment.id)]})




def load_all(env, mode: str = "update") -> None:
    """
    Load all registered scenarios in stable order.
    """
    load_base_seed(env, mode=mode)
    registry = _normalize_registry()
    ordered = sorted(
        registry.items(),
        key=lambda item: (item[1]["sequence"], item[0]),
    )
    for scenario, _spec in ordered:
        load_scenario(
            env,
            scenario,
            mode=mode,
            ensure_base=False,
            apply_passwords=False,
        )
    apply_demo_user_passwords(env)
    env.cr.commit()


def load_release_seed(env, mode: str = "update") -> None:
    """
    Load release-grade demo seed set.

    Excludes process-only failure drills (s40/s50), keeps business-complete
    walkthrough path for product demo and acceptance.
    """
    known = set(SCENARIOS.keys())
    load_base_seed(env, mode=mode)
    for scenario in RELEASE_SCENARIOS:
        if scenario not in known:
            raise ValueError(f"release scenario '{scenario}' not registered")
        load_scenario(
            env,
            scenario,
            mode=mode,
            ensure_base=False,
            apply_passwords=False,
        )
    apply_demo_user_passwords(env)
    env.cr.commit()


def _reset_s50_repairable_records(env) -> None:
    """Replay S50 from its intended bad seed without mutating guarded fields."""
    for xmlid in (
        "smart_construction_demo.sc_demo_payment_050_001",
        "smart_construction_demo.sc_demo_settlement_line_050_001",
        "smart_construction_demo.sc_demo_settlement_050_001",
    ):
        model_name, res_id = env["ir.model.data"]._xmlid_to_res_model_res_id(
            xmlid,
            raise_if_not_found=False,
        )
        if not model_name or not res_id:
            continue
        record = env[model_name].sudo().browse(res_id).exists()
        if record:
            record.with_context(allow_transition=True, allow_contract_change=True).unlink()
    env.cr.commit()
