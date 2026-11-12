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

    def test_historical_payment_readonly_entry_is_not_republished(self):
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
            self.assertEqual(rows, [])

    def test_policy_migration_adds_my_work_without_overwriting_existing_rows(self):
        policy_model = self.env["sc.product.policy"]
        self.assertFalse(hasattr(policy_model, "merge_locked_formal_menu_additions"))
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
        unrelated = None
        for group in groups:
            menus = []
            for menu in group.get("menus") or []:
                if menu.get("menu_xmlid") == "smart_construction_core.menu_sc_my_work":
                    removed = True
                    continue
                if (
                    unrelated is None
                    and menu.get("enabled")
                    and menu.get("release_state") == "released"
                ):
                    unrelated = (menu["menu_xmlid"], menu["release_state"])
                menus.append(menu)
            group["menus"] = menus
            if menus:
                retained.append(group)
        self.assertTrue(removed)
        self.assertTrue(unrelated)
        custom_capability = {
            "capability_key": "test.admin.capability",
            "identity_kind": "test",
            "label": "Admin maintained capability",
            "enabled": True,
            "release_state": "released",
        }
        policy.write({
            "menu_groups": retained,
            "capabilities": [custom_capability],
        })
        from odoo.addons.smart_core.delivery.edition_release_snapshot_service import (
            EditionReleaseSnapshotService,
        )
        snapshot_service = EditionReleaseSnapshotService(self.env)
        baseline = snapshot_service.freeze_release_surface(
            product_key="construction.standard",
            version="test-baseline",
            replace_active=True,
            note="test active baseline without My Work",
        )
        baseline_payload = deepcopy(
            self.env["sc.edition.release.snapshot"].sudo().browse(
                baseline["id"]
            ).snapshot_json
        )
        draft_groups = deepcopy(policy.menu_groups)
        for group in draft_groups:
            for menu in group.get("menus") or []:
                if menu.get("menu_xmlid") == unrelated[0]:
                    menu["release_state"] = "hidden"
                    menu["enabled"] = False
        policy.write({"menu_groups": draft_groups})

        result = policy_model._reconcile_locked_menu_release(
            "construction.standard",
            menu_xmlid="smart_construction_core.menu_sc_my_work",
            version="test-my-work-delta",
        )
        self.assertEqual(
            result["added"], ["smart_construction_core.menu_sc_my_work"]
        )
        self.assertTrue(result["snapshot_created"])
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
        self.assertIn(custom_capability, policy.capabilities)
        old = self.env["sc.edition.release.snapshot"].sudo().browse(
            baseline["id"]
        )
        self.assertEqual(old.snapshot_json, baseline_payload)
        active = self.env["sc.edition.release.snapshot"].sudo().search([
            ("product_key", "=", "construction.standard"),
            ("state", "=", "released"),
            ("is_active", "=", True),
            ("active", "=", True),
        ], limit=1)
        self.assertNotEqual(active.id, old.id)
        self.assertEqual(active.rollback_target_snapshot_id.id, old.id)
        payload = active.snapshot_json
        pairs = {
            (row.get("menu_id"), row.get("action_id"))
            for group in payload["policy"]["menu_groups"]
            for row in group.get("menus") or []
            if row.get("enabled") and row.get("release_state") == "released"
        }
        self.assertIn((menu.id, menu.action.id), pairs)
        snapshot_policy = payload["policy"]
        unrelated_snapshot_rows = [
            row
            for group in snapshot_policy["menu_groups"]
            for row in group.get("menus") or []
            if row.get("menu_xmlid") == unrelated[0]
        ]
        self.assertEqual(
            unrelated_snapshot_rows[0].get("release_state"), unrelated[1]
        )
        again = policy_model._reconcile_locked_menu_release(
            "construction.standard",
            menu_xmlid="smart_construction_core.menu_sc_my_work",
            version="test-my-work-delta-second",
        )
        self.assertEqual(again["added"], [])
        self.assertFalse(again["snapshot_created"])
        self.assertEqual(again["snapshot_id"], active.id)
        first_reconciled_payload = deepcopy(active.snapshot_json)
        # Simulate a governed rollback to the baseline. Replaying the migration
        # must not rewrite the already-published historical migration snapshot.
        active.write({
            "state": "superseded",
            "is_active": False,
            "superseded_at": "2026-11-12 00:00:00",
        })
        old.write({
            "state": "released",
            "is_active": True,
            "superseded_at": False,
        })
        replay = policy_model._reconcile_locked_menu_release(
            "construction.standard",
            menu_xmlid="smart_construction_core.menu_sc_my_work",
            version="test-my-work-delta",
        )
        self.assertTrue(replay["snapshot_created"])
        self.assertNotEqual(replay["snapshot_id"], active.id)
        self.assertEqual(active.snapshot_json, first_reconciled_payload)
        replay_snapshot = self.env["sc.edition.release.snapshot"].sudo().browse(
            replay["snapshot_id"]
        )
        self.assertEqual(replay_snapshot.rollback_target_snapshot_id.id, old.id)

    def test_policy_reconciliation_without_active_snapshot_has_one_target_row(self):
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
        for group in groups:
            group["menus"] = [
                menu for menu in group.get("menus") or []
                if menu.get("menu_xmlid") != "smart_construction_core.menu_sc_my_work"
            ]
        policy.write({
            "menu_groups": [group for group in groups if group["menus"]],
            "capabilities": [],
        })
        result = policy_model._reconcile_locked_menu_release(
            "construction.standard",
            menu_xmlid="smart_construction_core.menu_sc_my_work",
            version="test-first-publication",
        )
        self.assertTrue(result["snapshot_created"])
        snapshot = self.env["sc.edition.release.snapshot"].sudo().browse(
            result["snapshot_id"]
        )
        rows = [
            menu
            for group in snapshot.snapshot_json["policy"]["menu_groups"]
            for menu in group.get("menus") or []
            if menu.get("menu_xmlid") == "smart_construction_core.menu_sc_my_work"
        ]
        self.assertEqual(len(rows), 1)
