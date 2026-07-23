# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.services.locked_menu_policy_contract import (
    LockedMenuPolicyContractError,
)


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
            "invented_action": self.env["ir.model.data"].search_count(
                [
                    ("module", "=", "smart_construction_core"),
                    ("name", "=", "action_sc_tax_certificate_registration_user"),
                ]
            ),
            "invented_model": self.env["ir.model"].search_count(
                [("model", "=", "sc.legacy.payment.residual.fact")]
            ),
        }

    def test_unapproved_target_fails_before_artifact_mutation(self):
        before = self._artifact_state()
        with self.assertRaises(LockedMenuPolicyContractError) as raised:
            with self.env.cr.savepoint():
                self.env["sc.product.policy"].synchronize_locked_formal_menu_policy(
                    "construction.standard"
                )
        self.assertEqual(raised.exception.code, "BUSINESS_DECISION_REQUIRED")
        self.assertIn(
            "smart_construction_core.menu_sc_tax_certificate_registration_user",
            raised.exception.detail,
        )
        self.env.invalidate_all()
        self.assertEqual(self._artifact_state(), before)
