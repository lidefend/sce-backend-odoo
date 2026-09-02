# -*- coding: utf-8 -*-
import json
import importlib.util
from pathlib import Path

from odoo import api, models
from odoo.addons.smart_core.utils.backend_contract_boundaries import (
    MENU_CONFIG_NAV_ENABLED_PARAM,
    MENU_CONFIG_POLICY_MODEL,
    NAV_USER_DATA_ACCEPTANCE_ONLY_PARAM,
)
from odoo.addons.smart_construction_core.services.locked_menu_policy_contract import (
    FORMAL_ACTION_ONLY_MENU_TARGETS,
    FORMAL_BUSINESS_DECISION_REQUIRED_TARGETS,
    FORMAL_INITIALIZATION_ACTION_SPECS,
    LockedMenuPolicyContractError,
    assert_policy_matches_locked_contract,
    canonical_group_label,
    load_locked_menu_policy_contract,
)


FORMAL_CONTRACT_PRODUCT_MENU_XMLIDS = {
    # Locked product-center contract entries. These direct P1 menus are the
    # released product navigation contract; they must not depend on tenant or
    # user-acceptance policy rows to remain visible in config-only mode.
    "smart_construction_core.menu_sc_p1_income_contract",
    "smart_construction_core.menu_sc_p1_expense_contract",
    "smart_construction_core.menu_sc_p1_contract_change",
    "smart_construction_core.menu_sc_p1_daily_contract",
    "smart_construction_core.menu_sc_construction_contract",
    "smart_construction_core.menu_sc_contract_handling",
    "smart_construction_core.menu_sc_contract_income",
    "smart_construction_core.menu_sc_project_income_contract",
    "smart_construction_core.menu_sc_income_contract_execution",
    "smart_construction_core.menu_sc_contract_event",
    "smart_construction_core.menu_sc_general_contract",
    "smart_construction_core.menu_sc_contract_expense",
    "smart_construction_core.menu_sc_expense_contract_execution",
    "smart_construction_core.menu_sc_expense_contract_supplement",
}

FORMAL_SETTLEMENT_PRODUCT_MENU_XMLIDS = {
    "smart_construction_core.menu_sc_p1_income_settlement",
    "smart_construction_core.menu_sc_p1_expense_settlement",
    "smart_construction_core.menu_sc_settlement_order",
    "smart_construction_core.menu_sc_settlement_adjustment",
    "smart_construction_core.menu_sc_income_contract_settlement",
    "smart_construction_core.menu_sc_expense_contract_settlement",
    "smart_construction_core.menu_sc_material_settlement",
    "smart_construction_core.menu_sc_labor_settlement",
    "smart_construction_core.menu_sc_equipment_settlement",
    "smart_construction_core.menu_sc_material_rental_settlement",
    "smart_construction_core.menu_sc_subcontract_settlement",
}

USER_ACCEPTANCE_PRODUCT_MENU_XMLIDS = {
    "smart_construction_core.menu_sc_customer_partner",
    "smart_construction_core.menu_sc_supplier_partner",
}

# The locked ten-center product candidate deliberately keeps these legacy,
# roadmap, duplicate or incomplete menu facts unpublished. They remain valid
# XMLIDs/action authorities for migration and audit, but policy convergence
# must not reactivate their native menu rows after the final XML overlay.
LOCKED_TARGET_UNPUBLISHED_MENU_XMLIDS = {
    "smart_construction_core.menu_sc_workbench_my_approval_fact",
    "smart_construction_core.menu_sc_project_overview_group_v2",
    "smart_construction_core.menu_sc_project_ledger_group_v2",
    "smart_construction_core.menu_sc_project_planning_group_v2",
    "smart_construction_core.menu_sc_project_organization_group_v2",
    "smart_construction_core.menu_sc_project_milestone_group_v2",
    "smart_construction_core.menu_sc_project_collaboration_group_v2",
    "smart_construction_core.menu_sc_project_document_group_v2",
    "smart_construction_core.menu_sc_project_risk_group_v2",
    "smart_construction_core.menu_sc_project_closeout_group_v2",
    "smart_construction_core.menu_sc_project_quick_create",
    "smart_construction_core.menu_sc_tender_prepare",
    "smart_construction_core.menu_sc_tender_registration",
    "smart_construction_core.menu_sc_tender_registration_fee",
    "smart_construction_core.menu_sc_tender_opening",
    "smart_construction_core.menu_sc_field_mobile_roadmap_v2",
    "smart_construction_core.menu_sc_bim_collaboration_roadmap_v2",
    "smart_construction_core.menu_sc_schedule_delivery_group_v2",
    "smart_construction_core.menu_sc_quality_delivery_group_v2",
    "smart_construction_core.menu_sc_safety_delivery_group_v2",
    "smart_construction_core.menu_sc_material_management_group",
    "smart_construction_core.menu_sc_labor_management_group",
    "smart_construction_core.menu_sc_equipment_management_group",
    "smart_construction_core.menu_sc_material_rental_group",
    "smart_construction_core.menu_sc_subcontract_management_group",
    "smart_construction_core.menu_sc_supply_collaboration_roadmap_v2",
    "smart_construction_core.menu_sc_construction_contract",
    "smart_construction_core.menu_sc_contract_performance_roadmap_v2",
    "smart_construction_core.menu_sc_project_wbs_cost",
    "smart_construction_core.menu_sc_cost_forecast_roadmap_v2",
    "smart_construction_core.menu_sc_cost_cashflow_roadmap_v2",
    "smart_construction_core.menu_sc_noncash_business_group",
    "smart_construction_core.menu_sc_historical_payment_fact",
    "smart_construction_core.menu_sc_arrival_confirmation",
    "smart_construction_core.menu_sc_finance_interfund_analysis",
    "smart_construction_core.menu_sc_fund_forecast_roadmap_v2",
    "smart_construction_core.menu_sc_tax_filing_roadmap_v2",
    "smart_construction_core.menu_sc_invoice_verification_roadmap_v2",
    "smart_construction_core.menu_sc_business_entity",
    "smart_construction_core.menu_sc_report_prediction_roadmap_v2",
    "smart_construction_core.menu_sc_fuel_card_archive_group",
    "smart_construction_core.menu_sc_people_lifecycle_roadmap_v2",
    "smart_construction_core.menu_sc_resource_capacity_roadmap_v2",
}

TAX_CENTER_PRODUCT_MENU_XMLIDS = {
    "smart_construction_core.menu_sc_invoice_input",
    "smart_construction_core.menu_sc_invoice_application_user",
    "smart_construction_core.menu_sc_invoice_registration_user",
    "smart_construction_core.menu_sc_invoice_prepaid_tax_user",
    "smart_construction_core.menu_sc_tax_deduction_registration_user",
    "smart_construction_core.menu_sc_tax_certificate_registration_user",
}
PRODUCT_MENU_BUSINESS_DOMAIN_OVERRIDES = {
    "smart_construction_core.menu_sc_general_contract": {
        "path_domain": "合同管理",
        "integration_target": "sc.general.contract 一般合同",
        "product_domain": "contract",
        "product_domain_label": "合同管理",
    },
    "smart_construction_core.menu_sc_income_contract_settlement": {
        "path_domain": "结算管理",
        "integration_target": "sc.settlement.order 合同结算",
        "product_domain": "contract_settlement",
        "product_domain_label": "结算管理",
    },
    "smart_construction_core.menu_sc_expense_contract_settlement": {
        "path_domain": "结算管理",
        "integration_target": "sc.settlement.order 合同结算",
        "product_domain": "contract_settlement",
        "product_domain_label": "结算管理",
    },
    "smart_construction_core.menu_sc_subcontract_request_acceptance": {
        "path_domain": "分包管理",
        "integration_target": "sc.subcontract.request 分包管理",
        "product_domain": "subcontract",
        "product_domain_label": "分包管理",
    },
    "smart_construction_core.menu_sc_labor_usage_acceptance": {
        "path_domain": "劳务管理",
        "integration_target": "sc.labor.usage 劳务用工",
        "product_domain": "labor",
        "product_domain_label": "劳务管理",
    },
    "smart_construction_core.menu_sc_labor_casual_acceptance": {
        "path_domain": "劳务管理",
        "integration_target": "sc.labor.usage 劳务用工",
        "product_domain": "labor",
        "product_domain_label": "劳务管理",
    },
    "smart_construction_core.menu_sc_equipment_shift_acceptance": {
        "path_domain": "机械管理",
        "integration_target": "sc.equipment.usage 机械台班",
        "product_domain": "equipment",
        "product_domain_label": "机械管理",
    },
    "smart_construction_core.menu_sc_material_quote_acceptance": {
        "path_domain": "询价报价",
        "integration_target": "sc.material.rfq 询价报价",
        "product_domain": "material",
        "product_domain_label": "询价报价",
    },
    "smart_construction_core.menu_sc_material_inbound": {
        "path_domain": "材料管理",
        "integration_target": "sc.material.inbound 材料入库",
        "product_domain": "material",
        "product_domain_label": "材料管理",
    },
    "smart_construction_core.menu_sc_material_outbound": {
        "path_domain": "材料管理",
        "integration_target": "sc.material.outbound 材料出库",
        "product_domain": "material",
        "product_domain_label": "材料管理",
    },
    "smart_construction_core.menu_sc_user_income": {
        "path_domain": "收款管理",
        "integration_target": "sc.receipt.income 收款登记",
        "product_domain": "finance_receipt",
        "product_domain_label": "收款管理",
    },
    "smart_construction_core.menu_sc_engineering_progress_income": {
        "path_domain": "收款管理",
        "integration_target": "sc.receipt.income 收款登记",
        "product_domain": "finance_receipt",
        "product_domain_label": "收款管理",
    },
    "smart_construction_core.menu_sc_arrival_confirmation": {
        "path_domain": "收款管理",
        "product_domain": "finance_receipt",
        "product_domain_label": "收款管理",
    },
    "smart_construction_core.menu_sc_user_payment_apply": {
        "path_domain": "付款管理",
        "integration_target": "payment.request 收付款申请",
        "product_domain": "finance_payment",
        "product_domain_label": "付款管理",
    },
    "smart_construction_core.menu_sc_company_finance_expense": {
        "path_domain": "付款管理",
        "integration_target": "sc.payment.execution 付款执行",
        "product_domain": "finance_payment",
        "product_domain_label": "付款管理",
    },
    "smart_construction_core.menu_sc_partner_payment": {
        "path_domain": "付款管理",
        "integration_target": "sc.payment.execution 付款执行",
        "product_domain": "finance_payment",
        "product_domain_label": "付款管理",
    },
    "smart_construction_core.menu_sc_contractor_project_borrow": {
        "path_domain": "借还款",
        "integration_target": "sc.financing.loan 借款登记",
        "product_domain": "finance_loan",
        "product_domain_label": "借还款",
    },
    "smart_construction_core.menu_sc_project_borrow_company": {
        "path_domain": "借还款",
        "integration_target": "sc.financing.loan 借款登记",
        "product_domain": "finance_loan",
        "product_domain_label": "借还款",
    },
    "smart_construction_core.menu_sc_contractor_project_repay": {
        "path_domain": "借还款",
        "integration_target": "sc.expense.claim 还款登记",
        "product_domain": "finance_loan",
        "product_domain_label": "借还款",
    },
    "smart_construction_core.menu_sc_project_repay_company": {
        "path_domain": "借还款",
        "integration_target": "sc.expense.claim 还款登记",
        "product_domain": "finance_loan",
        "product_domain_label": "借还款",
    },
    "smart_construction_core.menu_sc_fund_daily_user_report": {
        "path_domain": "账户资金",
        "product_domain": "finance_account",
        "product_domain_label": "账户资金",
    },
    "smart_construction_core.menu_sc_fund_account_between_user": {
        "path_domain": "账户资金",
        "integration_target": "sc.fund.account.operation 账户资金操作",
        "product_domain": "finance_account",
        "product_domain_label": "账户资金",
    },
    "smart_construction_core.menu_sc_self_funding_advance_income": {
        "path_domain": "自筹资金",
        "integration_target": "sc.self.funding.registration 自筹垫付",
        "product_domain": "finance_self_funding",
        "product_domain_label": "自筹资金",
    },
    "smart_construction_core.menu_sc_self_funding_advance_refund": {
        "label": "自筹退回",
        "path_domain": "自筹资金",
        "integration_target": "sc.self.funding.registration 自筹退回",
        "product_domain": "finance_self_funding",
        "product_domain_label": "自筹资金",
    },
}
FINANCE_CASH_NONCASH_PRODUCT_MENU_OVERRIDES = {
    "smart_construction_core.menu_sc_deduction_bill": {
        "label": "扣款登记",
        "visible_menu_path": "智慧施工管理平台 / 财务中心 / 扣款与非现金 / 扣款登记",
        "product_domain": "finance_noncash",
        "product_domain_label": "扣款与非现金",
        "entry_intent": "handling",
        "entry_intent_label": "办理",
        "fact_model": "sc.expense.claim",
        "disposition_policy": "keep_list_form",
        "integration_target": "sc.expense.claim 扣款登记",
        "default_business_category_code": "finance.deduction.bill",
        "allowed_business_category_codes": ["finance.deduction.bill"],
        "required_relationships": ["project_id", "partner_id"],
        "entry_target_policy": "keep_list_form",
        "locked_data_policy": "read_only_source_facts_no_rewrite",
        "productization_source": "finance_cash_noncash_menu_split",
        "business_entry_contract_version": "business_entry_disposition.v1",
    },
    "smart_construction_core.menu_sc_reimbursement_request": {
        "visible_menu_path": "智慧施工管理平台 / 财务中心 / 费用与保证金 / 报销申请",
        "product_domain": "finance_cash",
        "product_domain_label": "费用与保证金",
    },
    "smart_construction_core.menu_sc_project_expense_claim": {
        "visible_menu_path": "智慧施工管理平台 / 财务中心 / 费用与保证金 / 项目费用报销单",
        "product_domain": "finance_cash",
        "product_domain_label": "费用与保证金",
    },
    "smart_construction_core.menu_sc_deduction_paid": {
        "visible_menu_path": "智慧施工管理平台 / 财务中心 / 费用与保证金 / 扣款实缴登记",
        "product_domain": "finance_cash",
        "product_domain_label": "费用与保证金",
        "disposition_policy": "keep_list_form",
        "integration_target": "sc.expense.claim 扣款实缴登记",
        "allowed_business_category_codes": ["finance.deduction.paid"],
        "entry_target_policy": "keep_list_form",
        "productization_source": "finance_cash_noncash_menu_split",
    },
    "smart_construction_core.menu_sc_deduction_paid_refund": {
        "visible_menu_path": "智慧施工管理平台 / 财务中心 / 费用与保证金 / 扣款实缴退回",
        "product_domain": "finance_cash",
        "product_domain_label": "费用与保证金",
        "disposition_policy": "keep_list_form",
        "integration_target": "sc.expense.claim 扣款实缴退回",
        "allowed_business_category_codes": ["finance.deduction.refund"],
        "entry_target_policy": "keep_list_form",
        "productization_source": "finance_cash_noncash_menu_split",
    },
}
FINANCE_CASH_EXPENSE_DEPOSIT_TARGET = "sc.expense.claim 费用/保证金申请"
FINANCE_CASH_EXPENSE_DEPOSIT_CATEGORY_CODES = {
    "finance.expense.reimbursement",
    "finance.expense.project",
    "finance.deposit.bid.pay",
    "finance.deposit.bid.return",
    "finance.deposit.contract.pay",
    "finance.deposit.contract.return",
}
FINANCE_DEDUCTION_CATEGORY_CODES = {
    "finance.deduction.bill",
    "finance.deduction.paid",
    "finance.deduction.refund",
}
FINANCE_DEPRECATED_CASH_CATEGORY_CODES = {
    "finance.deposit.self_funding.return",
}
USER_ACCEPTANCE_MENU_KEY_TOKENS = (
    "_acceptance",
    "user_acceptance",
)

INTERNAL_CONFIG_ONLY_GROUP_XMLIDS = {
    "base.group_no_one",
    "smart_core.group_smart_core_admin",
    "smart_construction_core.group_sc_cap_config_admin",
}

USER_CONFIRMED_POLICY_LOCK_NOTE = "user_confirmed_formal_menu_policy_62_locked"
USER_CONFIRMED_POLICY_BASELINE_PATHS = (
    "/mnt/scripts/verify/baselines/user_confirmed_formal_menu_policy_62.json",
    "scripts/verify/baselines/user_confirmed_formal_menu_policy_62.json",
)
USER_CONFIRMED_ENTRY_MATRIX_SCRIPT_PATHS = (
    "/mnt/scripts/verify/user_confirmed_62_business_entry_integration_matrix.py",
    "scripts/verify/user_confirmed_62_business_entry_integration_matrix.py",
)
USER_CONFIRMED_FORMAL_HIDDEN_GROUP_LABELS = {"用户核对菜单", "用户验收", "用户数据验收"}
CONFIG_CENTER_GROUP_LABEL = "配置中心"
CONFIG_CENTER_BUSINESS_BASE_LABEL = "业务基础数据"
CONFIG_CENTER_LOWCODING_LABEL = "低代码系统配置"
LEGACY_CONFIG_GROUP_LABELS = {"基础设置", "系统设置", "业务配置"}
CONFIG_CENTER_LOWCODING_MENU_XMLIDS = {
    "smart_construction_core.menu_sc_business_config_workbench",
    "smart_construction_core.menu_ui_menu_config_policy_business_config",
    "smart_construction_core.menu_ui_form_field_policy_business_config",
    "smart_construction_core.menu_ui_form_custom_field_wizard_business_config",
}
CONFIG_CENTER_BUSINESS_BASE_MENU_XMLIDS = {
    "smart_construction_core.menu_sc_business_category",
    "smart_construction_core.menu_sc_dictionary",
    "smart_construction_core.menu_sc_organization_department",
    "smart_construction_core.menu_sc_approval_scope",
    "smart_construction_core.menu_sc_approval_policy",
    "smart_construction_core.menu_sc_project_stage_requirement_items",
    "smart_construction_core.menu_sc_project_cost_code",
    "smart_construction_core.menu_sc_company_document_archive",
}
CONFIG_CENTER_INTERNAL_INCUBATING_MENU_XMLID_TOKENS = {
    "menu_project_quota",
    "menu_sc_dictionary_root",
    "menu_sc_dictionary_all",
    "menu_sc_dictionary_discipline",
    "menu_sc_dictionary_chapter",
    "menu_sc_dictionary_quota_item",
    "menu_sc_dictionary_sub_item",
    "menu_quota_import_wizard",
}
USER_CONFIRMED_FORMAL_VISIBLE_PARENT_XMLIDS = {
    "smart_construction_core.menu_sc_material_management_group",
    "smart_construction_core.menu_sc_labor_management_group",
    "smart_construction_core.menu_sc_equipment_management_group",
    "smart_construction_core.menu_sc_subcontract_management_group",
}
USER_CONFIRMED_FORMAL_HIDE_PATH_TOKENS = (
    "/用户验收",
    "/用户数据验收",
    "/用户核对菜单",
)
USER_CONFIRMED_FORMAL_HIDE_MENU_XMLIDS = (
    "smart_construction_core.menu_legacy_direct_direct_project_acceptance_root",
    "smart_construction_core.menu_legacy_direct_acceptance_engineering_progress_receipt",
)
USER_CONFIRMED_FORMAL_DEPRECATED_MENU_XMLIDS = {
    "smart_construction_core.menu_sc_self_funding_deposit",
    "smart_construction_core.menu_sc_self_funding_deposit_refund",
    "smart_construction_core.menu_legacy_55_user_acceptance_180_自筹保证金",
    "smart_construction_core.menu_legacy_55_user_acceptance_190_自筹保证金退回",
    "smart_construction_core.menu_sc_salary_registration",
}
MERGE_BY_CATEGORY_INTEGRATION_ACTION_XMLIDS_BY_MODEL = {
    "construction.contract": "smart_construction_core.action_construction_contract_handling",
    "construction.contract.income": "smart_construction_core.action_construction_contract_income",
    "construction.contract.expense": "smart_construction_core.action_construction_contract_expense",
    "sc.settlement.order": "smart_construction_core.action_sc_settlement_order",
    "sc.labor.usage": "smart_construction_core.action_sc_labor_usage",
    "sc.material.outbound": "smart_construction_core.action_sc_material_outbound",
    "sc.receipt.income": "smart_construction_core.action_sc_receipt_income",
    "payment.request": "smart_construction_core.action_payment_request",
    "sc.payment.execution": "smart_construction_core.action_sc_payment_execution",
    "sc.expense.claim": "smart_construction_core.action_sc_expense_claim",
    "sc.financing.loan": "smart_construction_core.action_sc_financing_loan",
    "sc.invoice.registration": "smart_construction_core.action_sc_invoice_registration",
    "sc.self.funding.registration": "smart_construction_core.action_sc_self_funding_registration",
}
SELF_FUNDING_REFUND_MENU_XMLID = "smart_construction_core.menu_sc_self_funding_advance_refund"
SELF_FUNDING_REFUND_CODE = "finance.self_funding.refund"

CONTRACT_HANDLING_CATEGORY_CODES = (
    "contract.income",
    "contract.income.supplement",
    "contract.expense",
    "contract.expense.supplement",
)


def _text(value):
    return str(value or "").strip()


def _is_user_acceptance_menu_key(value):
    key = _text(value)
    return key in USER_ACCEPTANCE_PRODUCT_MENU_XMLIDS or any(token in key for token in USER_ACCEPTANCE_MENU_KEY_TOKENS)


def _integration_model_from_target(target):
    first_token = _text(target).split(" ", 1)[0].split("/", 1)[0]
    if first_token in MERGE_BY_CATEGORY_INTEGRATION_ACTION_XMLIDS_BY_MODEL:
        return first_token
    return ""


class ScProductPolicy(models.Model):
    _inherit = "sc.product.policy"

    @api.model
    def _resolve_or_create_formal_initialization_action(self, action_xmlid):
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if action:
            return action
        spec = FORMAL_INITIALIZATION_ACTION_SPECS.get(action_xmlid)
        if not spec:
            return False
        model_name = _text(spec.get("res_model"))
        if model_name not in self.env:
            raise LockedMenuPolicyContractError(
                "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
                f"missing action model {model_name}",
            )
        module, name = action_xmlid.split(".", 1)
        action = self.env["ir.actions.act_window"].sudo().create(
            {
                "name": _text(spec.get("name")),
                "res_model": model_name,
                "view_mode": "tree,form",
                "domain": _text(spec.get("domain")) or "[]",
                "context": _text(spec.get("context")) or "{}",
            }
        )
        self.env["ir.model.data"].sudo().create(
            {
                "module": module,
                "name": name,
                "model": action._name,
                "res_id": action.id,
                "noupdate": True,
            }
        )
        return action

    @api.model
    def synchronize_locked_formal_menu_policy(
        self,
        product_key,
        *,
        baseline_path=None,
        checksum_path=None,
    ):
        """Converge one formal construction policy without catalog fallback."""
        product_key = _text(product_key)
        contract = load_locked_menu_policy_contract(
            baseline_path=baseline_path,
            checksum_path=checksum_path,
        )
        product = contract["products"].get(product_key)
        if not isinstance(product, dict):
            raise LockedMenuPolicyContractError("LOCKED_MENU_BASELINE_PRODUCT_MISMATCH", product_key)

        menu_groups = []
        for group in product.get("menu_groups") or []:
            legacy_label = _text(group.get("group_label") or group.get("label") or group.get("title"))
            group_label = canonical_group_label(legacy_label)
            next_group = dict(group)
            next_group.update(
                {
                    "group_label": group_label,
                    "group_key": "construction.%s" % group_label,
                    "label": group_label,
                    "title": group_label,
                }
            )
            menus = []
            for menu in group.get("menus") or []:
                row = dict(menu)
                menu_xmlid = _text(row.get("menu_xmlid") or row.get("page_key") or row.get("menu_key"))
                action_xmlid = _text(row.get("action_xmlid")) or FORMAL_ACTION_ONLY_MENU_TARGETS.get(menu_xmlid, "")
                if FORMAL_BUSINESS_DECISION_REQUIRED_TARGETS.get(menu_xmlid) == action_xmlid:
                    raise LockedMenuPolicyContractError(
                        "BUSINESS_DECISION_REQUIRED",
                        f"{product_key} unresolved disposition {menu_xmlid} -> {action_xmlid}",
                    )
                menu_rec = self.env.ref(menu_xmlid, raise_if_not_found=False) if menu_xmlid else False
                action = menu_rec.action if menu_rec else (
                    self._resolve_or_create_formal_initialization_action(action_xmlid) if action_xmlid else False
                )
                if not menu_rec and not action_xmlid:
                    raise LockedMenuPolicyContractError(
                        "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
                        f"{product_key} unresolved menu without stable action target {menu_xmlid}",
                    )
                if (
                    hasattr(menu_rec, "active")
                    and not menu_rec.active
                    and menu_xmlid not in LOCKED_TARGET_UNPUBLISHED_MENU_XMLIDS
                ):
                    menu_rec.sudo().write({"active": True})
                if not action:
                    raise LockedMenuPolicyContractError(
                        "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
                        f"{product_key} unresolved action {action_xmlid or menu_xmlid}",
                    )
                resolved_action_xmlid = action.get_external_id().get(action.id, "") or ""
                if action_xmlid and resolved_action_xmlid != action_xmlid:
                    raise LockedMenuPolicyContractError(
                        "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
                        f"{product_key} action identity mismatch {menu_xmlid}",
                    )
                action_id = int(action.id or 0)
                menu_id = int(menu_rec.id or 0) if menu_rec else 0
                action_res_model = _text(getattr(action, "res_model", ""))
                locked_res_model = _text(row.get("res_model") or row.get("model"))
                if locked_res_model and action_res_model != locked_res_model:
                    raise LockedMenuPolicyContractError(
                        "LOCKED_MENU_BASELINE_NORMALIZATION_MISMATCH",
                        f"{product_key} action model mismatch {menu_xmlid}",
                    )
                res_model = action_res_model or locked_res_model
                route = "/a/%s?menu_id=%s" % (action_id, menu_id) if menu_id else "/a/%s" % action_id
                row.update(
                    {
                        "menu_xmlid": menu_xmlid,
                        "menu_key": menu_xmlid,
                        "page_key": menu_xmlid,
                        "menu_id": menu_id,
                        "action_id": action_id,
                        "action_xmlid": resolved_action_xmlid,
                        "route": route,
                        "res_model": res_model,
                        "model": res_model,
                        "enabled": True,
                        "release_state": "released",
                        "access_level": "public",
                    }
                )
                row.pop("id", None)
                menus.append(row)
            next_group["menus"] = menus
            menu_groups.append(next_group)

        capabilities = self._capabilities_from_user_confirmed_menu_groups(menu_groups)

        values = {
            "active": True,
            "product_key": product_key,
            "base_product_key": _text(product.get("base_product_key")) or "construction",
            "edition_key": _text(product.get("edition_key")) or product_key.split(".", 1)[1],
            "state": _text(product.get("state")) or ("preview" if product_key.endswith(".preview") else "stable"),
            "access_level": "public",
            "allowed_role_codes": product.get("allowed_role_codes") if isinstance(product.get("allowed_role_codes"), list) else [],
            "label": _text(product.get("label")) or product_key,
            "version": _text(product.get("version")) or "v1",
            "scene_version_bindings": product.get("scene_version_bindings") if isinstance(product.get("scene_version_bindings"), dict) else {},
            "menu_groups": menu_groups,
            "scenes": product.get("scenes") if isinstance(product.get("scenes"), list) else [],
            "capabilities": capabilities,
            "note": "synchronized from versioned locked formal menu policy baseline",
        }
        rec = self.sudo().search([("product_key", "=", product_key)], limit=1)
        if rec:
            changed = any(rec[field_name] != field_value for field_name, field_value in values.items())
            if changed:
                rec.write(values)
        else:
            rec = self.sudo().create(values)
            changed = True
        match = assert_policy_matches_locked_contract(contract, product_key, rec.menu_groups)
        return {
            "policy": rec,
            "contract": contract,
            "changed": changed,
            "match": match,
        }

    @api.model
    def sync_construction_menu_product_policies(self):
        self._ensure_formal_product_navigation_runtime_params()
        for product_key in ("construction.standard", "construction.preview"):
            self.synchronize_locked_formal_menu_policy(product_key)
        return True

    @api.model
    def _ensure_formal_product_navigation_runtime_params(self):
        Param = self.env["ir.config_parameter"].sudo()
        Param.set_param(NAV_USER_DATA_ACCEPTANCE_ONLY_PARAM, "0")
        Param.set_param(MENU_CONFIG_NAV_ENABLED_PARAM, "1")
        return True

    @api.model
    def _load_user_confirmed_entry_matrix_index(self):
        candidates = []
        for raw_path in USER_CONFIRMED_ENTRY_MATRIX_SCRIPT_PATHS:
            path = Path(raw_path)
            if not path.is_absolute():
                path = Path(__file__).resolve().parents[4] / path
            candidates.append(path)
        for path in candidates:
            if not path.is_file():
                continue
            try:
                spec = importlib.util.spec_from_file_location("user_confirmed_business_entry_matrix_runtime", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                payload = module._build_matrix()
            except Exception:
                continue
            rows = payload.get("rows") if isinstance(payload, dict) else []
            index = {}
            for row in rows:
                if not isinstance(row, dict):
                    continue
                menu_xmlid = _text(row.get("menu_xmlid"))
                if menu_xmlid:
                    index[menu_xmlid] = row
            if index:
                return index
        return {}

    @api.model
    def _annotate_user_confirmed_business_entry(self, row, matrix_index):
        if not isinstance(row, dict):
            return row
        menu_xmlid = _text(row.get("menu_xmlid") or row.get("page_key") or row.get("menu_key"))
        matrix = matrix_index.get(menu_xmlid) if isinstance(matrix_index, dict) else None
        if not isinstance(matrix, dict):
            self._normalize_self_funding_refund_business_entry(row)
            return row
        next_row = dict(row)
        category_code = _text(matrix.get("default_business_category_code"))
        product_domain = _text(matrix.get("product_domain"))
        entry_intent = _text(matrix.get("entry_intent"))
        disposition_policy = _text(matrix.get("disposition_policy"))
        integration_target = _text(matrix.get("integration_target"))
        next_row.update(
            {
                "product_domain": product_domain,
                "product_domain_label": _text(matrix.get("product_domain_label")),
                "entry_intent": entry_intent,
                "entry_intent_label": _text(matrix.get("entry_intent_label")),
                "fact_model": _text(matrix.get("fact_model") or matrix.get("model")),
                "disposition_policy": disposition_policy,
                "integration_target": integration_target,
                "default_business_category_code": category_code,
                "allowed_business_category_codes": matrix.get("allowed_business_category_codes") if isinstance(matrix.get("allowed_business_category_codes"), list) else [],
                "required_relationships": matrix.get("required_relationships") if isinstance(matrix.get("required_relationships"), list) else [],
                "locked_data_policy": _text(matrix.get("locked_data_policy")) or "read_only_source_facts_no_rewrite",
                "productization_source": "user_confirmed_62_business_entry_integration_matrix",
                "business_entry_contract_version": "business_entry_disposition.v1",
            }
        )
        if category_code:
            next_row.setdefault("context_defaults", {})
            if isinstance(next_row["context_defaults"], dict):
                next_row["context_defaults"].setdefault("default_business_category_code", category_code)
        if disposition_policy == "merge_by_category":
            next_row["entry_target_policy"] = "merge_to_list_form_by_business_category"
            self._annotate_merge_by_category_integration_target(next_row)
        elif entry_intent in {"query", "analysis", "config", "master_data", "source_fact"}:
            next_row["entry_target_policy"] = "keep_separate_%s" % entry_intent
        else:
            next_row["entry_target_policy"] = "keep_list_form"
        self._normalize_contract_handling_business_entry(next_row)
        self._normalize_self_funding_refund_business_entry(next_row)
        return next_row

    @api.model
    def _normalize_self_funding_refund_business_entry(self, row):
        if not isinstance(row, dict):
            return row
        menu_xmlid = _text(row.get("menu_xmlid") or row.get("page_key") or row.get("menu_key"))
        if menu_xmlid != SELF_FUNDING_REFUND_MENU_XMLID:
            return row
        row.update(
            {
                "label": "自筹退回办理",
                "page_label": "自筹退回办理",
                "product_domain": "finance",
                "product_domain_label": "资金财务域",
                "entry_intent": "handling",
                "entry_intent_label": "办理",
                "fact_model": "sc.self.funding.registration",
                "disposition_policy": "merge_by_category",
                "integration_target": "sc.self.funding.registration 自筹退回办理",
                "default_business_category_code": SELF_FUNDING_REFUND_CODE,
                "allowed_business_category_codes": [SELF_FUNDING_REFUND_CODE],
                "required_relationships": ["project_id", "partner_id"],
                "entry_target_policy": "merge_to_list_form_by_business_category",
                "locked_data_policy": "read_only_source_facts_no_rewrite",
                "productization_source": "self_funding_refund_formal_entry",
                "policy_note": "self_funding_refund_uses_formal_registration_caliber",
                "business_entry_contract_version": "business_entry_disposition.v1",
                "visible_menu_path": "智慧施工管理平台 / 财务中心 / 自筹退回办理",
            }
        )
        context_defaults = row.setdefault("context_defaults", {})
        if isinstance(context_defaults, dict):
            context_defaults.clear()
            context_defaults["default_funding_type"] = "refund"
            context_defaults["default_business_category_code"] = SELF_FUNDING_REFUND_CODE
            context_defaults["allowed_business_category_codes"] = [SELF_FUNDING_REFUND_CODE]
        self._annotate_merge_by_category_integration_target(row)
        action = self.env.ref("smart_construction_core.action_sc_self_funding_registration_refund", raise_if_not_found=False)
        if action and _text(getattr(action, "res_model", "")) == "sc.self.funding.registration":
            action_id = int(action.id or 0)
            view_modes = [_text(item) for item in _text(getattr(action, "view_mode", "")).split(",") if _text(item)]
            row["integration_action_xmlid"] = "smart_construction_core.action_sc_self_funding_registration_refund"
            row["integration_action_id"] = action_id
            row["integration_view_modes"] = view_modes
            row["integration_entry_target"] = {
                "type": "compatibility",
                "route": "/a/%s" % action_id,
                "compatibility_refs": {
                    "action_id": action_id,
                    "model": "sc.self.funding.registration",
                    "view_modes": view_modes,
                    "delivery_mode": "merge_by_category_integration",
                },
            }
        return row

    @api.model
    def _normalize_contract_handling_business_entry(self, row):
        if not isinstance(row, dict):
            return row
        category_code = _text(row.get("default_business_category_code"))
        allowed_codes = row.get("allowed_business_category_codes") if isinstance(row.get("allowed_business_category_codes"), list) else []
        menu_xmlid = _text(row.get("menu_xmlid") or row.get("page_key") or row.get("menu_key"))
        is_contract_category = category_code in CONTRACT_HANDLING_CATEGORY_CODES or any(
            _text(code) in CONTRACT_HANDLING_CATEGORY_CODES for code in allowed_codes
        )
        is_contract_execution_menu = menu_xmlid in {
            "smart_construction_core.menu_sc_construction_contract",
            "smart_construction_core.menu_sc_contract_handling",
            "smart_construction_core.menu_sc_income_contract_execution",
            "smart_construction_core.menu_sc_expense_contract_execution",
            "smart_construction_core.menu_sc_expense_contract_supplement",
        }
        if not (is_contract_category or is_contract_execution_menu):
            return row
        if not category_code:
            category_code = "contract.income"
        row.update(
            {
                "label": "合同办理",
                "page_label": "合同办理",
                "product_domain": "contract",
                "product_domain_label": "合同结算域",
                "entry_intent": "handling",
                "entry_intent_label": "办理",
                "fact_model": "construction.contract",
                "res_model": "construction.contract",
                "model": "construction.contract",
                "disposition_policy": "merge_by_category",
                "integration_target": "construction.contract 合同办理",
                "default_business_category_code": category_code,
                "allowed_business_category_codes": [category_code],
                "required_relationships": ["project_id", "partner_id"],
                "entry_target_policy": "merge_to_list_form_by_business_category",
                "locked_data_policy": "read_only_source_facts_no_rewrite",
                "productization_source": "contract_handling_product_consolidation",
                "business_entry_contract_version": "business_entry_disposition.v1",
            }
        )
        context_defaults = row.setdefault("context_defaults", {})
        if isinstance(context_defaults, dict):
            context_defaults["default_business_category_code"] = category_code
            if category_code in {"contract.income", "contract.income.supplement"}:
                context_defaults["default_type"] = "out"
            elif category_code in {"contract.expense", "contract.expense.supplement"}:
                context_defaults["default_type"] = "in"
        self._annotate_merge_by_category_integration_target(row)
        return row

    @api.model
    def _annotate_merge_by_category_integration_target(self, row):
        source_model = _text(row.get("fact_model") or row.get("res_model"))
        integration_model = _integration_model_from_target(row.get("integration_target")) or source_model
        action_xmlid = MERGE_BY_CATEGORY_INTEGRATION_ACTION_XMLIDS_BY_MODEL.get(integration_model)
        if not action_xmlid:
            return row
        action = self.env.ref(action_xmlid, raise_if_not_found=False)
        if not action or _text(getattr(action, "res_model", "")) != integration_model:
            return row
        action_id = int(action.id or 0)
        if action_id <= 0:
            return row
        view_modes = [_text(item) for item in _text(getattr(action, "view_mode", "")).split(",") if _text(item)]
        row["integration_model"] = integration_model
        row["integration_action_xmlid"] = action_xmlid
        row["integration_action_id"] = action_id
        row["integration_view_modes"] = view_modes
        row["integration_entry_target"] = {
            "type": "compatibility",
            "route": "/a/%s" % action_id,
            "compatibility_refs": {
                "action_id": action_id,
                "model": integration_model,
                "view_modes": view_modes,
                "delivery_mode": "merge_by_category_integration",
            },
        }
        return row

    @api.model
    def _capabilities_from_user_confirmed_menu_groups(self, menu_groups):
        capabilities = []
        seen = set()
        for group in menu_groups or []:
            if not isinstance(group, dict):
                continue
            group_key = _text(group.get("group_key")) or _text(group.get("group_label")) or "construction.locked"
            group_label = _text(group.get("group_label")) or group_key
            for menu in group.get("menus") or []:
                if not isinstance(menu, dict):
                    continue
                page_key = _text(menu.get("page_key") or menu.get("menu_xmlid") or menu.get("menu_key"))
                if not page_key or page_key in seen:
                    continue
                seen.add(page_key)
                capabilities.append(
                    {
                        "capability_key": _text(menu.get("capability_key")) or "construction.menu.%s" % page_key.replace(".", "_"),
                        "label": _text(menu.get("label") or menu.get("page_label")) or page_key,
                        "group_key": group_key,
                        "group_label": group_label,
                        "target_scene_key": _text(menu.get("target_scene_key")),
                        "target_page_key": page_key,
                        "product_key": _text(menu.get("product_key")),
                        "delivery_level": "exclusive",
                        "entry_kind": "user_visible_menu_page",
                        "visible_menu_path": _text(menu.get("visible_menu_path")),
                        "enabled": bool(menu.get("enabled", True)),
                        "release_state": _text(menu.get("release_state")) or "released",
                        "access_level": _text(menu.get("access_level")) or "public",
                        "control_object": "用户已确认正式菜单页面",
                        "source_kind": "user_confirmed_menu_policy_baseline",
                        "menu_xmlid": _text(menu.get("menu_xmlid") or page_key),
                        "action_id": int(menu.get("action_id") or 0),
                        "res_model": _text(menu.get("res_model")),
                        "product_domain": _text(menu.get("product_domain")),
                        "entry_intent": _text(menu.get("entry_intent")),
                        "disposition_policy": _text(menu.get("disposition_policy")),
                        "integration_target": _text(menu.get("integration_target")),
                        "default_business_category_code": _text(menu.get("default_business_category_code")),
                        "allowed_business_category_codes": menu.get("allowed_business_category_codes") if isinstance(menu.get("allowed_business_category_codes"), list) else [],
                        "entry_target_policy": _text(menu.get("entry_target_policy")),
                    }
                )
        return capabilities

    @api.model
    def _is_user_confirmed_formal_group(self, group):
        if not isinstance(group, dict):
            return False
        label = _text(group.get("group_label") or group.get("label") or group.get("title"))
        key = _text(group.get("group_key") or group.get("key"))
        return label not in USER_CONFIRMED_FORMAL_HIDDEN_GROUP_LABELS and "acceptance" not in key.lower()

    @api.model
    def _canonical_formal_product_group_label(self, label):
        label = _text(label)
        if label in LEGACY_CONFIG_GROUP_LABELS:
            return CONFIG_CENTER_GROUP_LABEL
        return label

    @api.model
    def _converge_visible_product_menu_information_architecture(self, menu_groups):
        """Project the released policy into the productized navigation v2 tree.

        The locked baseline remains the page-identity authority.  This method
        changes only presentation grouping and visible paths, preserving menu
        XMLIDs, actions, permissions and business semantics.
        """
        group_projection = {
            "基础资料": ("组织行政", "基础资料"),
            "人事行政": ("组织行政", "人事薪酬"),
            "资料证照": ("组织行政", "资料证照"),
        }
        admin_approval_xmlids = {
            "smart_construction_core.menu_sc_leave_request",
            "smart_construction_core.menu_sc_seal_use_request",
        }
        project_level_two_by_xmlid = {
            "smart_construction_core.menu_sc_project_project": "项目台账",
            "smart_construction_core.menu_sc_tender_registration": "项目前期",
            "smart_construction_core.menu_sc_tender_registration_fee": "项目前期",
        }
        ordered_labels = (
            "项目中心",
            "合同中心",
            "成本中心",
            "物资与分包",
            "施工管理",
            "财务中心",
            "税务中心",
            "报表中心",
            "组织行政",
            CONFIG_CENTER_GROUP_LABEL,
        )
        merged = {}
        order = []
        for group in menu_groups or []:
            if not isinstance(group, dict):
                continue
            legacy_label = _text(group.get("group_label") or group.get("label") or group.get("title"))
            target_label, default_domain = group_projection.get(legacy_label, (legacy_label, ""))
            if target_label not in merged:
                next_group = dict(group)
                next_group.update(
                    {
                        "group_key": "construction.%s" % target_label,
                        "group_label": target_label,
                        "label": target_label,
                        "title": target_label,
                        "menus": [],
                    }
                )
                merged[target_label] = next_group
                order.append(target_label)
            target_group = merged[target_label]
            for menu in group.get("menus") or []:
                if not isinstance(menu, dict):
                    continue
                next_menu = dict(menu)
                menu_xmlid = _text(next_menu.get("menu_xmlid") or next_menu.get("page_key") or next_menu.get("menu_key"))
                label = _text(next_menu.get("label") or next_menu.get("page_label"))
                domain = default_domain
                if legacy_label == "人事行政" and menu_xmlid in admin_approval_xmlids:
                    domain = "行政审批"
                if target_label == "项目中心" and menu_xmlid in project_level_two_by_xmlid:
                    domain = project_level_two_by_xmlid[menu_xmlid]
                    next_menu["visible_menu_path"] = " / ".join(
                        part for part in ("智慧施工管理平台", target_label, domain, label) if part
                    )
                    next_menu["policy_note"] = "project_center_locked_level_two_projection"
                if target_label != legacy_label:
                    next_menu["product_key"] = target_label
                    next_menu["visible_menu_path"] = " / ".join(
                        part for part in ("智慧施工管理平台", target_label, domain, label) if part
                    )
                    next_menu["policy_note"] = "product_navigation_v2_visible_group_convergence"
                target_group["menus"].append(next_menu)
        return [merged[label] for label in ordered_labels if label in merged] + [
            merged[label] for label in order if label not in ordered_labels
        ]

    @api.model
    def _normalize_menu_for_canonical_group(self, menu, canonical_label, legacy_label=""):
        row = dict(menu or {})
        if canonical_label:
            row["product_key"] = canonical_label
        if legacy_label and canonical_label and legacy_label != canonical_label:
            for key in ("visible_menu_path", "menu_complete_name"):
                value = _text(row.get(key))
                if value:
                    row[key] = value.replace(" / %s /" % legacy_label, " / %s /" % canonical_label).replace(
                        "/%s/" % legacy_label,
                        "/%s/" % canonical_label,
                    )
        return row

    @api.model
    def _hydrate_user_confirmed_formal_menu(self, menu):
        row = dict(menu or {})
        menu_xmlid = _text(row.get("menu_xmlid") or row.get("page_key") or row.get("menu_key"))
        menu_record = self.env.ref(menu_xmlid, raise_if_not_found=False) if menu_xmlid else False
        if not menu_record:
            return row
        action = menu_record.action
        action_id = int(action.id or 0) if action else 0
        locked_res_model = _text(row.get("res_model"))
        res_model = locked_res_model or _text(getattr(action, "res_model", "") if action else "")
        view_modes = []
        if action and _text(getattr(action, "view_mode", "")):
            view_modes = [_text(item) for item in action.view_mode.split(",") if _text(item)]
        menu_is_active = bool(getattr(menu_record, "active", False))
        runtime_menu_id = int(menu_record.id) if menu_is_active else 0
        native_complete_name = _text(getattr(menu_record, "complete_name", ""))
        native_visible_path = " / ".join(
            part.strip() for part in native_complete_name.split("/") if part.strip()
        )
        runtime_route = ""
        if action_id:
            runtime_route = "/a/%s?menu_id=%s" % (action_id, runtime_menu_id) if runtime_menu_id else "/a/%s" % action_id
        row.update(
            {
                "menu_id": runtime_menu_id,
                "menu_xmlid": menu_xmlid,
                "menu_key": menu_xmlid,
                "page_key": menu_xmlid,
                "action_id": action_id or int(row.get("action_id") or 0),
                "res_model": res_model,
                "route": runtime_route or _text(row.get("route")),
                # The installed ir.ui.menu hierarchy is the navigation fact
                # authority. Release policy validates exposure; it must not
                # retain a stale flattened path after the native parent moves.
                "visible_menu_path": native_visible_path or _text(row.get("visible_menu_path")),
                "menu_complete_name": native_visible_path or _text(row.get("menu_complete_name")),
                "view_modes": view_modes or row.get("view_modes") or [],
                "enabled": True,
                "release_state": "released",
                "access_level": "public",
                "policy_note": "released_as_user_confirmed_formal_product_menu",
            }
        )
        return row

    @api.model
    def _normalize_config_center_product_menu_groups(self, menu_groups):
        out = []
        for group in menu_groups or []:
            if not isinstance(group, dict):
                continue
            group_label = _text(group.get("group_label") or group.get("label"))
            next_group = dict(group)
            menus = []
            for menu in group.get("menus") or []:
                if not isinstance(menu, dict):
                    continue
                next_menu = dict(menu)
                menu_xmlid = _text(next_menu.get("menu_xmlid") or next_menu.get("page_key") or next_menu.get("menu_key"))
                if any(token in menu_xmlid for token in CONFIG_CENTER_INTERNAL_INCUBATING_MENU_XMLID_TOKENS):
                    continue
                if group_label == CONFIG_CENTER_GROUP_LABEL:
                    label = _text(next_menu.get("label") or next_menu.get("page_label"))
                    subgroup = ""
                    if menu_xmlid in CONFIG_CENTER_LOWCODING_MENU_XMLIDS:
                        subgroup = CONFIG_CENTER_LOWCODING_LABEL
                        next_menu["product_domain"] = "lowcode_system_config"
                        next_menu["product_domain_label"] = CONFIG_CENTER_LOWCODING_LABEL
                        next_menu["entry_intent"] = "config"
                        next_menu["entry_intent_label"] = "配置"
                        next_menu["policy_note"] = "config_center_lowcode_system_config_grouped"
                    elif menu_xmlid in CONFIG_CENTER_BUSINESS_BASE_MENU_XMLIDS:
                        subgroup = CONFIG_CENTER_BUSINESS_BASE_LABEL
                        next_menu["product_domain"] = "business_base_data"
                        next_menu["product_domain_label"] = CONFIG_CENTER_BUSINESS_BASE_LABEL
                        next_menu["entry_intent"] = "master_data"
                        next_menu["entry_intent_label"] = "维护"
                        next_menu["policy_note"] = "config_center_business_base_data_grouped"
                    if subgroup and label:
                        next_menu["visible_menu_path"] = "智慧施工管理平台 / %s / %s / %s" % (
                            CONFIG_CENTER_GROUP_LABEL,
                            subgroup,
                            label,
                        )
                menus.append(next_menu)
            next_group["menus"] = menus
            out.append(next_group)
        return out

    @api.model
    def _consolidate_contract_handling_menu_entries(self, group):
        if not isinstance(group, dict):
            return group
        if _text(group.get("group_label") or group.get("label")) != "合同中心":
            return group

        old_handling_menu_xmlids = {
            "smart_construction_core.menu_sc_expense_contract_supplement",
            "smart_construction_core.menu_sc_income_contract_execution",
            "smart_construction_core.menu_sc_expense_contract_execution",
        }
        menus = [dict(menu) for menu in (group.get("menus") or []) if isinstance(menu, dict)]
        kept = []
        insertion_index = None
        for idx, menu in enumerate(menus):
            menu_xmlid = _text(menu.get("menu_xmlid") or menu.get("page_key") or menu.get("menu_key"))
            category_code = _text(menu.get("default_business_category_code"))
            if menu_xmlid in old_handling_menu_xmlids or category_code in CONTRACT_HANDLING_CATEGORY_CODES:
                if insertion_index is None:
                    insertion_index = len(kept)
                continue
            kept.append(menu)

        if insertion_index is None:
            group["menus"] = kept
            return group

        handling = self._hydrate_user_confirmed_formal_menu(
            {
                "label": "合同办理",
                "page_label": "合同办理",
                "menu_key": "smart_construction_core.menu_sc_construction_contract",
                "menu_xmlid": "smart_construction_core.menu_sc_construction_contract",
                "page_key": "smart_construction_core.menu_sc_construction_contract",
                "capability_key": "construction.menu.smart_construction_core_menu_sc_construction_contract",
                "product_key": "合同中心",
                "scene_key": "",
                "target_scene_key": "",
                "visible_menu_path": "智慧施工管理平台 / 合同中心 / 合同办理",
                "control_granularity": "user_visible_menu_page",
                "control_object": "用户已确认正式菜单页面",
                "source_kind": "contract_handling_product_consolidation",
                "res_model": "construction.contract",
            }
        )
        handling.update(
            {
                "label": "合同办理",
                "page_label": "合同办理",
                "res_model": "construction.contract",
                "fact_model": "construction.contract",
                "model": "construction.contract",
                "product_domain": "contract",
                "product_domain_label": "合同结算域",
                "entry_intent": "handling",
                "entry_intent_label": "办理",
                "disposition_policy": "merge_by_category",
                "integration_target": "construction.contract 合同办理",
                "default_business_category_code": "contract.income",
                "allowed_business_category_codes": list(CONTRACT_HANDLING_CATEGORY_CODES),
                "required_relationships": ["project_id", "partner_id"],
                "entry_target_policy": "merge_to_list_form_by_business_category",
                "locked_data_policy": "read_only_source_facts_no_rewrite",
                "productization_source": "contract_handling_product_consolidation",
                "business_entry_contract_version": "business_entry_disposition.v1",
                "context_defaults": {
                    "default_business_category_code": "contract.income",
                    "default_type": "out",
                    "allowed_business_category_codes": list(CONTRACT_HANDLING_CATEGORY_CODES),
                },
            }
        )
        self._annotate_merge_by_category_integration_target(handling)
        kept.insert(insertion_index, handling)
        group["menus"] = kept
        return group

    @api.model
    def _is_tax_center_menu(self, menu):
        if not isinstance(menu, dict):
            return False
        menu_xmlid = _text(menu.get("menu_xmlid") or menu.get("page_key") or menu.get("menu_key"))
        if menu_xmlid in TAX_CENTER_PRODUCT_MENU_XMLIDS:
            return True
        text = " ".join(
            _text(value)
            for value in (
                menu.get("label"),
                menu.get("page_label"),
                menu.get("visible_menu_path"),
                menu.get("product_domain"),
                menu.get("product_domain_label"),
                menu.get("default_business_category_code"),
                menu.get("integration_target"),
            )
            if _text(value)
        )
        return any(token in text for token in ("发票", "开票", "税款", "税额", "抵扣", "外经证", "税务"))

    @api.model
    def _move_tax_product_menus_to_tax_center(self, menu_groups):
        out = []
        tax_menus = []
        for group in menu_groups or []:
            if not isinstance(group, dict):
                continue
            group_label = _text(group.get("group_label") or group.get("label"))
            next_group = dict(group)
            menus = []
            for menu in group.get("menus") or []:
                if not isinstance(menu, dict):
                    continue
                next_menu = dict(menu)
                if group_label != "税务中心" and self._is_tax_center_menu(next_menu):
                    label = _text(next_menu.get("label") or next_menu.get("page_label"))
                    if _text(next_menu.get("integration_model") or next_menu.get("fact_model") or next_menu.get("res_model")) == "sc.invoice.registration":
                        next_menu["integration_target"] = "sc.invoice.registration 发票税务"
                    elif _text(next_menu.get("integration_model") or next_menu.get("fact_model") or next_menu.get("res_model")) == "sc.tax.deduction.registration":
                        next_menu["integration_target"] = "sc.tax.deduction.registration 抵扣登记"
                    next_menu.update(
                        {
                            "product_key": "税务中心",
                            "product_domain": "tax",
                            "product_domain_label": "发票税务",
                            "visible_menu_path": "智慧施工管理平台 / 税务中心 / %s" % (label or "税务业务"),
                            "policy_note": "tax_product_menu_split_from_finance_center",
                        }
                    )
                    tax_menus.append(next_menu)
                    continue
                menus.append(next_menu)
            next_group["menus"] = menus
            if menus or group_label != "财务中心":
                out.append(next_group)

        tax_group = None
        for group in out:
            if _text(group.get("group_label") or group.get("label")) == "税务中心":
                tax_group = group
                break
        if tax_group is None and tax_menus:
            tax_group = {
                "group_key": "construction.税务中心",
                "group_label": "税务中心",
                "category": "user_visible_menu",
                "menus": [],
            }
            out.append(tax_group)
        if tax_group is not None:
            existing = {
                _text(menu.get("menu_xmlid") or menu.get("page_key") or menu.get("menu_key"))
                for menu in tax_group.get("menus") or []
                if isinstance(menu, dict)
            }
            merged = [dict(menu) for menu in (tax_group.get("menus") or []) if isinstance(menu, dict)]
            for menu in tax_menus:
                key = _text(menu.get("menu_xmlid") or menu.get("page_key") or menu.get("menu_key"))
                if key and key in existing:
                    continue
                merged.append(menu)
                if key:
                    existing.add(key)
            tax_group["menus"] = merged
        return out

    @api.model
    def _normalize_product_menu_business_domains(self, menu_groups):
        out = []
        for group in menu_groups or []:
            if not isinstance(group, dict):
                continue
            group_label = _text(group.get("group_label") or group.get("label"))
            next_group = dict(group)
            menus = []
            for menu in group.get("menus") or []:
                if not isinstance(menu, dict):
                    continue
                next_menu = dict(menu)
                menu_xmlid = _text(next_menu.get("menu_xmlid") or next_menu.get("page_key") or next_menu.get("menu_key"))
                label = _text(next_menu.get("label") or next_menu.get("page_label"))

                if group_label == "合同中心" and label == "合同办理":
                    label = "施工合同"
                    next_menu.update(
                        {
                            "label": label,
                            "page_label": label,
                            "visible_menu_path": "智慧施工管理平台 / 合同中心 / 合同管理 / 施工合同",
                            "integration_target": "construction.contract 施工合同",
                            "product_domain": "contract",
                            "product_domain_label": "合同管理",
                            "policy_note": "product_menu_business_domain_normalized",
                        }
                    )
                    self._annotate_merge_by_category_integration_target(next_menu)

                override = PRODUCT_MENU_BUSINESS_DOMAIN_OVERRIDES.get(menu_xmlid)
                if override:
                    override_label = _text(override.get("label"))
                    if override_label:
                        next_menu["label"] = override_label
                        next_menu["page_label"] = override_label
                        label = override_label
                    path_domain = _text(override.get("path_domain"))
                    if path_domain and group_label:
                        next_menu["visible_menu_path"] = "智慧施工管理平台 / %s / %s / %s" % (
                            group_label,
                            path_domain,
                            _text(next_menu.get("label") or next_menu.get("page_label")) or path_domain,
                        )
                    for field in ("integration_target", "product_domain", "product_domain_label"):
                        if _text(override.get(field)):
                            next_menu[field] = _text(override.get(field))
                    next_menu["policy_note"] = "product_menu_business_domain_normalized"
                    if menu_xmlid != SELF_FUNDING_REFUND_MENU_XMLID:
                        self._annotate_merge_by_category_integration_target(next_menu)

                if group_label == "合同中心" and _text(next_menu.get("integration_target")) == "sc.settlement.order 结算办理":
                    next_menu["integration_target"] = "sc.settlement.order 合同结算"
                    self._annotate_merge_by_category_integration_target(next_menu)
                menus.append(next_menu)
            next_group["menus"] = menus
            out.append(next_group)
        return out

    @api.model
    def _apply_finance_cash_noncash_product_menu_overrides(self, menu_groups):
        out = []
        for group in menu_groups or []:
            if not isinstance(group, dict):
                continue
            next_group = dict(group)
            menus = []
            for menu in group.get("menus") or []:
                if not isinstance(menu, dict):
                    continue
                next_menu = dict(menu)
                menu_xmlid = _text(
                    next_menu.get("menu_xmlid")
                    or next_menu.get("page_key")
                    or next_menu.get("menu_key")
                )
                override = FINANCE_CASH_NONCASH_PRODUCT_MENU_OVERRIDES.get(menu_xmlid)
                if override:
                    next_menu.update(override)
                    label = _text(override.get("label"))
                    if label:
                        next_menu["page_label"] = label
                    next_menu["policy_note"] = "finance_cash_noncash_menu_split_released"
                if _text(next_menu.get("integration_target")) == "payment.request 收付款申请办理":
                    next_menu["integration_target"] = "payment.request 收付款申请"
                default_code = _text(next_menu.get("default_business_category_code"))
                allowed_codes = next_menu.get("allowed_business_category_codes")
                if isinstance(allowed_codes, list):
                    if default_code in FINANCE_DEDUCTION_CATEGORY_CODES:
                        next_menu["allowed_business_category_codes"] = [default_code]
                    else:
                        next_menu["allowed_business_category_codes"] = [
                            _text(code)
                            for code in allowed_codes
                            if _text(code)
                            and _text(code) not in FINANCE_DEDUCTION_CATEGORY_CODES
                            and _text(code) not in FINANCE_DEPRECATED_CASH_CATEGORY_CODES
                        ]
                next_allowed_codes = next_menu.get("allowed_business_category_codes")
                cash_codes = [
                    _text(code)
                    for code in (next_allowed_codes if isinstance(next_allowed_codes, list) else [default_code])
                    if _text(code) in FINANCE_CASH_EXPENSE_DEPOSIT_CATEGORY_CODES
                ]
                menu_xmlid = _text(next_menu.get("menu_xmlid") or next_menu.get("page_key") or next_menu.get("menu_key"))
                if (
                    cash_codes
                    and default_code not in FINANCE_DEDUCTION_CATEGORY_CODES
                    and menu_xmlid != SELF_FUNDING_REFUND_MENU_XMLID
                ):
                    label = _text(next_menu.get("label") or next_menu.get("page_label"))
                    if label:
                        next_menu["visible_menu_path"] = "智慧施工管理平台 / 财务中心 / 费用与保证金 / %s" % label
                    next_menu["product_domain"] = "finance_cash"
                    next_menu["product_domain_label"] = "费用与保证金"
                    next_menu["integration_target"] = FINANCE_CASH_EXPENSE_DEPOSIT_TARGET
                    next_menu["productization_source"] = "finance_cash_noncash_menu_split"
                    next_menu["policy_note"] = "finance_cash_expense_deposit_entry_retargeted"
                menus.append(next_menu)
            next_group["menus"] = menus
            out.append(next_group)
        return out

    @api.model
    def _sync_user_confirmed_formal_menu_overlay(self):
        Policy = self.env[MENU_CONFIG_POLICY_MODEL].sudo().with_context(active_test=False)
        Menu = self.env["ir.ui.menu"].sudo().with_context(active_test=False)

        def upsert(menu, visible, note):
            if not menu:
                return
            policy = Policy.search([("menu_id", "=", menu.id)], limit=1)
            values = {
                "menu_id": menu.id,
                "visible": bool(visible),
                "active": True,
                "note": note,
            }
            if policy:
                policy.write(values)
            else:
                Policy.create(values)

        for xmlid in USER_CONFIRMED_FORMAL_VISIBLE_PARENT_XMLIDS:
            upsert(self.env.ref(xmlid, raise_if_not_found=False), True, "user_confirmed_formal_parent_required_visible")

        for menu in Menu.search([]):
            complete_name = _text(menu.complete_name)
            if any(token in complete_name for token in USER_CONFIRMED_FORMAL_HIDE_PATH_TOKENS):
                upsert(menu, False, "user_confirmed_formal_release_hide_acceptance_surface")
        for xmlid in USER_CONFIRMED_FORMAL_HIDE_MENU_XMLIDS:
            upsert(self.env.ref(xmlid, raise_if_not_found=False), False, "user_confirmed_formal_release_hide_acceptance_surface")
        for xmlid in USER_CONFIRMED_FORMAL_DEPRECATED_MENU_XMLIDS:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            upsert(menu, False, "user_confirmed_formal_deprecated_self_funding_deposit_surface")
            if menu:
                menu.sudo().write({"active": False})

    @api.model
    def _apply_formal_contract_product_menu_domain(self, policy):
        if not policy:
            return False

        formal_domains = {
            xmlid: ("contract", "formal_contract_domain_user_acceptance_released")
            for xmlid in FORMAL_CONTRACT_PRODUCT_MENU_XMLIDS
        }
        formal_domains.update(
            {
                xmlid: ("settlement", "formal_settlement_domain_user_acceptance_released")
                for xmlid in FORMAL_SETTLEMENT_PRODUCT_MENU_XMLIDS
            }
        )

        def _menu_key(row):
            return _text(row.get("menu_xmlid") or row.get("page_key") or row.get("menu_key"))

        def _formal_domain(row_or_key):
            key = row_or_key if isinstance(row_or_key, str) else _menu_key(row_or_key)
            return formal_domains.get(key)

        def _is_user_acceptance(row):
            return _is_user_acceptance_menu_key(_menu_key(row))

        menu_groups = []
        for group in policy.menu_groups or []:
            if not isinstance(group, dict):
                continue
            next_group = dict(group)
            menus = []
            for menu in group.get("menus") or []:
                if not isinstance(menu, dict):
                    continue
                next_menu = dict(menu)
                formal_domain = _formal_domain(next_menu)
                if formal_domain:
                    release_domain, policy_note = formal_domain
                    next_menu.update(
                        {
                            "enabled": True,
                            "release_state": "released",
                            "access_level": "public",
                            "release_domain": release_domain,
                            "policy_note": policy_note,
                        }
                    )
                elif _is_user_acceptance(next_menu):
                    next_menu.update(
                        {
                            "enabled": True,
                            "release_state": "released",
                            "access_level": "public",
                            "release_domain": "user_acceptance",
                            "policy_note": "user_acceptance_surface_preserved_until_formal_domain_release",
                        }
                    )
                else:
                    next_menu.update(
                        {
                            "enabled": False,
                            "release_state": "hidden",
                            "release_domain": "pending_user_acceptance",
                            "policy_note": "hidden_until_domain_user_acceptance_release",
                        }
                    )
                menus.append(next_menu)
            next_group["menus"] = menus
            menu_groups.append(next_group)

        def _apply_release_state(rows):
            out = []
            for row in rows or []:
                if not isinstance(row, dict):
                    continue
                next_row = dict(row)
                page_key = _text(
                    next_row.get("menu_xmlid")
                    or next_row.get("target_page_key")
                    or next_row.get("page_key")
                    or next_row.get("menu_key")
                )
                formal_domain = _formal_domain(page_key)
                if formal_domain:
                    release_domain, _policy_note = formal_domain
                    next_row.update(
                        {
                            "enabled": True,
                            "release_state": "released",
                            "access_level": "public",
                            "release_domain": release_domain,
                        }
                    )
                elif _is_user_acceptance_menu_key(page_key):
                    next_row.update(
                        {
                            "enabled": True,
                            "release_state": "released",
                            "access_level": "public",
                            "release_domain": "user_acceptance",
                        }
                    )
                else:
                    next_row.update(
                        {
                            "enabled": False,
                            "release_state": "hidden",
                            "release_domain": "pending_user_acceptance",
                        }
                    )
                out.append(next_row)
            return out

        policy.write(
            {
                "menu_groups": menu_groups,
                "scenes": _apply_release_state(policy.scenes),
                "capabilities": _apply_release_state(policy.capabilities),
                "note": "formal product menus are released by domain; current released domains=contract,settlement; user acceptance surfaces remain visible",
            }
        )
        return True
