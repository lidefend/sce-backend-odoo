# -*- coding: utf-8 -*-
"""Demo scenario tick executor (P4 delivery tooling).

Reads the demo scenario manifest and advances one business day per call. Role
steps produce a ``mail.activity`` todo on the anchor project for every active
internal user holding the declared role; ``system_fact`` steps have no bound
handler yet and are recorded as ``unbound`` (never silently executed). The
idempotency ledger and heartbeat live in ``ir.config_parameter``.
"""
from __future__ import annotations

import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import file_path


LEDGER_PARAM = "sc.demo.scenario.ledger"
HEARTBEAT_PARAM = "sc.demo.scenario.heartbeat"
SCAN_MODELS = (
    "payment.request",
    "sc.settlement.order",
    "construction.contract",
    "project.task",
    "project.progress.entry",
    "sc.material.acceptance",
    "sc.material.outbound",
    "sc.material.inbound",
)

# system_fact bindings: each demo-internal fact key must resolve to a real,
# verifiable product fact. ``kind=readback`` proves an already-seeded state
# through a public read; ``kind=lifecycle`` drives a seeded record through its
# own public action chain. A fact without a binding, or whose binding fails,
# stays ``unbound`` (never silently executed).
_FACT_BINDINGS = {
    "demo.scenario.fact.project_approved": {
        "kind": "project_lifecycle",
        "project_code": "DEMO-PJ-EXEC",
        "state": "in_progress",
    },
    "demo.scenario.fact.wbs_boq_published": {
        "kind": "readback",
        "model": "construction.work.breakdown",
        "project_code": "DEMO-PJ-EXEC",
    },
    "demo.scenario.fact.material_plan": {
        "kind": "lifecycle",
        "scenario": "s80_execution_management_surface",
        "record": "sc_demo_plan_080_master",
        "state": "in_progress",
    },
    "demo.scenario.fact.construction_log": {
        "kind": "lifecycle",
        "scenario": "s70_daily_business_surface",
        "record": "sc_demo_construction_diary_070_daily",
        "state": "confirmed",
    },
    "demo.scenario.fact.purchase_order": {
        "kind": "lifecycle",
        "scenario": "s80_execution_management_surface",
        "record": "sc_demo_material_purchase_request_080_steel",
        "state": "approved",
    },
    "demo.scenario.fact.material_arrival": {
        "kind": "lifecycle",
        "scenario": "s80_execution_management_surface",
        "record": "sc_demo_material_inbound_080_steel",
        "state": "received",
    },
}


class DemoScenarioTick(models.AbstractModel):
    _name = "demo.scenario.tick"
    _description = "Demo scenario tick executor"

    @api.model
    def _manifest(self) -> dict:
        path = file_path(
            "smart_construction_demo/data/scenario/demo_scenario_manifest.json"
        )
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    @api.model
    def _ledger(self) -> dict:
        raw = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(LEDGER_PARAM, "{}")
        )
        try:
            ledger = json.loads(raw or "{}")
        except ValueError:
            ledger = {}
        return ledger if isinstance(ledger, dict) else {}

    @api.model
    def _role_users(self, role_code: str):
        group = self.env.ref(
            f"smart_construction_core.group_sc_role_{role_code}",
            raise_if_not_found=False,
        )
        if not group:
            return self.env["res.users"]
        return self.env["res.users"].sudo().search(
            [
                ("groups_id", "in", group.id),
                ("active", "=", True),
                ("share", "=", False),
            ]
        )

    @api.model
    def _anchor_project(self, project_code: str):
        return (
            self.env["project.project"]
            .sudo()
            .search([("project_code", "=", project_code)], limit=1)
        )

    @api.model
    def _todo_activity_type_id(self):
        activity_type = self.env.ref(
            "mail.mail_activity_data_todo", raise_if_not_found=False
        )
        if activity_type:
            return activity_type.id
        first = self.env["mail.activity.type"].sudo().search([], limit=1)
        if not first:
            raise UserError(_("No mail activity type available for demo todos."))
        return first.id

    @api.model
    def _bind_system_fact(self, step: dict) -> tuple[str, str]:
        """Bind one demo-internal system fact to a verified product fact.

        Returns ``(status, reason)`` where status is ``advanced`` when the fact
        is provably true through a public action/read, or ``unbound`` when no
        binding exists or the binding cannot be proven. Never fabricates a fact.
        """
        intent = step["intent_or_action"]
        binding = _FACT_BINDINGS.get(intent)
        if not binding:
            return "unbound", "no_binding"
        try:
            if binding["kind"] == "readback":
                return self._readback_fact(binding)
            if binding["kind"] == "project_lifecycle":
                return self._project_lifecycle_fact(binding)
            return self._lifecycle_fact(binding)
        except Exception as exc:  # noqa: BLE001 - fail closed, never fabricate
            return "unbound", f"{type(exc).__name__}: {exc}"

    @api.model
    def _readback_fact(self, binding: dict) -> tuple[str, str]:
        project_code = binding.get("project_code")
        domain: list = []
        if project_code:
            if binding["model"] == "project.project":
                domain.append(("project_code", "=", project_code))
            else:
                domain.append(("project_id.project_code", "=", project_code))
        records = self.env[binding["model"]].sudo().search(domain)
        if not records:
            return "unbound", "no_record"
        states = binding.get("states")
        if states:
            field = binding.get("field") or getattr(records[0], "_state_field", "state")
            if not any(records.filtered(lambda r: r[field] in states)):
                return "unbound", f"state_not_in_{states}"
        return "advanced", binding["model"]

    @api.model
    def _project_lifecycle_fact(self, binding: dict) -> tuple[str, str]:
        from ..seed.steps.step_20_projects_demo import _apply_lifecycle

        project = (
            self.env["project.project"]
            .sudo()
            .search([("project_code", "=", binding["project_code"])], limit=1)
        )
        if not project:
            return "unbound", "no_record"
        _apply_lifecycle(project, binding["state"])
        if project.lifecycle_state != binding["state"]:
            return "unbound", f"state_{project.lifecycle_state}"
        return "advanced", binding["project_code"]

    @api.model
    def _lifecycle_fact(self, binding: dict) -> tuple[str, str]:
        from ..tools.scenario_loader import _advance_scenario_lifecycle

        _advance_scenario_lifecycle(self.env, binding["scenario"])
        record = self.env.ref(
            f"smart_construction_demo.{binding['record']}",
            raise_if_not_found=False,
        )
        if not record:
            return "unbound", "record_missing"
        field = getattr(record, "_state_field", "state")
        if record[field] != binding["state"]:
            return "unbound", f"state_{record[field]}_expected_{binding['state']}"
        return "advanced", binding["record"]

    @api.model
    def run_tick(self) -> dict:
        manifest = self._manifest()
        ledger = self._ledger()
        pending = [
            step
            for step in manifest["steps"]
            if step["idempotency_key"] not in ledger
        ]
        if not pending:
            return {
                "status": "up_to_date",
                "business_date": None,
                "todos": 0,
                "unbound": 0,
            }

        next_date = min(step["business_date"] for step in pending)
        day_steps = sorted(
            (step for step in pending if step["business_date"] == next_date),
            key=lambda step: (step["day_index"], step["sequence"]),
        )
        activity_type_id = self._todo_activity_type_id()
        anchor_model = self.env["ir.model"].sudo().search(
            [("model", "=", "project.project")], limit=1
        )
        if not anchor_model:
            raise UserError(_("ir.model missing for project.project"))
        todos = 0
        unbound = 0
        unbound_reasons: dict[str, str] = {}
        for step in day_steps:
            if step["actor_mode"] == "system_fact":
                status, reason = self._bind_system_fact(step)
                ledger[step["idempotency_key"]] = status
                if status == "advanced":
                    pass
                else:
                    unbound += 1
                    unbound_reasons[step["idempotency_key"]] = reason
                continue

            users = self._role_users(step["actor_role"])
            if not users:
                raise UserError(
                    _("No active internal user for role %s") % step["actor_role"]
                )
            project_code = (step.get("params") or {}).get("project_code") or ""
            project = self._anchor_project(project_code) if project_code else None
            if not project:
                raise UserError(
                    _("Anchor project missing for step %s") % step["step_key"]
                )
            for user in users:
                self.env["mail.activity"].sudo().create(
                    {
                        "res_model": "project.project",
                        "res_model_id": anchor_model.id,
                        "res_id": project.id,
                        "user_id": user.id,
                        "activity_type_id": activity_type_id,
                        "summary": step["expected_state"] or step["step_key"],
                        "note": step["intent_or_action"],
                    }
                )
            ledger[step["idempotency_key"]] = "todo"
            todos += 1

        self.env["ir.config_parameter"].sudo().set_param(
            LEDGER_PARAM, json.dumps(ledger, ensure_ascii=False)
        )
        self.env["ir.config_parameter"].sudo().set_param(
            HEARTBEAT_PARAM, fields.Datetime.now().isoformat()
        )
        return {
            "status": "advanced",
            "business_date": next_date,
            "todos": todos,
            "unbound": unbound,
            "unbound_reasons": unbound_reasons,
        }

    @api.model
    def _experience_logins(self) -> list[str]:
        path = file_path("smart_construction_demo/data/experience_users.json")
        with open(path, encoding="utf-8") as handle:
            config = json.load(handle)
        return config.get("logins", []) if isinstance(config, dict) else []

    @api.model
    def plan_experience_reset(self, logins=None) -> dict:
        """Compute, never execute, the scoped experience-reset scope.

        Resolves the demo-declared experience logins (or the caller-supplied
        override) to users and scans the bounded business models for records
        they authored or edited. Demo seed records (``smart_construction_demo``
        XMLIDs) must never be in that scope.
        """
        if logins is None:
            logins = self._experience_logins()
        users = (
            self.env["res.users"].sudo().search([("login", "in", logins)])
            if logins
            else self.env["res.users"].browse()
        )
        user_ids = sorted(users.ids)
        scope: dict[str, list[int]] = {}
        baseline_violations: list[dict] = []
        for model_name in SCAN_MODELS:
            if model_name not in self.env:
                continue
            model = self.env[model_name].sudo()
            authored = (
                model.search(
                    [
                        "|",
                        ("create_uid", "in", user_ids),
                        ("write_uid", "in", user_ids),
                    ]
                )
                if user_ids
                else model.browse()
            )
            if authored:
                scope[model_name] = sorted(authored.ids)
            baseline_ids = set(
                self.env["ir.model.data"]
                .sudo()
                .search(
                    [
                        ("module", "=", "smart_construction_demo"),
                        ("model", "=", model_name),
                    ]
                )
                .mapped("res_id")
            )
            violating = authored.filtered(lambda record: record.id in baseline_ids)
            if violating:
                baseline_violations.append(
                    {"model": model_name, "ids": sorted(violating.ids)}
                )
        return {
            "experience_user_ids": user_ids,
            "scope": scope,
            "baseline_violations": baseline_violations,
        }
