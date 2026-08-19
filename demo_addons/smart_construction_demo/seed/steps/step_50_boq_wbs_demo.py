# -*- coding: utf-8 -*-
from odoo import fields

from ..registry import SeedStep, register


PROJECT_EXEC_CODE = "DEMO-PJ-EXEC"


def _projects(env):
    Project = env["project.project"].sudo()
    records = Project.search(
        [
            "|", "|", "|",
            ("project_code", "=", PROJECT_EXEC_CODE),
            ("name", "ilike", "展厅-"),
            ("name", "ilike", "演示项目"),
            ("project_code", "ilike", "DEMO-"),
        ]
    )
    return list({record.id: record for record in records}.values())


def _ensure_wbs(env, project, code, name, role, parent=None):
    Model = env["construction.work.breakdown"].sudo()
    plan = env["construction.wbs.plan"].sudo()._ensure_initial_plan(project)
    record = Model.search(
        [("project_id", "=", project.id), ("code", "=", code)], limit=1
    )
    values = {
        "project_id": project.id,
        "code": code,
        "name": name,
        "level_type": role,
        "plan_id": plan.id,
        "parent_id": parent.id if parent else False,
        "source_type": "manual",
    }
    if record:
        record.write(values)
        return record
    return Model.create(values)


def _ensure_cost_plan(env, project):
    Version = env["project.boq.version"].sudo()
    version = Version.search(
        [("project_id", "=", project.id), ("state", "=", "published")],
        order="published_at desc, id desc",
        limit=1,
    )
    if not version:
        return
    Plan = env["project.cost.plan"].sudo()
    plan = Plan.search(
        [("project_id", "=", project.id), ("version_code", "=", "DEMO-TARGET-V1")],
        limit=1,
    )
    if not plan:
        plan = Plan.create(
            {
                "name": "Demo 目标成本计划",
                "project_id": project.id,
                "boq_version_id": version.id,
                "version_code": "DEMO-TARGET-V1",
                "note": "人工、材料、机械、管理费和税费的产品 Demo 基线。",
            }
        )
    if not plan.line_ids:
        source = version.line_ids.filtered(lambda row: row.line_type == "item")[:1]
        if not source:
            return
        env["project.cost.plan.line"].sudo().with_context(
            skip_cost_tree_sync=True
        ).create(
            [
                {
                    "plan_id": plan.id,
                    "boq_line_id": source.id,
                    "cost_type": cost_type,
                    "name": label,
                    "unit_raw": source.uom_id.name,
                    "boq_quantity": source.quantity,
                    "budget_unit_consumption": 1.0,
                    "budget_unit_price": unit_price,
                    "target_unit_consumption": 1.0,
                    "target_unit_price": unit_price * 0.98,
                    "adjustment_ratio": 100.0,
                }
                for cost_type, label, unit_price in (
                    ("labor", "Demo 人工费", 20.0),
                    ("material", "Demo 材料费", 65.0),
                    ("machine", "Demo 机械费", 15.0),
                    ("overhead", "Demo 管理费", 8.0),
                    ("tax", "Demo 税金", 9.0),
                )
            ]
        )
        plan._rebuild_cost_tree()


def _ensure_location(env, project, code):
    Model = env["construction.location.breakdown"].sudo()
    record = Model.search(
        [("project_id", "=", project.id), ("code", "=", code)], limit=1
    )
    if record:
        return record
    return Model.create(
        {
            "project_id": project.id,
            "code": code,
            "name": "示范施工区域",
            "location_type": "zone",
        }
    )


def _ensure_section(env, project, code):
    Model = env["construction.contract.section"].sudo()
    record = Model.search(
        [("project_id", "=", project.id), ("code", "=", code)], limit=1
    )
    if record:
        return record
    return Model.create(
        {"project_id": project.id, "code": code, "name": "示范施工标段"}
    )


def _ensure_scope(env, project, wbs, location, section):
    Model = env["construction.execution.scope"].sudo()
    domain = [
        ("project_id", "=", project.id),
        ("wbs_id", "=", wbs.id),
        ("location_id", "=", location.id),
        ("contract_section_id", "=", section.id),
        ("active", "=", True),
    ]
    return Model.search(domain, limit=1) or Model.create(
        {
            "project_id": project.id,
            "wbs_id": wbs.id,
            "location_id": location.id,
            "contract_section_id": section.id,
            "source_type": "manual",
        }
    )


def run(env):
    Allocation = env["project.boq.allocation"].sudo()
    Boq = env["project.boq.line"].sudo()
    for project in _projects(env):
        prefix = project.project_code or f"SHOW-{project.id}"
        phase = _ensure_wbs(env, project, f"{prefix}-WBS", "示范实施阶段", "phase")
        account = _ensure_wbs(
            env, project, f"{prefix}-WBS-01", "示范控制账户", "control_account", phase
        )
        work_package = _ensure_wbs(
            env, project, f"{prefix}-WBS-01-01", "示范工作包", "work_package", account
        )
        location = _ensure_location(env, project, f"{prefix}-LBS-01")
        section = _ensure_section(env, project, f"{prefix}-SECTION-01")
        scope = _ensure_scope(env, project, work_package, location, section)
        for line in Boq.search(
            [("project_id", "=", project.id), ("line_type", "=", "item")]
        ):
            if Allocation.search_count(
                [("boq_line_id", "=", line.id), ("execution_scope_id", "=", scope.id)]
            ):
                continue
            Allocation.create(
                {
                    "boq_line_id": line.id,
                    "execution_scope_id": scope.id,
                    "allocation_basis": "ratio",
                    "allocation_ratio": 100.0,
                    "source_type": "manual",
                }
            )
        _ensure_cost_plan(env, project)

    env["ir.config_parameter"].sudo().set_param(
        "sc.seed.demo.boq_wbs", fields.Datetime.now().isoformat()
    )


register(
    SeedStep(
        name="demo_50_boq_wbs",
        description="Seed governed WBS, LBS, contract section and BOQ allocations.",
        run=run,
    )
)
