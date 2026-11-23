# -*- coding: utf-8 -*-
from types import SimpleNamespace

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.handlers.my_work_summary import MyWorkSummaryHandler
from odoo.addons.smart_construction_core.services.my_work_aggregate_service import (
    WorkItemAggregateService,
)
from odoo.addons.smart_construction_core.services.project_context_contract import (
    build_project_context,
)
from odoo.addons.smart_construction_core.services.project_creation_service import (
    ProjectCreationService,
)
from odoo.addons.smart_construction_core.services.project_execution_builders.project_execution_tasks_builder import (
    ProjectExecutionTasksBuilder,
)
from odoo.addons.smart_construction_core.services.project_dashboard_builders.project_metrics_builder import (
    ProjectMetricsBuilder,
)
from odoo.addons.smart_construction_core.services.project_dashboard_builders.project_progress_builder import (
    ProjectProgressBuilder,
)
from odoo.addons.smart_construction_core.services.project_execution_consistency_guard import (
    ProjectExecutionConsistencyGuard,
)
from odoo.addons.smart_construction_core.services.project_plan_bootstrap_builders.project_plan_tasks_builder import (
    ProjectPlanTasksBuilder,
)
from odoo.addons.smart_construction_core.services.project_task_state_support import (
    ProjectTaskStateSupport,
)


@tagged("post_install", "-at_install", "industry_business_model_02")
class TestIndustryBusinessModel02(TransactionCase):
    def _create_project(self, name):
        return self.env["project.project"].create(
            {
                "name": name,
                "manager_id": self.env.user.id,
                "user_id": self.env.user.id,
                "date_start": "2026-11-23",
            }
        )

    def _create_task(self, project, name, **values):
        data = {
            "name": name,
            "project_id": project.id,
            "user_ids": [Command.link(self.env.user.id)],
        }
        data.update(values)
        return self.env["project.task"].create(data)

    def test_project_creation_does_not_create_task(self):
        project = self._create_project("IB02 project without task")
        self.assertFalse(
            self.env["project.task"].search_count([("project_id", "=", project.id)])
        )
        before = self.env["project.task"].search_count([])
        summary = ProjectCreationService(self.env).post_create_bootstrap(project)
        self.assertEqual(self.env["project.task"].search_count([]), before)
        self.assertEqual(summary.get("project_tasks"), "optional")
        self.assertNotIn("project_task_root", summary)

    def test_execution_scope_allows_multiple_open_tasks(self):
        project = self._create_project("IB02 multiple open tasks")
        first = self._create_task(project, "Task A")
        second = self._create_task(project, "Task B")
        self.assertIn(first.state, self.env["project.task"].OPEN_STATES)
        self.assertIn(second.state, self.env["project.task"].OPEN_STATES)
        guard = ProjectExecutionConsistencyGuard(self.env)
        ok, reason, summary = guard.validate_scope(
            project,
            from_state="ready",
            to_state="in_progress",
        )
        self.assertTrue(ok, reason)
        self.assertEqual(summary.get("task_open_count"), 2)
        precheck = guard.readiness_precheck(project)
        keys = {row["key"] for row in precheck["checks"]}
        self.assertIn("execution_task", keys)
        self.assertNotIn("root_task", keys)
        self.assertNotIn("single_open_task", keys)
        self.assertFalse(
            precheck["summary"].get("project_execution_state_authoritative")
        )

    def test_project_context_uses_native_milestone(self):
        project = self._create_project("IB02 milestone context")
        project.write({"sc_execution_state": "done"})
        milestone = self.env["project.milestone"].create(
            {
                "name": "主体结构封顶",
                "project_id": project.id,
                "deadline": "2026-12-31",
            }
        )
        context = build_project_context(project)
        self.assertEqual(context.get("milestone"), milestone.display_name)
        self.assertEqual(context.get("milestone_label"), milestone.display_name)
        self.assertNotEqual(context.get("milestone"), "done")

    def test_execution_task_block_contains_only_project_tasks(self):
        project = self._create_project("IB02 task block")
        task = self._create_task(project, "On-site task")
        partner = self.env["res.partner"].create({"name": "IB02 partner"})
        tax = self.env["account.tax"].create(
            {
                "name": "IB02 sale tax",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "sale",
                "company_id": self.env.company.id,
            }
        )
        self.env["construction.contract"].create(
            {
                "subject": "IB02 contract pending",
                "project_id": project.id,
                "partner_id": partner.id,
                "state": "draft",
                "tax_id": tax.id,
            }
        )
        block = ProjectExecutionTasksBuilder(self.env).build(project=project)
        items = block["data"]["items"]
        self.assertEqual([item["source_model"] for item in items], ["project.task"])
        self.assertEqual(items[0]["task_id"], task.id)
        self.assertEqual(block["data"]["summary"]["source_model"], "project.task")
        self.assertEqual(block["data"]["summary"]["state_field"], "state")
        self.assertEqual(block["data"]["summary"]["explicit_count"], 1)
        self.assertEqual(items[0]["state"], task.state)

    def test_execution_task_block_uses_native_lifecycle_state(self):
        project = self._create_project("IB02 native state block")
        task = self._create_task(project, "Native lifecycle task")
        task.with_context(allow_transition=True).write({"sc_state": "done"})
        block = ProjectExecutionTasksBuilder(self.env).build(project=project)
        item = block["data"]["items"][0]
        self.assertEqual(item["state"], task.state)
        self.assertNotEqual(item["state"], "done")
        self.assertEqual(block["data"]["summary"]["open_count"], 1)

    def test_my_work_excludes_native_closed_task(self):
        project = self._create_project("IB02 closed task")
        task = self._create_task(project, "Closed task")
        task.write({"state": "1_done"})
        handler = MyWorkSummaryHandler(self.env, payload={})
        domain = handler._task_domain_for_user(self.env.user)
        self.assertFalse(
            self.env["project.task"].search_count(domain + [("id", "=", task.id)])
        )

    def test_legacy_workflow_todo_is_disabled_by_default(self):
        handler = MyWorkSummaryHandler(self.env, payload={})
        self.assertIsNone(handler._workflow_todo_domain(self.env.user))

    def test_work_item_aggregation_preserves_all_sources(self):
        rows = [
            {
                "id": 11,
                "title": "付款申请",
                "model": "payment.request",
                "record_id": 42,
                "source": "payment.request",
                "section": "todo",
                "priority": "medium",
                "action_key": "payment.request.open",
            },
            {
                "id": 12,
                "title": "付款审批",
                "model": "payment.request",
                "record_id": 42,
                "source": "tier.review",
                "section": "todo",
                "priority": "high",
                "action_key": "tier.review.approve",
            },
            {
                "id": 13,
                "title": "资料提醒",
                "model": "payment.request",
                "record_id": 42,
                "source": "mail.activity",
                "section": "todo",
                "priority": "medium",
                "action_key": "mail.activity.open",
            },
        ]
        aggregated = WorkItemAggregateService.aggregate_items(rows)
        self.assertEqual(len(aggregated), 1)
        item = aggregated[0]
        self.assertEqual(item["source_count"], 3)
        self.assertEqual(
            set(item["sources"]),
            {"payment.request", "tier.review", "mail.activity"},
        )
        self.assertEqual(item["action_key"], "tier.review.approve")
        self.assertEqual(len(item["source_refs"]), 3)

    def test_project_progress_and_task_completion_use_separate_native_facts(self):
        project = self._create_project("IB02 progress authority")
        done = self._create_task(project, "Done task")
        done.write({"state": "1_done"})
        canceled = self._create_task(project, "Canceled task")
        canceled.write({"state": "1_canceled"})
        overdue = self._create_task(
            project,
            "Overdue running task",
            date_deadline="2026-01-01",
        )
        self.assertEqual(overdue.state, "01_in_progress")

        wbs = self.env["construction.work.breakdown"].create(
            {"name": "IB02 progress WBS", "project_id": project.id}
        )
        self.env["project.progress.entry"].create(
            {
                "project_id": project.id,
                "wbs_id": wbs.id,
                "progress_rate": 63.0,
            }
        )
        self.env["project.milestone"].create(
            {
                "name": "IB02 delayed milestone",
                "project_id": project.id,
                "deadline": "2026-01-01",
            }
        )

        progress = ProjectProgressBuilder(self.env).build(project=project)["data"]
        self.assertEqual(progress["project_progress_percent"], 63.0)
        self.assertEqual(progress["task_completion_percent"], 50.0)
        self.assertEqual(progress["task_done"], 1)
        self.assertEqual(progress["task_cancelled"], 1)
        self.assertEqual(progress["task_blocked"], 0)
        self.assertEqual(progress["milestone_delay"], 1)

        metrics = ProjectMetricsBuilder(self.env).build(project=project)["data"]
        values = {row["key"]: row["value"] for row in metrics["items"]}
        self.assertEqual(values["progress_rate"], 63.0)
        self.assertEqual(values["task_completion_rate"], 50.0)

    def test_native_task_metrics_exclude_canceled_and_detect_waiting(self):
        metrics = ProjectTaskStateSupport.native_metrics(
            [
                SimpleNamespace(state="01_in_progress"),
                SimpleNamespace(state="04_waiting_normal"),
                SimpleNamespace(state="1_done"),
                SimpleNamespace(state="1_canceled"),
            ]
        )
        self.assertEqual(metrics["task_open_count"], 2)
        self.assertEqual(metrics["task_waiting_count"], 1)
        self.assertEqual(metrics["task_done_count"], 1)
        self.assertEqual(metrics["task_cancelled_count"], 1)
        self.assertEqual(metrics["task_completion_percent"], 33.33)

    def test_analytic_account_compatibility_fields_have_truthful_labels(self):
        for model_name in ("project.budget", "sc.project.document"):
            field = self.env[model_name]._fields["contract_id"]
            self.assertEqual(field.comodel_name, "account.analytic.account")
            self.assertEqual(field.string, "关联分析账户")

    def test_plan_nodes_reuse_wbs_as_the_task_relation_carrier(self):
        project = self._create_project("IB02 plan task boundary")
        plan = self.env["sc.plan"].create(
            {
                "name": "IB02 execution plan",
                "project_id": project.id,
                "company_id": self.env.company.id,
            }
        )
        wbs = self.env["construction.work.breakdown"].create(
            {"name": "IB02 work package", "project_id": project.id}
        )
        plan_line = self.env["sc.plan.line"].create(
            {
                "plan_id": plan.id,
                "name": "IB02 plan node",
                "node_type": "task",
                "wbs_id": wbs.id,
            }
        )
        first = self._create_task(project, "IB02 planned task 1", work_id=wbs.id)
        second = self._create_task(project, "IB02 planned task 2", work_id=wbs.id)
        self._create_task(project, "IB02 unplanned task")

        self.assertEqual(set(plan_line.task_ids.ids), {first.id, second.id})
        self.assertEqual(plan_line.task_count, 2)
        block = ProjectPlanTasksBuilder(self.env).build(project=project)
        items = block["data"]["items"]
        self.assertEqual({item["task_id"] for item in items}, {first.id, second.id})
        self.assertTrue(all(item["plan_line_id"] == plan_line.id for item in items))
        self.assertTrue(all(item["wbs_id"] == wbs.id for item in items))
        self.assertTrue(all(item["state"] for item in items))

        other_project = self._create_project("IB02 other WBS project")
        other_wbs = self.env["construction.work.breakdown"].create(
            {"name": "IB02 foreign work package", "project_id": other_project.id}
        )
        with self.assertRaises(ValidationError):
            plan_line.wbs_id = other_wbs

    def test_formal_settlement_order_is_the_project_close_authority(self):
        project = self._create_project("IB02 formal settlement authority")
        partner = self.env["res.partner"].create({"name": "IB02 settlement partner"})
        formal = self.env["sc.settlement.order"].create(
            {
                "name": "IB02 formal settlement",
                "project_id": project.id,
                "partner_id": partner.id,
                "settlement_type": "out",
            }
        )
        self.assertEqual(project.formal_settlement_ids, formal)
        self.assertFalse(project._sc_is_settlement_complete())
        blockers = project._workflow_lifecycle_blockers("warranty")
        self.assertTrue(any("未完成结算单" in row["message"] for row in blockers))

        legacy_project = self._create_project("IB02 legacy settlement only")
        self.env["project.settlement"].create(
            {
                "name": "IB02 legacy settlement",
                "project_id": legacy_project.id,
                "partner_id": partner.id,
                "type": "pay",
            }
        )
        self.assertTrue(legacy_project._sc_is_settlement_complete())
        self.assertFalse(
            any(
                "未完成结算单" in row["message"]
                for row in legacy_project._workflow_lifecycle_blockers("warranty")
            )
        )

    def test_boq_task_assignment_has_one_current_write_authority(self):
        project = self._create_project("IB02 BOQ task authority")
        task = self._create_task(project, "IB02 BOQ task")
        uom = self.env.ref("uom.product_uom_unit")
        version = self.env["project.boq.version"].create(
            {
                "name": "IB02 BOQ version",
                "code": "IB02-V1",
                "project_id": project.id,
            }
        )
        scalar_line = self.env["project.boq.line"].create(
            {
                "project_id": project.id,
                "version_id": version.id,
                "code": "IB02-001",
                "name": "IB02 scalar BOQ line",
                "uom_id": uom.id,
                "quantity": 2.0,
                "price": 10.0,
                "task_id": task.id,
            }
        )
        task.invalidate_recordset(
            ["boq_line_ids", "boq_quantity_total", "boq_amount_total", "boq_uom_id"]
        )
        self.assertIn(scalar_line, task.boq_line_ids)
        self.assertEqual(task.boq_quantity_total, 2.0)
        self.assertEqual(task.boq_amount_total, scalar_line.amount)

        legacy_line = self.env["project.boq.line"].create(
            {
                "project_id": project.id,
                "version_id": version.id,
                "code": "IB02-002",
                "name": "IB02 legacy BOQ line",
                "uom_id": uom.id,
                "quantity": 3.0,
                "price": 5.0,
            }
        )
        task.write({"legacy_boq_line_ids": [Command.link(legacy_line.id)]})
        task.invalidate_recordset(
            ["boq_line_ids", "boq_quantity_total", "boq_amount_total", "boq_uom_id"]
        )
        self.assertEqual(set(task.boq_line_ids.ids), {scalar_line.id, legacy_line.id})
        self.assertEqual(task.boq_quantity_total, 5.0)
