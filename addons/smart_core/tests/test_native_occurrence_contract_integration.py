from __future__ import annotations

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.app_config_engine.services.dispatchers.action_dispatcher import ActionDispatcher
from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import (
    assemble_unified_page_contract_v2,
)


@tagged("post_install", "-at_install", "smart_core", "native_occurrence_contract")
class TestNativeOccurrenceContractIntegration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tree = cls.env["ir.ui.view"].create({
            "name": "Native occurrence tree",
            "model": "res.partner",
            "type": "tree",
            "arch": (
                '<tree><field name="name" string="Name"/>'
                '<field name="name" string="Display name"/></tree>'
            ),
        })
        cls.form = cls.env["ir.ui.view"].create({
            "name": "Native occurrence form",
            "model": "res.partner",
            "type": "form",
            "arch": (
                '<form><header><button name="action_archive" type="object" '
                'id="native_occurrence_archive" string="Confirm" title="Archive partner"/>'
                '</header><sheet>'
                '<group name="identity"><field name="name" string="Name"/>'
                '<field name="name" string="Display name"/></group>'
                '<group name="secondary"><field name="email"/></group>'
                '</sheet></form>'
            ),
        })
        cls.env["ir.model.data"].create({
            "module": "smart_core",
            "name": "native_occurrence_tree",
            "model": "ir.ui.view",
            "res_id": cls.tree.id,
            "noupdate": True,
        })
        cls.env["ir.model.data"].create({
            "module": "smart_core",
            "name": "native_occurrence_form",
            "model": "ir.ui.view",
            "res_id": cls.form.id,
            "noupdate": True,
        })
        cls.action = cls.env["ir.actions.act_window"].create({
            "name": "Native occurrence action",
            "res_model": "res.partner",
            "view_mode": "tree,form",
            "view_id": cls.tree.id,
            "view_ids": [
                (0, 0, {"sequence": 10, "view_mode": "tree", "view_id": cls.tree.id}),
                (0, 0, {"sequence": 20, "view_mode": "form", "view_id": cls.form.id}),
            ],
        })

    def _source(self, view_type):
        source, _versions = ActionDispatcher(
            self.env,
            self.env["ir.model"].sudo().env,
        ).dispatch({
            "subject": "action",
            "action_id": self.action.id,
            "view_type": view_type,
        })
        return source

    def _contract(self, view_type):
        source = self._source(view_type)
        return assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            request_id="native.occurrence.%s" % view_type,
            node_actor_env=self.env,
        )

    @staticmethod
    def _walk(nodes):
        for node in nodes if isinstance(nodes, list) else []:
            if not isinstance(node, dict):
                continue
            yield node
            yield from TestNativeOccurrenceContractIntegration._walk(node.get("children"))

    def test_list_preserves_duplicate_same_name_occurrences(self):
        source = self._source("tree")
        collection_view = source["views"]["tree"]
        self.assertEqual(
            len(collection_view["column_occurrences"]),
            2,
            collection_view,
        )
        self.assertTrue(collection_view["viewIdentity"], collection_view)
        contract = self._contract("tree")
        self.assertEqual(contract["pageInfo"]["viewType"], "list")
        columns = contract["layoutContract"]["listProfile"]["columnOccurrences"]

        self.assertEqual([row["fieldCode"] for row in columns], ["name", "name"])
        self.assertNotEqual(columns[0]["occurrenceKey"], columns[1]["occurrenceKey"])
        self.assertEqual(
            len({row["nativeIdentity"]["occurrenceKey"] for row in columns}),
            2,
        )
        for row in columns:
            identity = row["nativeIdentity"]
            self.assertEqual(identity["kind"], "column")
            self.assertEqual(identity["viewType"], "tree")
            self.assertEqual(identity["viewXmlId"], "smart_core.native_occurrence_tree")
            self.assertTrue(identity["viewContentHash"])
            self.assertTrue(identity["viewStructureKey"].startswith("struct.v1."))
            self.assertTrue(identity["crossEnvironmentStable"])

    def test_form_fields_containers_and_buttons_share_identity_shape(self):
        contract = self._contract("form")
        nodes = list(self._walk(contract["layoutContract"]["containerTree"]))
        field_nodes = [
            node for node in nodes
            if str(node.get("type") or "").lower() == "field"
        ]
        container_nodes = [
            node for node in nodes
            if str(node.get("type") or "").lower() != "field"
            and node.get("nativeLocator")
        ]

        self.assertGreaterEqual(len(field_nodes), 3)
        self.assertTrue(container_nodes)
        for node in field_nodes + container_nodes:
            identity = node.get("nativeIdentity")
            self.assertTrue(identity)
            self.assertNotIn("native_locator", node)
            self.assertNotIn("occurrence_index", node)
            self.assertNotIn("source_position", node)
            self.assertEqual(identity["viewXmlId"], "smart_core.native_occurrence_form")
            self.assertIn(identity["kind"], {"field", "container"})
            self.assertTrue(identity["occurrenceKey"].startswith("occ.v1."))

        name_occurrences = [
            node["nativeIdentity"]["occurrenceKey"]
            for node in field_nodes
            if node.get("name") == "name"
        ]
        self.assertEqual(len(name_occurrences), 2)
        self.assertEqual(len(set(name_occurrences)), 2)

        buttons = [
            rule for rule in contract["actionContract"]["actionRuleList"]
            if rule.get("nativeIdentity", {}).get("name") == "action_archive"
        ]
        self.assertTrue(buttons)
        button_identity = buttons[0]["nativeIdentity"]
        self.assertEqual(button_identity["kind"], "button")
        self.assertEqual(button_identity["viewXmlId"], "smart_core.native_occurrence_form")
        self.assertTrue(button_identity["occurrenceKey"].startswith("occ.v1."))
        self.assertEqual(button_identity["type"], "object")
        self.assertEqual(button_identity["id"], "native_occurrence_archive")
        self.assertEqual(button_identity["string"], "Confirm")
        self.assertEqual(button_identity["title"], "Archive partner")
