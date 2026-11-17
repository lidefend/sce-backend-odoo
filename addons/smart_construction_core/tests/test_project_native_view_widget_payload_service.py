#!/usr/bin/env python3
"""Pure tests for project embedded-widget payload adaptation."""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


SERVICE = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "project_native_view_widget_payload_service.py"
)
SPEC = importlib.util.spec_from_file_location("project_native_view_widget_payload_service", SERVICE)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class Project:
    def __init__(self, record_id=7, exists=True):
        self.id = record_id
        self._exists = exists
        self.access_checks = []

    def exists(self):
        return self if self._exists else False

    def check_access_rights(self, operation):
        self.access_checks.append(("rights", operation))

    def check_access_rule(self, operation):
        self.access_checks.append(("rule", operation))

    def sc_get_stage_requirements(self, limit=3):
        return [{
            "title": "项目地点",
            "required": True,
            "done": False,
            "action_type": "act_window_xmlid",
            "action_ref": "smart_construction_core.action_sc_project_manage",
            "payload": {"project_id": self.id},
        }][:limit]

    def sc_get_next_actions(self, limit=3):
        return {
            "actions": [{
                "title": "提交立项",
                "hint": "补齐后可提交",
                "action_type": "object_method",
                "action_ref": "action_sc_submit",
                "payload": {"project_id": self.id},
            }][:limit],
            "fallback": {},
        }


class Env(dict):
    def __init__(self, project):
        super().__init__({"project.project": RecordSet(project)})
        self.project = project


class RecordSet:
    def __init__(self, project):
        self.project = project

    def browse(self, record_id):
        return self.project if record_id == self.project.id else Project(record_id, exists=False)


def request_for(record_id=7):
    return {
        "model": "project.project",
        "recordId": record_id,
        "widgets": [
            {
                "occurrenceKey": "occ.insight",
                "nativeWidget": "sc_insight_banner",
                "options": {"scene": "project.entry"},
            },
            {
                "occurrenceKey": "occ.stage",
                "nativeWidget": "sc_stage_requirements",
                "options": {"limit": 1},
            },
            {
                "occurrenceKey": "occ.next",
                "nativeWidget": "sc_next_actions",
                "options": {"limit": 1},
            },
        ],
    }


class Result:
    def get_insight(self, project, scene=None):
        return {
            "initiation": {
                "risk_count": 1,
                "ui_model": {
                    "hero": {
                        "title": "项目已创建，可以继续推进。",
                        "subtitle": "建议先完成项目地点。",
                    },
                    "next_best": {"item": {"because": "否则后续办理会受阻。"}},
                    "footer": {"text": "其余准备可稍后补齐。"},
                },
            },
        }


def install_insight_stub():
    package_names = [
        "odoo",
        "odoo.addons",
        "odoo.addons.smart_construction_core",
        "odoo.addons.smart_construction_core.services",
        "odoo.addons.smart_construction_core.services.insight",
    ]
    for name in package_names:
        sys.modules.setdefault(name, types.ModuleType(name))
    insight_module = types.ModuleType(
        "odoo.addons.smart_construction_core.services.insight.project_insight_service"
    )
    insight_module.ProjectInsightService = lambda env: Result()
    sys.modules[insight_module.__name__] = insight_module


class PayloadServiceTests(unittest.TestCase):
    def setUp(self):
        install_insight_stub()

    def test_builds_generic_payloads_from_existing_project_services(self):
        project = Project()
        payload = module.ProjectNativeViewWidgetPayloadService(Env(project)).build(request_for())
        widgets = payload["widgets"]
        self.assertEqual(widgets["occ.insight"]["payloadSchema"], "insight_summary.v1")
        self.assertEqual(widgets["occ.insight"]["payload"]["tone"], "warning")
        self.assertIn("项目地点", widgets["occ.insight"]["payload"]["message"] + widgets["occ.insight"]["payload"]["detail"])
        stage = widgets["occ.stage"]["payload"]
        self.assertEqual(stage["title"], "阶段要求")
        self.assertEqual(stage["items"][0]["state"], "required")
        self.assertEqual(stage["items"][0]["actionType"], "act_window_xmlid")
        self.assertEqual(stage["items"][0]["actionPayload"], {"project_id": 7})
        next_action = widgets["occ.next"]["payload"]
        self.assertEqual(next_action["items"][0]["title"], "提交立项")
        self.assertEqual(next_action["items"][0]["actionType"], "object_method")
        self.assertTrue(next_action["items"][0]["enabled"])
        self.assertEqual(project.access_checks, [("rights", "read"), ("rule", "read")])

    def test_unknown_model_or_record_returns_no_payload(self):
        project = Project()
        env = Env(project)
        service = module.ProjectNativeViewWidgetPayloadService(env)
        self.assertEqual(service.build({"model": "x.other", "recordId": 7, "widgets": []}), {"widgets": {}})
        self.assertEqual(service.build(request_for(record_id=99)), {"widgets": {}})

    def test_next_action_uses_existing_fallback_when_rules_are_empty(self):
        project = Project()

        def no_actions(limit=3):
            return {
                "actions": [],
                "fallback": {
                    "title": "查看阶段要求",
                    "action_type": "object_method",
                    "action_ref": "action_view_stage_requirements",
                    "payload": {},
                },
            }

        project.sc_get_next_actions = no_actions
        payload = module.ProjectNativeViewWidgetPayloadService(Env(project)).build(request_for())
        item = payload["widgets"]["occ.next"]["payload"]["items"][0]
        self.assertEqual(item["title"], "查看阶段要求")
        self.assertEqual(item["actionRef"], "action_view_stage_requirements")


if __name__ == "__main__":
    unittest.main()
