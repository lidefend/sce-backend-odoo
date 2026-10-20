# -*- coding: utf-8 -*-
"""Read-only runtime preflight for the demo scenario tick.

It proves, against the live demo database, that every declared step is
executable before the tick runner writes anything: each non-system actor role
resolves to an active internal demo user, every bound product action is
callable, and ``system_fact`` steps remain explicitly demo-internal.
"""
from __future__ import annotations

import json

from odoo.tools.misc import file_path
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "-standard", "demo_scenario_tick")
class TestDemoScenarioTickPreflight(TransactionCase):
    def test_manifest_roles_and_actions_resolve(self):
        manifest_path = file_path(
            "smart_construction_demo/data/scenario/demo_scenario_manifest.json"
        )
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)

        for raw in manifest["steps"]:
            mode = raw["actor_mode"]
            role = raw["actor_role"]
            action = raw["intent_or_action"]
            if mode == "system_fact":
                self.assertEqual(role, "system")
                self.assertTrue(
                    action.startswith("demo.scenario.fact."),
                    f"{action!r} must stay demo-internal",
                )
                continue

            group = self.env.ref(
                f"smart_construction_core.group_sc_role_{role}", raise_if_not_found=False
            )
            self.assertTrue(group, f"missing role group for {role!r}")
            users = self.env["res.users"].sudo().search(
                [
                    ("groups_id", "in", group.id),
                    ("active", "=", True),
                    ("share", "=", False),
                ]
            )
            self.assertTrue(users, f"no active internal user for role {role!r}")

            model_name, method = action.rsplit(".", 1)
            model = self.env[model_name]
            self.assertTrue(
                hasattr(model, method), f"{action!r} is not callable"
            )


@tagged("post_install", "-at_install", "-standard", "demo_scenario_tick")
class TestDemoScenarioTickRun(TransactionCase):
    def test_run_tick_advances_three_days_and_records_heartbeat(self):
        self.env["ir.config_parameter"].sudo().set_param("sc.demo.scenario.ledger", "{}")
        tick = self.env["demo.scenario.tick"]

        dates = []
        for _ in range(3):
            result = tick.run_tick()
            self.assertEqual(result["status"], "advanced")
            self.assertTrue(result["business_date"])
            dates.append(result["business_date"])

        self.assertEqual(len(set(dates)), 3)
        ledger = json.loads(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sc.demo.scenario.ledger", "{}")
        )
        self.assertEqual(len(ledger), 12)
        self.assertEqual(
            sorted(key for key, value in ledger.items() if value == "todo").__len__(), 6
        )
        self.assertEqual(
            sorted(key for key, value in ledger.items() if value == "unbound").__len__(), 6
        )
        self.assertTrue(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("sc.demo.scenario.heartbeat")
        )
        activities = self.env["mail.activity"].sudo().search_count(
            [("res_model", "=", "project.project")]
        )
        self.assertGreaterEqual(activities, 6)
        self.assertEqual(tick.run_tick()["status"], "up_to_date")
