# -*- coding: utf-8 -*-
import runpy
import json
from copy import deepcopy
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged

@tagged("post_install", "-at_install", "r11c_locked_menu")
class TestLockedMenuPolicyInitialization(TransactionCase):
    def _product_policy_state(self):
        policies = self.env["sc.product.policy"].sudo().with_context(
            active_test=False
        ).search([
            ("product_key", "in", ["construction.standard", "construction.preview"]),
        ])
        return {
            policy.product_key: {
                "menu_groups": deepcopy(policy.menu_groups),
                "capabilities": deepcopy(policy.capabilities),
            }
            for policy in policies
        }

    def _run_preview_promotion_migration(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "17.0.0.183"
            / "post-migrate.py"
        )
        migration = runpy.run_path(str(path))
        result = migration["migrate"](self.env.cr, "17.0.0.182")
        self.env["sc.product.policy"].invalidate_model()
        return result

    def _run_center_identity_migration(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "migrations"
            / "17.0.0.184"
            / "post-migrate.py"
        )
        migration = runpy.run_path(str(path))
        result = migration["migrate"](self.env.cr, "17.0.0.183")
        self.env["sc.product.policy"].invalidate_model()
        return result

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

    def test_preview_promotion_migration_preserves_maintained_policy_and_is_idempotent(self):
        policy_model = self.env["sc.product.policy"]
        target_xmlid = "smart_construction_core.menu_sc_project_quick_create"
        standard = policy_model.search(
            [("product_key", "=", "construction.standard")], limit=1
        )
        preview = policy_model.search(
            [("product_key", "=", "construction.preview")], limit=1
        )
        expected_menu_ids = {
            policy.product_key: {menu["menu_xmlid"] for group in policy.menu_groups
                                 for menu in group["menus"]}
            for policy in (standard, preview)
        }
        standard_groups = deepcopy(standard.menu_groups)
        for group in standard_groups:
            group["menus"] = [
                menu for menu in group.get("menus") or []
                if menu.get("menu_xmlid") != target_xmlid
            ]
        standard.write({"menu_groups": [group for group in standard_groups if group["menus"]]})
        preview_groups = deepcopy(preview.menu_groups)
        for group in preview_groups:
            for menu in group.get("menus") or []:
                if menu.get("menu_xmlid") == target_xmlid:
                    menu.update({
                        "release_state": "preview",
                        "capability_maturity": "PREVIEW_FOUNDATION",
                    })
        preview.write({"menu_groups": preview_groups})
        stale_maturity_key = "smart_construction_core.menu_sc_project_project"
        stale_groups = deepcopy(standard.menu_groups)
        for group in stale_groups:
            for menu in group.get("menus") or []:
                if menu.get("menu_xmlid") == stale_maturity_key:
                    menu["capability_maturity"] = "PREVIEW_FOUNDATION"
        standard.write({"menu_groups": stale_groups})
        hidden_xmlid = "smart_construction_core.menu_sc_project_project"
        for target in (standard, preview):
            groups = deepcopy(target.menu_groups)
            for group in groups:
                for menu in group.get("menus") or []:
                    if menu.get("menu_xmlid") == hidden_xmlid:
                        menu.update({
                            "release_state": "hidden",
                            "enabled": False,
                            "capability_maturity": "MAINTAINED_HIDDEN",
                        })
            target.write({"menu_groups": groups})
        extra_xmlid = "test.close03.maintained_extension"
        extra_row = {
            "menu_xmlid": extra_xmlid,
            "label": "Maintained extension",
            "enabled": True,
            "release_state": "released",
            "capability_maturity": "MAINTAINED_EXTENSION",
        }
        for target in (standard, preview):
            groups = deepcopy(target.menu_groups)
            groups[0].setdefault("menus", []).append(deepcopy(extra_row))
            capabilities = deepcopy(target.capabilities)
            capabilities.append({
                "capability_key": "test.close03.maintained_extension",
                "identity_kind": "menu",
                "menu_xmlid": extra_xmlid,
                "label": "Maintained extension",
                "enabled": True,
                "release_state": "released",
                "capability_maturity": "MAINTAINED_EXTENSION",
            })
            target.write({"menu_groups": groups, "capabilities": capabilities})

        hidden_before = {
            product_key: next(
                menu
                for group in state["menu_groups"]
                for menu in group.get("menus") or []
                if menu.get("menu_xmlid") == hidden_xmlid
            )
            for product_key, state in self._product_policy_state().items()
        }
        first = self._run_preview_promotion_migration()
        self.assertIn(target_xmlid, first["construction.standard"]["diagnostics"]["standard_added"])
        first_state = self._product_policy_state()
        for target in (standard, preview):
            target.invalidate_recordset()
            rows = [
                menu
                for group in target.menu_groups
                for menu in group.get("menus") or []
            ]
            expected = expected_menu_ids[target.product_key] | {extra_xmlid}
            self.assertEqual({row["menu_xmlid"] for row in rows}, expected)
            self.assertEqual(len(rows), len(expected))
            by_xmlid = {menu.get("menu_xmlid"): menu for menu in rows}
            self.assertEqual(
                {
                    key: by_xmlid[extra_xmlid].get(key)
                    for key in extra_row
                },
                extra_row,
            )
            self.assertEqual(by_xmlid[hidden_xmlid], hidden_before[target.product_key])
            self.assertTrue(all(
                menu.get("release_state") == "released"
                for xmlid, menu in by_xmlid.items()
                if xmlid not in {extra_xmlid, hidden_xmlid}
            ))
            self.assertTrue(all(
                menu.get("capability_maturity") == "RELEASED_FOUNDATION"
                for xmlid, menu in by_xmlid.items()
                if xmlid not in {extra_xmlid, hidden_xmlid}
            ))
            self.assertIn(target_xmlid, {menu.get("menu_xmlid") for menu in rows})
            capabilities = {
                capability.get("menu_xmlid"): capability
                for capability in target.capabilities
            }
            self.assertEqual(capabilities[extra_xmlid]["capability_maturity"], "MAINTAINED_EXTENSION")

        for product_key in ("construction.standard", "construction.preview"):
            self.assertGreater(first[product_key]["changed_count"], 0)
            expected = expected_menu_ids[product_key] | {extra_xmlid}
            policy = policy_model.search([("product_key", "=", product_key)], limit=1)
            self.assertEqual({row["menu_xmlid"] for row in policy.capabilities}, expected)
            self.assertEqual(first[product_key]["persisted_count"], len(expected))
            self.assertEqual(first[product_key]["capability_count"], len(expected))

        second = self._run_preview_promotion_migration()
        self.assertEqual(second["construction.standard"]["diagnostics"]["changed_entry_xmlids"], [])
        self.assertEqual(second["construction.preview"]["diagnostics"]["changed_entry_xmlids"], [])
        self.assertEqual(self._product_policy_state(), first_state)

    def test_preview_promotion_migration_accepts_unmaintained_canonical_policy(self):
        from odoo.addons.smart_construction_core.services.product_menu_source import load_source, project
        _contract, publication = project(load_source())
        expected = {row["product_key"]: {cap["menu_xmlid"] for cap in row["capabilities"]}
                    for row in publication["products"]}
        result = self._run_preview_promotion_migration()
        for product_key in ("construction.standard", "construction.preview"):
            self.assertTrue(expected[product_key])
            policy = self.env["sc.product.policy"].search([("product_key", "=", product_key)], limit=1)
            self.assertEqual({row["menu_xmlid"] for row in policy.capabilities}, expected[product_key])
            self.assertEqual(result[product_key]["changed_count"], len(expected[product_key]))
            self.assertEqual(result[product_key]["persisted_count"], len(expected[product_key]))
            self.assertEqual(result[product_key]["capability_count"], len(expected[product_key]))
            self.assertFalse(result[product_key]["missing_xmlids"])
            self.assertFalse(result[product_key]["wrong_release_xmlids"])
            self.assertFalse(result[product_key]["wrong_maturity_xmlids"])

    def test_preview_promotion_validation_rejects_canonical_preview_rows(self):
        policy_model = self.env["sc.product.policy"]
        standard = policy_model.search(
            [("product_key", "=", "construction.standard")], limit=1
        )
        groups = deepcopy(standard.menu_groups)
        target = next(
            menu
            for group in groups
            for menu in group.get("menus") or []
            if menu.get("menu_xmlid") == "smart_construction_core.menu_sc_project_quick_create"
        )
        target.update({
            "release_state": "preview",
            "capability_maturity": "PREVIEW_FOUNDATION",
        })
        standard.write({"menu_groups": groups})

        with self.assertRaisesRegex(
            RuntimeError, "CLOSE03_PREVIEW_PROMOTION_INCOMPLETE"
        ):
            policy_model.validate_preview_entry_promotion({
                "changed_entry_xmlids": {
                    "construction.standard": [
                        "smart_construction_core.menu_sc_project_quick_create",
                    ],
                    "construction.preview": [],
                },
            })

    def test_center_identity_migration_maps_legacy_names_and_is_idempotent(self):
        policy = self.env["sc.product.policy"].search(
            [("product_key", "=", "construction.standard")], limit=1
        )
        legacy_groups = deepcopy(policy.menu_groups)
        for group in legacy_groups:
            label = str(group.get("group_label") or group.get("label") or "").strip()
            group["group_key"] = f"construction.{label}"
            group.pop("label", None)
            if "sequence" not in group and "center_sequence" not in group:
                group["center_sequence"] = 10
        self.env.cr.execute(
            "UPDATE sc_product_policy SET menu_groups=%s::jsonb "
            "WHERE id=%s",
            (json.dumps(legacy_groups, ensure_ascii=False), policy.id),
        )
        policy.invalidate_recordset()
        first = self._run_center_identity_migration()
        policy.invalidate_recordset()
        self.assertIn(
            "construction.standard",
            {row["product_key"] for row in first["changed"]},
        )
        self.assertEqual(
            [group["center_key"] for group in policy.menu_groups],
            [
                "workspace.home.workbench",
                "construction.center.project",
                "construction.center.contract",
                "construction.center.cost",
                "construction.center.supply_chain",
                "construction.center.finance",
                "construction.center.tax",
                "construction.center.accounting",
                "construction.center.reporting",
                "construction.center.administration",
                "construction.center.product_configuration",
            ],
        )
        self.assertTrue(
            all(
                group["group_key"] == group["center_key"]
                for group in policy.menu_groups
            )
        )
        second = self._run_center_identity_migration()
        self.assertEqual(second["changed"], [])

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
