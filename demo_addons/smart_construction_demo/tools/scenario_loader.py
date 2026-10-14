# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from odoo.tools import convert
from odoo.tools.misc import file_path

from ..hooks import apply_demo_user_passwords, guard_demo_scope


def _demo_carrier_context(env) -> dict:
    """Governed-migration-carrier context for scenario XML loads.

    The demo release seed provisions terminal-state facts (approved
    settlements, confirmed payments, issued material documents, ...).
    Product hardening reserves those state transitions for service flows
    behind authority sentinels ("受治理迁移载体" boundaries). The release
    seed — git-versioned, PR-reviewed, loaded through audited scripts — is
    such a governed carrier, so scenario XML loads run with the owning
    modules' own tokens. Sentinels are imported from their defining
    modules (never re-declared here) so refactors stay in lockstep; the
    same cross-module sentinel import pattern already exists in
    smart_construction_core (payment_ledger imports funding_baseline's
    allocation token).
    """
    from odoo.addons.smart_construction_core.models.core import (
        equipment_management,
        expense_claim,
        funding_baseline,
        payment_execution,
        payment_ledger,
        payment_ledger_allocation,
        payment_request,
        receipt_income,
        self_funding_registration,
        tax_deduction_registration,
    )
    from odoo.addons.smart_construction_core.models.projection import treasury_ledger
    from odoo.addons.smart_construction_core.models.support import tender

    settlement_model = env["sc.settlement.order"]
    cost_ledger_model = env["project.cost.ledger"]
    return {
        "sc_expense_fact_authority_token": (
            expense_claim._EXPENSE_FACT_AUTHORITY_TOKEN
        ),
        "_sc_funding_baseline_token": funding_baseline._FUNDING_BASELINE_TOKEN,
        "_sc_funding_allocation_token": funding_baseline._FUNDING_ALLOCATION_TOKEN,
        equipment_management._COST_SOURCE_STATE_CONTEXT_KEY: (
            equipment_management._COST_SOURCE_STATE_TOKEN
        ),
        "_sc_payment_execution_batch_ready_token": (
            payment_execution._PAYMENT_EXECUTION_BATCH_READY_TOKEN
        ),
        "sc_payment_ledger_authority_token": (
            payment_ledger._PAYMENT_LEDGER_AUTHORITY_TOKEN
        ),
        "sc_payment_ledger_allocation_authority_token": (
            payment_ledger_allocation._PAYMENT_LEDGER_ALLOCATION_AUTHORITY_TOKEN
        ),
        "_sc_funding_baseline_binding_token": (
            payment_request._FUNDING_BINDING_TOKEN
        ),
        "_sc_terminal_cash_source_claim_token": (
            payment_request._TERMINAL_CASH_SOURCE_CLAIM_TOKEN
        ),
        "sc_receipt_fact_authority_token": (
            receipt_income._RECEIPT_FACT_AUTHORITY_TOKEN
        ),
        "sc_self_funding_authority_token": (
            self_funding_registration._SELF_FUNDING_AUTHORITY_TOKEN
        ),
        settlement_model._LIFECYCLE_CONTEXT_KEY: (
            settlement_model._LIFECYCLE_SERVICE_TOKEN
        ),
        "sc_tax_fact_authority_token": (
            tax_deduction_registration._TAX_FACT_AUTHORITY_TOKEN
        ),
        "sc_treasury_authority_token": treasury_ledger._TREASURY_AUTHORITY_TOKEN,
        "sc_tender_guarantee_authority_token": (
            tender._TENDER_GUARANTEE_AUTHORITY_TOKEN
        ),
        cost_ledger_model._GENERATED_CONTEXT_KEY: (
            cost_ledger_model._GENERATED_SERVICE_TOKEN
        ),
    }


BASE_SEED_FILES: List[str] = [
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
    "s67_scene_pack_surface",
    "s68_cockpit_workbench_surface",
    "s69_payment_ledger_surface",
    "s70_daily_business_surface",
    "s71_governance_audit_surface",
    "s72_project_governance_surface",
    "s73_risk_settlement_surface",
    "s74_partner_supplier_surface",
    "s75_summary_projection_surface",
    "s76_workflow_compat_surface",
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
    "s70_daily_business_surface": {
        "sc_demo_receipt_income_070_progress": "confirmed",
        "sc_demo_payment_execution_070_material": "confirmed",
        "sc_demo_treasury_reconciliation_070_daily": "confirmed",
        "sc_demo_invoice_registration_070_input": "registered",
        "sc_demo_construction_diary_070_daily": "confirmed",
    },
    "s78_project_document_wbs_surface": {
        "sc_demo_document_078_safety_review": "approved",
        "sc_demo_document_078_quality_archive": "done",
    },
    "s80_execution_management_surface": {
        "sc_demo_material_purchase_request_080_steel": "approved",
        "sc_demo_material_rfq_080_steel": "selected",
        "sc_demo_material_acceptance_080_steel": "accepted",
        "sc_demo_material_inbound_080_steel": "received",
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
        "sc_demo_financing_loan_085_bank": "confirmed",
        "sc_demo_hr_payroll_085_salary": "done",
        "sc_demo_hr_payroll_085_bonus": "done",
        "sc_demo_subcontract_plan_085_fitout": "approved",
        "sc_demo_subcontract_request_085_fitout": "approved",
        "sc_demo_subcontract_register_085_fitout": "active",
        "sc_demo_subcontract_settlement_085_fitout": "confirmed",
    },
    "s86_tender_rental_finance_surface": {
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
        "sc_demo_safety_plan_089_dangerous": "approved",
        "sc_demo_safety_disclosure_089_dangerous": "approved",
    },
}

# (model, intended terminal state) -> ordered public action methods.
# When a model carries no approval rule the submission action completes the
# approval inline (one-step handling), so the chain is just the submit.
_DEMO_LIFECYCLE_CHAINS = {
    ("sc.receipt.income", "confirmed"): ("action_confirm",),
    ("sc.payment.execution", "confirmed"): ("action_confirm",),
    ("sc.treasury.reconciliation", "confirmed"): ("action_confirm",),
    ("sc.invoice.registration", "registered"): ("action_confirm", "action_register"),
    ("sc.construction.diary", "confirmed"): ("action_confirm",),
    ("sc.project.document", "approved"): ("action_submit",),
    ("sc.project.document", "done"): ("action_submit", "action_archive"),
    ("sc.material.purchase.request", "approved"): ("action_submit",),
    ("sc.material.rfq", "selected"): ("action_submit", "action_select"),
    ("sc.material.acceptance", "accepted"): ("action_submit", "action_accept"),
    ("sc.material.inbound", "received"): ("action_submit", "action_receive"),
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
    ("sc.labor.usage", "confirmed"): ("action_confirm",),
    ("sc.labor.settlement", "confirmed"): ("action_submit", "action_confirm"),
    ("sc.equipment.settlement", "confirmed"): ("action_submit", "action_confirm"),
    ("sc.contract.event", "approved"): ("action_submit",),
    ("sc.contract.event", "done"): ("action_submit", "action_done"),
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

# Records whose approval-bearing steps must be carried out by the configured
# reviewer role instead of the system loader. The user is a member of the
# approval group of the record's policy (sc.expense.claim -> finance manager).
_DEMO_LIFECYCLE_REVIEWER = {
    "sc_demo_expense_claim_086_deposit_pay": "smart_construction_demo.user_sc_finance_mgr_test",
    "sc_demo_expense_claim_086_deposit_refund": "smart_construction_demo.user_sc_finance_mgr_test",
}

# Approval tier seat map: reviewer group -> the demo account that owns that
# seat. The product ships its user-visible approval templates with several
# tiers (付款/收款申请: 财务经办确认 -> 项目负责人审核 -> 财务审核 -> 管理层终审),
# and each tier may only be decided by a member of its own group. Declaring the
# seat once means the generic driver below can walk any chain for any model, so
# a scenario that adds an approval-bearing document needs no tier-specific code.
_DEMO_APPROVAL_ACTORS = {
    "smart_construction_core.group_sc_role_finance_user":
        "smart_construction_demo.user_sc_fin_01",
    "smart_construction_core.group_sc_cap_project_manager":
        "smart_construction_demo.user_demo_project_manager",
    "smart_construction_core.group_sc_cap_finance_manager":
        "smart_construction_demo.user_sc_fin_mgr_01",
    "smart_construction_core.group_sc_role_executive":
        "smart_construction_demo.user_demo_role_executive",
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


def _demo_scope_record_actors_to_project(env, record) -> None:
    """Subscribe the record-rule-scoped demo seats to the record's project.

    ``payment.request`` scopes the 业务发起 and 财务经办 seats to
    ``project_id.user_id`` or project followers, so the seeded requester could
    not submit its own request until it followed the project. Only a
    subscription is written; no ACL or record rule is touched, and an
    already-visible record keeps the submitter able to read exactly what the
    product's own rule allows. Idempotent.
    """
    _demo_project_members(env, record.project_id, _DEMO_PAYMENT_SCOPED_SEATS)


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
    _demo_scope_record_actors_to_project(env, record)
    if record.state == "draft":
        submitter = env.ref(submitter_xmlid or _DEMO_DOCUMENT_SUBMITTER, raise_if_not_found=False)
        record.with_user(submitter).action_submit()
        record.invalidate_recordset()
    rounds = 0
    while record.state in ("submit", "approve") and record.validation_status in ("waiting", "pending"):
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
        seat = env.ref(seat_xmlid, raise_if_not_found=False)
        if not seat:
            raise ValueError("demo approval: declared seat %s is missing" % seat_xmlid)
        record.with_user(seat).action_approval_decision()
        record.invalidate_recordset()
    return record


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
            continue
        reviewer_xmlid = _DEMO_LIFECYCLE_REVIEWER.get(xmlid)
        actor = env.ref(reviewer_xmlid, raise_if_not_found=False) if reviewer_xmlid else None
        record = record.sudo()
        if actor:
            record = record.with_user(actor)
        state_field = getattr(record, "_state_field", "state")
        current_state = record[state_field]
        if current_state == target or current_state in _DEMO_LIFECYCLE_BEYOND_TARGET.get(
            (record._name, target), ()
        ):
            continue
        fact_values = _DEMO_LIFECYCLE_FACT_WRITES.get(xmlid)
        if fact_values is not None:
            record.write(fact_values)
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
                getattr(record, method_name)()
                record.invalidate_recordset()
        if record[state_field] != target:
            raise ValueError(
                "demo lifecycle: %s stayed at %s, expected %s after %s"
                % (xmlid, record[state_field], target, chain if fact_values is None else "fact write")
            )


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

    # idref is used by Odoo converter to resolve xmlids in-file
    idref = {}
    carrier_env = env["base"].with_context(**_demo_carrier_context(env)).env

    for relpath in files:
        abspath = file_path(f"{module}/{relpath}")

        # convert_file will parse XML and create/update records.
        # mode='update' makes this idempotent-friendly for repeated loads.
        convert.convert_file(
            carrier_env,
            module,
            abspath,
            idref,
            mode=mode,
            noupdate=False,
            kind="data",
        )

    if scenario == "s00_min_path":
        _ensure_s00_boq_visibility(env)
    if scenario == "s65_cost_budget_funding_surface":
        _ensure_funding_baseline(env, "sc_demo_funding_baseline_065")
    if scenario == "s69_payment_ledger_surface":
        _ensure_s69_settlement_lifecycle(env)
        _ensure_s69_payment_request_approved(env)
        _ensure_s69_payment_ledger(env)
        _ensure_funding_baseline(env, "sc_demo_funding_baseline_069_payment")
    if scenario == "s78_project_document_wbs_surface":
        _ensure_s78_project_document_wbs(env)
    if scenario == "s80_execution_management_surface":
        _ensure_s80_material_lifecycle(env)
    if scenario == "s86_tender_rental_finance_surface":
        _ensure_s86_tender_guarantee_lifecycle(env)
        _ensure_s86_deposit_payment_anchor(env)
    _advance_scenario_lifecycle(env, scenario)
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
    carrier_env = env["base"].with_context(**_demo_carrier_context(env)).env
    for relpath in BASE_SEED_FILES:
        abspath = file_path(f"{module}/{relpath}")
        convert.convert_file(
            carrier_env,
            module,
            abspath,
            idref,
            mode=mode,
            noupdate=False,
            kind="data",
        )
    env.cr.commit()


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
    baseline = baseline.sudo()
    if baseline.state == "draft":
        baseline.action_activate()


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
    while the parent is mutable); approval then goes through the lifecycle
    service write so the approved fact stays governed.
    Idempotent: skips settlements already approved or beyond.
    """
    settlement = env.ref(
        "smart_construction_demo.sc_demo_settlement_069_payment",
        raise_if_not_found=False,
    )
    if not settlement:
        return
    settlement = settlement.sudo()
    if settlement.state == "draft":
        settlement._write_lifecycle("approve")


def _ensure_s86_tender_guarantee_lifecycle(env) -> None:
    """Advance S86 tender guarantees through the controlled confirm action.

    tender.guarantee create() is an absolute guard (no direct ``confirmed``
    terminal state), so the XML loads drafts and the confirm runs through
    action_confirm(), which also seeds the treasury ledger entries.
    Idempotent: skips records already confirmed.
    """
    for xmlid in (
        "smart_construction_demo.sc_demo_tender_guarantee_086_out",
        "smart_construction_demo.sc_demo_tender_guarantee_086_return",
    ):
        guarantee = env.ref(xmlid, raise_if_not_found=False)
        if guarantee and guarantee.state == "draft":
            guarantee.sudo().action_confirm()


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
            claim.sudo().write({"attachment_ids": [(4, attachment.id)]})


def _ensure_s86_deposit_payment_anchor(env) -> None:
    """Drive the S86 deposit payment/receipt requests through the real chain.

    A deposit claim is a cash 办理事实, so the product requires an approved
    payment/receipt request as its cash source, and a payment request is a
    four-tier approval document (财务经办确认 -> 项目负责人审核 -> 财务审核 ->
    管理层终审). The seed declares drafts only and the generic approval driver
    walks every tier with the demo seat that owns it, wiring the project
    membership the record rules require on the way. Idempotent.
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
        settlement.action_paid()
        settlement.invalidate_recordset()
    if settlement.state != "paid":
        raise ValueError(
            "demo lifecycle: 租赁结算付款后仍为 %s，预期 paid" % settlement.state
        )


def _ensure_s80_material_lifecycle(env) -> None:
    """Advance S80 material outbound/settlement through controlled lifecycle.

    Both parents' detail-line create() guards are absolute (no carrier token
    bypass): lines may only load while the parent is mutable, so the XML
    creates drafts and the terminal states are reached through the governed
    cost-source state writes afterwards.
    Idempotent: skips records already at or beyond the target state.
    """
    outbound = env.ref(
        "smart_construction_demo.sc_demo_material_outbound_080_steel",
        raise_if_not_found=False,
    )
    if outbound and outbound.state == "draft":
        outbound.sudo()._write_cost_source_state({"state": "issued"})
    settlement = env.ref(
        "smart_construction_demo.sc_demo_material_settlement_080_steel",
        raise_if_not_found=False,
    )
    if settlement and settlement.state == "draft":
        settlement.sudo()._write_cost_source_state({"state": "confirmed"})


def _ensure_s69_payment_ledger(env) -> None:
    """Create the S69 ledger through the payment-request service boundary."""
    module = "smart_construction_demo"
    request = env.ref(f"{module}.sc_demo_payment_request_069_pay", raise_if_not_found=False)
    if not request:
        return
    Ledger = env["payment.ledger"].sudo()
    ledger = Ledger.search([("payment_request_id", "=", request.id)], limit=1)
    if ledger:
        return
    request.sudo().with_context(payment_soft_gate=True)._ensure_payment_ledger(
        amount=120000.0,
        paid_at="2025-08-24 10:00:00",
        ref="S69-PAY-LEDGER-001",
        note="S69 支付台账样例。",
    )


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
