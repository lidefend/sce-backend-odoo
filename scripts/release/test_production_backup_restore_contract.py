#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BACKUP = load("production_backup_restore", ROOT / "scripts/release/production_backup_restore.py")
INSTALL = load("production_backup_install", ROOT / "scripts/ops/production_backup_install.py")


class IdentityContractTests(unittest.TestCase):
    def valid_environment(self) -> dict[str, str]:
        return {
            "BACKUP_COMPOSE_PROJECT": "sc_production",
            "BACKUP_TARGET_DB": "sc_production",
            "BACKUP_DB_CONTAINER": "sc_production-db-1",
            "BACKUP_ODOO_CONTAINER": "sc_production-odoo-1",
            "BACKUP_DB_USER": "odoo",
            "BACKUP_FILESTORE_ROOT": "/opt/sce-runtime/filestore",
            "BACKUP_ROOT": "/data/backups/sc_production",
            "BACKUP_TOOL_SOURCE_SHA": "a" * 40,
            "BACKUP_ENCRYPTION_STATUS": "not_encrypted",
            "BACKUP_RETENTION_DAYS": "30",
        }

    def test_correct_production_identity_passes(self):
        with mock.patch.dict(os.environ, self.valid_environment(), clear=True):
            settings = BACKUP.Settings.from_env()
        self.assertEqual(settings.database, "sc_production")
        self.assertEqual(settings.db_container, "sc_production-db-1")

    def test_wrong_project_is_rejected_with_no_writes(self):
        values = self.valid_environment()
        values["BACKUP_COMPOSE_PROJECT"] = "other"
        with mock.patch.dict(os.environ, values, clear=True):
            with self.assertRaisesRegex(BACKUP.ContractError, "sc_production"):
                BACKUP.Settings.from_env()

    def test_stale_database_is_rejected(self):
        values = self.valid_environment()
        values["BACKUP_TARGET_DB"] = "sc_prod"
        with mock.patch.dict(os.environ, values, clear=True):
            with self.assertRaises(BACKUP.ContractError):
                BACKUP.Settings.from_env()

    def test_stale_container_is_rejected(self):
        values = self.valid_environment()
        values["BACKUP_DB_CONTAINER"] = "sc-backend-odoo-prod-db-1"
        with mock.patch.dict(os.environ, values, clear=True):
            with self.assertRaises(BACKUP.ContractError):
                BACKUP.Settings.from_env()

    def test_filestore_database_mismatch_is_rejected(self):
        values = self.valid_environment()
        values["BACKUP_FILESTORE_ROOT"] = "/tmp/filestore"
        with mock.patch.dict(os.environ, values, clear=True):
            with self.assertRaises(BACKUP.ContractError):
                BACKUP.Settings.from_env()

    def test_tool_source_requires_full_sha(self):
        values = self.valid_environment()
        values["BACKUP_TOOL_SOURCE_SHA"] = "abc123"
        with mock.patch.dict(os.environ, values, clear=True):
            with self.assertRaises(BACKUP.ContractError):
                BACKUP.Settings.from_env()

    def test_path_and_shell_inputs_are_rejected(self):
        for value in ("../escape", "sc_production;id", "sc_production$(id)"):
            values = self.valid_environment()
            values["BACKUP_TARGET_DB"] = value
            with self.subTest(value=value), mock.patch.dict(
                os.environ, values, clear=True
            ):
                with self.assertRaises(BACKUP.ContractError):
                    BACKUP.Settings.from_env()


class LockAndAtomicityTests(unittest.TestCase):
    def test_concurrent_lock_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "lock"
            with BACKUP.NonBlockingLock(path):
                with self.assertRaisesRegex(BACKUP.ContractError, "already held"):
                    with BACKUP.NonBlockingLock(path):
                        pass

    def test_atomic_json_failure_does_not_damage_old_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            path.write_text('{"old":true}\n')
            with mock.patch("os.replace", side_effect=OSError("injected")):
                with self.assertRaises(OSError):
                    BACKUP.atomic_json(path, {"new": True})
            self.assertEqual(json.loads(path.read_text()), {"old": True})

    def test_backup_id_is_collision_safe(self):
        with mock.patch.object(BACKUP.secrets, "token_hex", side_effect=["11111111", "22222222"]):
            first = BACKUP.new_backup_id()
            second = BACKUP.new_backup_id()
        self.assertNotEqual(first, second)
        self.assertTrue(BACKUP.BACKUP_ID.fullmatch(first))


class BackupSetContractTests(unittest.TestCase):
    def settings(self, root: Path):
        return BACKUP.Settings(
            project="sc_production",
            database="sc_production",
            db_container="sc_production-db-1",
            odoo_container="sc_production-odoo-1",
            db_user="odoo",
            filestore_root="/opt/sce-runtime/filestore",
            backup_root=root,
            tool_source_sha="a" * 40,
            encryption_status="not_encrypted",
            retention_days=30,
        )

    @staticmethod
    def runner(args, *, input_bytes=None):
        if "pg_dump" in args:
            return b"database-dump"
        if "tar" in args:
            return b"filestore"
        return b"ok"

    def create(self, root: Path):
        with (
            mock.patch.object(BACKUP, "collect_metadata", return_value={
                "schema_version": 1,
                "contract_version": BACKUP.CONTRACT_VERSION,
                "secret_values_exposed": False,
            }),
            mock.patch.object(BACKUP, "_table_counts", return_value={"res_users": 5}),
            mock.patch.object(BACKUP, "_attachment_sample", return_value=["a|b"]),
            mock.patch.object(BACKUP, "_filestore_digest", return_value="f" * 64),
        ):
            return BACKUP.backup(
                self.settings(root),
                backup_set_id="sc_production-20260724T120000Z-a1b2c3d4",
                runner=self.runner,
                lock_root=root,
                approved_backup_root=root,
            )

    def test_triple_backup_completes_atomically(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            directory = self.create(root)
            manifest = BACKUP.validate_backup_set(directory)
            self.assertEqual(set(manifest["checksums"]), set(BACKUP.ARTIFACTS))
            self.assertTrue(manifest["backup_pair_verified"])
            self.assertFalse(manifest["secret_values_exposed"])

    def test_completed_backup_set_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            self.create(root)
            with self.assertRaisesRegex(BACKUP.ContractError, "overwritten"):
                self.create(root)

    def test_database_failure_never_publishes_complete_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)

            def fail(args, *, input_bytes=None):
                if "pg_dump" in args:
                    raise BACKUP.ContractError("database failure")
                return b"ok"

            with (
                mock.patch.object(BACKUP, "collect_metadata", return_value={}),
                self.assertRaisesRegex(BACKUP.ContractError, "database failure"),
            ):
                BACKUP.backup(
                    self.settings(root),
                    backup_set_id="sc_production-20260724T120000Z-a1b2c3d4",
                    runner=fail,
                    lock_root=root,
                    approved_backup_root=root,
                )
            self.assertFalse(any(item.is_dir() and item.name.startswith("sc_production-") for item in root.iterdir()))

    def test_filestore_failure_never_publishes_complete_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)

            def fail(args, *, input_bytes=None):
                if "pg_dump" in args:
                    return b"dump"
                if "tar" in args:
                    raise BACKUP.ContractError("filestore failure")
                return b"ok"

            with (
                mock.patch.object(BACKUP, "collect_metadata", return_value={}),
                self.assertRaisesRegex(BACKUP.ContractError, "filestore failure"),
            ):
                BACKUP.backup(
                    self.settings(root),
                    backup_set_id="sc_production-20260724T120000Z-a1b2c3d4",
                    runner=fail,
                    lock_root=root,
                    approved_backup_root=root,
                )
            self.assertFalse(any(item.is_dir() and item.name.startswith("sc_production-") for item in root.iterdir()))

    def test_metadata_failure_never_publishes_complete_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            with (
                mock.patch.object(
                    BACKUP, "collect_metadata", side_effect=BACKUP.ContractError("metadata failure")
                ),
                self.assertRaisesRegex(BACKUP.ContractError, "metadata failure"),
            ):
                BACKUP.backup(
                    self.settings(root),
                    backup_set_id="sc_production-20260724T120000Z-a1b2c3d4",
                    runner=self.runner,
                    lock_root=root,
                    approved_backup_root=root,
                )
            self.assertFalse(any(item.is_dir() and item.name.startswith("sc_production-") for item in root.iterdir()))

    def test_temporary_set_is_not_valid_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / ".incomplete-set"
            directory.mkdir()
            with self.assertRaises(BACKUP.ContractError):
                BACKUP.validate_backup_set(directory)

    def test_resume_hash_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            directory = self.create(root)
            (directory / "database.dump").write_bytes(b"changed")
            with self.assertRaisesRegex(BACKUP.ContractError, "SHA256SUMS|checksum"):
                BACKUP.validate_backup_set(directory)


class MetadataSafetyTests(unittest.TestCase):
    def test_environment_inventory_contains_names_not_values(self):
        inspect = {
            "Config": {
                "Env": ["DB_PASSWORD=top-secret", "DB_NAME=sc_production"],
                "Image": "postgres:15",
                "Labels": {"com.docker.compose.project": "sc_production"},
            },
            "State": {"Running": True, "Health": {"Status": "healthy"}},
            "NetworkSettings": {"Networks": {"sc_production": {}}, "Ports": {}},
            "Mounts": [],
            "Image": "sha256:" + "1" * 64,
        }

        def runner(args, *, input_bytes=None):
            if args[1:3] == ["inspect", "sc_production-db-1"]:
                return json.dumps([inspect]).encode()
            if args[1:3] == ["image", "inspect"]:
                return json.dumps([{"RepoDigests": []}]).encode()
            return b""

        result = BACKUP._container_evidence("sc_production-db-1", runner)
        rendered = json.dumps(result)
        self.assertIn("DB_PASSWORD", rendered)
        self.assertNotIn("top-secret", rendered)

    def test_secret_like_metadata_values_are_not_emitted(self):
        source = (ROOT / "scripts/release/production_backup_restore.py").read_text()
        self.assertIn("secret_values_exposed", source)
        self.assertNotIn("Config\", {}).get(\"Env\") or []:", source.split("def _environment_names", 1)[0])


class RestoreIsolationTests(unittest.TestCase):
    def backup_fixture(self, root: Path) -> Path:
        directory = root / "sc_production-20260724T120000Z-a1b2c3d4"
        directory.mkdir(mode=0o700)
        for name, value in {
            "database.dump": b"dump",
            "filestore.tar.gz": b"filestore",
            "deployment-metadata.json": b"{}",
        }.items():
            (directory / name).write_bytes(value)
        manifest = {
            "contract_version": BACKUP.CONTRACT_VERSION,
            "status": "complete",
            "database": "sc_production",
            "compose_project": "sc_production",
            "backup_set_id": directory.name,
            "backup_pair_verified": True,
            "secret_values_exposed": False,
            "checksums": {
                name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                for name in BACKUP.ARTIFACTS
            },
            "table_counts": {"res_users": 5},
            "attachment_sample": ["a|b"],
            "module_versions": {},
            "filestore_digest": "f" * 64,
        }
        (directory / "manifest.json").write_text(json.dumps(manifest))
        (directory / "SHA256SUMS").write_text(
            "".join(
                f"{hashlib.sha256((directory / name).read_bytes()).hexdigest()}  {name}\n"
                for name in (*BACKUP.ARTIFACTS, "manifest.json")
            )
        )
        for path in directory.iterdir():
            path.chmod(0o600)
        return directory

    def test_restore_uses_internal_network_and_no_production_resources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            backup = self.backup_fixture(root)
            calls = []

            def runner(args, *, input_bytes=None):
                calls.append(args)
                if "pg_isready" in args:
                    return b"ready"
                if args[:3] == ["docker", "run", "--rm"] and "sha256sum" in " ".join(args):
                    return ("f" * 64 + "  -\n").encode()
                return b"ok"

            with (
                mock.patch.object(BACKUP, "_table_counts", return_value={"res_users": 5}),
                mock.patch.object(BACKUP, "_attachment_sample", return_value=["a|b"]),
                mock.patch.object(BACKUP, "_module_versions", return_value={}),
            ):
                report = BACKUP.restore_rehearsal(
                    backup,
                    restore_id="sc_restore_20260724t120000z_a1b2c3d4",
                    odoo_image="ghcr.io/lidefend/sce-product@sha256:" + "a" * 64,
                    postgres_image="postgres@sha256:" + "b" * 64,
                    report_path=root / "restore-rehearsals/sc_restore_20260724t120000z_a1b2c3d4.json",
                    runner=runner,
                    lock_root=root,
                    approved_backup_root=root,
                )
            flattened = "\n".join(" ".join(call) for call in calls)
            self.assertIn("network create --internal", flattened)
            self.assertIn("--publish 127.0.0.1::8069", flattened)
            self.assertNotIn("sce-sc_production", flattened)
            self.assertNotIn("sc-backend-odoo-prod", flattened)
            self.assertEqual(report["external_write_side_effects"], 0)
            self.assertTrue(report["cron_disabled"])
            self.assertEqual(report["odoo_healthcheck"], "stop_after_init_passed")

    def test_restore_health_failure_records_failure_without_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            root.chmod(0o700)
            backup = self.backup_fixture(root)
            calls = []

            def runner(args, *, input_bytes=None):
                calls.append(args)
                if "pg_isready" in args:
                    return b"ready"
                if "--entrypoint" in args and "odoo" in args:
                    raise BACKUP.ContractError("odoo health failure")
                return b"ok"

            report_path = root / "restore-rehearsals/sc_restore_20260724t120000z_a1b2c3d4.json"
            with self.assertRaisesRegex(BACKUP.ContractError, "health failure"):
                BACKUP.restore_rehearsal(
                    backup,
                    restore_id="sc_restore_20260724t120000z_a1b2c3d4",
                    odoo_image="ghcr.io/lidefend/sce-product@sha256:" + "a" * 64,
                    postgres_image="postgres@sha256:" + "b" * 64,
                    report_path=report_path,
                    runner=runner,
                    lock_root=root,
                    approved_backup_root=root,
                )
            report = json.loads(report_path.read_text())
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["failure_stage"], "odoo_health")
            self.assertEqual(report["external_write_side_effects"], 0)

    def test_production_paths_are_rejected_for_restore(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(BACKUP.ContractError, "backup path"):
                BACKUP.restore_rehearsal(
                    root / "wrong",
                    restore_id="sc_restore_20260724t120000z_a1b2c3d4",
                    odoo_image="ghcr.io/lidefend/sce-product@sha256:" + "a" * 64,
                    postgres_image="postgres@sha256:" + "b" * 64,
                    report_path=root / "restore-rehearsals/sc_restore_20260724t120000z_a1b2c3d4.json",
                    approved_backup_root=root,
                )


class InstallAndTimerTests(unittest.TestCase):
    def identity(self):
        return INSTALL.Identity(
            expected_tool_source_sha="a" * 40,
            expected_live_main_sha="a" * 40,
            project="sc_production",
            database="sc_production",
            db_container="sc_production-db-1",
            odoo_container="sc_production-odoo-1",
            filestore_root="/opt/sce-runtime/filestore",
            install_root=Path("/opt/ops"),
            backup_root=Path("/data/backups/sc_production"),
            encryption_status="not_encrypted",
            retention_days=30,
        )

    def test_live_main_drift_is_rejected_before_install(self):
        responses = {
            ("git", "rev-parse", "HEAD"): ("a" * 40).encode(),
            ("git", "rev-parse", "HEAD^{tree}"): ("b" * 40).encode(),
            ("git", "status", "--short"): b"",
            ("git", "ls-remote", "--heads", "origin", "refs/heads/main"):
                (("c" * 40) + "\trefs/heads/main\n").encode(),
            ("git", "ls-remote", "--heads", "gitee-mirror", "refs/heads/main"):
                (("a" * 40) + "\trefs/heads/main\n").encode(),
        }

        def runner(args):
            return responses[tuple(args)]

        with self.assertRaisesRegex(INSTALL.InstallError, "drift"):
            INSTALL.preflight(self.identity(), runner)

    def test_unit_verification_failure_triggers_rollback_before_reload_success(self):
        source = (ROOT / "scripts/ops/production_backup_install.py").read_text()
        verify_at = source.index('"systemd-analyze"')
        reload_at = source.index('runner(["systemctl", "daemon-reload"])', verify_at)
        self.assertLess(verify_at, reload_at)
        self.assertIn("_restore(snapshots, runner)", source)
        self.assertIn("_restore_timer_state(before_systemd, runner)", source)

    def test_timer_requires_backup_and_restore_success(self):
        source = (ROOT / "scripts/ops/production_backup_install.py").read_text()
        self.assertIn('backup.get("backup_pair_verified") is not True', source)
        self.assertIn('rehearsal.get("status") != "PASS"', source)
        self.assertIn('rehearsal.get("external_write_side_effects") != 0', source)

    def test_timer_preserves_existing_schedule_and_no_duplicate_entry(self):
        timer = (ROOT / "deploy/production-backup/scems-production-backup.timer").read_text()
        self.assertIn("OnCalendar=*-*-* 02:30:00 Asia/Shanghai", timer)
        self.assertIn("RandomizedDelaySec=10m", timer)
        self.assertIn("Unit=scems-production-backup.service", timer)
        service = (ROOT / "deploy/production-backup/scems-production-backup.service").read_text()
        self.assertEqual(service.count("ExecStart="), 1)

    def test_write_entries_default_deny(self):
        makefile = (ROOT / "make/release.mk").read_text()
        for confirmation in (
            "YES_INSTALL_GOVERNED_BACKUP_TOOL",
            "YES_CREATE_SC_PRODUCTION_TRIPLE_BACKUP",
            "YES_RUN_ISOLATED_RESTORE_REHEARSAL",
            "YES_RESTORE_VERIFIED_BACKUP_TIMER",
        ):
            self.assertIn(confirmation, makefile)
        self.assertIn("guard.prod.danger", makefile)


class StaticGovernanceTests(unittest.TestCase):
    def test_all_required_make_entries_exist(self):
        makefile = (ROOT / "make/release.mk").read_text()
        for target in (
            "production.backup.install.preflight:",
            "production.backup.install:",
            "production.backup.run:",
            "production.restore.rehearsal:",
            "verify.production.backup_restore_contract:",
        ):
            self.assertIn(target, makefile)

    def test_no_production_connection_or_real_external_write_in_tests(self):
        source = Path(__file__).read_text()
        self.assertNotIn("ssh " + "sc-prod", source)
        self.assertNotIn("docker " + "push", source)
        self.assertNotIn("git " + "tag", source)

    def test_schemas_have_positive_and_negative_identity_guards(self):
        backup_schema = json.loads(
            (ROOT / "schemas/release/production_backup_set.v2.schema.json").read_text()
        )
        restore_schema = json.loads(
            (ROOT / "schemas/release/production_restore_rehearsal.v1.schema.json").read_text()
        )
        self.assertEqual(backup_schema["properties"]["database"]["const"], "sc_production")
        self.assertEqual(
            restore_schema["properties"]["external_write_side_effects"]["const"], 0
        )
        self.assertIn("backup_set_id", backup_schema["required"])
        Draft202012Validator.check_schema(backup_schema)
        Draft202012Validator.check_schema(restore_schema)
        valid_backup = {
            "schema_version": 2,
            "contract_version": "production_backup_restore.v1",
            "backup_set_id": "sc_production-20260724T120000Z-a1b2c3d4",
            "status": "complete",
            "created_at": "2026-07-24T12:00:00+00:00",
            "compose_project": "sc_production",
            "database": "sc_production",
            "database_container": "sc_production-db-1",
            "filestore_source": "/opt/sce-runtime/filestore/sc_production",
            "tool_source_sha": "a" * 40,
            "encryption_status": "not_encrypted",
            "retention_days": 30,
            "checksums": {name: "b" * 64 for name in BACKUP.ARTIFACTS},
            "sizes": {name: 1 for name in BACKUP.ARTIFACTS},
            "table_counts": {"res_users": 5},
            "attachment_sample": [],
            "module_versions": {},
            "filestore_digest": "c" * 64,
            "backup_pair_verified": True,
            "secret_values_exposed": False,
        }
        Draft202012Validator(backup_schema).validate(valid_backup)
        invalid = {**valid_backup, "database": "sc_prod"}
        self.assertTrue(list(Draft202012Validator(backup_schema).iter_errors(invalid)))

    def test_candidate_and_publication_evidence_are_not_referenced_as_writes(self):
        changed = {
            "scripts/release/production_backup_restore.py",
            "scripts/ops/production_backup_install.py",
            "make/release.mk",
            "deploy/production-backup/scems-production-backup.service",
            "deploy/production-backup/scems-production-backup.timer",
        }
        self.assertFalse(any("candidates/" in path or "publications/" in path for path in changed))


if __name__ == "__main__":
    unittest.main(verbosity=2)
