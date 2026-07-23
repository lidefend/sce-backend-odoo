#!/usr/bin/env python3
from __future__ import annotations

import atexit
import hashlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "production_db_init", ROOT / "scripts/release/production_db_init.py"
)
assert SPEC and SPEC.loader
db_init = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(db_init)

RELEASE_IDENTITY_TMP = tempfile.TemporaryDirectory()
atexit.register(RELEASE_IDENTITY_TMP.cleanup)
RELEASE_IDENTITY_ROOT = Path(RELEASE_IDENTITY_TMP.name)


def environment(database: str = "sc_migration_rehearsal") -> dict[str, str]:
    source_sha = "a" * 40
    image_digest = "sha256:" + "b" * 64
    manifest = RELEASE_IDENTITY_ROOT / f"{database}-product-release-manifest.json"
    checksum = RELEASE_IDENTITY_ROOT / f"{database}-product-release-manifest.sha256"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "product_release_manifest.v3",
                "repository": "lidefend/sce-backend-odoo",
                "branch": "main",
                "source_sha": source_sha,
                "oci_revision": source_sha,
                "container_source_revision": source_sha,
                "image_digest": image_digest,
                "registry_repository": "ghcr.io/lidefend/sce-product",
                "registry_refs": [f"ghcr.io/lidefend/sce-product@{image_digest}"] * 2,
                "local_image_id": "sha256:" + "1" * 64,
                "archive_config_digest": "sha256:" + "2" * 64,
                "archive_reload_image_id": "sha256:" + "3" * 64,
                "archive_sha256": "c" * 64,
                "baseline_checksum": "d" * 64,
                "scan": {
                    "status": "completed",
                    "source_sha": source_sha,
                    "image_digest": image_digest,
                    "counts": {
                        "CRITICAL": 0,
                        "HIGH": 0,
                        "MEDIUM": 0,
                        "LOW": 0,
                        "SECRET": 0
                    },
                    "policy": {"result": "pass"}
                }
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    checksum.write_text(
        f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  {manifest.name}\n",
        encoding="utf-8",
    )
    env = {
        "TARGET_DB": database,
        "SC_ENVIRONMENT": "migration_rehearsal" if database == "sc_migration_rehearsal" else "production",
        "SC_FILESTORE_SCOPE": database,
        "SC_ALLOW_DEMO_DATA": "0",
        "SC_SOURCE_REVISION": source_sha,
        "EXPECTED_RELEASE_SHA": source_sha,
        "EXPECTED_IMAGE_DIGEST": image_digest,
        "RELEASE_MANIFEST_PATH": str(manifest),
        "RELEASE_MANIFEST_CHECKSUM_PATH": str(checksum),
        "PLATFORM_RELEASE_DB": database,
    }
    for key, suffix in {
        "SC_DATABASE_VOLUME": "postgres", "SC_REDIS_VOLUME": "redis",
        "SC_FILESTORE_VOLUME": "filestore", "SC_SESSION_VOLUME": "sessions",
        "SC_TMP_VOLUME": "tmp", "SC_LOG_VOLUME": "logs",
    }.items():
        env[key] = f"sce-{database}-{suffix}"
    return env


class FakeAdmin:
    def __init__(self, exists: bool = False, create_failure: bool = False, cleanup_failure: bool = False):
        self.present = exists
        self.create_failure = create_failure
        self.cleanup_failure = cleanup_failure
        self.create_calls = 0
        self.cleanup_calls = 0

    def exists(self, database: str) -> bool:
        return self.present

    def create(self, database: str) -> None:
        self.create_calls += 1
        if self.create_failure:
            raise RuntimeError("injected create failure")
        self.present = True

    def cleanup_created(self, database: str) -> None:
        self.cleanup_calls += 1
        if self.cleanup_failure:
            raise RuntimeError("injected cleanup failure")
        self.present = False


def result(status: int):
    return lambda *args, **kwargs: subprocess.CompletedProcess(args[0], status)


class InitializationCompensationTests(unittest.TestCase):
    def test_preexisting_database_is_preserved(self):
        admin = FakeAdmin(exists=True)
        with self.assertRaises(db_init.InitializationError):
            db_init.initialize("/tmp/odoo.conf", environment(), admin, result(0))
        self.assertTrue(admin.present)
        self.assertEqual(admin.create_calls, 0)
        self.assertEqual(admin.cleanup_calls, 0)

    def test_create_failure_never_attempts_cleanup(self):
        admin = FakeAdmin(create_failure=True)
        with self.assertRaises(db_init.InitializationError):
            db_init.initialize("/tmp/odoo.conf", environment(), admin, result(0))
        self.assertEqual(admin.cleanup_calls, 0)

    def test_failed_base_initialization_cleans_owned_database(self):
        admin = FakeAdmin()
        self.assertEqual(db_init.initialize("/tmp/odoo.conf", environment(), admin, result(42)), 42)
        self.assertFalse(admin.present)
        self.assertEqual(admin.cleanup_calls, 1)

    def test_cleanup_allows_safe_retry(self):
        admin = FakeAdmin()
        self.assertEqual(db_init.initialize("/tmp/odoo.conf", environment(), admin, result(42)), 42)
        self.assertEqual(db_init.initialize("/tmp/odoo.conf", environment(), admin, result(0)), 0)
        self.assertTrue(admin.present)
        self.assertEqual(admin.create_calls, 2)

    def test_cleanup_failure_is_fail_closed_and_explicit(self):
        admin = FakeAdmin(cleanup_failure=True)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            status = db_init.initialize("/tmp/odoo.conf", environment(), admin, result(42))
        self.assertEqual(status, db_init.ORPHAN_DATABASE_EXIT)
        self.assertTrue(admin.present)
        self.assertIn("orphan database may exist", stderr.getvalue())

    def test_reserved_databases_never_reach_create_or_cleanup(self):
        for database in ("sc_prod", "postgres", "template0", "template1"):
            with self.subTest(database=database):
                admin = FakeAdmin()
                with self.assertRaises(db_init.ContractError):
                    db_init.initialize("/tmp/odoo.conf", environment(database), admin, result(42))
                self.assertEqual(admin.create_calls, 0)
                self.assertEqual(admin.cleanup_calls, 0)

    def test_production_without_confirmation_never_creates_or_cleans(self):
        admin = FakeAdmin()
        with self.assertRaises(db_init.ContractError):
            db_init.initialize("/tmp/odoo.conf", environment("sc_production"), admin, result(42))
        self.assertEqual(admin.create_calls, 0)
        self.assertEqual(admin.cleanup_calls, 0)

    def test_production_confirmation_is_rechecked_before_cleanup(self):
        env = environment("sc_production")
        env["SC_PRODUCTION_CHANGE_APPROVED"] = "I_ACKNOWLEDGE_SC_PRODUCTION_CHANGE"
        admin = FakeAdmin()

        def revoke_confirmation(*args, **kwargs):
            kwargs["env"].pop("SC_PRODUCTION_CHANGE_APPROVED")
            return subprocess.CompletedProcess(args[0], 42)

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            status = db_init.initialize("/tmp/odoo.conf", env, admin, revoke_confirmation)
        self.assertEqual(status, db_init.ORPHAN_DATABASE_EXIT)
        self.assertEqual(admin.cleanup_calls, 0)
        self.assertIn("orphan database may exist", stderr.getvalue())

    def test_confirmed_production_failure_cleans_only_owned_database(self):
        env = environment("sc_production")
        env["SC_PRODUCTION_CHANGE_APPROVED"] = "I_ACKNOWLEDGE_SC_PRODUCTION_CHANGE"
        admin = FakeAdmin()
        self.assertEqual(db_init.initialize("/tmp/odoo.conf", env, admin, result(42)), 42)
        self.assertFalse(admin.present)
        self.assertEqual(admin.cleanup_calls, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
