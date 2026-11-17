from __future__ import annotations

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.app_config_engine.services.assemblers.page_assembler import PageAssembler
from odoo.addons.smart_core.app_config_engine.services.dispatchers.action_dispatcher import ActionDispatcher
from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import (
    _native_view_identity_for,
    assemble_unified_page_contract_v2,
    rebind_native_occurrence_identities,
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
                '<widget name="web_ribbon" title="Paid" '
                'options="{\'bg_color\': \'text-bg-success\'}"/>'
                '<widget name="web_ribbon" title="Draft" options="False"/>'
                '<widget name="sc_stage_requirements" options="{\'limit\': 3}"/>'
                '<group name="identity"><field name="name" string="Name"/>'
                '<field name="name" string="Display name"/></group>'
                '<group name="secondary"><field name="email"/>'
                '<field name="parent_id" domain="[(\'is_company\', \'=\', True)]" '
                'context="{\'default_is_company\': True}" options="{\'no_create\': True}"/></group>'
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
            self.assertIn(identity["kind"], {"field", "container", "widget"})
            self.assertTrue(identity["occurrenceKey"].startswith("occ.v1."))

        field_by_container = {
            node["containerId"]: node["nativeIdentity"]
            for node in field_nodes
            if node.get("containerId")
        }
        widget_count = 0
        for node in nodes:
            for widget in node.get("widgetList") or []:
                self.assertIsInstance(widget, dict)
                identity = widget.get("nativeIdentity")
                self.assertTrue(identity, widget)
                self.assertEqual(identity["kind"], "field", widget)
                owner = field_by_container.get(widget.get("ownerContainerId"))
                self.assertTrue(owner, widget)
                self.assertEqual(identity, owner, widget)
                widget_count += 1
        self.assertGreater(widget_count, 0)

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
        self.assertTrue(
            buttons[0]["backendIdentity"].startswith(
                "native_button:object:action_archive:"
            )
        )

    def test_legacy_view_identity_without_view_type_is_not_claimed(self):
        self.assertEqual(
            _native_view_identity_for(
                {"views": {"tree": {"viewIdentity": {"viewId": 17}}}},
                "tree",
            ),
            {},
        )

    def test_form_field_domain_projection_uses_explicit_view_expression(self):
        contract = self._contract("form")
        widgets = [
            widget
            for node in self._walk(contract["layoutContract"]["containerTree"])
            for widget in node.get("widgetList") or []
            if widget.get("fieldCode") == "parent_id"
        ]
        self.assertEqual(len(widgets), 1)
        widget = widgets[0]
        raw = "[('is_company', '=', True)]"
        context = "{'default_is_company': True}"
        self.assertEqual(widget["fieldDescriptor"]["domain"], raw)
        self.assertEqual(widget["fieldDescriptor"]["domain_expression"]["raw"], raw)
        self.assertEqual(widget["fieldDescriptor"]["context"], context)
        self.assertEqual(widget["fieldDescriptor"]["widget_options"], {"no_create": True})

    def test_form_embedded_widget_contract_preserves_identity_options_and_support(self):
        contract = self._contract("form")
        widgets = [
            node
            for node in self._walk(contract["layoutContract"]["containerTree"])
            if node.get("type") == "widget"
        ]

        self.assertEqual([node["componentKey"] for node in widgets], [
            "sc.display.ribbon",
            "sc.display.ribbon",
            "sc.unsupported.native_node",
        ])
        self.assertEqual([node["nativeIdentity"]["kind"] for node in widgets], ["widget", "widget", "widget"])
        self.assertEqual(len({node["nativeIdentity"]["occurrenceKey"] for node in widgets[:2]}), 2)
        self.assertEqual(widgets[0]["componentConfig"]["nativeWidget"], "web_ribbon")
        self.assertEqual(widgets[0]["componentConfig"]["options"], {"bg_color": "text-bg-success"})
        self.assertIs(widgets[1]["componentConfig"]["options"], False)
        self.assertEqual(widgets[2]["componentConfig"]["reasonCode"], "NATIVE_VIEW_WIDGET_UNSUPPORTED")
        self.assertTrue(all("fieldCode" not in node for node in widgets))
        self.assertTrue(all("fieldDescriptor" not in node for node in widgets))

    def test_final_handler_boundary_restores_occurrences_after_mutation(self):
        source = self._source("tree")
        view_identity = _native_view_identity_for(source, "tree")
        contract = self._contract("tree")
        profile = contract["layoutContract"]["listProfile"]
        profile.pop("columnOccurrences", None)
        legacy_rule = contract["actionContract"]["actionRuleList"][1]
        legacy_rule["nativeIdentity"] = {
            "authoritative": True,
            "name": "action_archive",
            "native_locator": "/form[1]/header[1]/button[1]",
            "occurrence_index": 1,
            "type": "object",
        }
        source["views"]["tree"].pop("viewIdentity", None)

        rebind_native_occurrence_identities(
            contract,
            source,
            view_identity=view_identity,
        )

        columns = contract["layoutContract"]["listProfile"]["columnOccurrences"]
        self.assertEqual(len(columns), 2)
        identity = legacy_rule["nativeIdentity"]
        self.assertEqual(identity["schemaVersion"], "1.0.0")
        self.assertEqual(identity["kind"], "button")
        self.assertTrue(identity["occurrenceKey"].startswith("occ.v1."))

    def test_identity_helper_falls_back_when_carrier_has_no_arch(self):
        class _ParsedOnlyCarrier:
            @staticmethod
            def fetch(_env, _model, _view_type, _view_id):
                return {"_arch_root": None, "view_type": "tree"}

        contract = {"views": {"tree": {}}}
        identity = PageAssembler(
            self.env,
            self.env["ir.model"].sudo().env,
        ).ensure_native_view_identity(
            contract,
            model="res.partner",
            view_type="tree",
            view_id=self.tree.id,
            carrier=_ParsedOnlyCarrier(),
        )
        self.assertTrue(identity)
        self.assertEqual(identity["viewXmlId"], "smart_core.native_occurrence_tree")
        self.assertEqual(contract["views"]["tree"]["viewIdentity"], identity)

    def test_identity_helper_replaces_partial_existing_identity(self):
        partial = {
            "viewId": self.tree.id,
            "model": "res.partner",
            "viewType": "tree",
        }
        contract = {"views": {"tree": {"viewIdentity": partial}}}
        identity = PageAssembler(
            self.env,
            self.env["ir.model"].sudo().env,
        ).ensure_native_view_identity(
            contract,
            model="res.partner",
            view_type="tree",
            view_id=self.tree.id,
        )
        self.assertTrue(identity)
        self.assertNotEqual(identity, partial)
        for key in (
            "model",
            "viewType",
            "viewContentHash",
            "viewStructureKey",
            "crossEnvironmentStable",
        ):
            self.assertIn(key, identity)
        self.assertEqual(contract["views"]["tree"]["viewIdentity"], identity)
