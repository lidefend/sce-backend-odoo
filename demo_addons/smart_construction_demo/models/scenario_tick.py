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
        for step in day_steps:
            if step["actor_mode"] == "system_fact":
                ledger[step["idempotency_key"]] = "unbound"
                unbound += 1
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
