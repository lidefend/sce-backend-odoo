# -*- coding: utf-8 -*-
import runpy
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "system_product_release")
class TestSystemProductRelease(TransactionCase):
    PRODUCT_KEYS = ("construction.standard", "construction.preview")

    def _active_system_release(self, product_key):
        return self.env["sc.edition.release.snapshot"].sudo().search([
            ("product_key", "=", product_key),
            ("state", "=", "released"),
            ("is_active", "=", True),
            ("active", "=", True),
        ], order="released_at desc, activated_at desc, id desc", limit=1)

    def test_fresh_install_materializes_the_shipped_product_release(self):
        from odoo.addons.smart_core.delivery.edition_release_snapshot_service import (
            EditionReleaseSnapshotService,
        )
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import (
            load_runtime_surface,
        )

        service = EditionReleaseSnapshotService(self.env)
        self.assertTrue(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("smart_core.release_operator.catalog_source_db")
        )
        for product_key in self.PRODUCT_KEYS:
            with self.subTest(product_key=product_key):
                snapshot = self._active_system_release(product_key)
                self.assertTrue(snapshot)
                self.assertEqual(snapshot.version.split("-", 2)[:2], ["system", "baseline"])
                integrity = service.assert_frozen_release_integrity(snapshot)
                self.assertTrue(integrity["exact_match"])
                policy = snapshot.snapshot_json.get("policy") or {}
                scenarios = (policy.get("business_scene_composition") or {}).get("scenarios")
                self.assertEqual(46, len(scenarios or []))
        runtime = load_runtime_surface(self.env)
        self.assertEqual("published_release", runtime.get("runtime_scope"))
        self.assertEqual(46, len(runtime.get("scenarios") or []))

    def test_system_product_release_materialization_is_idempotent(self):
        initial = {
            product_key: self._active_system_release(product_key).id
            for product_key in self.PRODUCT_KEYS
        }
        result = self.env["sc.product.policy"].sudo().ensure_system_product_release_snapshots()
        self.assertTrue(all(row["reused"] for row in result["products"]))
        self.assertEqual(
            initial,
            {
                product_key: self._active_system_release(product_key).id
                for product_key in self.PRODUCT_KEYS
            },
        )

    def test_upgrade_migration_materializes_missing_system_release(self):
        snapshots = self.env["sc.edition.release.snapshot"].sudo()
        snapshots.search([
            ("product_key", "in", self.PRODUCT_KEYS),
            ("is_active", "=", True),
        ]).write({"is_active": False})
        migration = runpy.run_path(str(
            Path(__file__).resolve().parents[1] / "migrations/0.1.2/post-migrate.py"
        ))
        migration["migrate"](self.env.cr, "0.1.1")
        for product_key in self.PRODUCT_KEYS:
            with self.subTest(product_key=product_key):
                self.assertTrue(self._active_system_release(product_key))
