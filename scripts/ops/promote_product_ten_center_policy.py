#!/usr/bin/env python3
"""Project the locked P1 menu contract into the released product policy.

The product contract is authoritative for the complete product menu surface.
Delivery maturity is governed separately and must never make a contracted
menu disappear.  The separately approved current accounting foundation is
retained by the 2026-08-11 decision.  Native Odoo menu ancestry never becomes
a second product-navigation truth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "scripts/verify/baselines/formal_business_product_menu_policy_v1.json"
CHECKSUM = BASELINE.with_suffix(BASELINE.suffix + ".sha256")
PRODUCT_CONTRACT = ROOT / "config/product_menu_contract_v1.json"

TARGET_CENTERS = (
    "工作台", "项目中心", "合同中心", "成本中心", "财务中心",
    "税务中心", "会计账务中心", "报表中心", "行政中心", "产品配置",
)
LEGACY_SOURCE_CENTERS = frozenset({"物资与分包", "施工管理", "组织行政", "配置中心", "基础设置", "系统设置", "业务配置"})

# center, label, menu XMLID, action XMLID, model, path below center
RELEASED_MENU_BINDINGS = (
    ("工作台", "数据总览", "smart_construction_core.menu_sc_operating_metrics_project", "smart_construction_core.action_sc_operating_metrics_project", "sc.operating.metrics.project", ("数据总览",)),
    ("工作台", "项目看板", "smart_construction_core.menu_sc_project_kanban", "smart_construction_core.action_project_dashboard", "project.project", ("项目看板",)),
    ("工作台", "待办事项", "smart_construction_core.menu_sc_workbench_my_todo_fact", "smart_construction_core.action_sc_workbench_task_center", "sc.workbench.item", ("待办事项",)),
    ("工作台", "消息通知", "smart_construction_core.menu_sc_product_message_notification_v1", "smart_construction_core.action_sc_product_message_notification_v1", "mail.activity", ("消息通知",)),
    ("项目中心", "新项目立项", "smart_construction_core.menu_sc_project_initiation", "smart_construction_core.action_project_initiation", "project.project", ("项目创建", "新项目立项")),
    ("项目中心", "项目信息编辑", "smart_construction_core.menu_sc_product_project_edit_v1", "smart_construction_core.action_sc_product_project_edit_v1", "project.project", ("项目创建", "项目信息编辑")),
    ("项目中心", "项目启停管理", "smart_construction_core.menu_sc_product_project_lifecycle_v1", "smart_construction_core.action_sc_product_project_lifecycle_v1", "project.project", ("项目创建", "项目启停管理")),
    ("项目中心", "客户档案", "smart_construction_core.menu_sc_customer_partner", "smart_construction_core.action_sc_customer_partner", "res.partner", ("客商管理", "客户档案")),
    ("项目中心", "供应商档案", "smart_construction_core.menu_sc_supplier_partner", "smart_construction_core.action_sc_supplier_partner", "res.partner", ("客商管理", "供应商档案")),
    ("项目中心", "客商黑名单", "smart_construction_core.menu_sc_product_partner_blacklist_v1", "smart_construction_core.action_sc_product_partner_blacklist_v1", "res.partner", ("客商管理", "客商黑名单")),
    ("项目中心", "招标信息", "smart_construction_core.menu_sc_product_tender_information_v1", "smart_construction_core.action_sc_product_tender_information_v1", "tender.opportunity", ("招投标管理", "招标信息")),
    ("项目中心", "投标项目", "smart_construction_core.menu_sc_project_tender", "smart_construction_core.action_tender_bid", "tender.bid", ("招投标管理", "投标项目")),
    ("项目中心", "标书管理", "smart_construction_core.menu_sc_product_tender_document_v1", "smart_construction_core.action_sc_product_tender_document_v1", "tender.document", ("招投标管理", "标书管理")),
    ("项目中心", "投标保证金", "smart_construction_core.menu_sc_tender_guarantee", "smart_construction_core.action_sc_tender_guarantee", "tender.guarantee", ("招投标管理", "投标保证金")),
    ("项目中心", "中标管理", "smart_construction_core.menu_sc_tender_won", "smart_construction_core.action_sc_tender_won", "tender.bid", ("招投标管理", "中标管理")),
    ("项目中心", "安全检查", "smart_construction_core.menu_sc_safety_issue", "smart_construction_core.action_sc_safety_issue", "sc.safety.issue", ("施工管理", "安全检查")),
    ("项目中心", "质量验收", "smart_construction_core.menu_sc_product_quality_acceptance_v1", "smart_construction_core.action_sc_product_quality_acceptance_v1", "sc.quality.acceptance", ("施工管理", "质量验收")),
    ("项目中心", "工程资料", "smart_construction_core.menu_sc_project_documents", "smart_construction_core.action_sc_project_document", "sc.project.document", ("施工管理", "工程资料")),
    ("项目中心", "施工日志", "smart_construction_core.menu_sc_construction_diary", "smart_construction_core.action_sc_construction_diary", "sc.construction.diary", ("施工管理", "施工日志")),
    ("项目中心", "施工进度", "smart_construction_core.menu_sc_construction_progress", "smart_construction_core.action_project_progress_entry", "project.progress.entry", ("施工管理", "施工进度")),
    ("项目中心", "签证变更", "smart_construction_core.menu_sc_product_site_variation_v1", "smart_construction_core.action_sc_product_site_variation_v1", "sc.settlement.adjustment", ("施工管理", "签证变更")),
    ("项目中心", "劳务实名制", "smart_construction_core.menu_sc_product_labor_realname_v1", "smart_construction_core.action_sc_product_labor_realname_v1", "sc.labor.worker", ("劳务成本", "劳务实名制")),
    ("项目中心", "劳务成本登记", "smart_construction_core.menu_sc_product_labor_cost_v1", "smart_construction_core.action_sc_product_labor_cost_v1", "sc.labor.usage", ("劳务成本", "劳务成本登记")),
    ("项目中心", "劳务扣款明细", "smart_construction_core.menu_sc_product_labor_deduction_v1", "smart_construction_core.action_sc_product_labor_deduction_v1", "sc.labor.deduction", ("劳务成本", "劳务扣款明细")),
    ("项目中心", "材料入库", "smart_construction_core.menu_sc_material_inbound", "smart_construction_core.action_sc_material_inbound_handling", "sc.material.inbound", ("材料成本", "材料入库")),
    ("项目中心", "材料出库", "smart_construction_core.menu_sc_material_outbound", "smart_construction_core.action_sc_material_outbound", "sc.material.outbound", ("材料成本", "材料出库")),
    ("项目中心", "材料退货", "smart_construction_core.menu_sc_product_material_return_v1", "smart_construction_core.action_sc_material_return", "sc.material.outbound", ("材料成本", "材料退货")),
    ("项目中心", "机械台班登记", "smart_construction_core.menu_sc_product_equipment_shift_v1", "smart_construction_core.action_sc_equipment_usage", "sc.equipment.usage", ("机械成本", "机械台班登记")),
    ("项目中心", "分包成本登记", "smart_construction_core.menu_sc_product_subcontract_cost_v1", "smart_construction_core.action_sc_subcontract_register", "sc.subcontract.register", ("分包成本", "分包成本登记")),
    ("项目中心", "分包签证费用", "smart_construction_core.menu_sc_product_subcontract_variation_v1", "smart_construction_core.action_sc_subcontract_settlement", "sc.subcontract.settlement", ("分包成本", "分包签证费用")),
    ("项目中心", "薪资核算清单", "smart_construction_core.menu_sc_product_project_payroll_v1", "smart_construction_core.action_sc_product_project_payroll_v1", "sc.hr.payroll.document", ("项目薪资", "薪资核算清单")),
    ("项目中心", "薪资发放登记", "smart_construction_core.menu_sc_product_project_salary_payment_v1", "smart_construction_core.action_sc_product_project_salary_payment_v1", "sc.hr.payroll.document", ("项目薪资", "薪资发放登记")),
    ("项目中心", "班组借/扣款登记", "smart_construction_core.menu_sc_product_team_loan_deduction_v1", "smart_construction_core.action_sc_product_team_loan_deduction_v1", "sc.expense.claim", ("班组借/扣款", "班组借/扣款登记")),
    ("合同中心", "收入合同", "smart_construction_core.menu_sc_p1_income_contract", "smart_construction_core.action_construction_contract_income", "construction.contract.income", ("收入合同",)),
    ("合同中心", "支出合同", "smart_construction_core.menu_sc_p1_expense_contract", "smart_construction_core.action_construction_contract_expense", "construction.contract.expense", ("支出合同",)),
    ("合同中心", "合同变更", "smart_construction_core.menu_sc_p1_contract_change", "smart_construction_core.action_sc_settlement_adjustment", "sc.settlement.adjustment", ("合同变更",)),
    ("合同中心", "日常合同", "smart_construction_core.menu_sc_p1_daily_contract", "smart_construction_core.action_sc_general_contract", "sc.general.contract", ("日常合同",)),
    ("合同中心", "日常合同结算", "smart_construction_core.menu_sc_product_general_contract_settlement_v1", "smart_construction_core.action_sc_product_general_contract_settlement_v1", "sc.settlement.order", ("日常合同结算",)),
    ("合同中心", "收入结算", "smart_construction_core.menu_sc_p1_income_settlement", "smart_construction_core.action_sc_settlement_order_income", "sc.settlement.order", ("收入结算",)),
    ("合同中心", "支出结算", "smart_construction_core.menu_sc_p1_expense_settlement", "smart_construction_core.action_sc_settlement_order_expense", "sc.settlement.order", ("支出结算",)),
    ("成本中心", "项目预算", "smart_construction_core.menu_sc_p1_project_budget", "smart_construction_core.action_project_budget", "project.cost.plan", ("项目预算",)),
    ("成本中心", "成本计划编制", "smart_construction_core.menu_sc_p1_cost_plan", "smart_construction_core.action_project_cost_plan", "project.cost.plan", ("成本计划编制",)),
    ("成本中心", "成本归集", "smart_construction_core.menu_sc_p1_cost_ledger", "smart_construction_core.action_project_cost_ledger", "project.cost.ledger", ("成本归集",)),
    ("成本中心", "项目盈亏分析", "smart_construction_core.menu_sc_p1_profit_analysis", "smart_construction_core.action_project_profit_compare", "project.profit.compare", ("项目盈亏分析",)),
    ("财务中心", "收款登记", "smart_construction_core.menu_sc_receipt_income", "smart_construction_core.action_sc_receipt_income", "sc.receipt.income", ("收款登记",)),
    ("财务中心", "付款申请", "smart_construction_core.menu_sc_user_payment_apply", "smart_construction_core.action_payment_request_user_payment_apply", "payment.request", ("付款申请",)),
    ("财务中心", "实付登记", "smart_construction_core.menu_sc_payment_execution", "smart_construction_core.action_sc_payment_execution_actual_outflow", "sc.payment.execution", ("实付登记",)),
    ("财务中心", "费用报销", "smart_construction_core.menu_sc_reimbursement_request", "smart_construction_core.action_sc_expense_claim_reimbursement_request", "sc.expense.claim", ("费用报销",)),
    ("财务中心", "往来款登记", "smart_construction_core.menu_sc_product_current_account_v1", "smart_construction_core.action_sc_product_current_account_v1", "sc.fund.account.operation", ("往来款登记",)),
    ("财务中心", "公司收入", "smart_construction_core.menu_sc_user_income", "smart_construction_core.action_sc_receipt_income_user_income", "sc.receipt.income", ("公司收入",)),
    ("财务中心", "公司支出", "smart_construction_core.menu_sc_company_finance_expense", "smart_construction_core.action_sc_payment_execution_company_finance_expense", "sc.payment.execution", ("公司支出",)),
    ("财务中心", "公司&项目扣款", "smart_construction_core.menu_sc_deduction_bill", "smart_construction_core.action_sc_expense_claim_deduction_bill", "sc.expense.claim", ("公司&项目扣款",)),
    ("财务中心", "公司&项目退款", "smart_construction_core.menu_sc_product_company_project_refund_v1", "smart_construction_core.action_sc_product_company_project_refund_v1", "sc.expense.claim", ("公司&项目退款",)),
    ("财务中心", "备用金", "smart_construction_core.menu_sc_advance_fund", "smart_construction_core.action_sc_expense_claim_advance_fund", "sc.expense.claim", ("备用金",)),
    ("财务中心", "资金汇总", "smart_construction_core.menu_sc_funding_plan_summary", "smart_construction_core.action_project_funding_baseline_summary", "project.funding.baseline", ("资金汇总",)),
    ("税务中心", "外经证", "smart_construction_core.menu_sc_tax_certificate_registration_user", "smart_construction_core.action_sc_tax_certificate_registration_user", "sc.tax.certificate.registration", ("外经证",)),
    ("税务中心", "预缴登记", "smart_construction_core.menu_sc_invoice_prepaid_tax_user", "smart_construction_core.action_sc_invoice_prepaid_tax_user", "sc.invoice.registration", ("预缴登记",)),
    ("税务中心", "开票申请", "smart_construction_core.menu_sc_invoice_application_user", "smart_construction_core.action_sc_invoice_application_user", "sc.invoice.registration", ("开票申请",)),
    ("税务中心", "销项开票", "smart_construction_core.menu_sc_invoice_registration_user", "smart_construction_core.action_sc_invoice_registration_user", "sc.invoice.registration", ("销项开票",)),
    ("税务中心", "发票红冲", "smart_construction_core.menu_sc_output_invoice_change_registration", "smart_construction_core.action_sc_output_invoice_change_registration", "sc.output.invoice.adjustment", ("发票红冲",)),
    ("税务中心", "进项发票", "smart_construction_core.menu_sc_invoice_input", "smart_construction_core.action_sc_invoice_input", "sc.invoice.registration", ("进项发票",)),
    ("税务中心", "税额抵扣", "smart_construction_core.menu_sc_tax_deduction_registration_user", "smart_construction_core.action_sc_tax_deduction_registration_user", "sc.tax.deduction.registration", ("税额抵扣",)),
    ("税务中心", "项目专项抵扣", "smart_construction_core.menu_sc_product_project_tax_deduction_v1", "smart_construction_core.action_sc_product_project_tax_deduction_v1", "sc.tax.deduction.registration", ("项目专项抵扣",)),
    ("税务中心", "税务申报", "smart_construction_core.menu_sc_product_tax_filing_v1", "smart_construction_core.action_sc_product_tax_filing_v1", "sc.invoice.registration", ("税务申报",)),
    ("报表中心", "项目报表", "smart_construction_core.menu_sc_project_operation_statistics_report", "smart_construction_core.action_sc_project_operation_statistics_report", "sc.operating.metrics.project", ("项目报表",)),
    ("报表中心", "成本报表", "smart_construction_core.menu_sc_comprehensive_cost_statistics_report", "smart_construction_core.action_sc_comprehensive_cost_statistics_report", "sc.comprehensive.cost.summary", ("成本报表",)),
    ("报表中心", "资金报表", "smart_construction_core.menu_sc_fund_daily_summary", "smart_construction_core.action_sc_fund_daily_summary", "sc.fund.daily.summary", ("资金报表",)),
    ("报表中心", "税务报表", "smart_construction_core.menu_sc_product_tax_report_v1", "smart_construction_core.action_sc_product_tax_report_v1", "sc.invoice.registration", ("税务报表",)),
    ("报表中心", "劳务分包报表", "smart_construction_core.menu_sc_product_labor_subcontract_report_v1", "smart_construction_core.action_sc_product_labor_subcontract_report_v1", "sc.labor.usage", ("劳务分包报表",)),
    ("行政中心", "部门管理", "smart_construction_core.menu_sc_organization_department", "smart_construction_core.action_sc_organization_department", "hr.department", ("部门管理",)),
    ("行政中心", "岗位管理", "smart_construction_core.menu_sc_product_job_management_v1", "smart_construction_core.action_sc_product_job_management_v1", "hr.job", ("岗位管理",)),
    ("行政中心", "人员档案", "smart_construction_core.menu_sc_runtime_user_management", "smart_construction_core.action_sc_runtime_user_management", "res.users", ("人员档案",)),
    ("行政中心", "证书管理", "smart_construction_core.menu_sc_certificate_registration", "smart_construction_core.action_sc_certificate_registration", "sc.document.admin.document", ("证书管理",)),
    ("行政中心", "社保公积", "smart_construction_core.menu_sc_product_social_fund_v1", "smart_construction_core.action_sc_product_social_fund_v1", "sc.hr.payroll.document", ("社保公积",)),
    ("行政中心", "工资薪酬", "smart_construction_core.menu_sc_payroll_management", "smart_construction_core.action_sc_payroll_management", "sc.hr.payroll.document", ("工资薪酬",)),
    ("行政中心", "办公资产", "smart_construction_core.menu_sc_product_office_asset_v1", "smart_construction_core.action_sc_product_office_asset_v1", "sc.office.admin.document", ("办公资产",)),
    ("行政中心", "制度文件", "smart_construction_core.menu_sc_product_policy_document_v1", "smart_construction_core.action_sc_company_document_archive", "sc.document.admin.document", ("制度文件",)),
    ("产品配置", "表单配置", "smart_construction_core.menu_sc_business_config_workbench", "smart_construction_core.action_sc_business_config_workbench", "ui.business.config.contract", ("表单配置",)),
    ("产品配置", "流程审批配置", "smart_construction_core.menu_sc_approval_policy", "smart_construction_core.action_sc_approval_policy", "sc.approval.policy", ("流程审批配置",)),
    ("产品配置", "字段管理", "smart_construction_core.menu_ui_form_field_policy_business_config", "smart_construction_core.action_ui_form_field_policy_business_config", "ui.form.field.policy", ("字段管理",)),
    ("产品配置", "数据权限", "smart_construction_core.menu_sc_product_data_permission_v1", "smart_construction_core.action_sc_product_data_permission_v1", "ui.business.config.contract", ("数据权限",)),
    ("产品配置", "系统参数", "smart_construction_core.menu_sc_product_system_parameter_v1", "smart_construction_core.action_sc_product_system_parameter_v1", "ui.business.config.contract", ("系统参数",)),
    ("产品配置", "编码规则", "smart_construction_core.menu_sc_product_numbering_rule_v1", "smart_construction_core.action_sc_product_numbering_rule_v1", "ui.business.config.contract", ("编码规则",)),
)

ACCOUNTING_MENUS = (
    ("日记账分录", "account.menu_action_move_journal_line_form", "account.action_move_journal_line", "account.move", "凭证与分录"),
    ("日记账项目", "account.menu_action_account_moves_all", "account.action_account_moves_all", "account.move.line", "凭证与分录"),
    ("会计科目表", "account.menu_action_account_form", "account.action_account_form", "account.account", "会计科目"),
    ("日记账", "smart_construction_core.menu_sc_account_journal_foundation", "smart_construction_core.action_sc_account_journal_foundation", "account.journal", "账簿基础"),
    ("分析账户", "smart_construction_core.menu_sc_analytic_account_foundation", "smart_construction_core.action_sc_analytic_account_foundation", "account.analytic.account", "分析核算"),
    ("分析分配模型", "smart_construction_core.menu_sc_analytic_distribution_foundation", "smart_construction_core.action_sc_analytic_distribution_foundation", "account.analytic.distribution.model", "分析核算"),
)
REPLACED_NATIVE_ACCOUNTING_MENU_XMLIDS = frozenset({"account.menu_action_account_journal_form", "account.account_analytic_def_account", "account.menu_analytic__distribution_model"})


def _contract_delivery_by_target() -> dict[tuple[str, str], str]:
    contract = json.loads(PRODUCT_CONTRACT.read_text(encoding="utf-8"))
    targets: dict[tuple[str, str], str] = {}
    for center in contract.get("centers") or []:
        center_name = str(center.get("name") or "").strip()
        for item in center.get("level_two") or []:
            children = item.get("children") if isinstance(item.get("children"), list) else None
            candidates = children or [item]
            for candidate in candidates:
                target = (center_name, str(candidate.get("name") or "").strip())
                targets[target] = str(candidate.get("delivery") or "").strip()
    return targets


def _menu_row(center: str, label: str, menu_xmlid: str, action_xmlid: str, model: str, path: tuple[str, ...], *, maturity: str, source_kind: str = "p1_locked_menu_surface_projection") -> dict:
    capability_key = "construction.menu.%s" % menu_xmlid.replace(".", "_")
    domain_label = path[-2] if len(path) > 1 else center
    return {
        "access_level": "public", "action_xmlid": action_xmlid,
        "business_entry_contract_version": "business_entry_disposition.v1",
        "capability_key": capability_key, "capability_maturity": maturity,
        "control_granularity": "user_visible_menu_page",
        "control_object": "P1 施工行业正式产品入口", "disposition_policy": "keep_list_form",
        "enabled": True, "entry_intent": "handling", "entry_intent_label": "办理",
        "entry_target_policy": "keep_list_form", "group_key": f"construction.{center}",
        "group_label": center, "integration_target": f"{model} {label}", "label": label,
        "locked_data_policy": "odoo_model_acl_and_record_rules", "menu_key": menu_xmlid,
        "menu_xmlid": menu_xmlid, "model": model, "name": label, "page_key": menu_xmlid,
        "page_label": label, "policy_note": "locked_complete_product_menu_surface",
        "product_domain": center, "product_domain_label": domain_label, "product_key": center,
        "productization_source": source_kind, "release_domain": "construction",
        "release_state": "released", "res_model": model, "source_kind": source_kind,
        "target_scene_key": "", "title": label, "view_modes": ["tree", "form"],
        "visible_menu_path": " / ".join(("智慧施工管理平台", center, *path)),
    }


def _capability_from_menu(row: dict) -> dict:
    keys = ("access_level", "capability_key", "capability_maturity", "control_object", "disposition_policy", "enabled", "entry_intent", "entry_intent_label", "entry_target_policy", "group_key", "group_label", "integration_target", "label", "menu_xmlid", "product_domain", "product_domain_label", "product_key", "release_state", "res_model", "source_kind", "target_scene_key", "visible_menu_path")
    capability = {key: row[key] for key in keys if key in row}
    capability["entry_kind"] = "user_visible_menu_page"
    capability["target_page_key"] = row["page_key"]
    return capability


def promote(payload: dict) -> dict:
    bindings = {(row[0], row[1]) for row in RELEASED_MENU_BINDINGS}
    bindings.update({("会计账务中心", row[0]) for row in ACCOUNTING_MENUS})
    delivery_by_target = _contract_delivery_by_target()
    expected = set(delivery_by_target)
    if bindings != expected:
        raise ValueError(f"menu binding/contract mismatch: missing={sorted(expected - bindings)} extra={sorted(bindings - expected)}")
    for product in payload.get("products") or []:
        incoming = {str(group.get("group_label") or "").strip() for group in product.get("menu_groups") or []}
        unknown = incoming - set(TARGET_CENTERS) - LEGACY_SOURCE_CENTERS
        if unknown:
            raise ValueError(f"unapproved first-level product center: {sorted(unknown)!r}")
        rows_by_center = {center: [] for center in TARGET_CENTERS}
        for binding in RELEASED_MENU_BINDINGS:
            rows_by_center[binding[0]].append(_menu_row(
                *binding,
                maturity=delivery_by_target[(binding[0], binding[1])],
            ))
        for label, menu_xmlid, action_xmlid, model, _domain_label in ACCOUNTING_MENUS:
            rows_by_center["会计账务中心"].append(_menu_row(
                "会计账务中心", label, menu_xmlid, action_xmlid, model, (label,),
                maturity=delivery_by_target[("会计账务中心", label)],
                source_kind="p1_accounting_foundation_projection",
            ))
        product["menu_groups"] = [{"category": "user_visible_menu", "group_key": f"construction.{center}", "group_label": center, "label": center, "title": center, "menus": rows_by_center[center]} for center in TARGET_CENTERS]
        product["capabilities"] = [_capability_from_menu(menu) for group in product["menu_groups"] for menu in group["menus"]]
    counts = {sum(len(group.get("menus") or []) for group in product.get("menu_groups") or []) for product in payload.get("products") or []}
    if len(counts) != 1:
        raise ValueError(f"product menu counts diverged: {sorted(counts)}")
    menu_count = counts.pop()
    strategy = payload.setdefault("policy_strategy", {})
    strategy["effective_menu_count_per_product"] = menu_count
    strategy["effective_capability_count_per_product"] = menu_count
    strategy["runtime_projection"] = "locked_complete_product_contract_plus_approved_current_accounting"
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    current = BASELINE.read_text(encoding="utf-8")
    payload = promote(json.loads(current))
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    if args.write:
        BASELINE.write_text(rendered, encoding="utf-8")
        CHECKSUM.write_text(f"{digest}  {BASELINE.name}\n", encoding="utf-8")
    elif current != rendered or CHECKSUM.read_text(encoding="utf-8") != f"{digest}  {BASELINE.name}\n":
        raise SystemExit("locked ten-center policy or checksum is not in canonical promoted form")
    print(json.dumps({"products": len(payload.get("products") or []), "menu_count": payload["policy_strategy"]["effective_menu_count_per_product"], "sha256": digest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
