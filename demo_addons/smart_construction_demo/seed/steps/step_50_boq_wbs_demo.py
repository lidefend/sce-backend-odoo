# -*- coding: utf-8 -*-
from odoo import fields

from ..registry import SeedStep, register
from ..business_roles import business_model, project_actor, prepare_project, write_if_changed


PROJECT_EXEC_CODE = "DEMO-PJ-EXEC"


def _projects(env):
    Project = business_model(env, "project.project")
    records = Project.search(
        [
            "|", "|",
            ("project_code", "=", PROJECT_EXEC_CODE),
            ("name", "ilike", "展厅-"),
            ("project_code", "ilike", "DEMO-"),
        ]
    )
    return list({record.id: record for record in records}.values())


def _ensure_wbs(env, project, code, name, role, parent=None):
    Model = business_model(env, "construction.work.breakdown")
    record = Model.search(
        [("project_id", "=", project.id), ("code", "=", code)], limit=1
    )
    values = {
        "project_id": project.id,
        "code": code,
        "name": name,
        "level_type": role,
        "parent_id": parent.id if parent else False,
        "source_type": "manual",
    }
    if record:
        write_if_changed(record, values)
        return record
    return Model.create(values)


def _ensure_cost_plan(env, project):
    Version = business_model(env, "project.boq.version")
    version = Version.search(
        [("project_id", "=", project.id), ("state", "=", "published")],
        order="published_at desc, id desc",
        limit=1,
    )
    if not version:
        return
    Plan = business_model(env, "project.cost.plan")
    plan = Plan.search(
        [("project_id", "=", project.id), ("version_code", "=", "DEMO-TARGET-V1")],
        limit=1,
    )
    if not plan:
        plan = Plan.create(
            {
                "name": "目标成本计划",
                "project_id": project.id,
                "boq_version_id": version.id,
                "version_code": "DEMO-TARGET-V1",
                "note": "由已发布清单的手工单项材料分析生成的目标成本基线。",
            }
        )
    if not plan.line_ids:
        plan.action_generate_from_boq()
    if not plan.line_ids or any(not line.analysis_id for line in plan.line_ids):
        raise ValueError("Demo cost plan must retain its real analysis source")


def _ensure_location(env, project, code):
    Model = business_model(env, "construction.location.breakdown")
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
    Model = business_model(env, "construction.contract.section")
    record = Model.search(
        [("project_id", "=", project.id), ("code", "=", code)], limit=1
    )
    if record:
        return record
    return Model.create(
        {"project_id": project.id, "code": code, "name": "示范施工标段"}
    )


def _ensure_scope(env, project, wbs, location, section):
    Model = business_model(env, "construction.execution.scope")
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
    Allocation = business_model(env, "project.boq.allocation")
    Boq = business_model(env, "project.boq.line")
    for project in _projects(env):
        prepare_project(env, project)
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
            # Scene XML carriers (e.g. s79 fire-pipe) already declare a full
            # 100% allocation for their own BOQ lines. A second allocation to
            # the showroom scope would push the cumulative quantity past the
            # source quantity and fail the product's allocation-bounds check.
            # Skip any item that already carries an active allocation instead
            # of only skipping the same scope.
            if Allocation.search_count(
                [("boq_line_id", "=", line.id), ("active", "=", True)]
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
