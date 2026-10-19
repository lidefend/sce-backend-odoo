# -*- coding: utf-8 -*-
"""Converge existing demo databases onto the realistic visible-data baseline.

Most affected records are declared with ``noupdate="1"``, so a module upgrade
cannot refresh them from XML.  This post-migration rewrites only user-visible
labels; technical identifiers (XMLID, login, project_code, model and table
names) stay untouched.  It is restricted to demo databases and is idempotent.
"""

import json


MODULE = "smart_construction_demo"
DEMO_DATABASES = {"sc_dev_demo", "sc_demo"}


USERS = [
    # (XMLID, login, display name, partner/work email or None)
    ("user_sc_pm_01", "pm1", "张建国", "zhangjianguo@zhihui-construction.cn"),
    ("user_sc_contract_01", "ct1", "李慧敏", "lihuimin@zhihui-construction.cn"),
    ("user_sc_fin_01", "fin1", "王秀兰", "wangxiulan@zhihui-construction.cn"),
    ("user_sc_fin_mgr_01", "fin_mgr", "陈志强", "chenzhiqiang@zhihui-construction.cn"),
    ("user_sc_cost_01", "cost1", "刘晓东", "liuxiaodong@zhihui-construction.cn"),
    ("user_sc_material_01", "mat1", "赵鹏", "zhaopeng@zhihui-construction.cn"),
    ("user_sc_material_mgr_01", "mat_mgr", "孙立军", "sunlijun@zhihui-construction.cn"),
    ("user_sc_purchase_01", "pur1", "周文静", "zhouwenjing@zhihui-construction.cn"),
    ("user_demo_role_owner", "demo_role_owner", "高建华", "gaojianhua@zhihui-construction.cn"),
    ("user_demo_role_executive", "demo_role_executive", "何明远", "hemingyuan@zhihui-construction.cn"),
    ("user_demo_role_pm", "demo_role_pm", "马晓峰", "maxiaofeng@zhihui-construction.cn"),
    ("user_demo_role_finance", "demo_role_finance", "冯丽", "fengli@zhihui-construction.cn"),
    ("user_demo_role_project_a_member", "demo_role_project_a_member", "邓超", "dengchao@zhihui-construction.cn"),
    ("user_demo_project_read", "demo_role_project_read", "曹敏", "caomin@zhihui-construction.cn"),
    ("user_demo_project_user", "demo_role_project_user", "韩磊", "hanlei@zhihui-construction.cn"),
    ("user_demo_project_manager", "demo_role_project_manager", "王建军", "wangjianjun@zhihui-construction.cn"),
    ("user_sc_operation_demo", "sc_demo_operation", "郑雅琴", "zhengyaqin@zhihui-construction.cn"),
    ("user_sc_accounting_manager_demo", "sc_demo_accounting_manager", "吴海燕", "wuhaiyan@zhihui-construction.cn"),
    ("user_sc_business_config_demo", "sc_demo_business_config", "徐磊", "xulei@zhihui-construction.cn"),
    ("user_sc_rental_payment_checker_demo", "sc_demo_rental_payment_checker", "黄倩", "huangqian@zhihui-construction.cn"),
    ("user_wutao_full_product", "wutao", "吴涛", None),
    # Capability accounts keep their login and carry a job title as display name.
    ("user_sc_contract_manager_cap", "sc_contract_mgr", "合同审批岗", "sc_contract_mgr@zhihui-construction.cn"),
    ("user_sc_contract_user_cap", "sc_contract_user_cap", "合同经办岗", "sc_contract_user_cap@zhihui-construction.cn"),
    ("user_sc_contract_read_cap", "sc_contract_read", "合同查询岗", "sc_contract_read@zhihui-construction.cn"),
    ("user_sc_cost_manager_cap", "sc_cost_mgr", "成本审批岗", "sc_cost_mgr@zhihui-construction.cn"),
    ("user_sc_cost_user_cap", "sc_cost_user_cap", "成本经办岗", "sc_cost_user_cap@zhihui-construction.cn"),
    ("user_sc_cost_read_cap", "sc_cost_read", "成本查询岗", "sc_cost_read@zhihui-construction.cn"),
    ("user_sc_material_mgr_test", "sc_material_mgr", "物资审批岗", "sc_material_mgr@zhihui-construction.cn"),
    ("user_sc_material_user_cap", "sc_material_user_cap", "物资经办岗", "sc_material_user_cap@zhihui-construction.cn"),
    ("user_sc_material_read_cap", "sc_material_read", "物资查询岗", "sc_material_read@zhihui-construction.cn"),
    ("user_sc_finance_mgr_test", "sc_finance_mgr", "财务审批岗", "sc_finance_mgr@zhihui-construction.cn"),
    ("user_sc_finance_user_cap", "sc_finance_user_cap", "财务经办岗", "sc_finance_user_cap@zhihui-construction.cn"),
    ("user_sc_finance_read_cap", "sc_finance_read", "财务查询岗", "sc_finance_read@zhihui-construction.cn"),
    ("user_sc_settlement_manager_cap", "sc_settlement_mgr", "结算审批岗", "sc_settlement_mgr@zhihui-construction.cn"),
    ("user_sc_settlement_user_cap", "sc_settlement_user_cap", "结算经办岗", "sc_settlement_user_cap@zhihui-construction.cn"),
    ("user_sc_settlement_read_cap", "sc_settlement_read", "结算查询岗", "sc_settlement_read@zhihui-construction.cn"),
    ("user_sc_project_manager_cap", "sc_project_mgr", "项目审批岗", "sc_project_mgr@zhihui-construction.cn"),
    ("user_sc_project_user", "sc_project_user", "项目经办岗", "sc_project_user@zhihui-construction.cn"),
    ("user_sc_project_viewer_test", "sc_project_viewer", "项目查询岗", "sc_project_viewer@zhihui-construction.cn"),
    ("user_sc_purchase_manager_cap", "sc_purchase_mgr", "采购审批岗", "sc_purchase_mgr@zhihui-construction.cn"),
    ("user_sc_purchase_user_cap", "sc_purchase_user_cap", "采购经办岗", "sc_purchase_user_cap@zhihui-construction.cn"),
    ("user_sc_purchase_read_cap", "sc_purchase_read", "采购查询岗", "sc_purchase_read@zhihui-construction.cn"),
    # Legacy fixture and smoke accounts use job titles instead of demo markers.
    ("user_demo_full", "demo_full", "综合能力岗", None),
    ("sc_demo_user_pm", "demo_pm", "项目经理岗", None),
    ("sc_demo_user_finance", "demo_finance", "财务经办岗", None),
    ("sc_demo_user_cost", "demo_cost", "成本管理岗", None),
    ("sc_demo_user_audit", "demo_audit", "数据审计岗", None),
    ("sc_demo_user_readonly", "demo_readonly", "只读查询岗", None),
    ("sc_demo_user_test_admin", "sc_test_admin", "综合管理岗", None),
    ("user_demo_e2e_smoke", "svc_e2e_smoke", "接口巡检账号", "svc_e2e_smoke@example.com"),
]


PROJECT_XMLIDS = [
    (
        "sc_demo_project_001",
        "德阳智能制造产教融合项目",
        "项目位于德阳经开区，建设内容包括智能制造实训中心、产教融合综合楼及配套道路管网，"
        "总建筑面积约 8.6 万平方米，合同额约 3.2 亿元，计划工期 2025 年 1 月至 2026 年 12 月，"
        "目前处于主体施工阶段。",
    ),
    (
        "sc_demo_project_002",
        "城东片区安置房项目",
        "项目位于城东新区，建设内容包括 6 栋安置住宅、社区服务中心及地下车库，"
        "总建筑面积约 9.4 万平方米，合同额约 2.8 亿元，计划工期 2025 年 3 月至 2027 年 2 月，"
        "目前处于基础施工阶段。",
    ),
]


PROJECT_CODES = [
    ("DEMO-PJ-INIT", "城西科创园一期工程（立项阶段）"),
    ("DEMO-PJ-TENDER", "滨江路市政道路提升工程（前期阶段）"),
    ("DEMO-PJ-EXEC", "东环路城市快速路提升工程（在建阶段）"),
    ("DEMO-PJ-STAGE-DRAFT", "临港产业园标准厂房项目（立项阶段）"),
    ("DEMO-PJ-STAGE-RUN", "城北新区安置房项目（在建阶段）"),
    ("DEMO-PJ-STAGE-PAUSE", "老城区雨污分流改造工程（暂停阶段）"),
    ("DEMO-PJ-STAGE-CLOSING", "高新片区学校建设项目（结算阶段）"),
    ("DEMO-PJ-STAGE-DONE", "城南污水处理厂扩建工程（完工阶段）"),
    ("DEMO-PJ-STAGE-WARRANTY", "经开区综合管廊工程（质保阶段）"),
    ("DEMO-PJ-STAGE-CLOSED", "城东片区安置房二期工程（归档阶段）"),
]


SCENE_PAYLOAD = {
    "code": "s67_demo_ops_scene",
    "name": "运营管理场景",
    "layout": "grid",
    "tiles": [
        {
            "key": "demo.ops.dashboard",
            "title": "运营总览",
            "scenario": "s67_scene_pack_surface",
        }
    ],
}


RECORD_UPDATES = [
    ("sc_demo_capability_group_067_demo_ops", "sc.capability.group", "sc_capability_group", {
        "label": "运营管理能力",
    }),
    ("sc_demo_capability_067_demo_dashboard", "sc.capability", "sc_capability", {
        "name": "运营管理驾驶舱",
        "ui_label": "运营总览",
        "ui_hint": "用于场景编排与能力目录的运营总览入口。",
    }),
    ("sc_demo_scene_067_demo_ops", "sc.scene", "sc_scene", {
        "name": "运营管理场景",
        "description": "场景编排覆盖运营总览与能力目录。",
    }),
    ("sc_demo_scene_tile_067_demo_dashboard", "sc.scene.tile", "sc_scene_tile", {
        "title": "运营总览",
    }),
    ("sc_demo_scene_version_067_v1", "sc.scene.version", "sc_scene_version", {
        "payload_json": json.dumps(SCENE_PAYLOAD, ensure_ascii=False),
    }),
    ("sc_demo_pack_registry_067_demo_surface", "sc.pack.registry", "sc_pack_registry", {
        "name": "运营管理场景包",
        "vendor": "智建科技",
        "notes": "场景编排与能力目录场景包。",
        "changelog": "1.0.0: 新增运营管理能力与场景。",
    }),
    ("sc_demo_expense_claim_070_travel", "sc.expense.claim", "sc_expense_claim", {
        "applicant_name": "张建国",
    }),
    ("sc_demo_payment_execution_070_material", "sc.payment.execution", "sc_payment_execution", {
        "handler_name": "王秀兰",
    }),
    ("sc_demo_invoice_registration_070_input", "sc.invoice.registration", "sc_invoice_registration", {
        "handler_name": "王秀兰",
    }),
    ("sc_demo_construction_diary_070_daily", "sc.construction.diary", "sc_construction_diary", {
        "project_manager": "张建国",
        "handler_name": "张建国",
    }),
    ("sc_demo_project_member_assignment_072_pm", "sc.project.member.assignment", "sc_project_member_assignment", {
        "note": "正式项目成员授权。",
    }),
    ("sc_demo_partner_supplier_074_service", "res.partner", "res_partner", {
        "sc_supplier_note": "客商扩展字段与供应商类型资料。",
    }),
    ("sc_demo_material_rfq_080_steel", "sc.material.rfq", "sc_material_rfq", {
        "contact_name": "赵鹏",
    }),
    ("sc_demo_equipment_usage_080_crane", "sc.equipment.usage", "sc_equipment_usage", {
        "operator_name": "刘建军",
    }),
    ("sc_demo_hr_payroll_085_salary", "sc.hr.payroll.document", "sc_hr_payroll_document", {
        "employee_name": "张建国",
    }),
    ("sc_demo_hr_payroll_085_bonus", "sc.hr.payroll.document", "sc_hr_payroll_document", {
        "employee_name": "张建国",
    }),
    ("sc_demo_expense_claim_086_deposit_pay", "sc.expense.claim", "sc_expense_claim", {
        "applicant_name": "赵春梅",
    }),
    ("sc_demo_expense_claim_086_deposit_refund", "sc.expense.claim", "sc_expense_claim", {
        "applicant_name": "赵春梅",
    }),
    ("sc_demo_labor_usage_087_masonry", "sc.labor.usage", "sc_labor_usage", {
        "foreman_name": "陈国栋",
    }),
    ("sc_demo_invoice_registration_088_output", "sc.invoice.registration", "sc_invoice_registration", {
        "handler_name": "王秀兰",
        "invoice_holder": "陈志强",
    }),
    ("sc_demo_output_invoice_adjustment_088_red_flush", "sc.output.invoice.adjustment", "sc_output_invoice_adjustment", {
        "note": "销项发票变更登记，保持草稿待确认。",
    }),
    ("sc_demo_audit_log_071_payment_amount", "sc.audit.log", "sc_audit_log", {
        "reason": "治理审计留痕：付款申请已完成治理复核。",
    }),
    ("sc_demo_account_receivable", "account.account", "account_account", {
        "name": "应收账款",
    }),
    ("sc_demo_account_revenue", "account.account", "account_account", {
        "name": "工程收入",
    }),
]


JSONB_TRANSLATABLE_COLUMNS = {
    ("account_account", "name"),
    ("project_project", "name"),
}


def _is_demo_database(dbname):
    name = (dbname or "").strip().lower()
    return name in DEMO_DATABASES or name.startswith("sc_demo_") or name.endswith("_demo")


def _xmlid_record(cr, xmlid, model):
    cr.execute(
        """
        SELECT res_id
          FROM ir_model_data
         WHERE module = %s AND name = %s AND model = %s
        """,
        (MODULE, xmlid, model),
    )
    row = cr.fetchone()
    return int(row[0]) if row else None


def _resolve_user(cr, xmlid, login):
    user_id = _xmlid_record(cr, xmlid, "res.users")
    if user_id is not None:
        cr.execute("SELECT login FROM res_users WHERE id = %s", (user_id,))
        row = cr.fetchone()
        if not row:
            return None
        if row[0] != login:
            raise RuntimeError(
                "%s XMLID points at login %r instead of %r" % (xmlid, row[0], login)
            )
        return user_id

    cr.execute("SELECT id FROM res_users WHERE login = %s ORDER BY id", (login,))
    user_ids = [int(row[0]) for row in cr.fetchall()]
    if len(user_ids) > 1:
        raise RuntimeError("%s must identify exactly one demo principal" % login)
    return user_ids[0] if user_ids else None


def _update_users(cr):
    for xmlid, login, name, email in USERS:
        user_id = _resolve_user(cr, xmlid, login)
        if user_id is None:
            continue
        cr.execute("SELECT partner_id FROM res_users WHERE id = %s", (user_id,))
        row = cr.fetchone()
        if not row or not row[0]:
            continue
        partner_id = int(row[0])
        cr.execute(
            "UPDATE res_partner SET name = %s WHERE id = %s AND name IS DISTINCT FROM %s",
            (name, partner_id, name),
        )
        if email:
            cr.execute(
                "UPDATE res_partner SET email = %s WHERE id = %s AND email IS DISTINCT FROM %s",
                (email, partner_id, email),
            )
        cr.execute(
            """
            UPDATE hr_employee
               SET name = %s
             WHERE user_id = %s AND name IS DISTINCT FROM %s
            """,
            (name, user_id, name),
        )
        if email:
            cr.execute(
                """
                UPDATE hr_employee
                   SET work_email = %s
                 WHERE user_id = %s AND work_email IS DISTINCT FROM %s
                """,
                (email, user_id, email),
            )


def _update_projects(cr):
    for xmlid, name, description in PROJECT_XMLIDS:
        project_id = _xmlid_record(cr, xmlid, "project.project")
        if project_id is None:
            continue
        _update_jsonb_text(cr, "project_project", "name", project_id, name)
        cr.execute(
            """
            UPDATE project_project
               SET description = %s
             WHERE id = %s
               AND description IS DISTINCT FROM %s
            """,
            (description, project_id, description),
        )

    for code, name in PROJECT_CODES:
        cr.execute("SELECT id FROM project_project WHERE project_code = %s", (code,))
        project_ids = [int(row[0]) for row in cr.fetchall()]
        if len(project_ids) > 1:
            raise RuntimeError("%s must identify exactly one project" % code)
        if not project_ids:
            continue
        _update_jsonb_text(cr, "project_project", "name", project_ids[0], name)


def _update_jsonb_text(cr, table, column, record_id, value):
    cr.execute(
        """
        UPDATE {table}
           SET {column} = jsonb_set(
                   jsonb_set(
                       COALESCE({column}, '{{}}'::jsonb),
                       '{{en_US}}',
                       to_jsonb(%s::text),
                       true
                   ),
                   '{{zh_CN}}',
                   to_jsonb(%s::text),
                   true
               )
         WHERE id = %s
           AND (
               {column}->>'en_US' IS DISTINCT FROM %s
               OR {column}->>'zh_CN' IS DISTINCT FROM %s
           )
        """.format(table=table, column=column),
        (value, value, record_id, value, value),
    )


def _update_text(cr, table, column, record_id, value):
    cr.execute(
        "UPDATE {table} SET {column} = %s WHERE id = %s AND {column} IS DISTINCT FROM %s".format(
            table=table,
            column=column,
        ),
        (value, record_id, value),
    )


def _update_jsonb_value(cr, table, column, record_id, value):
    cr.execute(
        "UPDATE {table} SET {column} = %s::jsonb WHERE id = %s AND {column} IS DISTINCT FROM %s::jsonb".format(
            table=table,
            column=column,
        ),
        (value, record_id, value),
    )


def _update_records(cr):
    for xmlid, model, table, values in RECORD_UPDATES:
        record_id = _xmlid_record(cr, xmlid, model)
        if record_id is None:
            continue
        for column, value in values.items():
            if (table, column) in JSONB_TRANSLATABLE_COLUMNS:
                _update_jsonb_text(cr, table, column, record_id, value)
            elif column == "payload_json":
                _update_jsonb_value(cr, table, column, record_id, value)
            else:
                _update_text(cr, table, column, record_id, value)


def migrate(cr, installed_version):
    del installed_version
    if not _is_demo_database(cr.dbname):
        return
    _update_users(cr)
    _update_projects(cr)
    _update_records(cr)
