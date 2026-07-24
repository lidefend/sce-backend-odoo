#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "daily_candidate_data_continuity",
    ROOT / "scripts/ops/daily_candidate_data_continuity.py",
)
assert SPEC and SPEC.loader
CONTINUITY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTINUITY)
CONTRACT_PATH = (
    ROOT / "scripts/ops/daily_candidate_data_continuity_contract_v1.json"
)


class ContractTests(unittest.TestCase):
    def test_fixed_daily_candidate_identity_loads(self):
        contract = CONTINUITY._load_contract(CONTRACT_PATH)
        self.assertEqual(contract["environment_class"], "DAILY_CANDIDATE_ENVIRONMENT")
        self.assertEqual(contract["database"], "sc_demo")
        self.assertEqual(contract["database_volume"], "sc_dev_db_data")
        self.assertEqual(
            contract["source_repository"], "/opt/projects/repos/sce-backend-odoo"
        )
        self.assertFalse(contract["upgrade_contract"]["fixture_write_allowed"])
        self.assertFalse(contract["upgrade_contract"]["demo_data_write_allowed"])

    def test_changed_database_identity_is_rejected(self):
        contract = json.loads(CONTRACT_PATH.read_text())
        contract["database"] = "sc_production"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "contract.json"
            path.write_text(json.dumps(contract))
            with self.assertRaisesRegex(CONTINUITY.ContinuityError, "database"):
                CONTINUITY._load_contract(path)

    def test_tool_contains_no_candidate_reset_or_volume_down_path(self):
        source = (ROOT / "scripts/ops/daily_candidate_data_continuity.py").read_text()
        self.assertNotIn("docker compose down", source)
        self.assertNotIn("dropdb", source)
        self.assertNotIn("smart_construction_demo", source)
        self.assertNotIn("module uninstall", source)

    def test_destructive_make_targets_require_daily_candidate_guard(self):
        runtime_make = (ROOT / "make/runtime_ops.mk").read_text()
        for target in ("db.reset:", "demo.reset:", "db.demo.reset:", "db.reset.manual:"):
            body = runtime_make.split(target, 1)[1].splitlines()[0]
            if target in {"db.demo.reset:", "db.reset.manual:"} and ":=" in body:
                body = runtime_make.split(target, 2)[2].splitlines()[0]
            self.assertIn("guard.daily_candidate.preserve", body, target)
        guards = (ROOT / "make/guards.mk").read_text()
        self.assertIn('COMPOSE_PROJECT_NAME)" = "sc-backend-odoo-dev"', guards)
        self.assertIn('DAILY_CANDIDATE_TARGET_DB)" = "sc_demo"', guards)


class BackupContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = CONTINUITY._load_contract(CONTRACT_PATH)

    def test_backup_requires_exact_confirmation_before_runtime_access(self):
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(CONTINUITY, "_assert_runtime") as runtime,
        ):
            with self.assertRaisesRegex(CONTINUITY.ContinuityError, "confirmation"):
                CONTINUITY.backup(self.contract)
        runtime.assert_not_called()

    def test_backup_root_is_fixed(self):
        changed = dict(self.contract)
        changed["backup_root"] = "/tmp/daily_candidate"
        with self.assertRaisesRegex(CONTINUITY.ContinuityError, "identity"):
            CONTINUITY._safe_backup_root(changed)

    def _valid_backup(self, root: Path) -> Path:
        directory = root / "sc_demo-20260724T000000Z-deadbeef"
        directory.mkdir(mode=0o700)
        for name, content in (
            ("database.dump", b"dump"),
            ("filestore.tar.gz", b"archive"),
        ):
            path = directory / name
            path.write_bytes(content)
            path.chmod(0o600)
        manifest = {
            "schema_version": self.contract["schema_version"],
            "database": "sc_demo",
            "environment_class": "DAILY_CANDIDATE_ENVIRONMENT",
            "backup_status": "complete",
            "pair_stable_during_capture": True,
            "backup_set_id": directory.name,
            "checksums": {
                "database.dump": CONTINUITY._sha(directory / "database.dump"),
                "filestore.tar.gz": CONTINUITY._sha(directory / "filestore.tar.gz"),
            },
        }
        CONTINUITY._write_json(directory / "manifest.json", manifest)
        CONTINUITY._write_checksums(directory)
        return directory

    def test_complete_paired_backup_validates(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = self._valid_backup(Path(temporary))
            result = CONTINUITY.validate_backup(
                self.contract, directory, strict_permissions=True
            )
            self.assertEqual(result["database"], "sc_demo")

    def test_tampered_filestore_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = self._valid_backup(Path(temporary))
            (directory / "filestore.tar.gz").write_bytes(b"changed")
            with self.assertRaisesRegex(CONTINUITY.ContinuityError, "filestore"):
                CONTINUITY.validate_backup(self.contract, directory)

    def test_permissive_artifact_mode_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = self._valid_backup(Path(temporary))
            (directory / "database.dump").chmod(0o644)
            with self.assertRaisesRegex(CONTINUITY.ContinuityError, "0600"):
                CONTINUITY.validate_backup(
                    self.contract, directory, strict_permissions=True
                )
            self.assertEqual(
                stat.S_IMODE((directory / "database.dump").stat().st_mode), 0o644
            )


class RestoreIsolationTests(unittest.TestCase):
    def test_restore_requires_confirmation_before_validation(self):
        contract = CONTINUITY._load_contract(CONTRACT_PATH)
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(CONTINUITY, "validate_backup") as validate,
        ):
            with self.assertRaisesRegex(CONTINUITY.ContinuityError, "confirmation"):
                CONTINUITY.restore_drill(contract, Path("/not-used"))
        validate.assert_not_called()

    def test_restore_resource_namespace_is_not_candidate_project(self):
        self.assertTrue(CONTINUITY.DRILL_PREFIX.startswith("sc-daily-continuity-drill-"))
        self.assertNotIn("sc-backend-odoo-dev", CONTINUITY.DRILL_PREFIX)

    def test_restore_count_ranges_allow_normal_capture_activity(self):
        restored = {
            "database_uuid": "uuid",
            "table_counts": {"project_project": 11},
            "stable_sample_ids": {"project_project": [1, 2, 3]},
            "payment_request_relation_sample_digest": "digest-before",
        }
        expected = {
            "database_uuid": "uuid",
            "table_count_ranges": {
                "project_project": {"minimum": 10, "maximum": 12}
            },
            "stable_sample_ids": {"project_project": [1, 2]},
            "stable_payment_request_relation_sample_digest": "digest-before",
        }
        CONTINUITY._assert_restored_sentinels(restored, expected)

    def test_closeout_refuses_missing_restore_evidence(self):
        contract = CONTINUITY._load_contract(CONTRACT_PATH)
        with mock.patch.object(
            CONTINUITY, "validate_backup", return_value={"backup_set_id": "unused"}
        ):
            with self.assertRaisesRegex(CONTINUITY.ContinuityError, "restore evidence"):
                CONTINUITY.closeout(contract, Path("/not-used"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
