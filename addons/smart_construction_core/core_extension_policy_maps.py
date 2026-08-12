# -*- coding: utf-8 -*-
from __future__ import annotations

ROLE_SURFACE_OVERRIDES = {
    "restricted": {
        "label": "受限用户",
        "landing_scene_candidates": ["workspace.home"],
        "menu_xmlids": [],
        "deny_all_navigation": True,
    },
    "project_member": {
        "label": "项目成员",
        "landing_scene_candidates": ["workspace.home", "projects.list", "projects.ledger"],
        "menu_xmlids": [
            "smart_construction_core.menu_sc_project_center",
            "smart_construction_core.menu_sc_contract_center",
            "smart_construction_core.menu_sc_construction_center",
        ],
        "primary_menu_xmlids": [
            "smart_construction_core.menu_sc_project_project",
            "smart_construction_core.menu_sc_general_contract",
            "smart_construction_core.menu_sc_p1_daily_contract",
            "smart_construction_core.menu_sc_plan",
            "smart_construction_core.menu_sc_plan_report",
            "smart_construction_core.menu_sc_construction_diary",
            "smart_construction_core.menu_sc_certificate_registration",
            "smart_construction_core.menu_sc_company_document_archive",
            "smart_construction_core.menu_sc_document_borrow",
        ],
        "role_home_menu_xmlids": [],
        "contextual_menu_xmlids": [
            "smart_construction_core.menu_sc_site_documents",
            "smart_construction_core.menu_sc_project_wbs",
            "smart_construction_core.menu_sc_project_kanban",
            "smart_construction_core.menu_sc_contract_expense",
            "smart_construction_core.menu_sc_contract_income",
            "smart_construction_core.menu_sc_quality_issue",
            "smart_construction_core.menu_sc_quality_rectification",
            "smart_construction_core.menu_sc_quality_recheck",
            "smart_construction_core.menu_sc_safety_issue",
            "smart_construction_core.menu_sc_safety_rectification",
            "smart_construction_core.menu_sc_safety_recheck",
        ],
        "denied_menu_xmlids": [],
        "menu_blocklist_xmlids": [
            "smart_construction_core.menu_sc_finance_center",
            "smart_construction_core.menu_sc_settlement_center",
            "smart_construction_core.menu_payment_request",
            "smart_construction_core.menu_sc_tax_center",
            "smart_construction_core.menu_sc_hr_center",
            "smart_construction_core.menu_sc_tender_registration",
        ],
        "action_blocklist_xmlids": [
            "smart_construction_core.action_sc_tender_registration",
        ],
        "model_blocklist": [
            "payment.request",
            "sc.payment.execution",
            "sc.settlement.order",
        ],
        "model_prefix_blocklist": [
            "account.",
            "hr.",
            "payment.",
            "sc.finance.",
            "sc.payment.",
            "sc.settlement.",
            "sc.tax.",
        ],
        "group_key_blocklist": [
            "construction.财务中心",
            "construction.税务中心",
            "construction.人事行政",
        ],
    },
    "business_full": {
        "label": "业务全功能",
        "exclusive_surface": True,
        "landing_scene_candidates": ["workspace.home", "projects.list"],
        "discover_installed_capabilities": True,
        "menu_xmlids": [
            "smart_construction_core.menu_sc_root",
        ],
        "primary_menu_xmlids": [],
        "role_home_menu_xmlids": [],
        "contextual_menu_xmlids": [],
        "admin_menu_xmlids": [],
        "denied_menu_xmlids": [],
        "menu_blocklist_xmlids": [],
        "action_blocklist_xmlids": [],
        "model_blocklist": [],
        "model_prefix_blocklist": [],
        "group_key_blocklist": [],
    },
    "business_config_admin": {
        "label": "业务配置管理员",
        "landing_scene_candidates": ["projects.list", "projects.ledger", "projects.intake"],
        # The primary role owns the landing surface, while the released
        # construction catalogue is still intersected with the user's native
        # Odoo ACL-visible menu facts.  This composes existing business
        # capabilities without granting platform administration or exposing
        # raw native menus outside the formal product policy.
        "discover_installed_capabilities": True,
        "menu_xmlids": [
            "smart_construction_core.menu_sc_root",
            "smart_construction_core.menu_sc_business_config_center",
        ],
        "primary_menu_xmlids": [
            "smart_construction_core.menu_sc_historical_payment_fact",
        ],
        "role_home_menu_xmlids": [],
        "contextual_menu_xmlids": [],
        "contextual_action_authorities": [
            {
                "menu_xmlid": "smart_construction_core.menu_sc_invoice_input_report_user",
                "action_xmlid": "smart_construction_core.action_sc_invoice_input_report_user",
                "allowed_operation": "read",
                "required_capability": "menu_action_read",
                "source": "business_config.invoice_input_report_acceptance_route",
            },
        ],
        "admin_menu_xmlids": [
            "smart_construction_core.menu_sc_runtime_user_management",
            "smart_construction_core.menu_sc_business_config_workbench",
            "smart_construction_core.menu_ui_menu_config_policy_business_config",
            "smart_construction_core.menu_ui_form_field_policy_business_config",
            "smart_construction_core.menu_ui_form_custom_field_wizard_business_config",
            "smart_construction_core.menu_sc_approval_policy",
        ],
        "denied_menu_xmlids": [],
        "admin_action_authorities": [
            {
                "action_xmlid": "smart_construction_core.action_sc_runtime_user_management",
                "menu_xmlid": "smart_construction_core.menu_sc_runtime_user_management",
                "allowed_operation": "write",
                "required_capability": "business_config_admin",
                "context_requirements": {},
                "source": "nav_policy_01.business_config_admin",
            },
        ],
    },
    "system_admin": {
        "label": "系统管理员",
        "exclusive_surface": True,
        "landing_scene_candidates": ["workspace.home"],
        "discover_installed_capabilities": True,
        "system_configuration_visible": True,
        "deny_all_navigation": False,
        "menu_xmlids": [],
        "primary_menu_xmlids": [],
        "role_home_menu_xmlids": [],
        "contextual_menu_xmlids": [],
        "admin_menu_xmlids": [
            "smart_construction_core.menu_ui_menu_config_policy_business_config",
        ],
        "denied_menu_xmlids": [],
        "admin_action_authorities": [
            {
                "action_xmlid": "smart_construction_core.action_sc_runtime_user_management",
                "allowed_operation": "read",
                "required_capability": "platform_admin",
                "context_requirements": {},
                "source": "nav_policy_01.system_admin",
            },
        ],
    },
    "owner": {
        "label": "企业负责人",
        "landing_scene_candidates": ["workspace.home", "projects.list", "projects.intake"],
        "menu_xmlids": [
            "smart_construction_core.menu_sc_project_center",
            "smart_construction_core.menu_sc_contract_center",
        ],
        "primary_menu_xmlids": [
            "smart_construction_core.menu_sc_project_project",
            "smart_construction_core.menu_sc_general_contract",
            "smart_construction_core.menu_sc_plan",
            "smart_construction_core.menu_sc_plan_report",
            "smart_construction_core.menu_sc_construction_diary",
        ],
        "role_home_menu_xmlids": [],
        "contextual_menu_xmlids": [
            "smart_construction_core.menu_sc_site_documents",
            "smart_construction_core.menu_sc_project_wbs",
            "smart_construction_core.menu_sc_project_documents",
            "smart_construction_core.menu_sc_contract_expense",
            "smart_construction_core.menu_sc_expense_contract_material",
            "smart_construction_core.menu_sc_expense_contract_normal",
            "smart_construction_core.menu_sc_expense_contract_labor",
            "smart_construction_core.menu_sc_expense_contract_rental",
            "smart_construction_core.menu_sc_expense_contract_subcontract",
            "smart_construction_core.menu_sc_expense_contract_other",
            "smart_construction_core.menu_sc_expense_contract_supplement",
            "smart_construction_core.menu_sc_expense_contract_execution",
            "smart_construction_core.menu_sc_contract_income",
            "smart_construction_core.menu_sc_project_income_contract",
            "smart_construction_core.menu_sc_contract_event",
        ],
        "denied_menu_xmlids": [],
        "menu_blocklist_xmlids": [
            "smart_construction_core.menu_sc_tender_registration",
        ],
        "action_blocklist_xmlids": [
            "smart_construction_core.action_sc_tender_registration",
        ],
    },
    "pm": {
        "label": "项目经理",
        "landing_scene_candidates": ["workspace.home", "portal.dashboard", "projects.ledger", "projects.list", "projects.intake"],
        "menu_xmlids": [
            "smart_construction_core.menu_sc_project_center",
            "smart_construction_core.menu_sc_contract_center",
            "smart_construction_core.menu_sc_cost_center",
        ],
        "primary_menu_xmlids": [
            "smart_construction_core.menu_sc_project_project",
            "smart_construction_core.menu_sc_boq_version",
            "smart_construction_core.menu_sc_project_boq_root",
            "smart_construction_core.menu_sc_boq_analysis",
            "smart_construction_core.menu_sc_project_budget",
            "smart_construction_core.menu_sc_project_work_breakdown",
            "smart_construction_core.menu_sc_wbs_plan_version",
            "smart_construction_core.menu_sc_project_location_breakdown",
            "smart_construction_core.menu_sc_project_contract_section",
            "smart_construction_core.menu_sc_project_execution_scope",
            "smart_construction_core.menu_sc_project_boq_allocation",
            "smart_construction_core.menu_sc_general_contract",
            "smart_construction_core.menu_sc_p1_daily_contract",
            "smart_construction_core.menu_sc_plan",
            "smart_construction_core.menu_sc_plan_report",
            "smart_construction_core.menu_sc_construction_diary",
            "smart_construction_core.menu_sc_settlement_order",
            "smart_construction_core.menu_sc_settlement_adjustment",
            "smart_construction_core.menu_sc_expense_contract_settlement",
            "smart_construction_core.menu_sc_expense_contract_variation",
            "smart_construction_core.menu_sc_income_contract_settlement",
            "smart_construction_core.menu_sc_income_contract_variation",
            "smart_construction_core.menu_sc_tender_registration",
            "smart_construction_core.menu_sc_tender_registration_fee",
        ],
        "role_home_menu_xmlids": [],
        "contextual_menu_xmlids": [
            "smart_construction_core.menu_sc_project_wbs",
            "smart_construction_core.menu_sc_project_kanban",
            "smart_construction_core.menu_sc_site_documents",
            "smart_construction_core.menu_sc_contract_expense",
            "smart_construction_core.menu_sc_expense_contract_material",
            "smart_construction_core.menu_sc_expense_contract_normal",
            "smart_construction_core.menu_sc_expense_contract_labor",
            "smart_construction_core.menu_sc_expense_contract_rental",
            "smart_construction_core.menu_sc_expense_contract_subcontract",
            "smart_construction_core.menu_sc_expense_contract_other",
            "smart_construction_core.menu_sc_expense_contract_supplement",
            "smart_construction_core.menu_sc_expense_contract_execution",
            "smart_construction_core.menu_sc_contract_income",
            "smart_construction_core.menu_sc_project_income_contract",
        ],
        "denied_menu_xmlids": [
            "smart_construction_core.menu_sc_project_tender",
            "smart_construction_core.menu_sc_tender_prepare",
            "smart_construction_core.menu_sc_tender_opening",
            "smart_construction_core.menu_sc_tender_won",
            "smart_construction_core.menu_sc_tender_guarantee",
        ],
        "contextual_action_authorities": [
            {
                "action_xmlid": "smart_construction_core.action_project_boq_import_wizard",
                "allowed_operation": "create",
                "required_capability": "cost_boq_import",
                "context_requirements": {},
                "source": "nav_policy_01.pm.boq_import_workbench_action",
            },
            {
                "menu_xmlid": "smart_construction_core.menu_sc_project_budget",
                "action_xmlid": "smart_construction_core.action_project_cost_plan_line",
                "allowed_operation": "read",
                "required_capability": "cost_plan_line_read",
                "context_requirements": {},
                "source": "nav_policy_01.pm.cost_plan_detail_ledger_action",
            },
            {
                "menu_xmlid": "smart_construction_core.menu_sc_project_budget",
                "action_xmlid": "smart_construction_core.action_project_cost_plan_node",
                "allowed_operation": "read",
                "required_capability": "cost_plan_line_read",
                "context_requirements": {},
                "source": "nav_policy_01.pm.cost_plan_compilation_tree_action",
            },
            {
                "action_xmlid": "smart_construction_core.action_construction_contract_income_execution",
                "allowed_operation": "read",
                "required_capability": "contract_read",
                "context_requirements": {
                    "required_query": ["company_id", "project_id", "contract_id"],
                    "company_query": "company_id",
                    "selected_record_query": "project_id",
                    "record_query": "contract_id",
                    "record_model": "construction.contract",
                    "record_selected_context_field": "project_id",
                    "record_company_field": "company_id",
                },
                "source": "nav_policy_01.pm.contract_relation",
            },
        ],
        "menu_blocklist_xmlids": ["smart_construction_core.menu_sc_project_manage"],
    },
    "finance": {
        "label": "财务主管",
        "landing_scene_candidates": ["workspace.home", "finance.payment_requests", "projects.ledger", "projects.list"],
        "menu_xmlids": [
            "smart_construction_core.menu_sc_finance_center",
            "smart_construction_core.menu_sc_settlement_center",
            "smart_construction_core.menu_payment_request",
        ],
        "primary_menu_xmlids": [
            "smart_construction_core.menu_sc_historical_payment_fact",
            "smart_construction_core.menu_payment_request_receive",
            "smart_construction_core.menu_sc_receipt_income",
            "smart_construction_core.menu_sc_user_income",
            "smart_construction_core.menu_sc_engineering_progress_income",
            "smart_construction_core.menu_sc_settlement_order",
            "smart_construction_core.menu_sc_settlement_adjustment",
            "smart_construction_core.menu_sc_user_payment_apply_acceptance",
            "smart_construction_core.menu_sc_payment_execution",
            "smart_construction_core.menu_sc_partner_payment",
            "smart_construction_core.menu_sc_company_finance_expense",
            "smart_construction_core.menu_sc_invoice_input",
            "smart_construction_core.menu_sc_invoice_application_user",
            "smart_construction_core.menu_sc_invoice_registration_user",
            "smart_construction_core.menu_sc_invoice_prepaid_tax_user",
            "smart_construction_core.menu_sc_tax_certificate_registration_user",
            "smart_construction_core.menu_sc_tax_deduction_registration_user",
            "smart_construction_core.menu_sc_finance_project_capital_position",
            "smart_construction_core.menu_sc_finance_counterparty_position_summary",
            "smart_construction_core.menu_sc_finance_project_counterparty_position",
            "smart_construction_core.menu_sc_company_contractor_responsibility_summary",
            "smart_construction_core.menu_sc_company_contractor_responsibility_fact",
            "smart_construction_core.menu_sc_treasury_reconciliation",
            "smart_construction_core.menu_sc_fund_daily_user_report",
            "smart_construction_core.menu_sc_borrowing_request",
            "smart_construction_core.menu_sc_repayment_registration",
            "smart_construction_core.menu_sc_contractor_project_repay",
            "smart_construction_core.menu_sc_contractor_project_borrow",
            "smart_construction_core.menu_sc_project_borrow_company",
            "smart_construction_core.menu_sc_project_repay_company",
            "smart_construction_core.menu_sc_self_funding_advance_income",
            "smart_construction_core.menu_sc_self_funding_advance_refund",
            "smart_construction_core.menu_sc_fund_account_between_user",
            "smart_construction_core.menu_sc_deduction_bill",
            "smart_construction_core.menu_sc_reimbursement_request",
            "smart_construction_core.menu_sc_expense_claim",
            "smart_construction_core.menu_sc_project_expense_claim",
            "smart_construction_core.menu_sc_deduction_paid",
            "smart_construction_core.menu_sc_deduction_paid_refund",
            "smart_construction_core.menu_sc_bid_deposit_pay",
            "smart_construction_core.menu_sc_bid_deposit_return",
            "smart_construction_core.menu_sc_contract_deposit_register",
            "smart_construction_core.menu_sc_contract_deposit_return",
        ],
        "role_home_menu_xmlids": [],
        "contextual_menu_xmlids": [
            "smart_construction_core.menu_sc_invoice_output",
            "smart_construction_core.menu_sc_output_invoice_change_registration",
            "smart_construction_core.menu_sc_output_invoice_adjustment",
            "smart_construction_core.menu_receipt_invoice_line",
            "smart_construction_core.menu_sc_finance_business_project_summary",
            "smart_construction_core.menu_sc_interfund_movement_project_summary",
            "smart_construction_core.menu_sc_finance_business_fact",
            "smart_construction_core.menu_sc_interfund_movement_fact",
            "smart_construction_core.menu_sc_invoice_input_report_user",
            "smart_construction_core.menu_sc_funding_plan_declaration",
            "smart_construction_core.menu_sc_financing_loan_registration",
            "smart_construction_core.menu_sc_fund_transfer_out",
            "smart_construction_core.menu_sc_fund_transfer_between",
            "smart_construction_core.menu_sc_fund_balance_adjustment",
            "smart_construction_core.menu_sc_company_deduction",
            "smart_construction_core.menu_sc_company_income",
            "smart_construction_core.menu_sc_company_expense",
            "smart_construction_core.menu_sc_advance_fund",
            "smart_construction_core.menu_sc_borrowing_bill",
            "smart_construction_core.menu_sc_repayment_bill",
            "smart_construction_core.menu_sc_expense_reimbursement_group",
        ],
        "contextual_action_authorities": [
            {
                "menu_xmlid": "smart_construction_core.menu_sc_invoice_input_report_user",
                "action_xmlid": "smart_construction_core.action_sc_invoice_input_report_user",
                "allowed_operation": "read",
                "required_capability": "menu_action_read",
                "source": "finance.invoice_input_report_contextual_route",
            },
        ],
        "denied_menu_xmlids": [],
        "menu_blocklist_xmlids": [
            "smart_construction_core.menu_sc_plan",
            "smart_construction_core.menu_sc_plan_report",
        ],
        "action_blocklist_xmlids": [
            "smart_construction_core.action_sc_plan",
            "smart_construction_core.action_sc_plan_report",
        ],
    },
    "executive": {
        "label": "管理层",
        "landing_scene_candidates": ["portal.dashboard", "project.management", "projects.list", "projects.ledger", "projects.intake"],
        "menu_xmlids": [
            "smart_construction_core.menu_sc_root",
            "smart_construction_core.menu_sc_projection_root",
            "smart_construction_core.menu_sc_project_center",
        ],
        "primary_menu_xmlids": [
            "smart_construction_core.menu_sc_historical_payment_fact",
        ],
    },
}

ROLE_GROUPS_EXPLICIT = {
    "system_admin": {
        "smart_core.group_smart_core_admin",
    },
    "business_full": {
        "smart_construction_core.group_sc_business_full",
    },
    "owner": {
        "smart_construction_core.group_sc_role_owner",
    },
    "project_member": {
        "smart_construction_core.group_sc_cap_project_read",
    },
    "business_config_admin": {
        "smart_construction_core.group_sc_cap_business_config_admin",
    },
    "executive": {
        "smart_construction_core.group_sc_role_executive",
    },
    "pm": {
        "smart_construction_core.group_sc_role_project_manager",
        "smart_construction_core.group_sc_role_project_user",
    },
    "finance": {
        "smart_construction_core.group_sc_role_finance_manager",
        "smart_construction_core.group_sc_role_finance_user",
    },
}

ROLE_GROUPS_CAPABILITY_FALLBACK = {
    "pm": {
        "smart_construction_core.group_sc_cap_project_manager",
        "smart_construction_core.group_sc_cap_project_user",
    },
    "finance": {
        "smart_construction_core.group_sc_cap_finance_user",
        "smart_construction_core.group_sc_cap_finance_manager",
    },
}

ROLE_PRECEDENCE = ("system_admin", "business_full", "business_config_admin", "executive", "owner", "pm", "finance")

NAV_MENU_SCENE_MAP = {
    "smart_construction_core.menu_sc_project_initiation": "projects.intake",
    "smart_construction_core.menu_sc_project_project": "projects.list",
    "smart_construction_core.menu_sc_project_management_scene": "project.management",
    "smart_construction_core.menu_sc_project_cost_code": "config.project_cost_code",
    "smart_construction_core.menu_sc_root": "projects.list",
    "smart_construction_core.menu_sc_project_dashboard": "projects.dashboard",
    "smart_construction_core.menu_sc_history_todo": "workspace.home",
    "smart_construction_core.menu_sc_operating_metrics_project": "dashboard.company",
    "smart_construction_core.menu_sc_dashboard_cost_cockpit_fact": "cost.control",
    "smart_construction_core.menu_sc_dictionary": "data.dictionary",
    "smart_construction_core.menu_payment_request": "finance.payment_requests",
}

NAV_ACTION_SCENE_MAP = {
    "smart_construction_core.action_project_initiation": "projects.intake",
    "smart_construction_core.action_sc_project_list": "projects.list",
    "smart_construction_core.action_project_dashboard": "projects.dashboard",
    "smart_construction_core.action_project_dictionary": "data.dictionary",
    "smart_construction_core.action_project_cost_code": "config.project_cost_code",
    "smart_construction_core.action_sc_dashboard_cost_cockpit_fact": "cost.control",
    "smart_construction_core.action_payment_request": "finance.payment_requests",
    "smart_construction_core.action_payment_request_my": "finance.payment_requests",
}

NAV_MODEL_VIEW_SCENE_MAP = {
    ("project.project", "list"): "projects.list",
    ("project.project", "form"): "projects.intake",
    ("payment.request", "list"): "finance.payment_requests",
    ("payment.request", "form"): "finance.payment_requests",
}

SERVER_ACTION_WINDOW_MAP = {
    "smart_construction_core.action_exec_structure_entry": "smart_construction_core.action_exec_structure_wbs",
}

FILE_ATTACHMENT_ALLOWED_MODEL_EXACT = {
    "payment.ledger",
    "payment.request",
    "payment.request.line",
}

FILE_ATTACHMENT_ALLOWED_MODEL_PREFIXES = ("construction.", "project.", "quota.", "sc.", "tender.")

FILE_ATTACHMENT_ALLOWED_LEGACY_MODEL_PREFIXES = ("sc.legacy.",)

FILE_ATTACHMENT_EXCLUDED_MODEL_PREFIXES = (
    "sc.legacy.",
    "sc.ops.",
    "sc.pack.",
    "sc.scene.",
    "sc.subscription.",
    "sc.usage.",
    "sc.workbench.",
    "ui.form.",
)

FILE_UPLOAD_ALLOWED_MODELS = ["project.project", "project.task", "payment.request"]

FILE_DOWNLOAD_ALLOWED_MODELS = ["project.project", "project.task", "payment.request"]

LEGACY_VISIBLE_BUSINESS_COLUMN_LABELS_BY_MODEL = {
    "project.project": {
        "name": "项目名称",
    },
    "res.partner": {
        "sc_business_role_label": "业务角色",
        "sc_business_fact_basis": "业务事实依据",
        "sc_source_project_name": "来源项目",
        "sc_source_receipt_amount": "来源收款金额",
        "sc_source_payment_amount": "来源付款金额",
        "sc_source_document_state": "来源单据状态",
        "sc_source_push_result": "来源推送结果",
        "sc_source_partner_code": "来源客商编码",
        "sc_source_cooperation_type": "来源合作类型",
        "sc_source_created_by": "来源创建人",
        "sc_source_created_at": "来源创建时间",
        "sc_source_fact_count": "关联业务数",
        "sc_source_fact_source": "业务来源",
    },
    "project.material.plan": {
        "legacy_visible_01": "单据状态",
        "legacy_visible_02": "单据编号",
        "legacy_visible_03": "单据日期",
        "legacy_visible_04": "到货时间",
        "legacy_visible_05": "采购材料名称",
        "legacy_visible_06": "规格型号",
        "legacy_visible_07": "单位",
        "legacy_visible_08": "数量",
        "legacy_visible_09": "材料别名(设计/清单)",
        "legacy_visible_10": "备注",
        "legacy_visible_11": "附件",
        "legacy_visible_12": "项目名称",
        "legacy_visible_13": "录入人",
        "legacy_visible_14": "录入时间",
        "source_created_by": "录入人",
        "source_created_at": "录入时间",
    },
    "sc.material.inbound": {
        "legacy_visible_01": "单据状态",
        "legacy_visible_02": "入库单号",
        "legacy_visible_03": "单据日期",
        "legacy_visible_04": "供应商名称",
        "legacy_visible_05": "材料名称",
        "legacy_visible_06": "规格型号",
        "legacy_visible_07": "数量",
        "legacy_visible_08": "单价",
        "legacy_visible_09": "税率",
        "legacy_visible_10": "含税金额",
        "legacy_visible_11": "入库总数量",
        "legacy_visible_12": "付款状态",
        "legacy_visible_13": "已付款金额",
        "legacy_visible_14": "未付款金额",
        "legacy_visible_15": "结算状态",
        "legacy_visible_16": "已结算金额",
        "legacy_visible_17": "项目名称",
        "legacy_visible_18": "备注",
        "legacy_visible_19": "附件",
        "legacy_visible_20": "录入人",
        "legacy_visible_21": "录入时间",
        "legacy_visible_22": "采购人",
        "source_created_by": "录入人",
        "source_created_at": "录入时间",
    },
}

BUSINESS_LIST_DEFAULT_VISIBILITY_BY_MODEL = {
    "project.project": {
        "critical": ["name", "project_code", "lifecycle_state", "user_id"],
        "roles": {
            "name": "description",
            "project_code": "identity",
            "lifecycle_state": "status",
            "user_id": "relation",
            "owner_id": "relation",
            "partner_id": "relation",
            "sc_partner_display_name": "relation",
            "operation_strategy": "status",
            "contract_amount": "money",
            "dashboard_progress_rate": "text",
            "date_start": "date",
            "date": "date",
            "write_date": "date",
        },
    },
    "sc.general.contract": {
        "critical": [
            "name",
            "contract_no",
            "contract_name",
            "state",
            "contract_date",
            "amount_total",
            "project_id",
        ],
        "roles": {
            "name": "identity",
            "contract_no": "identity",
            "contract_name": "description",
            "state": "status",
            "contract_date": "date",
            "amount_total": "money",
            "project_id": "relation",
            "partner_id": "relation",
        },
    },
    "construction.contract": {
        "critical": [
            "name",
            "state",
            "date_contract",
            "project_id",
            "partner_id",
            "visible_contract_amount",
        ],
        "roles": {
            "name": "description",
            "contract_no": "identity",
            "state": "status",
            "date_contract": "date",
            "project_id": "relation",
            "partner_id": "relation",
            "visible_contract_amount": "money",
        },
    },
    "res.partner": {
        "roles": {
            "name": "description",
            "company_type": "status",
            "state_id": "relation",
            "country_id": "relation",
            "user_id": "relation",
        },
        "hidden": [
            "sc_business_role_label",
            "sc_business_fact_basis",
            "sc_source_project_name",
            "sc_source_receipt_amount",
            "sc_source_payment_amount",
            "sc_source_document_state",
            "sc_source_push_result",
            "sc_source_partner_code",
            "sc_source_cooperation_type",
            "sc_source_created_by",
            "sc_source_created_at",
            "sc_source_fact_count",
            "sc_source_fact_source",
        ],
    },
}

API_DATA_WRITE_ALLOWLIST = {
    "project.project": ["name", "description", "date_start"],
    "project.task": ["name", "description", "date_deadline", "project_id"],
    "purchase.order.line": ["name", "order_id"],
    "res.partner": ["name", "email", "phone", "sc_supplier_type", "sc_supplier_type_ids"],
    # Transient import records are created through the generic native form runtime,
    # then executed through their ACL-protected object button.
    "sc.norm.import.wizard": ["data_file", "filename", "clear_before"],
}

API_DATA_MUTATION_POLICIES = {
}

DRAFT_DELETE_ALLOWED_STATES = ("cancel", "cancelled", "draft")

def _state_unlink_policy(
    model_name: str,
    business_label: str,
    allowed_states=DRAFT_DELETE_ALLOWED_STATES,
    state_field: str = "state",
):
    return {
        "allowed": True,
        "delete_mode": "unlink",
        "policy_kind": "state_limited_business_document",
        "state_field": state_field,
        "allowed_states": list(allowed_states),
        "reason_code": "DRAFT_BUSINESS_DOCUMENT_DELETE_ALLOWED",
        "message": f"允许删除未形成业务事实的{business_label}；仅限草稿/取消等未提交状态，并继续受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    }

API_DATA_DRAFT_UNLINK_POLICIES = {
    "construction.contract": _state_unlink_policy("construction.contract", "合同记录"),
    "construction.contract.income": _state_unlink_policy("construction.contract.income", "收入合同"),
    "construction.contract.expense": _state_unlink_policy("construction.contract.expense", "支出合同"),
    "payment.request": _state_unlink_policy("payment.request", "付款申请"),
    "sc.general.contract": _state_unlink_policy("sc.general.contract", "综合合同"),
    "sc.expense.claim": _state_unlink_policy("sc.expense.claim", "费用与保证金单据"),
    "sc.financing.loan": _state_unlink_policy("sc.financing.loan", "融资借款单据"),
    "sc.invoice.registration": _state_unlink_policy("sc.invoice.registration", "发票登记单据"),
    "sc.payment.execution": _state_unlink_policy("sc.payment.execution", "付款执行单"),
    "sc.receipt.income": _state_unlink_policy("sc.receipt.income", "收款收入登记"),
    "sc.fund.account.operation": _state_unlink_policy("sc.fund.account.operation", "资金账户操作单"),
    "sc.self.funding.registration": _state_unlink_policy("sc.self.funding.registration", "自筹资金登记"),
    "sc.tax.deduction.registration": _state_unlink_policy("sc.tax.deduction.registration", "税票抵扣登记"),
    "sc.settlement.order": _state_unlink_policy("sc.settlement.order", "结算单"),
    "sc.settlement.adjustment": _state_unlink_policy("sc.settlement.adjustment", "结算调整单"),
    "project.material.plan": _state_unlink_policy("project.material.plan", "材料计划"),
    "sc.material.purchase.request": _state_unlink_policy("sc.material.purchase.request", "材料采购申请"),
    "sc.material.acceptance": _state_unlink_policy("sc.material.acceptance", "材料验收单"),
    "sc.material.inbound": _state_unlink_policy("sc.material.inbound", "材料入库单"),
    "sc.material.outbound": _state_unlink_policy("sc.material.outbound", "材料出库单"),
    "sc.material.rfq": _state_unlink_policy("sc.material.rfq", "材料询比价"),
    "sc.material.settlement": _state_unlink_policy("sc.material.settlement", "材料结算单"),
    "sc.material.rental.plan": _state_unlink_policy("sc.material.rental.plan", "材料租赁计划"),
    "sc.material.rental.order": _state_unlink_policy("sc.material.rental.order", "材料租赁订单"),
    "sc.material.rental.settlement": _state_unlink_policy("sc.material.rental.settlement", "材料租赁结算"),
    "sc.labor.plan": _state_unlink_policy("sc.labor.plan", "劳务计划"),
    "sc.labor.request": _state_unlink_policy("sc.labor.request", "劳务申请"),
    "sc.labor.usage": _state_unlink_policy("sc.labor.usage", "劳务使用记录"),
    "sc.labor.settlement": _state_unlink_policy("sc.labor.settlement", "劳务结算"),
    "sc.labor.price": _state_unlink_policy("sc.labor.price", "劳务价格单"),
    "sc.equipment.plan": _state_unlink_policy("sc.equipment.plan", "设备计划"),
    "sc.equipment.request": _state_unlink_policy("sc.equipment.request", "设备申请"),
    "sc.equipment.usage": _state_unlink_policy("sc.equipment.usage", "设备使用记录"),
    "sc.equipment.settlement": _state_unlink_policy("sc.equipment.settlement", "设备结算"),
    "sc.equipment.price": _state_unlink_policy("sc.equipment.price", "设备价格单"),
    "sc.safety.plan": _state_unlink_policy("sc.safety.plan", "安全方案"),
    "sc.safety.disclosure": _state_unlink_policy("sc.safety.disclosure", "安全交底"),
    "sc.safety.issue": _state_unlink_policy("sc.safety.issue", "安全问题"),
    "sc.safety.patrol.task": _state_unlink_policy("sc.safety.patrol.task", "安全巡检任务"),
    "sc.quality.issue": _state_unlink_policy("sc.quality.issue", "质量问题"),
    "sc.quality.rectification": _state_unlink_policy(
        "sc.quality.rectification",
        "质量整改记录",
        ("submitted", "rectifying", "rechecking", "cancel"),
        state_field="issue_state",
    ),
    "sc.quality.recheck": _state_unlink_policy(
        "sc.quality.recheck",
        "质量复验记录",
        ("rectifying", "rechecking", "cancel"),
        state_field="issue_state",
    ),
    "sc.safety.rectification": _state_unlink_policy(
        "sc.safety.rectification",
        "安全整改记录",
        ("submitted", "rectifying", "rechecking", "cancel"),
        state_field="issue_state",
    ),
    "sc.safety.recheck": _state_unlink_policy(
        "sc.safety.recheck",
        "安全复验记录",
        ("rectifying", "rechecking", "cancel"),
        state_field="issue_state",
    ),
    "sc.construction.diary": _state_unlink_policy("sc.construction.diary", "施工日志"),
    "project.progress.entry": _state_unlink_policy("project.progress.entry", "进度填报"),
    "project.risk.action": _state_unlink_policy("project.risk.action", "风险措施"),
    "sc.plan": _state_unlink_policy("sc.plan", "项目计划"),
    "sc.plan.line": _state_unlink_policy("sc.plan.line", "项目计划明细"),
    "sc.plan.version": _state_unlink_policy("sc.plan.version", "计划版本"),
    "sc.plan.report": _state_unlink_policy("sc.plan.report", "计划上报"),
    "tender.bid": _state_unlink_policy("tender.bid", "投标主单", ("prepare", "estimating")),
    "tender.doc.purchase": _state_unlink_policy("tender.doc.purchase", "投标文件购买申请"),
    "tender.doc.review": _state_unlink_policy("tender.doc.review", "投标文件审查"),
    "tender.guarantee": _state_unlink_policy("tender.guarantee", "投标保证金"),
}

API_DATA_UNLINK_POLICIES = {
    "construction.contract": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理合同记录；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "construction.contract.income": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理收入合同记录；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "construction.contract.expense": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理支出合同记录；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "hr.department": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理组织部门；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "payment.request": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理付款申请；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "payment.request.line": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理付款申请明细；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "project.cost.code": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理成本科目；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "project.dictionary": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理业务字典；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "project.task": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许删除任务记录；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "project.tags": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "RELATION_MAINTENANCE_DELETE_ALLOWED",
        "message": "允许删除项目标签等关系维护数据；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "res.partner": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理客户/供应商资料；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "sc.approval.policy": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理审批策略；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "sc.approval.step": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理审批步骤；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "sc.document.admin.document": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理行政档案；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "sc.hr.payroll.document": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理薪酬档案；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "sc.office.admin.document": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理办公行政资料；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "sc.project.stage.requirement.item": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理阶段要求；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
    "sc.supplier.type": {
        "allowed": True,
        "delete_mode": "unlink",
        "reason_code": "DELETE_POLICY_ALLOWED",
        "message": "允许业务配置管理员整理供应商类型；仍受模型 ACL 与记录规则约束。",
        "source": "smart_construction_core",
    },
}

API_DATA_UNLINK_POLICIES.update(API_DATA_DRAFT_UNLINK_POLICIES)

API_DATA_UNLINK_ALLOWED_MODELS = list(API_DATA_UNLINK_POLICIES)

MODEL_CODE_MAPPING = {
    "project": "project.project",
    "task": "project.task",
}

CRITICAL_SCENE_TARGET_OVERRIDES = {
    "projects.list",
    "projects.detail",
    "projects.intake",
    "projects.ledger",
    "projects.execution",
    "projects.dashboard",
    "project.management",
    "my_work.workspace",
    "portal.dashboard",
    "finance.payment_requests",
}

CRITICAL_SCENE_TARGET_ROUTE_OVERRIDES = {
    "my_work.workspace": "/my-work",
}

INDUSTRY_CREATE_FIELD_FALLBACKS = {
    "project.project": {
        "selection_defaults": {
            "privacy_visibility": "followers",
            "rating_status": "stage",
            "last_update_status": "to_define",
            "rating_status_period": "monthly",
        }
    }
}
# Formal fields exposed to the generic API search surface.  This map is product
# policy: migration aliases and customer-specific projection names are forbidden.
API_DATA_FORMAL_SEARCH_FIELDS = {
    "payment.request": (
        "name", "project_id", "partner_id", "date_request", "amount",
        "amount_uppercase", "accepted_amount_uppercase", "note",
    ),
    "tender.guarantee": ("name", "project_id", "company_id", "remark"),
    "sc.settlement.order": (
        "name", "project_id", "settlement_unit_id", "source_created_by", "note",
    ),
}
