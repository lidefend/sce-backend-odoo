# -*- coding: utf-8 -*-
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
