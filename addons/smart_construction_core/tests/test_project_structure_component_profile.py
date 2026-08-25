# -*- coding: utf-8 -*-
import importlib.util
from pathlib import Path
from lxml import etree

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval

from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler


EXPECTED_LEVELS = [
    {
        "field": "project_id",
        "label_field": "name",
    },
    {
        "field": "parent_id",
        "code_field": "code",
        "label_field": "name",
        "parent_field": "project_id",
        "self_parent_field": "parent_id",
        "domain_operator": "child_of",
        "order": "project_id, parent_path, sequence, id",
    },
]

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "17.0.0.134"
    / "post-migration.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location(
        "smart_construction_core_17_0_0_134_post",
        MIGRATION_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("project_structure_component_profile", "post_install", "-at_install")
class TestProjectStructureComponentProfile(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.migration = _load_migration()

    def test_execution_structure_native_view_declares_hierarchy_browser(self):
        view = self.env.ref("smart_construction_core.view_exec_structure_wbs_tree")
        root = etree.fromstring(view.arch_db.encode("utf-8"))

        self.assertEqual(root.tag, "tree")
        self.assertEqual(root.get("js_class"), "smart_hierarchy_browser")

    def test_execution_structure_action_declares_authoritative_hierarchy_profile(self):
        action = self.env.ref("smart_construction_core.action_exec_structure_wbs")
        context = safe_eval(action.context or "{}", {"context": {}})

        self.assertEqual(
            context["hierarchy_scope"],
            {"field": "project_id", "context_field": "default_project_id"},
        )
        self.assertEqual(context["hierarchy_levels"], EXPECTED_LEVELS)
        self.assertNotIn("hierarchy_create", context)
        self.assertNotIn("hierarchy_commands", context)

    def test_generated_tree_contract_is_owned_only_by_wbs_planner(self):
        contract = self.env.ref(
            "smart_construction_core."
            "business_config_contract_construction_work_breakdown_tree_structure_generated"
        )

        self.assertEqual(contract.action_id, self.env.ref("smart_construction_core.action_work_breakdown"))
        self.assertEqual(contract.view_id, self.env.ref("smart_construction_core.view_work_breakdown_tree"))

    def test_scope_migration_is_precise_and_idempotent(self):
        contract = self.env.ref(
            "smart_construction_core."
            "business_config_contract_construction_work_breakdown_tree_structure_generated"
        )
        expected_action = self.env.ref("smart_construction_core.action_work_breakdown")
        expected_view = self.env.ref("smart_construction_core.view_work_breakdown_tree")
        self.env.cr.execute(
            "UPDATE ui_business_config_contract SET action_id=NULL, view_id=NULL WHERE id=%s",
            [contract.id],
        )
        self.env.invalidate_all()

        self.migration.migrate(self.env.cr, "17.0.0.133")
        self.env.invalidate_all()
        contract = contract.exists()
        first = (contract.action_id.id, contract.view_id.id)
        self.migration.migrate(self.env.cr, "17.0.0.134")
        self.env.invalidate_all()

        self.assertEqual(first, (expected_action.id, expected_view.id))
        self.assertEqual((contract.action_id.id, contract.view_id.id), first)

    def test_project_entry_preserves_same_profile_and_exact_project_scope(self):
        project = self.env["project.project"].create({"name": "Phase 9 project structure profile"})

        action = project._exec_structure_action()

        self.assertEqual(action["views"][0][0], self.env.ref("smart_construction_core.view_exec_structure_wbs_tree").id)
        self.assertEqual(action["domain"], [("project_id", "=", project.id)])
        self.assertEqual(action["context"]["default_project_id"], project.id)
        self.assertEqual(
            action["context"]["hierarchy_scope"],
            {"field": "project_id", "context_field": "default_project_id"},
        )
        self.assertEqual(action["context"]["hierarchy_levels"], EXPECTED_LEVELS)

    def test_effective_action_projection_selects_ready_hierarchy_browser(self):
        project = self.env["project.project"].create({"name": "Phase 9 effective project structure"})
        action = self.env.ref("smart_construction_core.action_exec_structure_wbs").read()[0]
        action["context"] = {
            **safe_eval(action.get("context") or "{}", {"context": {}}),
            "default_project_id": project.id,
        }

        page, _versions = PageAssembler(
            self.env,
            self.env["ir.model"].sudo().env,
        ).assemble_page_contract(
            {
                "model": "construction.work.breakdown",
                "view_types": ["tree", "form"],
                "action_id": action["id"],
                "context": {"default_project_id": project.id},
            },
            action=action,
        )

        presentation = page["views"]["tree"]["collection_presentation"]
        self.assertEqual(presentation.get("semantic"), "hierarchy_browser", presentation)
        self.assertTrue(presentation.get("enabled"), presentation)
        config = presentation["config"]
        self.assertEqual(config["tree"]["levels"][0]["model"], "project.project")
        self.assertEqual(config["tree"]["levels"][1]["model"], "construction.work.breakdown")
        self.assertEqual(config["list"]["domain"], [("project_id", "=", project.id)])
        self.assertEqual(config["create"], {"enabled": False, "label": ""})
        self.assertEqual(config["commands"], [])

    def test_missing_project_still_returns_selection_notification_without_profile_guessing(self):
        action = self.env["project.project"]._exec_structure_action()

        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "display_notification")
        self.assertNotIn("hierarchy_levels", action["params"]["next"]["context"])
