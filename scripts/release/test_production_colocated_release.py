#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


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
        self.assertIn("SHA256SUMS", self.backup)
        self.assertIn("required platform table missing", self.backup)
        self.assertIn(f"test -d '{{filestore_root}}/{{database}}'", self.backup)
        self.assertNotIn(
            "find '{filestore_root}/{database}' -type f -print -quit",
            self.backup,
        )

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


class BackupArtifactContractTests(unittest.TestCase):
    def _environment(self) -> dict[str, str]:
        return {
            "BACKUP_TARGET_DB": "sc_production",
            "BACKUP_DB_CONTAINER": "sc_production-db-1",
            "BACKUP_ODOO_CONTAINER": "sc_production-odoo-1",
            "BACKUP_DB_USER": "odoo",
            "BACKUP_FILESTORE_ROOT": "/opt/sce-runtime/filestore",
            "BACKUP_TOOL_REVISION": "a" * 40,
        }

    def _fake_run(self, calls, *, fail_at: str | None = None):
        def run(args, *, input_bytes=None):
            calls.append((tuple(args), input_bytes))
            command = " ".join(args)
            if fail_at and fail_at in command:
                raise BACKUP.BackupError(f"simulated failure: {fail_at}")
            if "pg_dump" in args:
                return b"postgresql-custom-dump"
            if "tar" in args:
                return b"gzip-filestore-archive"
            if "SELECT current_database()" in args:
                return b"sc_production\n"
            if "pg_restore" in args:
                return b"restore catalog\n"
            return b""

        return run

    def _create_backup(self, root: Path, *, caller_umask: int = 0o022):
        calls = []
        previous = os.umask(caller_umask)
        try:
            with (
                mock.patch.dict(os.environ, self._environment(), clear=False),
                mock.patch.object(
                    BACKUP, "_run", side_effect=self._fake_run(calls)
                ),
            ):
                directory = BACKUP.backup(root)
        finally:
            os.umask(previous)
        return directory, calls

    def test_backup_enforces_modes_independently_of_caller_umask(self):
        for caller_umask in (0o022, 0o000):
            with self.subTest(caller_umask=oct(caller_umask)):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    root.chmod(0o700)
                    directory, _calls = self._create_backup(
                        root, caller_umask=caller_umask
                    )
                    self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
                    for name in BACKUP.ARTIFACTS + (
                        BACKUP.CHECKSUM_FILE,
                    ):
                        self.assertEqual(
                            (directory / name).stat().st_mode & 0o777,
                            0o600,
                        )

    def test_backup_generates_complete_relative_checksum_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            directory, _calls = self._create_backup(root)
            lines = (directory / BACKUP.CHECKSUM_FILE).read_text().splitlines()
            self.assertEqual(len(lines), 3)
            self.assertEqual(
                {line.split("  ", 1)[1] for line in lines},
                set(BACKUP.ARTIFACTS),
            )
            self.assertFalse(
                any(
                    line.endswith(BACKUP.CHECKSUM_FILE)
                    or line.split("  ", 1)[1].startswith("/")
                    for line in lines
                )
            )
            BACKUP.validate_backup(
                directory, require_artifact_contract=True
            )
            result = subprocess.run(
                ["sha256sum", "-c", BACKUP.CHECKSUM_FILE],
                cwd=directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_checksum_validation_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            directory, _calls = self._create_backup(root)
            with (directory / "database.dump").open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaisesRegex(BACKUP.BackupError, "validation"):
                BACKUP.validate_backup(
                    directory, require_artifact_contract=True
                )

    def test_missing_empty_and_symlink_artifacts_are_rejected(self):
        for mutation in ("missing", "empty", "symlink"):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    root.chmod(0o700)
                    directory, _calls = self._create_backup(root)
                    target = directory / "filestore.tar.gz"
                    if mutation == "missing":
                        target.unlink()
                    elif mutation == "empty":
                        target.write_bytes(b"")
                        target.chmod(0o600)
                    else:
                        payload = directory / "filestore-copy"
                        payload.write_bytes(target.read_bytes())
                        target.unlink()
                        target.symlink_to(payload)
                    with self.assertRaises(BACKUP.BackupError):
                        BACKUP.validate_backup(
                            directory, require_artifact_contract=True
                        )

    def test_missing_manifest_is_a_controlled_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            directory, _calls = self._create_backup(root)
            (directory / "manifest.json").unlink()
            with self.assertRaisesRegex(BACKUP.BackupError, "manifest"):
                BACKUP.validate_backup(
                    directory, require_artifact_contract=True
                )

    def test_pg_restore_failure_leaves_no_final_or_partial_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            calls = []
            with (
                mock.patch.dict(os.environ, self._environment(), clear=False),
                mock.patch.object(
                    BACKUP,
                    "_run",
                    side_effect=self._fake_run(calls, fail_at="pg_restore"),
                ),
                self.assertRaises(BACKUP.BackupError),
            ):
                BACKUP.backup(root)
            self.assertEqual(list(root.iterdir()), [])

    def test_database_or_filestore_command_failure_leaves_no_backup(self):
        for failure in ("pg_dump", " tar "):
            with self.subTest(failure=failure):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    root.chmod(0o700)
                    calls = []
                    with (
                        mock.patch.dict(
                            os.environ, self._environment(), clear=False
                        ),
                        mock.patch.object(
                            BACKUP,
                            "_run",
                            side_effect=self._fake_run(calls, fail_at=failure),
                        ),
                        self.assertRaises(BACKUP.BackupError),
                    ):
                        BACKUP.backup(root)
                    self.assertEqual(list(root.iterdir()), [])

    def test_empty_database_or_filestore_payload_leaves_no_backup(self):
        for empty_command in ("pg_dump", "tar"):
            with self.subTest(empty_command=empty_command):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    root.chmod(0o700)
                    calls = []
                    normal = self._fake_run(calls)

                    def empty_one(args, *, input_bytes=None):
                        if empty_command in args:
                            return b""
                        return normal(args, input_bytes=input_bytes)

                    with (
                        mock.patch.dict(
                            os.environ, self._environment(), clear=False
                        ),
                        mock.patch.object(
                            BACKUP, "_run", side_effect=empty_one
                        ),
                        self.assertRaises(BACKUP.BackupError),
                    ):
                        BACKUP.backup(root)
                    self.assertEqual(list(root.iterdir()), [])

    def test_manifest_write_failure_leaves_no_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            calls = []
            with (
                mock.patch.dict(os.environ, self._environment(), clear=False),
                mock.patch.object(
                    BACKUP, "_run", side_effect=self._fake_run(calls)
                ),
                mock.patch.object(
                    BACKUP, "_write_text", side_effect=OSError("write failed")
                ),
                self.assertRaises(BACKUP.BackupError),
            ):
                BACKUP.backup(root)
            self.assertEqual(list(root.iterdir()), [])

    def test_checksum_creation_failure_leaves_no_installable_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            calls = []
            with (
                mock.patch.dict(os.environ, self._environment(), clear=False),
                mock.patch.object(
                    BACKUP, "_run", side_effect=self._fake_run(calls)
                ),
                mock.patch.object(
                    BACKUP,
                    "_write_checksums",
                    side_effect=OSError("write failed"),
                ),
                self.assertRaises(BACKUP.BackupError),
            ):
                BACKUP.backup(root)
            self.assertEqual(list(root.iterdir()), [])

    def test_permission_validation_failure_removes_partial_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            calls = []
            with (
                mock.patch.dict(os.environ, self._environment(), clear=False),
                mock.patch.object(
                    BACKUP, "_run", side_effect=self._fake_run(calls)
                ),
                mock.patch.object(
                    BACKUP,
                    "_validate_artifacts",
                    side_effect=BACKUP.BackupError("unsafe permissions"),
                ),
                self.assertRaises(BACKUP.BackupError),
            ):
                BACKUP.backup(root)
            self.assertEqual(list(root.iterdir()), [])

    def test_checksum_validation_failure_removes_partial_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            calls = []
            with (
                mock.patch.dict(os.environ, self._environment(), clear=False),
                mock.patch.object(
                    BACKUP, "_run", side_effect=self._fake_run(calls)
                ),
                mock.patch.object(
                    BACKUP,
                    "_validate_checksums",
                    side_effect=BACKUP.BackupError("checksum mismatch"),
                ),
                self.assertRaises(BACKUP.BackupError),
            ):
                BACKUP.backup(root)
            self.assertEqual(list(root.iterdir()), [])

    def test_symlink_root_and_existing_newer_recovery_point_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / "target"
            target.mkdir(mode=0o700)
            linked = base / "linked"
            linked.symlink_to(target, target_is_directory=True)
            with (
                mock.patch.dict(os.environ, self._environment(), clear=False),
                self.assertRaises(BACKUP.BackupError),
            ):
                BACKUP.backup(linked)

            future = target / "sc_production-99991231T235959Z"
            future.mkdir(mode=0o700)
            with (
                mock.patch.dict(os.environ, self._environment(), clear=False),
                self.assertRaisesRegex(BACKUP.BackupError, "later"),
            ):
                BACKUP.backup(target)

    def test_manifest_additions_preserve_schema_one_compatibility(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            directory, calls = self._create_backup(root)
            manifest = json.loads(
                (directory / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["schema_version"], 1)
            self.assertEqual(manifest["database"], "sc_production")
            self.assertEqual(manifest["database_format"], "postgresql_custom")
            self.assertEqual(manifest["filestore_artifact"], "filestore.tar.gz")
            self.assertEqual(manifest["tool_revision"], "a" * 40)
            self.assertEqual(manifest["backup_status"], "complete")
            self.assertEqual(
                manifest["structure_validation"], "pg_restore_list_passed"
            )
            commands = [" ".join(args) for args, _input in calls]
            self.assertLess(
                next(i for i, value in enumerate(commands) if "pg_dump" in value),
                next(
                    i
                    for i, value in enumerate(commands)
                    if "pg_restore" in value
                ),
            )
            serialized = json.dumps(manifest)
            for forbidden in (
                "password",
                "token",
                "cookie",
                "authorization",
                "secrets.env",
            ):
                self.assertNotIn(forbidden, serialized.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
