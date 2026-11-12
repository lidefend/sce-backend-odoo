# -*- coding: utf-8 -*-
from copy import deepcopy

from odoo.tests.common import TransactionCase, tagged

@tagged("post_install", "-at_install", "r11c_locked_menu")
class TestLockedMenuPolicyInitialization(TransactionCase):
    def _artifact_state(self):
        policies = self.env["sc.product.policy"].search_read(
            [("product_key", "in", ["construction.standard", "construction.preview"])],
            ["product_key", "menu_groups"],
            order="product_key",
        )
        return {
            "policies": policies,
            "snapshots": self.env["sc.edition.release.snapshot"].search_count([]),
            "formal_action": self.env["ir.model.data"].search_count(
                [
                    ("module", "=", "smart_construction_core"),
                    ("name", "=", "action_sc_tax_certificate_registration_user"),
                ]
            ),
            "legacy_model": self.env["ir.model"].search_count(
                [("model", "=", "sc.legacy.payment.residual.fact")]
            ),
        }

    def test_approved_tax_certificate_target_initializes_without_legacy_model(self):
        self.env["sc.product.policy"].synchronize_locked_formal_menu_policy("construction.standard")
        policy = self.env["sc.product.policy"].search(
            [("product_key", "=", "construction.standard")], limit=1
        )
        row = next(
            menu
            for group in policy.menu_groups
            for menu in group.get("menus", [])
            if menu.get("menu_xmlid") == "smart_construction_core.menu_sc_tax_certificate_registration_user"
        )
        self.assertEqual(row.get("res_model"), "sc.tax.certificate.registration")
        self.assertGreater(row.get("menu_id"), 0)
        self.assertEqual(self._artifact_state()["formal_action"], 1)
        self.assertEqual(self._artifact_state()["legacy_model"], 0)

    def test_historical_payment_readonly_entry_is_in_locked_products(self):
        menu_xmlid = "smart_construction_core.menu_sc_historical_payment_fact"
        for product_key in ("construction.standard", "construction.preview"):
            self.env["sc.product.policy"].synchronize_locked_formal_menu_policy(product_key)
            policy = self.env["sc.product.policy"].search(
                [("product_key", "=", product_key)], limit=1
            )
            rows = [
                menu
                for group in policy.menu_groups
                for menu in group.get("menus", [])
                if menu.get("menu_xmlid") == menu_xmlid
            ]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].get("res_model"), "sc.historical.payment.fact")
            self.assertEqual(rows[0].get("entry_intent"), "inquiry")
            self.assertGreater(rows[0].get("menu_id"), 0)

    def test_policy_migration_adds_my_work_without_overwriting_existing_rows(self):
        policy_model = self.env["sc.product.policy"]
        policy_model.synchronize_locked_formal_menu_policy("construction.standard")
        policy = policy_model.search(
            [("product_key", "=", "construction.standard")], limit=1
        )
        self.env["sc.edition.release.snapshot"].sudo().search([
            ("product_key", "=", "construction.standard"),
            ("is_active", "=", True),
        ]).write({"is_active": False})
        groups = deepcopy(policy.menu_groups)
        retained = []
        removed = False
        for group in groups:
            menus = []
            for menu in group.get("menus") or []:
                if menu.get("menu_xmlid") == "smart_construction_core.menu_sc_my_work":
                    removed = True
                    continue
                menus.append(menu)
            group["menus"] = menus
            if menus:
                retained.append(group)
        self.assertTrue(removed)
        policy.write({"menu_groups": retained})

        result = policy_model.merge_locked_formal_menu_additions(
            "construction.standard",
            menu_xmlids=["smart_construction_core.menu_sc_my_work"],
        )
        self.assertEqual(
            result["added"], ["smart_construction_core.menu_sc_my_work"]
        )
        rows = [
            menu
            for group in policy.menu_groups
            for menu in group.get("menus") or []
            if menu.get("menu_xmlid") == "smart_construction_core.menu_sc_my_work"
        ]
        self.assertEqual(len(rows), 1)
        menu = self.env.ref("smart_construction_core.menu_sc_my_work")
        self.assertEqual(rows[0].get("menu_id"), menu.id)
        self.assertEqual(rows[0].get("action_id"), menu.action.id)
        self.assertEqual(rows[0].get("release_state"), "released")
        again = policy_model.merge_locked_formal_menu_additions(
            "construction.standard",
            menu_xmlids=["smart_construction_core.menu_sc_my_work"],
        )
        self.assertEqual(again["added"], [])
        self.assertEqual(
            again["skipped"], ["smart_construction_core.menu_sc_my_work"]
        )
        from odoo.addons.smart_core.delivery.edition_release_snapshot_service import (
            EditionReleaseSnapshotService,
        )
        snapshot = EditionReleaseSnapshotService(self.env).freeze_release_surface(
            product_key="construction.standard",
            replace_active=True,
            note="test policy and release coherence",
        )
        active = self.env["sc.edition.release.snapshot"].sudo().search([
            ("product_key", "=", "construction.standard"),
            ("state", "=", "released"),
            ("is_active", "=", True),
            ("active", "=", True),
        ], limit=1)
        self.assertEqual(active.id, snapshot["id"])
        payload = active.snapshot_json
        pairs = {
            (menu.get("menu_id"), menu.get("action_id"))
            for group in payload["policy"]["menu_groups"]
            for menu in group.get("menus") or []
            if menu.get("enabled") and menu.get("release_state") == "released"
        }
        self.assertIn((menu.id, menu.action.id), pairs)
