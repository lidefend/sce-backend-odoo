# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.app_config_engine.services.dispatchers.action_dispatcher import ActionDispatcher
from odoo.addons.smart_core.app_config_engine.services.assemblers.client_url_report import ClientUrlReportAssembler
from odoo.addons.smart_core.app_config_engine.services.dispatchers.nav_dispatcher import NavDispatcher
from odoo.addons.smart_core.handlers.ui_contract import UiContractHandler


@tagged("post_install", "-at_install", "smart_core", "action_dispatcher")
class TestActionDispatcherServerMapping(TransactionCase):
    @staticmethod
    def _bound_action_identity(row):
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        action_id = payload.get("action_id") or row.get("action_id")
        server_action_id = payload.get("server_action_id") or row.get("server_action_id")
        xml_id = payload.get("xml_id") or row.get("xml_id")
        if action_id:
            return "window:%s" % int(action_id)
        if server_action_id:
            return "server:%s" % int(server_action_id)
        if xml_id:
            return "xmlid:%s" % str(xml_id)
        return "key:%s" % str(row.get("key") or "")

    def _assert_multi_actions_are_explicitly_bound(self, data, model_name):
        buttons = data.get("buttons") if isinstance(data.get("buttons"), list) else []
        toolbar = data.get("toolbar") if isinstance(data.get("toolbar"), dict) else {}
        header_rows = toolbar.get("header") if isinstance(toolbar.get("header"), list) else []
        button_by_identity = {
            self._bound_action_identity(row): row
            for row in buttons
            if isinstance(row, dict)
        }
        self.assertEqual(len(button_by_identity), len(buttons), "buttons carrier has duplicate action identity")
        header_by_identity = {
            self._bound_action_identity(row): row
            for row in header_rows
            if isinstance(row, dict)
        }
        self.assertEqual(len(header_by_identity), len(header_rows), "toolbar carrier has duplicate action identity")
        self.assertTrue(set(header_by_identity).issubset(set(button_by_identity)))
        for identity, row in header_by_identity.items():
            source = row.get("source_authority") if isinstance(row.get("source_authority"), dict) else {}
            self.assertEqual(source.get("kind"), "odoo_native_bound_action_projection")
            self.assertEqual(
                self._bound_action_identity(button_by_identity[identity]),
                identity,
            )
            if row.get("selection") != "multi":
                continue
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            action_id = int(payload.get("action_id") or 0)
            self.assertGreater(action_id, 0, row)
            action = self.env["ir.actions.act_window"].sudo().browse(action_id).exists()
            self.assertTrue(action, row)
            self.assertEqual(action.binding_model_id.model, model_name)
            binding_types = {
                value.strip().replace("tree", "list")
                for value in str(action.binding_view_types or "").split(",")
                if value.strip()
            }
            self.assertIn("list", binding_types, row)

    def _assert_list_profile_matches_effective_tree(self, data):
        views = data.get("views") if isinstance(data.get("views"), dict) else {}
        tree = views.get("tree") if isinstance(views.get("tree"), dict) else {}
        meta = tree.get("meta") if isinstance(tree.get("meta"), dict) else {}
        projection = (
            meta.get("projection_identity")
            if isinstance(meta.get("projection_identity"), dict)
            else {}
        )
        self.assertGreater(int(projection.get("source_view_id") or 0), 0)
        tree_columns = [str(name) for name in tree.get("columns") or []]
        self.assertTrue(tree_columns)
        profile = data.get("list_profile") if isinstance(data.get("list_profile"), dict) else {}
        self.assertEqual(profile.get("source"), "contract_governance.curated_list_facts")
        self.assertEqual(profile.get("columns") or [], tree_columns)
        schema_labels = {
            str(row.get("name")): str(row.get("label") or row.get("string") or "")
            for row in tree.get("columns_schema") or []
            if isinstance(row, dict) and row.get("name")
        }
        profile_labels = profile.get("column_labels") if isinstance(profile.get("column_labels"), dict) else {}
        self.assertEqual(
            {name: profile_labels.get(name) for name in tree_columns},
            {name: schema_labels.get(name) for name in tree_columns},
        )

    def test_server_action_prefers_mapping_before_materialize(self):
        dispatcher = ActionDispatcher(self.env, self.env)
        payload = {"subject": "action", "action_id": 462}
        server_info = {
            "type": "ir.actions.server",
            "_name": "ir.actions.server",
            "id": 462,
            "xml_id": "smart_construction_core.action_exec_structure_entry",
            "exists": True,
        }
        mapped = {
            "type": "ir.actions.act_window",
            "_name": "ir.actions.act_window",
            "id": 999,
            "res_model": "construction.work.breakdown",
            "view_mode": "tree,form",
            "exists": True,
        }
        expected = ({"subject": "mapped"}, {"v": 1})

        with (
            patch.object(dispatcher.resolver, "resolve_action", return_value=object()),
            patch.object(dispatcher.resolver, "as_action_info", return_value=server_info),
            patch.object(dispatcher.resolver, "map_server_to_window", return_value=mapped) as mocked_map,
            patch.object(dispatcher, "_dispatch_resolved", return_value=expected) as mocked_dispatch,
        ):
            result = dispatcher.dispatch(payload)

        self.assertEqual(result, expected)
        mocked_map.assert_called_once_with(462, "smart_construction_core.action_exec_structure_entry")
        mocked_dispatch.assert_called_once_with(mapped, payload)

    def test_unmapped_server_action_fails_closed_without_execution(self):
        dispatcher = ActionDispatcher(self.env, self.env)
        payload = {"subject": "action", "action_id": 777}
        server_info = {
            "type": "ir.actions.server",
            "_name": "ir.actions.server",
            "id": 777,
            "xml_id": "x.y.z",
            "exists": True,
        }
        with (
            patch.object(dispatcher.resolver, "resolve_action", return_value=object()),
            patch.object(dispatcher.resolver, "as_action_info", return_value=server_info),
            patch.object(dispatcher.resolver, "map_server_to_window", return_value=None) as mocked_map,
            patch.object(
                ClientUrlReportAssembler,
                "assemble_diagnostic_contract",
                return_value=({"subject": "diagnostic"}, {"v": 1}),
            ) as mocked_diagnostic,
        ):
            result = dispatcher.dispatch(payload)

        self.assertEqual(result, ({"subject": "diagnostic"}, {"v": 1}))
        mocked_map.assert_called_once_with(777, "x.y.z")
        mocked_diagnostic.assert_called_once()
        self.assertFalse(hasattr(dispatcher.resolver, "materialize_server_action"))
        self.assertFalse(hasattr(dispatcher.resolver, "safe_probe_server_action"))

    def test_ui_contract_action_open_exec_structure_returns_page_contract(self):
        action = self.env.ref("smart_construction_core.action_exec_structure_entry", raise_if_not_found=False)
        if not action:
            self.skipTest("smart_construction_core.action_exec_structure_entry not installed")

        run_env = self.env
        pm_user = self.env["res.users"].sudo().search([("login", "=", "sc_fx_pm")], limit=1)
        if pm_user:
            run_env = self.env(user=pm_user)

        handler = UiContractHandler(run_env)
        result = handler.handle(payload={"params": {"op": "action_open", "action_id": int(action.id)}})

        self.assertTrue(result.get("ok"), result)
        data = result.get("data") or {}
        head = data.get("head") if isinstance(data.get("head"), dict) else {}
        model = str(data.get("model") or head.get("model") or "").strip()
        body = data.get("data") if isinstance(data.get("data"), dict) else {}
        contract_type = str(body.get("type") or "").strip().lower()
        self.assertTrue(model, f"ui.contract(action_open) returned empty model: {result}")
        self.assertNotEqual(contract_type, "diagnostic", f"unexpected diagnostic contract: {result}")

    def test_ui_contract_action_open_project_list_matches_current_product_contract(self):
        action = self.env.ref("smart_construction_core.action_sc_project_list", raise_if_not_found=False)
        if not action:
            self.skipTest("smart_construction_core.action_sc_project_list not installed")

        run_env = self.env
        demo_user = self.env["res.users"].sudo().search([("login", "=", "demo_full")], limit=1)
        if demo_user:
            run_env = self.env(user=demo_user)

        handler = UiContractHandler(run_env)
        result = handler.handle(payload={"params": {"op": "action_open", "action_id": int(action.id)}})

        self.assertTrue(result.get("ok"), result)
        data = result.get("data") or {}
        head = data.get("head") if isinstance(data.get("head"), dict) else {}
        self.assertEqual(str(head.get("view_type") or data.get("view_type") or "").strip().lower(), "tree")

        self._assert_multi_actions_are_explicitly_bound(data, "project.project")
        self._assert_list_profile_matches_effective_tree(data)

    def test_ui_contract_action_open_payment_list_matches_current_product_contract(self):
        action = self.env.ref("smart_construction_core.action_sc_finance_dashboard", raise_if_not_found=False)
        if not action:
            self.skipTest("smart_construction_core.action_sc_finance_dashboard not installed")

        run_env = self.env
        demo_user = self.env["res.users"].sudo().search([("login", "=", "demo_full")], limit=1)
        if demo_user:
            run_env = self.env(user=demo_user)

        handler = UiContractHandler(run_env)
        result = handler.handle(payload={"params": {"op": "action_open", "action_id": int(action.id)}})

        self.assertTrue(result.get("ok"), result)
        data = result.get("data") or {}
        head = data.get("head") if isinstance(data.get("head"), dict) else {}
        self.assertEqual(str(head.get("view_type") or data.get("view_type") or "").strip().lower(), "tree")

        self._assert_multi_actions_are_explicitly_bound(data, "payment.request")
        self._assert_list_profile_matches_effective_tree(data)

    def test_ui_contract_action_open_material_plan_list_matches_current_product_contract(self):
        action = self.env.ref("smart_construction_core.action_project_material_plan", raise_if_not_found=False)
        if not action:
            self.skipTest("smart_construction_core.action_project_material_plan not installed")

        run_env = self.env
        demo_user = self.env["res.users"].sudo().search([("login", "=", "demo_full")], limit=1)
        if demo_user:
            run_env = self.env(user=demo_user)

        handler = UiContractHandler(run_env)
        result = handler.handle(payload={"params": {"op": "action_open", "action_id": int(action.id)}})

        self.assertTrue(result.get("ok"), result)
        data = result.get("data") or {}
        head = data.get("head") if isinstance(data.get("head"), dict) else {}
        self.assertEqual(str(head.get("view_type") or data.get("view_type") or "").strip().lower(), "tree")

        self._assert_multi_actions_are_explicitly_bound(data, "project.material.plan")
        self._assert_list_profile_matches_effective_tree(data)

    def test_ui_contract_action_open_payment_form_excludes_list_toolbar_actions(self):
        action = self.env.ref("smart_construction_core.action_sc_finance_dashboard", raise_if_not_found=False)
        if not action:
            self.skipTest("smart_construction_core.action_sc_finance_dashboard not installed")

        payment = self.env["payment.request"].sudo().search([], limit=1)
        if not payment:
            self.skipTest("payment.request demo data not installed")

        run_env = self.env
        demo_user = self.env["res.users"].sudo().search([("login", "=", "demo_full")], limit=1)
        if demo_user:
            run_env = self.env(user=demo_user)

        handler = UiContractHandler(run_env)
        result = handler.handle(payload={"params": {
            "op": "action_open",
            "action_id": int(action.id),
            "record_id": int(payment.id),
            "render_profile": "edit",
        }})

        self.assertTrue(result.get("ok"), result)
        data = result.get("data") or {}
        head = data.get("head") if isinstance(data.get("head"), dict) else {}
        self.assertEqual(str(head.get("view_type") or data.get("view_type") or "").strip().lower(), "form")

        buttons = data.get("buttons") if isinstance(data.get("buttons"), list) else []
        toolbar = data.get("toolbar") if isinstance(data.get("toolbar"), dict) else {}
        header_rows = toolbar.get("header") if isinstance(toolbar.get("header"), list) else []
        self.assertFalse(header_rows, f"form contract should not expose toolbar header rows: {result}")

        for row in buttons:
            if not isinstance(row, dict):
                continue
            self.assertEqual(str(row.get("selection") or "none").strip().lower(), "none", result)
            self.assertIn(str(row.get("level") or "").strip().lower(), {"header", "smart", "sidebar", "footer"}, result)

    def test_ui_contract_action_open_tier_review_payment_list_hides_nav_loop_actions(self):
        action = self.env.ref("smart_construction_core.action_sc_tier_review_my_payment_request", raise_if_not_found=False)
        if not action:
            self.skipTest("smart_construction_core.action_sc_tier_review_my_payment_request not installed")

        run_env = self.env
        demo_user = self.env["res.users"].sudo().search([("login", "=", "demo_full")], limit=1)
        if demo_user:
            run_env = self.env(user=demo_user)

        handler = UiContractHandler(run_env)
        result = handler.handle(payload={"params": {"op": "action_open", "action_id": int(action.id)}})

        self.assertTrue(result.get("ok"), result)
        data = result.get("data") or {}
        head = data.get("head") if isinstance(data.get("head"), dict) else {}
        self.assertEqual(str(head.get("model") or "").strip(), "tier.review")
        self.assertEqual(str(head.get("view_type") or data.get("view_type") or "").strip().lower(), "tree")

        def has_nav_loop(rows):
            return any(
                isinstance(row, dict)
                and str(row.get("key") or "").startswith("smart_construction_core.action_sc_tier_review_my_")
                for row in rows
            )

        buttons = data.get("buttons") if isinstance(data.get("buttons"), list) else []
        toolbar = data.get("toolbar") if isinstance(data.get("toolbar"), dict) else {}
        header_rows = toolbar.get("header") if isinstance(toolbar.get("header"), list) else []
        self.assertFalse(has_nav_loop(buttons), result)
        self.assertFalse(has_nav_loop(header_rows), result)

    def test_nav_enrich_server_action_infers_mapped_model(self):
        menu = self.env.ref("smart_construction_core.menu_sc_project_wbs", raise_if_not_found=False)
        if not menu:
            self.skipTest("smart_construction_core.menu_sc_project_wbs not installed")

        dispatcher = NavDispatcher(self.env, self.env)
        tree = [{"menu_id": int(menu.id), "children": []}]
        dispatcher._enrich_nav_models(tree)
        model = str(tree[0].get("model") or "").strip()
        self.assertEqual(model, "construction.work.breakdown")

    def test_nav_enrich_menu_action_keeps_formal_self_funding_refund_projection(self):
        menu = self.env.ref("smart_construction_core.menu_sc_self_funding_advance_refund", raise_if_not_found=False)
        current_action = self.env.ref("smart_construction_core.action_sc_self_funding_registration_refund", raise_if_not_found=False)
        stale_action = self.env.ref("smart_construction_core.action_sc_self_funding_deposit_refund", raise_if_not_found=False)
        if not menu or not current_action or not stale_action:
            self.skipTest("self funding refund menu/action fixtures not installed")

        dispatcher = NavDispatcher(self.env, self.env)
        tree = [
            {
                "menu_id": int(menu.id),
                "action_id": int(stale_action.id),
                "action_type": "ir.actions.act_window",
                "action_xmlid": "smart_construction_core.action_sc_self_funding_deposit_refund",
                "model": "sc.expense.claim",
                "action": {
                    "id": int(stale_action.id),
                    "type": "ir.actions.act_window",
                    "res_model": "sc.expense.claim",
                },
                "children": [],
            }
        ]
        dispatcher._enrich_nav_models(tree)

        self.assertEqual(tree[0].get("action_id"), current_action.id)
        self.assertEqual(tree[0].get("action_xmlid"), "smart_construction_core.action_sc_self_funding_registration_refund")
        self.assertEqual(tree[0].get("model"), "sc.self.funding.registration")
