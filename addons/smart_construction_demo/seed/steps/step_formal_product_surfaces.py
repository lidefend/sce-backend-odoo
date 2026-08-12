# -*- coding: utf-8 -*-
"""Seed one honest, navigable sample for formal product pages added after V1."""

from odoo import fields

from ..registry import SeedStep, register


def _ensure(Model, domain, values):
    record = Model.sudo().search(domain, limit=1)
    return record or Model.sudo().create(values)


def run(env):
    project = env.ref("smart_construction_demo.sc_demo_project_001")
    owner = env.ref("smart_construction_demo.sc_demo_partner_owner_001")
    supplier = env.ref("smart_construction_demo.sc_demo_partner_vendor_steel")
    admin = env.ref("base.user_admin")
    today = fields.Date.context_today(env.user)

    _ensure(env["hr.job"], [("name", "=", "Demo 项目成本工程师")], {
        "name": "Demo 项目成本工程师",
        "company_id": project.company_id.id,
    })
    analytic_plan = env["account.analytic.plan"].sudo().search([], limit=1)
    if analytic_plan:
        analytic_account = _ensure(
            env["account.analytic.account"],
            [("code", "=", "DEMO-ANALYTIC-001")],
            {
                "name": "Demo 项目成本分析账户",
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
        "name": "Demo 项目部移动工作站",
        "category": "computer",
        "company_id": project.company_id.id,
        "location": "项目部综合办公室",
        "purchase_date": today,
        "purchase_value": 12800.0,
        "currency_id": project.company_id.currency_id.id,
        "status": "in_use",
        "note": "产品 Demo 行政资产样本。",
    })

    contract = env["construction.contract"].sudo().search(
        [("project_id", "=", project.id)], limit=1
    )
    variation = _ensure(
        env["sc.site.variation"],
        [("project_id", "=", project.id), ("subject", "=", "Demo 基础局部设计调整")],
        {
            "subject": "Demo 基础局部设计调整",
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
            [("contract_id", "=", contract.id), ("subject", "=", "Demo 基础变更价款调整")],
            {
                "contract_id": contract.id,
                "source_site_variation_id": variation.id,
                "subject": "Demo 基础变更价款调整",
                "change_type": "price",
                "change_date": today,
                "reason": "承接已确认的现场设计调整。",
                "before_summary": "按原合同基础做法执行。",
                "after_summary": "按复核后的基础做法执行。",
                "amount_delta": 18500.0,
            },
        )

    worker = _ensure(env["sc.labor.worker"], [
        ("project_id", "=", project.id), ("id_number", "=", "DEMO-LABOR-001")
    ], {
        "name": "Demo 钢筋工张师傅",
        "project_id": project.id,
        "contractor_id": supplier.id,
        "labor_team": "钢筋班组",
        "trade": "钢筋工",
        "id_type": "other",
        "id_number": "DEMO-LABOR-001",
        "phone": "13800000001",
        "entry_date": today,
        "state": "active",
        "note": "虚构的产品 Demo 人员。",
    })
    _ensure(env["sc.labor.deduction"], [
        ("project_id", "=", project.id), ("reason", "=", "Demo 安全文明施工整改扣款")
    ], {
        "project_id": project.id,
        "contractor_id": supplier.id,
        "labor_team": worker.labor_team,
        "worker_id": worker.id,
        "deduction_type": "safety",
        "reason": "Demo 安全文明施工整改扣款",
        "amount": 200.0,
        "currency_id": project.company_id.currency_id.id,
        "state": "draft",
    })

    _ensure(env["sc.quality.acceptance"], [
        ("project_id", "=", project.id), ("name", "=", "Demo 首层钢筋隐蔽验收")
    ], {
        "name": "Demo 首层钢筋隐蔽验收",
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
        raise_if_not_found=False,
    )
    warehouse = inbound.warehouse_id if inbound else env["stock.warehouse"].sudo().search([], limit=1)
    location = (
        inbound.location_dest_id
        if inbound and "location_dest_id" in inbound._fields
        else warehouse.lot_stock_id
    )
    if warehouse and location:
        _ensure(env["sc.material.supplier.return"], [
            ("project_id", "=", project.id), ("reason", "=", "Demo 到货规格复核退货")
        ], {
            "project_id": project.id,
            "source_inbound_id": inbound.id if inbound else False,
            "supplier_id": inbound.supplier_id.id if inbound and inbound.supplier_id else supplier.id,
            "warehouse_id": warehouse.id,
            "source_location_id": location.id,
            "return_date": today,
            "reason": "Demo 到货规格复核退货",
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
            "note": "产品 Demo 薪资发放样本。",
        })

    bid = env["tender.bid"].sudo().search([], limit=1)
    _ensure(env["tender.opportunity"], [("code", "=", "DEMO-TO-001")], {
        "name": "Demo 城市更新配套工程招标",
        "code": "DEMO-TO-001",
        "company_id": project.company_id.id,
        "owner_id": owner.id,
        "contact_name": "Demo 招标联系人",
        "contact_phone": "13800000002",
        "location": "四川省示范区",
        "publish_date": today,
        "deadline": fields.Datetime.now(),
        "estimated_amount": 3200000.0,
        "source": "产品 Demo 招标公告",
        "qualification_requirements": "具备相应施工资质。",
        "project_id": project.id,
        "state": "following",
    })
    if bid:
        _ensure(env["tender.document"], [
            ("bid_id", "=", bid.id), ("name", "=", "Demo 技术标响应文件")
        ], {
            "name": "Demo 技术标响应文件",
            "bid_id": bid.id,
            "document_type": "technical",
            "version": "V1.0",
            "responsible_id": admin.id,
            "deadline": fields.Datetime.now(),
            "note": "产品 Demo 标书编制样本。",
            "state": "preparing",
        })

    _ensure(env["sc.tax.certificate.registration"], [
        ("company_id", "=", project.company_id.id),
        ("tax_report_management_no", "=", "DEMO-TAX-CERT-001"),
    ], {
        "company_id": project.company_id.id,
        "project_id": project.id,
        "taxpayer_name": project.company_id.name,
        "taxpayer_identifier": "DEMO-TAXPAYER-001",
        "tax_report_management_no": "DEMO-TAX-CERT-001",
        "cross_region_business_address": "四川省示范区 Demo 项目现场",
        "validity_start_date": today,
        "validity_end_date": fields.Date.add(today, months=6),
        "handler_id": admin.id,
        "state": "draft",
        "note": "产品 Demo 外经证样本。",
    })
    _ensure(env["sc.tax.filing"], [
        ("company_id", "=", project.company_id.id),
        ("period_start", "=", fields.Date.start_of(today, "month")),
        ("period_end", "=", fields.Date.end_of(today, "month")),
    ], {
        "company_id": project.company_id.id,
        "period_start": fields.Date.start_of(today, "month"),
        "period_end": fields.Date.end_of(today, "month"),
        "handler_id": admin.id,
        "other_tax_adjustment": 0.0,
        "state": "draft",
        "note": "产品 Demo 税务申报样本。",
    })

    env["ir.config_parameter"].sudo().set_param(
        "sc.seed.demo.formal_product_surfaces", fields.Datetime.now().isoformat()
    )


register(SeedStep(
    name="demo_formal_product_surfaces",
    description="Seed current formal product transaction and administration surfaces.",
    run=run,
))
