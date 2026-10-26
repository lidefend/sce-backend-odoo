# -*- coding: utf-8 -*-
"""Seed one honest, navigable sample for formal product pages added after V1."""

from odoo import fields

from ..registry import SeedStep, register
from ..business_roles import business_model, prepare_project


def _ensure(Model, domain, values):
    Model = business_model(Model.env, Model._name)
    record = Model.search(domain, limit=2)
    if len(record) > 1:
        raise ValueError("Demo identity is ambiguous: %s" % Model._name)
    return record or Model.create(values)


def run(env):
    project = env.ref("smart_construction_demo.sc_demo_project_001")
    owner = env.ref("smart_construction_demo.sc_demo_partner_owner_001")
    supplier = env.ref("smart_construction_demo.sc_demo_partner_vendor_steel")
    prepare_project(env, project)
    admin = env.ref("smart_construction_demo.user_sc_project_manager_cap")
    today = fields.Date.context_today(env.user)

    _ensure(env["hr.job"], [("name", "=", "项目成本工程师")], {
        "name": "项目成本工程师",
        "company_id": project.company_id.id,
    })
    analytic_plan = _ensure(env["account.analytic.plan"], [("name", "=", "项目成本分析")], {"name": "项目成本分析"})
    if analytic_plan:
        analytic_account = _ensure(
            env["account.analytic.account"],
            [("code", "=", "DEMO-ANALYTIC-001")],
            {
                "name": "项目成本分析账户",
                "code": "DEMO-ANALYTIC-001",
                "plan_id": analytic_plan.id,
                "company_id": project.company_id.id,
                "partner_id": owner.id,
            },
        )
        _ensure(
            env["account.analytic.distribution.model"],
            [("company_id", "=", project.company_id.id), ("partner_id", "=", owner.id)],
            {
                "company_id": project.company_id.id,
                "partner_id": owner.id,
                "analytic_distribution": {str(analytic_account.id): 100.0},
            },
        )
    _ensure(env["sc.office.asset"], [("asset_code", "=", "DEMO-ASSET-001")], {
        "asset_code": "DEMO-ASSET-001",
        "name": "项目部移动工作站",
        "category": "computer",
        "company_id": project.company_id.id,
        "location": "项目部综合办公室",
        "purchase_date": today,
        "purchase_value": 12800.0,
        "currency_id": project.company_id.currency_id.id,
        "status": "in_use",
        "note": "产品行政资产样本。",
    })

    contract = env.ref("smart_construction_demo.sc_demo_contract_out_001")
    if contract.project_id != project:
        raise ValueError("Demo contract project differs from its declared owner")
    variation = _ensure(
        env["sc.site.variation"],
        [("project_id", "=", project.id), ("subject", "=", "基础局部设计调整")],
        {
            "subject": "基础局部设计调整",
            "project_id": project.id,
            "contract_id": contract.id if contract else False,
            "event_type": "design_change",
            "variation_scope": "general",
            "event_date": today,
            "location": "1#楼基础施工区",
            "cause": "现场地质条件复核",
            "description": "根据现场复核结果调整局部基础做法。",
            "quantity_impact": "混凝土与钢筋工程量小幅调整。",
            "estimated_amount_delta": 18500.0,
            "currency_id": project.company_id.currency_id.id,
            "responsible_id": admin.id,
        },
    )
    if contract:
        _ensure(
            env["sc.contract.change"],
            [("contract_id", "=", contract.id), ("subject", "=", "基础变更价款调整")],
            {
                "contract_id": contract.id,
                "source_site_variation_id": variation.id,
                "subject": "基础变更价款调整",
                "change_type": "price",
                "change_date": today,
                "reason": "承接待审批的现场设计调整。",
                "before_summary": "按原合同基础做法执行。",
                "after_summary": "按复核后的基础做法执行。",
                "amount_delta": 18500.0,
            },
        )

    worker = _ensure(env["sc.labor.worker"], [
        ("project_id", "=", project.id), ("id_number", "=", "DEMO-LABOR-001")
    ], {
        "name": "王海峰",
        "project_id": project.id,
        "contractor_id": supplier.id,
        "labor_team": "钢筋班组",
        "trade": "钢筋工",
        "id_type": "other",
        "id_number": "DEMO-LABOR-001",
        "phone": "0838-DEMO-001",
        "entry_date": today,
        "state": "active",
        "note": "项目钢筋班组作业人员。",
    })
    _ensure(env["sc.labor.deduction"], [
        ("project_id", "=", project.id), ("reason", "=", "安全文明施工整改扣款")
    ], {
        "project_id": project.id,
        "contractor_id": supplier.id,
        "labor_team": worker.labor_team,
        "worker_id": worker.id,
        "deduction_type": "safety",
        "reason": "安全文明施工整改扣款",
        "amount": 200.0,
        "currency_id": project.company_id.currency_id.id,
        "state": "draft",
    })

    _ensure(env["sc.quality.acceptance"], [
        ("project_id", "=", project.id), ("name", "=", "首层钢筋隐蔽验收")
    ], {
        "name": "首层钢筋隐蔽验收",
        "project_id": project.id,
        "acceptance_type": "hidden_work",
        "acceptance_date": today,
        "location": "1#楼首层",
        "standard": "施工图及现行验收规范",
        "responsible_id": admin.id,
        "participant_ids": [(6, 0, [admin.id])],
        "result": "passed",
        "conclusion": "抽检项目符合要求，同意进入下一道工序。",
        "state": "draft",
    })

    inbound = env.ref(
        "smart_construction_demo.sc_demo_material_inbound_080_steel",
    )
    warehouse = inbound.warehouse_id
    location = (
        inbound.location_dest_id
        if inbound and "location_dest_id" in inbound._fields
        else warehouse.lot_stock_id
    )
    if warehouse and location:
        _ensure(env["sc.material.supplier.return"], [
            ("project_id", "=", project.id), ("reason", "=", "到货规格复核退货")
        ], {
            "project_id": project.id,
            "source_inbound_id": inbound.id if inbound else False,
            "supplier_id": inbound.supplier_id.id if inbound and inbound.supplier_id else supplier.id,
            "warehouse_id": warehouse.id,
            "source_location_id": location.id,
            "return_date": today,
            "reason": "到货规格复核退货",
            "responsible_id": admin.id,
            "state": "draft",
        })

    payroll = env.ref(
        "smart_construction_demo.sc_demo_hr_payroll_085_salary",
        raise_if_not_found=False,
    )
    if payroll and payroll.state == "done":
        _ensure(env["sc.hr.salary.payment"], [
            ("payroll_document_id", "=", payroll.id), ("payment_reference", "=", "DEMO-SALARY-PAY-001")
        ], {
            "payroll_document_id": payroll.id,
            "payment_date": today,
            "payment_amount": payroll.net_salary,
            "payment_method": "bank",
            "payment_reference": "DEMO-SALARY-PAY-001",
            "responsible_id": admin.id,
            "state": "draft",
            "note": "产品薪资发放样本。",
        })

    bid = env.ref("smart_construction_demo.sc_demo_tender_bid_086_complex")
    opportunity = _ensure(env["tender.opportunity"], [("code", "=", "DEMO-TO-001")], {
        "name": "城市更新配套工程招标",
        "code": "DEMO-TO-001",
        "company_id": project.company_id.id,
        "owner_id": owner.id,
        "contact_name": "赵春梅",
        "contact_phone": "0838-DEMO-002",
        "location": "四川省示范区",
        "publish_date": today,
        "deadline": fields.Datetime.now(),
        "estimated_amount": 3200000.0,
        "source": "产品招标公告",
        "qualification_requirements": "具备相应施工资质。",
        "project_id": project.id,
        "state": "draft",
    })
    if opportunity.state == "draft":
        opportunity.action_follow()
    if bid:
        document = _ensure(env["tender.document"], [
            ("bid_id", "=", bid.id), ("name", "=", "技术标响应文件")
        ], {
            "name": "技术标响应文件",
            "bid_id": bid.id,
            "document_type": "technical",
            "version": "V1.0",
            "responsible_id": admin.id,
            "deadline": fields.Datetime.now(),
            "note": "产品标书编制样本。",
            "state": "draft",
        })

        if document.state == "draft":
            document.action_start()

    _ensure(env["sc.tax.certificate.registration"], [
        ("company_id", "=", project.company_id.id),
        ("tax_report_management_no", "=", "DEMO-TAX-CERT-001"),
    ], {
        "company_id": project.company_id.id,
        "project_id": project.id,
        "taxpayer_name": project.company_id.name,
        "taxpayer_identifier": "DEMO-TAXPAYER-001",
        "tax_report_management_no": "DEMO-TAX-CERT-001",
        "cross_region_business_address": "四川省德阳市项目现场",
        "validity_start_date": today,
        "validity_end_date": fields.Date.add(today, months=6),
        "handler_id": env.ref("smart_construction_demo.user_sc_fin_mgr_01").id,
        "state": "draft",
        "note": "产品外经证样本。",
    })
    _ensure(env["sc.tax.filing"], [
        ("company_id", "=", project.company_id.id),
        ("period_start", "=", fields.Date.start_of(today, "month")),
        ("period_end", "=", fields.Date.end_of(today, "month")),
    ], {
        "company_id": project.company_id.id,
        "period_start": fields.Date.start_of(today, "month"),
        "period_end": fields.Date.end_of(today, "month"),
        "handler_id": env.ref("smart_construction_demo.user_sc_fin_mgr_01").id,
        "other_tax_adjustment": 0.0,
        "state": "draft",
        "note": "产品税务申报样本。",
    })

    env["ir.config_parameter"].sudo().set_param(
        "sc.seed.demo.formal_product_surfaces", fields.Datetime.now().isoformat()
    )


register(SeedStep(
    name="demo_formal_product_surfaces",
    description="Seed current formal product transaction and administration surfaces.",
    run=run,
))


def run_posted_journal(env):
    """One dedicated posted demo entry, authored through the ordinary manager."""
    from ...tools.scenario_loader import _demo_action_record

    company = env.ref("base.main_company")
    actor_xmlid = "smart_construction_demo.user_sc_accounting_manager_demo"
    Move = _demo_action_record(env, env["account.move"], "create", actor_xmlid).with_context(
        allowed_company_ids=company.ids)
    journal = Move.env["account.journal"].search([
        ("company_id", "=", company.id), ("type", "=", "general"), ("code", "=", "MISC")], limit=2)
    if len(journal) != 1:
        raise ValueError("Demo requires exactly one main-company MISC general journal")
    debit = env.ref("smart_construction_demo.sc_demo_account_receivable")
    credit = env.ref("smart_construction_demo.sc_demo_account_revenue")
    partner = env.ref("smart_construction_demo.sc_demo_partner_owner_001")
    assert debit.company_id == credit.company_id == company
    assert debit.account_type == "asset_receivable" and credit.account_type == "income"
    marker = "SC-DEMO-POSTED-JOURNAL-001"
    xmlid = "smart_construction_demo.sc_demo_posted_journal_001"
    registered = env.ref(xmlid, raise_if_not_found=False)
    if registered and (registered._name != "account.move" or not registered.exists()):
        raise ValueError("Demo journal XMLID must identify an existing account.move")
    move = Move.browse(registered.id) if registered else Move.browse()
    if not move:
        if env["account.move"].search_count([("ref", "=", marker)]):
            raise ValueError("Demo journal reference already exists without seed ownership")
        today = fields.Date.context_today(Move)
        move = Move.create({"move_type": "entry", "company_id": company.id,
            "journal_id": journal.id, "date": today, "ref": marker,
            "line_ids": [
                (0, 0, {"name": "示例工程收入确认", "account_id": debit.id,
                    "partner_id": partner.id, "date_maturity": today, "debit": 100.0, "credit": 0.0}),
                (0, 0, {"name": "示例工程收入确认", "account_id": credit.id,
                    "partner_id": partner.id, "debit": 0.0, "credit": 100.0}),
            ]})
        env["ir.model.data"].sudo().create({"module": "smart_construction_demo",
            "name": "sc_demo_posted_journal_001", "model": "account.move", "res_id": move.id, "noupdate": True})
    assert move.company_id == company and move.journal_id == journal
    assert move.ref == marker and move.move_type == "entry"
    assert len(move.line_ids) == 2
    assert sorted((line.account_id.id, line.debit, line.credit) for line in move.line_ids) == sorted([
        (debit.id, 100.0, 0.0), (credit.id, 0.0, 100.0)])
    assert all(line.partner_id == partner for line in move.line_ids)
    if move.state == "draft":
        move.action_post()
    assert move.state == "posted" and move.name and move.name != "/"
    print("[demo.posted_journal] id=%s state=%s lines=%s" % (move.id, move.state, move.line_ids.ids))


register(SeedStep(
    name="demo_posted_journal",
    description="Seed one owned ordinary-manager posted journal entry; leave existing drafts untouched.",
    run=run_posted_journal,
))
