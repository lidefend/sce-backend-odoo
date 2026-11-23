# -*- coding: utf-8 -*-
"""Read-only INDUSTRY-BUSINESS-MODEL-02 data and relation inventory."""

import json


def _count(env, model_name, domain=None):
    if model_name not in env:
        return None
    return int(env[model_name].sudo().search_count(domain or []))


def _group(env, model_name, field_name, domain=None):
    if model_name not in env or field_name not in env[model_name]._fields:
        return {}
    rows = env[model_name].sudo().read_group(
        domain or [],
        [field_name],
        [field_name],
        lazy=False,
    )
    result = {}
    for row in rows:
        value = row.get(field_name)
        if isinstance(value, (list, tuple)):
            value = value[0] if value else False
        key = str(value) if value not in (False, None) else "false"
        result[key] = int(row.get("__count") or 0)
    return result


def _scalar(env, sql):
    env.cr.execute(sql)
    row = env.cr.fetchone()
    return int((row or [0])[0] or 0)


def _contract_content_readback(env, task):
    from odoo.addons.smart_construction_core.services.project_context_contract import (
        build_project_context,
    )
    from odoo.addons.smart_construction_core.services.project_dashboard_builders.project_progress_builder import (
        ProjectProgressBuilder,
    )
    from odoo.addons.smart_construction_core.services.project_execution_service import (
        ProjectExecutionService,
    )

    sample = task.search([("project_id", "!=", False)], order="id desc", limit=1)
    if not sample:
        return {"status": "not_applicable", "reason": "no_project_task"}
    project = sample.project_id
    block = ProjectExecutionService(env).build_block(
        "execution_tasks",
        project=project,
        context={},
    )
    summary = (block.get("data") or {}).get("summary") or {}
    items = (block.get("data") or {}).get("items") or []
    item_sources = sorted({str(item.get("source_model") or "") for item in items})
    item_states = {
        int(item.get("task_id") or 0): str(item.get("state") or "")
        for item in items
    }
    task_states = {
        int(row.id): str(row.state or "")
        for row in task.browse([task_id for task_id in item_states if task_id > 0])
    }
    project_context = build_project_context(project)
    progress = (ProjectProgressBuilder(env).build(project=project).get("data") or {})
    budget_contract = env["project.budget"]._fields["contract_id"]
    document_contract = env["sc.project.document"]._fields["contract_id"]
    result = {
        "status": "passed",
        "project_id": int(project.id),
        "task_id": int(sample.id),
        "block_key": str(block.get("block_key") or ""),
        "block_state": str(block.get("state") or ""),
        "source_model": str(summary.get("source_model") or ""),
        "state_field": str(summary.get("state_field") or ""),
        "item_sources": item_sources,
        "item_states_match_orm": item_states == task_states,
        "project_progress_percent": float(progress.get("project_progress_percent") or 0.0),
        "task_completion_percent": float(progress.get("task_completion_percent") or 0.0),
        "budget_contract_model": budget_contract.comodel_name,
        "budget_contract_label": str(budget_contract.string or ""),
        "document_contract_model": document_contract.comodel_name,
        "document_contract_label": str(document_contract.string or ""),
        "milestone": str(project_context.get("milestone") or ""),
    }
    if (
        result["block_key"] != "block.project.execution_tasks"
        or result["block_state"] not in {"ready", "empty"}
        or result["source_model"] != "project.task"
        or result["state_field"] != "state"
        or any(source != "project.task" for source in item_sources)
        or not result["item_states_match_orm"]
        or result["budget_contract_model"] != "account.analytic.account"
        or result["budget_contract_label"] != "关联分析账户"
        or result["document_contract_model"] != "account.analytic.account"
        or result["document_contract_label"] != "关联分析账户"
    ):
        result["status"] = "failed"
    return result


def build_report(env):
    project = env["project.project"].sudo()
    task = env["project.task"].sudo()
    plan_line_model = env["sc.plan.line"].sudo() if "sc.plan.line" in env else None
    wbs = env["construction.work.breakdown"].sudo()

    projects_with_tasks = _scalar(
        env,
        """
        SELECT count(DISTINCT project_id)
          FROM project_task
         WHERE project_id IS NOT NULL
        """,
    )
    projects_with_multiple_tasks = _scalar(
        env,
        """
        SELECT count(*)
          FROM (
              SELECT project_id
                FROM project_task
               WHERE project_id IS NOT NULL
               GROUP BY project_id
              HAVING count(*) > 1
          ) grouped
        """,
    )

    root_tasks = task.search([
        "|",
        ("name", "ilike", "项目根任务"),
        ("name", "ilike", "Project Root Task"),
    ])

    plan_without_task_relation = {
        "task_field_present": bool(plan_line_model and "task_id" in plan_line_model._fields),
        "task_ids_field_present": bool(plan_line_model and "task_ids" in plan_line_model._fields),
    }

    predecessor_relation_exists = False
    try:
        env.cr.execute(
            "SELECT to_regclass('public.sc_plan_line_predecessor_rel') IS NOT NULL"
        )
        predecessor_relation_exists = bool((env.cr.fetchone() or [False])[0])
    except Exception:
        predecessor_relation_exists = False

    boq_dual = {}
    try:
        boq_dual = {
            "boq_task_id_non_null": _scalar(
                env,
                "SELECT count(*) FROM project_boq_line WHERE task_id IS NOT NULL",
            ),
            "task_boq_relation_rows": _scalar(
                env,
                "SELECT count(*) FROM project_task_boq_rel",
            ),
            "boq_task_id_missing_relation": _scalar(
                env,
                """
                SELECT count(*)
                  FROM project_boq_line b
                 WHERE b.task_id IS NOT NULL
                   AND NOT EXISTS (
                       SELECT 1
                         FROM project_task_boq_rel r
                        WHERE r.boq_id = b.id
                          AND r.task_id = b.task_id
                   )
                """,
            ),
            "relation_missing_boq_task_id": _scalar(
                env,
                """
                SELECT count(*)
                  FROM project_task_boq_rel r
                  JOIN project_boq_line b ON b.id = r.boq_id
                 WHERE b.task_id IS DISTINCT FROM r.task_id
                """,
            ),
        }
    except Exception as exc:
        boq_dual = {"error": exc.__class__.__name__}

    report = {
        "schema": "industry_business_model_02_data_audit/v1",
        "database": str(env.cr.dbname),
        "project_task": {
            "project_count": _count(env, "project.project"),
            "task_count": _count(env, "project.task"),
            "projects_with_tasks": projects_with_tasks,
            "projects_with_multiple_tasks": projects_with_multiple_tasks,
            "root_task_count": len(root_tasks),
            "sc_state": _group(env, "project.task", "sc_state"),
            "native_state": _group(env, "project.task", "state"),
            "project_id": _group(env, "project.task", "project_id"),
            "sc_execution_state": _group(env, "project.project", "sc_execution_state"),
        },
        "plan_task_boundary": {
            "plan_count": _count(env, "sc.plan"),
            "plan_line_count": _count(env, "sc.plan.line"),
            "node_type": _group(env, "sc.plan.line", "node_type"),
            "state": _group(env, "sc.plan.line", "state"),
            "with_predecessor": (
                _scalar(
                    env,
                    "SELECT count(DISTINCT line_id) FROM sc_plan_line_predecessor_rel",
                )
                if predecessor_relation_exists
                else None
            ),
            "predecessor_relation_rows": (
                _scalar(env, "SELECT count(*) FROM sc_plan_line_predecessor_rel")
                if predecessor_relation_exists
                else None
            ),
            "predecessor_relation_exists": predecessor_relation_exists,
            **plan_without_task_relation,
        },
        "wbs_task_boundary": {
            "wbs_count": _count(env, "construction.work.breakdown"),
            "wbs_with_tasks": _scalar(
                env,
                """
                SELECT count(DISTINCT work_id)
                  FROM project_task
                 WHERE work_id IS NOT NULL
                """,
            )
            ,
            "tasks_without_wbs": _scalar(
                env,
                "SELECT count(*) FROM project_task WHERE work_id IS NULL",
            ),
        },
        "settlement_authority": {
            "legacy_project_settlement_count": _count(env, "project.settlement"),
            "legacy_project_settlement_state": _group(
                env, "project.settlement", "state"
            ),
            "formal_settlement_order_count": _count(env, "sc.settlement.order"),
            "formal_settlement_order_state": _group(
                env, "sc.settlement.order", "state"
            ),
        },
        "boq_task_relation": boq_dual,
        "contract_field_semantics": {
            "budget_contract_id_non_null": _count(
                env,
                "project.budget",
                [("contract_id", "!=", False)],
            ),
            "document_contract_id_non_null": _count(
                env,
                "sc.project.document",
                [("contract_id", "!=", False)],
            ),
        },
        "contract_content": _contract_content_readback(env, task),
    }
    if report["contract_content"].get("status") == "failed":
        raise AssertionError("contract content readback mismatch")
    return report


report = build_report(env)
env.cr.rollback()
print(
    "INDUSTRY_BUSINESS_MODEL_02_DATA_AUDIT_JSON="
    + json.dumps(report, ensure_ascii=False, sort_keys=True)
)
