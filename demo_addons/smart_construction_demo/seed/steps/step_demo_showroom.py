# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import UserError

from ..registry import SeedStep, register
from ..business_roles import business_model, project_actor, prepare_project, ensure_manual_boq_analysis
from ..tier_flow import advance_settlement, ensure_project_initiation_approved


SHOWROOM_PROJECTS = [
    {"name": "展厅-智能制造示范项目", "state": "in_progress", "with_chain": True},
    {"name": "展厅-市政工程样板段", "state": "closing", "with_chain": True},
    {"name": "展厅-工业园区建设一期", "state": "warranty", "with_chain": True},
    {"name": "展厅-绿色建材基地", "state": "in_progress", "with_chain": True},
    {"name": "展厅-智慧园区运营中心", "state": "in_progress", "with_chain": False},
    {"name": "展厅-产线升级改造工程", "state": "done", "with_chain": False},
    {"name": "展厅-城市更新综合体", "state": "closing", "with_chain": False},
    {"name": "展厅-科技研发中心", "state": "warranty", "with_chain": False},
    {"name": "展厅-海绵城市示范区", "state": "done", "with_chain": False},
    {"name": "展厅-装配式住宅试点", "state": "in_progress", "with_chain": False},
    {"name": "展厅-停工整改样板", "state": "paused", "with_chain": False},
]


def _complete_settlement(settlement):
    return advance_settlement(settlement, complete=True)

TASKS_PER_PROJECT = 12


def _get_demo_user(env, login):
    return env["res.users"].sudo().search([("login", "=", login)], limit=1)


def _ensure_boq(env, project, idx):
    Boq = business_model(env, "project.boq.line")
    if Boq.search_count([("project_id", "=", project.id)]) > 0:
        return
    Version = business_model(env, "project.boq.version")
    version = Version.search(
        [
            ("project_id", "=", project.id),
            ("source_type", "=", "contract"),
            ("code", "=", "SHOWROOM-V1"),
        ],
        limit=1,
    )
    if not version:
        version = Version.create(
            {
                "name": "展厅合同清单 V1",
                "code": "SHOWROOM-V1",
                "project_id": project.id,
                "source_type": "contract",
                "note": "产品 Demo 展厅的可重放清单版本。",
            }
        )
    uom_unit = env.ref("uom.product_uom_unit")
    code_prefix = f"SR-{idx:02d}"
    line = Boq.create(
        {
            "version_id": version.id,
            "project_id": project.id,
            "code": f"{code_prefix}-001",
            "name": f"{project.name}-清单项",
            "uom_id": uom_unit.id,
            "quantity": 10.0,
            "price": 120.0,
            "section_type": "building",
        }
    )
    ensure_manual_boq_analysis(env, line, 120.0)
    if version.state == "draft":
        version.action_validate()
    if version.state == "validated":
        version.action_publish()


def _ensure_tasks(env, project, user, target):
    Task = business_model(env, "project.task")
    existing = Task.search([("project_id", "=", project.id)])
    if len(existing) >= target:
        return
    start = len(existing) + 1
    for i in range(start, target + 1):
        vals = {
            "name": f"{project.name}-任务 {i:02d}",
            "project_id": project.id,
        }
        if user:
            vals["user_ids"] = [(6, 0, [user.id])]
        Task.create(vals)


def _ensure_lifecycle(project, target_state):
    project = project_actor(project)
    if project.lifecycle_state != "draft":
        return
    # 启动项目的前置事实是立项已通过；种子只调用产品自己的提交动作，
    # 未配置审批模板时该动作本身完成立项，配置了模板则走真实审批链。
    ensure_project_initiation_approved(project)
    if target_state == "in_progress":
        project.action_set_lifecycle_state("in_progress")
    elif target_state == "paused":
        project.action_set_lifecycle_state("paused")
    elif target_state == "closing":
        project.action_set_lifecycle_state("in_progress")
        project.action_set_lifecycle_state("closing")
    elif target_state == "done":
        project.action_set_lifecycle_state("in_progress")
        project.action_set_lifecycle_state("done")
    elif target_state == "warranty":
        project.action_set_lifecycle_state("in_progress")
        project.action_set_lifecycle_state("done")
        project.action_set_lifecycle_state("warranty")


def _ensure_project_prereqs(env, project):
    vals = {}
    if not project.owner_id:
        partner = env.ref("smart_construction_demo.seed_partner_contract", raise_if_not_found=False)
        if not partner:
            partner = env["res.partner"].sudo().create({"name": "Demo-业主单位"})
        vals["owner_id"] = partner.id
        if not project.partner_id:
            vals["partner_id"] = partner.id
    elif not project.partner_id:
        vals["partner_id"] = project.owner_id.id
    if not project.location:
        vals["location"] = "示范区"
    if vals:
        project.write(vals)


def _ensure_purchase_order(env, settlement):
    from .step_40_contracts_demo import _ensure_purchase_order as ensure_purchase
    return ensure_purchase(env, settlement)


def _ensure_contract_chain(env, project, idx):
    partner = env.ref("smart_construction_demo.seed_partner_contract", raise_if_not_found=False)
    if not partner:
        partner = env["res.partner"].sudo().create({"name": "Demo-合同相对方"})

    Contract = business_model(env, "construction.contract")
    tax = env.ref("smart_construction_seed.tax_purchase_13", raise_if_not_found=False)
    if not tax:
        tax = Contract._get_default_tax("in")

    subject = f"展厅合同-支出-{idx:02d}"
    contract = Contract.search(
        [("subject", "=", subject), ("project_id", "=", project.id)],
        limit=1,
    )
    if not contract:
        contract = Contract.create(
            {
                "subject": subject,
                "type": "in",
                "project_id": project.id,
                "partner_id": partner.id,
                "tax_id": tax.id if tax else False,
                "date_contract": fields.Date.context_today(env.user),
            }
        )

    Settlement = business_model(env, "sc.settlement.order")
    Line = business_model(env, "sc.settlement.order.line")
    settle_name = f"SHOW-SO-{idx:02d}"
    settlement = Settlement.search([("name", "=", settle_name)], limit=1)
    if not settlement:
        settlement = Settlement.create(
            {
                "name": settle_name,
                "project_id": project.id,
                "contract_id": contract.id,
                "partner_id": partner.id,
                "settlement_type": "out",
                "note": "seed:demo_showroom",
            }
        )
    if not settlement.line_ids:
        Line.create(
            {
                "settlement_id": settlement.id,
                "name": "展厅-结算行",
                "qty": 1.0,
                "price_unit": 100.0,
            }
        )
    _ensure_purchase_order(env, settlement)
    _complete_settlement(settlement)

    Payment = business_model(env, "payment.request")
    pay_name = f"SHOW-PR-{idx:02d}"
    payment = Payment.search([("name", "=", pay_name)], limit=1)
    if not payment:
        Payment.create(
            {
                "name": pay_name,
                "type": "pay",
                "project_id": project.id,
                "contract_id": contract.id,
                "settlement_id": settlement.id,
                "partner_id": partner.id,
                "amount": 50.0,
                "note": "seed:demo_showroom",
            }
        )


def run(env):
    Project = business_model(env, "project.project")
    demo_pm = _get_demo_user(env, "demo_pm")
    # project.company_id is a stored compute derived from the analytic
    # account or the partner's company; a name-only create leaves it empty,
    # which later breaks company-scoped facts (e.g. funding baselines that
    # require an explicit company/currency owner).
    seed_company_id = env.ref("base.main_company").id
    for idx, spec in enumerate(SHOWROOM_PROJECTS, start=1):
        project = Project.search([("name", "=", spec["name"])], limit=1)
        created = False
        if not project:
            project = Project.create(
                {"name": spec["name"], "company_id": seed_company_id}
            )
            created = True
        prepare_project(env, project)
        _ensure_boq(env, project, idx)
        _ensure_tasks(env, project, demo_pm, TASKS_PER_PROJECT)
        _ensure_project_prereqs(env, project)
        if spec["with_chain"]:
            _ensure_contract_chain(env, project, idx)
        if created or project.lifecycle_state == "draft":
            _ensure_lifecycle(project, spec["state"])

    # The cockpit scenario is loaded before the showroom projects exist on a
    # freshly created tenant.  Reconcile its business facts only after the
    # authoritative showroom set has been established.  The model method is
    # idempotent and remains the single owner of those facts.
    env["project.project"].sc_demo_seed_cockpit_round2()

    env["ir.config_parameter"].sudo().set_param("sc.seed.demo_showroom", "1")
    return {"ok": True, "projects": len(SHOWROOM_PROJECTS)}


register(
    SeedStep(
        name="demo_showroom",
        description="Create showroom-friendly projects, tasks, and happy-path docs.",
        run=run,
    )
)
