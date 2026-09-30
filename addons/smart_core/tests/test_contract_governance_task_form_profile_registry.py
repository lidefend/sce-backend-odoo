# -*- coding: utf-8 -*-
import importlib.util
import sys
import unittest
from pathlib import Path


SMART_CORE_DIR = Path(__file__).resolve().parents[1]


def _load_contract_governance():
    sys.modules.pop("smart_core_contract_governance_under_test", None)
    spec = importlib.util.spec_from_file_location(
        "smart_core_contract_governance_under_test",
        SMART_CORE_DIR / "utils" / "contract_governance.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _task_form_contract():
    return {
        "head": {"model": "project.task", "view_type": "form"},
        "fields": {
            "name": {"string": "Name", "type": "char"},
            "project_id": {"string": "Project", "type": "many2one"},
            "description": {"string": "Description", "type": "text"},
        },
        "views": {"form": {"layout": []}},
    }


def _native_occurrence(name, locator, source_position):
    return {
        "type": "field",
        "name": name,
        "native_locator": locator,
        "occurrence_index": 1,
        "source_position": source_position,
    }


def _native_task_form_contract():
    """A resolved native layout carrying complete occurrence identity.

    The flat field configuration is only an overlay, so the resident native
    layout is what supplies every projected node's position identity.
    """
    return {
        "head": {"model": "project.task", "view_type": "form"},
        "fields": {
            "name": {"string": "Name", "type": "char"},
            "project_id": {"string": "Project", "type": "many2one"},
            "description": {"string": "Description", "type": "text"},
        },
        "views": {"form": {"layout": [
            {"type": "header", "children": []},
            {"type": "sheet", "name": "project_task_form_sheet", "children": [
                {"type": "group", "name": "core", "children": [
                    _native_occurrence("name", "/form[1]/sheet[1]/group[1]/field[1]", 4),
                    _native_occurrence("project_id", "/form[1]/sheet[1]/group[1]/field[2]", 5),
                    {"type": "notebook", "children": [
                        {"type": "page", "children": [
                            _native_occurrence(
                                "description",
                                "/form[1]/sheet[1]/notebook[1]/page[1]/field[1]",
                                9,
                            ),
                        ]},
                    ]},
                ]},
            ]},
        ]}},
    }


def _task_form_profile():
    return {
        "fields": ["name", "project_id", "description"],
        "field_labels": {
            "name": "任务名称",
            "project_id": "所属项目",
            "description": "执行说明",
        },
        "core_group_label": "任务基础信息",
        "description_group_label": "任务说明",
        "description_fields": ["description"],
    }


def _projected_field_nodes(layout):
    nodes = []

    def _walk(items):
        for raw in items or []:
            if not isinstance(raw, dict):
                continue
            if str(raw.get("type") or "").lower() == "field":
                nodes.append(raw)
            _walk(raw.get("children"))

    _walk(layout)
    return nodes


class TestContractGovernanceTaskFormProfileRegistry(unittest.TestCase):
    def test_registered_task_model_without_profile_does_not_inject_layout(self):
        module = _load_contract_governance()
        module.register_legacy_project_task_form_governance_model("project.task")

        data = _task_form_contract()
        module.apply_project_form_domain_override(data, "user")

        self.assertNotIn("visible_fields", data)
        self.assertEqual(data["views"]["form"]["layout"], [])

    def test_task_form_profile_is_extension_registered(self):
        module = _load_contract_governance()
        module.register_legacy_project_task_form_governance_model("project.task")
        module.register_legacy_project_task_form_profile(
            "project.task",
            {
                "fields": ["name", "project_id", "description"],
                "field_labels": {
                    "name": "任务名称",
                    "project_id": "所属项目",
                    "description": "执行说明",
                },
                "core_group_label": "任务基础信息",
                "description_group_label": "任务说明",
                "description_fields": ["description"],
            },
        )

        data = _native_task_form_contract()
        module.apply_project_form_domain_override(data, "user")

        self.assertEqual(data["visible_fields"], ["name", "project_id", "description"])
        self.assertEqual([row["label"] for row in data["field_groups"]], ["任务基础信息", "任务说明"])
        groups = data["views"]["form"]["layout"][0]["children"]
        self.assertEqual(groups[0]["string"], "任务基础信息")
        self.assertEqual(groups[1]["string"], "任务说明")
        self.assertEqual([node["fieldInfo"]["label"] for node in groups[0]["children"]], ["任务名称", "所属项目"])
        self.assertEqual([node["fieldInfo"]["label"] for node in groups[1]["children"]], ["执行说明"])

    def test_projected_task_field_nodes_keep_native_occurrence_identity(self):
        """The overlay may relabel and regroup fields, never invent occurrences."""
        module = _load_contract_governance()
        module.register_legacy_project_task_form_governance_model("project.task")
        module.register_legacy_project_task_form_profile("project.task", _task_form_profile())

        data = _native_task_form_contract()
        module.apply_project_form_domain_override(data, "user")

        nodes = _projected_field_nodes(data["views"]["form"]["layout"])
        self.assertEqual([node["name"] for node in nodes], ["name", "project_id", "description"])
        for node in nodes:
            self.assertTrue(
                node.get("native_locator"),
                f"projected node {node.get('name')!r} lost its native locator",
            )
            self.assertGreater(int(node.get("occurrence_index") or 0), 0)
            self.assertGreaterEqual(int(node.get("source_position") or -1), 0)

        by_name = {node["name"]: node for node in nodes}
        self.assertEqual(
            by_name["name"]["native_locator"],
            "/form[1]/sheet[1]/group[1]/field[1]",
        )
        # description is only reachable through a notebook page; walking every
        # child carrier is what keeps its identity from being fabricated.
        self.assertEqual(
            by_name["description"]["native_locator"],
            "/form[1]/sheet[1]/notebook[1]/page[1]/field[1]",
        )

    def test_shipped_task_form_profile_projects_every_field_with_identity(self):
        """Regression for the 5xx: the shipped profile must never fabricate a node."""
        module = _load_contract_governance()
        module.register_legacy_project_task_form_governance_model("project.task")
        module.register_legacy_project_task_form_profile(
            "project.task",
            {
                "fields": [
                    "name",
                    "project_id",
                    "stage_id",
                    "sc_state",
                    "user_ids",
                    "date_deadline",
                    "priority",
                    "description",
                ],
                "field_labels": {"name": "任务名称", "project_id": "所属项目"},
                "description_fields": ["description"],
            },
        )

        data = _native_task_form_contract()
        data["fields"]["stage_id"] = {"string": "Stage", "type": "many2one"}
        data["fields"]["sc_state"] = {"string": "State", "type": "selection"}
        data["fields"]["user_ids"] = {"string": "Assignees", "type": "many2many"}
        data["fields"]["date_deadline"] = {"string": "Deadline", "type": "datetime"}
        data["fields"]["priority"] = {"string": "Priority", "type": "selection"}
        layout = data["views"]["form"]["layout"]
        layout[1]["children"][0]["children"].extend([
            _native_occurrence("stage_id", "/form[1]/header[1]/field[1]", 10),
            _native_occurrence("sc_state", "/form[1]/header[1]/field[4]", 13),
            _native_occurrence("user_ids", "/form[1]/sheet[1]/group[1]/field[5]", 6),
            _native_occurrence("date_deadline", "/form[1]/sheet[1]/group[1]/field[6]", 7),
            _native_occurrence("priority", "/form[1]/sheet[1]/group[1]/field[7]", 8),
        ])

        module.apply_project_form_domain_override(data, "user")

        nodes = _projected_field_nodes(data["views"]["form"]["layout"])
        self.assertEqual(len(nodes), 8)
        self.assertEqual(data["visible_fields"], [node["name"] for node in nodes])
        for node in nodes:
            self.assertTrue(node.get("native_locator"))
            self.assertGreater(int(node.get("occurrence_index") or 0), 0)

    def test_config_field_without_native_occurrence_is_dropped_not_fabricated(self):
        """An unprojectable configured field must not become a locator-less occurrence."""
        module = _load_contract_governance()
        module.register_legacy_project_task_form_governance_model("project.task")
        module.register_legacy_project_task_form_profile(
            "project.task",
            {
                "fields": ["name", "ghost_field"],
                "field_labels": {"name": "任务名称"},
                "description_fields": [],
            },
        )

        data = _native_task_form_contract()
        data["fields"]["ghost_field"] = {"string": "Ghost", "type": "char"}
        module.apply_project_form_domain_override(data, "user")

        nodes = _projected_field_nodes(data["views"]["form"]["layout"])
        self.assertEqual([node["name"] for node in nodes], ["name"])
        self.assertEqual(data["visible_fields"], ["name"])

    def test_sheet_occurrence_wins_over_out_of_sheet_carrier(self):
        """A hidden carrier outside the sheet must not displace the visible input."""
        module = _load_contract_governance()
        module.register_legacy_project_task_form_governance_model("project.task")
        module.register_legacy_project_task_form_profile(
            "project.task",
            {"fields": ["project_id"], "field_labels": {}, "description_fields": []},
        )

        data = _native_task_form_contract()
        data["views"]["form"]["layout"].insert(
            0,
            _native_occurrence("project_id", "/form[1]/field[8]", 2),
        )
        module.apply_project_form_domain_override(data, "user")

        nodes = _projected_field_nodes(data["views"]["form"]["layout"])
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["native_locator"], "/form[1]/sheet[1]/group[1]/field[2]")


if __name__ == "__main__":
    unittest.main()
