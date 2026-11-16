from __future__ import annotations

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.app_config_engine.services.dispatchers.action_dispatcher import ActionDispatcher
from odoo.addons.smart_core.core.unified_page_contract_v2_assembler import (
    assemble_unified_page_contract_v2,
)


@tagged("post_install", "-at_install", "smart_core", "native_action_contract")
class TestNativeActionContractIntegration(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tree = cls.env["ir.ui.view"].create({
            "name": "Native Action Contract tree",
            "model": "res.partner",
            "type": "tree",
            "arch": '<tree><field name="name"/></tree>',
        })
        cls.form = cls.env["ir.ui.view"].create({
            "name": "Native Action Contract form",
            "model": "res.partner",
            "type": "form",
            "arch": '<form><sheet><field name="name"/></sheet></form>',
        })
        cls.search = cls.env["ir.ui.view"].create({
            "name": "Native Action Contract search",
            "model": "res.partner",
            "type": "search",
            "arch": (
                '<search><field name="name"/>'
                '<filter name="active_only" string="Active" '
                'domain="[(\'active\',\'=\',True)]"/></search>'
            ),
        })
        cls.action = cls.env["ir.actions.act_window"].create({
            "name": "Native Action Contract action",
            "res_model": "res.partner",
            "view_mode": "tree,form",
            "view_id": cls.tree.id,
            "search_view_id": cls.search.id,
            "view_ids": [
                (0, 0, {"sequence": 20, "view_mode": "tree", "view_id": cls.tree.id}),
                (0, 0, {"sequence": 10, "view_mode": "form", "view_id": cls.form.id}),
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
        return assemble_unified_page_contract_v2(
            self._source(view_type),
            source_type="ui.contract",
            request_id="native.action.contract.%s" % view_type,
            node_actor_env=self.env,
        )

    def test_action_contract_publishes_identity_view_set_and_search(self):
        contract = self._contract("tree")
        native_action = contract["nativeActionContract"]

        self.assertEqual(native_action["schemaVersion"], "1.0.0")
        self.assertEqual(native_action["identity"]["actionId"], self.action.id)
        self.assertEqual(native_action["identity"]["model"], "res.partner")
        page_view_type = contract["pageInfo"]["viewType"]
        self.assertEqual(
            native_action["viewSet"]["activeViewType"],
            "tree" if page_view_type == "list" else page_view_type,
        )
        self.assertEqual(
            [(row["viewType"], row["viewId"]) for row in native_action["viewSet"]["orderedViews"]],
            [
                ("tree" if str(view_type).lower() == "list" else str(view_type).lower(), view_id)
                for view_id, view_type in self.action.views
            ],
        )
        self.assertEqual(native_action["search"]["viewId"], self.search.id)
        self.assertEqual(native_action["search"]["authority"], "action_search_view")
        self.assertEqual(native_action["readiness"]["backendContract"]["status"], "ready")
        self.assertEqual(native_action["readiness"]["clientRenderer"]["status"], "unknown")
        self.assertEqual(native_action["readiness"]["businessExecution"]["status"], "not_applicable")

    def test_active_view_follows_the_requested_action_view(self):
        contract = self._contract("form")
        native_action = contract["nativeActionContract"]

        self.assertEqual(native_action["viewSet"]["defaultViewType"], "form")
        self.assertEqual(native_action["viewSet"]["activeViewType"], "form")
        self.assertEqual(contract["pageInfo"]["viewType"], "form")

    def test_model_only_page_does_not_invent_native_action_contract(self):
        source, _versions = ActionDispatcher(
            self.env,
            self.env["ir.model"].sudo().env,
        ).dispatch({
            "subject": "model",
            "model": "res.partner",
            "view_type": "form",
        })
        contract = assemble_unified_page_contract_v2(
            source,
            source_type="ui.contract",
            request_id="native.action.contract.model-only",
            node_actor_env=self.env,
        )

        self.assertNotIn("nativeActionContract", contract)
