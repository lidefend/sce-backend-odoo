#!/usr/bin/env python3
"""One-off demo data baseline repair (P4 ops tooling).

Aligns the existing demo projects with the unified ``DEMO-PJ-`` code scheme and
assigns a real, named person as the project owner/manager instead of OdooBot or
a capability-seat account. It also promotes the s69 payment-ledger contract
through its real confirm action so the historical settlement/payment chain is
backed by an in-force contract. The XML/seed carriers are the long-term source
of truth; this script only repairs rows created before those changes.
"""
from __future__ import annotations

from odoo.exceptions import UserError


CODE_MAP = {
    "SC-DEY-2025-001": "DEMO-PJ-001",
    "PRJ260002": "DEMO-PJ-002",
    "S65-COST-2025-001": "DEMO-PJ-065",
    "S69-PAY-2025-001": "DEMO-PJ-069",
    "S73-RISK-2025-001": "DEMO-PJ-073",
}

# Showroom project codes are keyed by the business name so an auto-numbered
# existing row can be re-labelled without guessing its XMLID.
SHOWROOM_CODE_BY_NAME = {
    "德阳经开区智能制造产业园项目": "DEMO-PJ-201",
    "旌阳区市政道路提档升级工程": "DEMO-PJ-202",
    "罗江工业园区标准厂房一期": "DEMO-PJ-203",
    "广汉绿色建材产业基地项目": "DEMO-PJ-204",
    "天府数谷智慧园区运营中心": "DEMO-PJ-205",
    "东汽数字化产线改造工程": "DEMO-PJ-206",
    "旌湖片区城市更新综合体": "DEMO-PJ-207",
    "德阳高新区科技研发中心": "DEMO-PJ-208",
    "岷江路海绵城市示范区工程": "DEMO-PJ-209",
    "中江装配式住宅试点项目": "DEMO-PJ-210",
    "什邡产业园区停缓建整改项目": "DEMO-PJ-211",
}


def _env():
    return globals()["env"]


def run() -> dict:
    env = _env()
    pm_person = env["res.users"].sudo().search([("login", "=", "pm1")], limit=1)
    if not pm_person:
        raise UserError("demo project identity repair requires the real user 'pm1'")

    applied = {
        "codes": 0,
        "owners": 0,
        "test_residue_deleted": 0,
        "contracts_confirmed": 0,
        "orphan_drafts_deleted": 0,
    }
    projects = env["project.project"].sudo().search(
        ["|", ("project_code", "ilike", "DEMO-"), ("project_code", "in", list(CODE_MAP))]
    )
    # Include showroom projects regardless of their auto-numbered code.
    projects |= env["project.project"].sudo().search(
        [("name", "in", list(SHOWROOM_CODE_BY_NAME))]
    )

    for project in projects:
        vals = {}
        expected = CODE_MAP.get(project.project_code)
        if expected and project.project_code != expected:
            vals["project_code"] = expected
        else:
            by_name = SHOWROOM_CODE_BY_NAME.get(project.name)
            if by_name and project.project_code != by_name:
                vals["project_code"] = by_name
        if project.user_id.id != pm_person.id:
            vals["user_id"] = pm_person.id
        if not project.manager_id or project.manager_id.id != pm_person.id:
            vals["manager_id"] = pm_person.id
        if vals:
            project.write(vals)
            if "project_code" in vals:
                applied["codes"] += 1
            if "user_id" in vals:
                applied["owners"] += 1

    # Test-residue shells (成本并发隔离测试项目) are created by a product test
    # and carry no business records; they are not demo data and must not remain
    # in the demo database.
    test_residue = env["project.project"].sudo().search(
        [("name", "=", "成本并发隔离测试项目")]
    )
    # Delete dependent test-residue records first to satisfy foreign keys.
    for model_name in ("project.cost.period",):
        if model_name in env:
            dependent = env[model_name].sudo().search(
                [("project_id", "in", test_residue.ids)]
            )
            if dependent:
                dependent.unlink()
    for project in test_residue:
        has_records = any(
            env[model].sudo().search_count([("project_id", "=", project.id)]) > 0
            for model in (
                "project.task",
                "construction.contract",
                "sc.settlement.order",
                "payment.request",
                "project.cost.ledger",
                "project.progress.entry",
                "project.boq.version",
                "construction.work.breakdown",
                "project.budget",
            )
            if model in env
        )
        if has_records:
            raise UserError(
                f"test-residue project {project.id} has associated records; "
                "refuse to delete before owning-layer cleanup"
            )
        project.unlink()
        applied["test_residue_deleted"] += 1

    # s69 payment-ledger lifecycle: the XML carrier only creates the contract
    # draft, while the settlement is already approved and the payment done. The
    # contract must therefore be in-force; confirm it through the product's own
    # action and tier chain instead of writing a state field directly.
    contract_069 = env.ref(
        "smart_construction_demo.sc_demo_contract_in_069_payment", raise_if_not_found=False
    )
    if contract_069 and contract_069.state == "draft":
        from odoo.addons.smart_construction_demo.seed.steps.step_40_contracts_demo import _confirm_contract
        _confirm_contract(contract_069)
        applied["contracts_confirmed"] = 1

    # Experience-test residue: 1-yuan drafts created by the demo finance seat
    # carry no contract/settlement and pollute the showcase project. They are
    # not business facts and must be removed, never displayed as a main case.
    orphan_drafts = env["payment.request"].sudo().search(
        [
            ("project_id", "=", contract_069.project_id.id),
            ("state", "=", "draft"),
            ("amount", "=", 1.0),
            ("contract_id", "=", False),
            ("settlement_id", "=", False),
        ]
    )
    if orphan_drafts:
        orphan_drafts.unlink()
        applied["orphan_drafts_deleted"] = len(orphan_drafts)

    env.cr.commit()
    return applied


print("PROJECT_IDENTITY_REPAIR " + str(run()))
