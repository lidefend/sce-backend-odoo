#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "production_colocated_backup", ROOT / "scripts/release/production_colocated_backup.py"
)
assert SPEC and SPEC.loader
BACKUP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BACKUP)


class ColocatedReleaseStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = (ROOT / "scripts/release/initialize_colocated_platform_snapshot.py").read_text()
        cls.configure = (ROOT / "scripts/release/configure_colocated_platform_core.py").read_text()
        cls.compose = (ROOT / "docker-compose.production-candidate.yml").read_text()
        cls.backup = (ROOT / "scripts/release/production_colocated_backup.py").read_text()
        cls.matrix = (ROOT / "scripts/release/verify_colocated_platform_matrix.py").read_text()
        cls.system_init = (ROOT / "addons/smart_core/handlers/system_init.py").read_text()
        cls.policy_sync = (ROOT / "addons/smart_construction_core/models/support/product_policy_sync.py").read_text()

    def test_snapshot_uses_release_service_not_direct_table_insert(self):
        self.assertIn("EditionReleaseSnapshotService", self.snapshot)
        self.assertIn("freeze_release_surface", self.snapshot)
        self.assertNotIn(".create(", self.snapshot)
        self.assertNotIn("INSERT INTO", self.snapshot)

    def test_snapshot_has_idempotent_fingerprint_short_circuit(self):
        self.assertIn("_text(existing_draft.get(\"fingerprint\")) == fingerprint", self.snapshot)
        self.assertIn('"idempotent": True', self.snapshot)

    def test_snapshot_synchronizes_and_gates_locked_policy_before_freeze(self):
        body = self.snapshot.split("def main():", 1)[1]
        sync_at = body.index("synchronize_locked_formal_menu_policy")
        pre_gate_at = body.index("assert_policy_matches_locked_contract")
        freeze_at = body.index("freeze_release_surface")
        post_gate_at = body.index("assert_snapshot_matches_locked_contract")
        self.assertLess(sync_at, pre_gate_at)
        self.assertLess(pre_gate_at, freeze_at)
        self.assertLess(freeze_at, post_gate_at)
        self.assertIn("env.cr.rollback()", self.snapshot)

    def test_formal_synchronization_has_no_catalog_fallback(self):
        method = self.policy_sync.split("def synchronize_locked_formal_menu_policy", 1)[1].split(
            "def sync_construction_menu_product_policies", 1
        )[0]
        self.assertIn("load_locked_menu_policy_contract", method)
        self.assertNotIn("ProductPolicyCatalogSyncService", method)

    def test_formal_synchronization_stops_before_resolving_unapproved_target(self):
        method = self.policy_sync.split("def synchronize_locked_formal_menu_policy", 1)[1].split(
            "def sync_construction_menu_product_policies", 1
        )[0]
        decision_at = method.index("FORMAL_BUSINESS_DECISION_REQUIRED_TARGETS")
        menu_resolution_at = method.index("self.env.ref(menu_xmlid")
        self.assertLess(decision_at, menu_resolution_at)
        self.assertIn('"BUSINESS_DECISION_REQUIRED"', method)

    def test_configuration_requires_exact_ack_and_current_database(self):
        self.assertIn("I_ACKNOWLEDGE_COLOCATED_PLATFORM_CONFIGURATION", self.configure)
        self.assertIn("expected_db != current_db", self.configure)

    def test_formal_compose_has_no_platform_database_default(self):
        self.assertIn("PLATFORM_RELEASE_DB:?PLATFORM_RELEASE_DB is required", self.compose)

    def test_backup_is_paired_and_targets_sc_production(self):
        self.assertEqual(BACKUP.PRODUCTION_DB, "sc_production")
        self.assertIn("database.dump", self.backup)
        self.assertIn("filestore.tar.gz", self.backup)
        self.assertIn("required platform table missing", self.backup)
        self.assertIn("find '{filestore_root}/{database}' -type f -print -quit", self.backup)

    def test_restore_drill_namespace_and_container_isolation_are_enforced(self):
        self.assertTrue(BACKUP.RESTORE_DB.fullmatch("r10e_restore_acceptance"))
        self.assertFalse(BACKUP.RESTORE_DB.fullmatch("sc_production"))
        self.assertIn("restore drill containers must be isolated", self.backup)

    def test_production_missing_snapshot_withholds_ungated_navigation(self):
        self.assertIn('if release_gate.get("fail_closed"):', self.system_init)
        self.assertIn('delivery_payload["nav"] = []', self.system_init)

    def test_database_matrix_has_fixed_45_request_inventory_and_safe_rejection(self):
        self.assertIn('if len(cases) != 45:', self.matrix)
        self.assertIn('status in {400, 401, 403}', self.matrix)
        self.assertIn('"X-Platform-DB"', self.matrix)


class BackupManifestValidationTests(unittest.TestCase):
    def test_valid_nonempty_backup_manifest_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            values = {"database.dump": b"database", "filestore.tar.gz": b"filestore"}
            checksums = {}
            for name, value in values.items():
                (root / name).write_bytes(value)
                checksums[name] = BACKUP._sha(root / name)
            (root / "manifest.json").write_text(json.dumps({
                "database": "sc_production", "checksums": checksums,
            }))
            self.assertEqual(BACKUP.validate_backup(root)["database"], "sc_production")

    def test_wrong_database_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "manifest.json").write_text(json.dumps({"database": "sc_prod", "checksums": {}}))
            with self.assertRaisesRegex(BACKUP.BackupError, "identity"):
                BACKUP.validate_backup(root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
