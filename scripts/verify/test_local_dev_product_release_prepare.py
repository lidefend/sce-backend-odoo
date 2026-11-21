from __future__ import annotations

import importlib.util
import re
import sys
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts/dev/local_dev_product_release_prepare.py"
SPEC = importlib.util.spec_from_file_location(
    "local_dev_product_release_prepare",
    SCRIPT_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class LocalDevProductReleasePrepareTest(unittest.TestCase):
    def test_identity_is_exact_and_fail_closed(self):
        revision = "a" * 40
        self.assertEqual(
            MODULE.validate_identity(
                database="sc_dev_demo",
                environment="dev",
                source_revision=revision,
            )["source_revision"],
            revision,
        )
        for values, message in (
            (
                {
                    "database": "sc_demo",
                    "environment": "dev",
                    "source_revision": revision,
                },
                "DATABASE_DENIED",
            ),
            (
                {
                    "database": "sc_dev_demo",
                    "environment": "acceptance",
                    "source_revision": revision,
                },
                "ENVIRONMENT_DENIED",
            ),
            (
                {
                    "database": "sc_dev_demo",
                    "environment": "dev",
                    "source_revision": "abc123",
                },
                "SOURCE_REVISION_REQUIRED",
            ),
        ):
            with self.subTest(values=values), self.assertRaisesRegex(
                RuntimeError, message
            ):
                MODULE.validate_identity(**values)

    def test_release_version_uses_exact_source_prefix(self):
        revision = "fab3415370b513e1fbb453d317e8b316171785f5"
        self.assertEqual(MODULE.release_version(revision), "local-dev-fab3415370b5")
        with self.assertRaisesRegex(RuntimeError, "SOURCE_REVISION_REQUIRED"):
            MODULE.release_version("fab3415")

    def test_runtime_release_uses_the_same_policy_and_commits_only_after_integrity(self):
        revision = "a" * 40
        policy = {
            "product_key": "construction.standard",
            "business_scene_composition": {"scenarios": []},
        }

        class Cursor:
            dbname = "sc_dev_demo"

            def __init__(self):
                self.commits = 0

            def commit(self):
                self.commits += 1

        class Snapshot:
            id = 17
            version = MODULE.release_version(revision)
            state = "released"
            is_active = True
            active = True

            def exists(self):
                return True

        class SnapshotModel:
            def sudo(self):
                return self

            def browse(self, record_id):
                self.record_id = record_id
                return Snapshot()

        class Service:
            def __init__(self, env):
                self.env = env
                self.policy = None

            def freeze_release_surface(self, **kwargs):
                self.policy = kwargs["policy_override"]
                return {"id": 17}

            def assert_frozen_release_integrity(self, snapshot):
                if self.env.cr.commits:
                    raise AssertionError("integrity must be checked before commit")
                return {"effective_count": 132, "released_count": 120}

        cursor = Cursor()
        env = type(
            "Env",
            (dict,),
            {"cr": cursor},
        )({"sc.edition.release.snapshot": SnapshotModel()})
        service_module = types.ModuleType(
            "odoo.addons.smart_core.delivery.edition_release_snapshot_service"
        )
        service_module.EditionReleaseSnapshotService = lambda current_env: Service(current_env)
        with mock.patch.dict(
            sys.modules,
            {service_module.__name__: service_module},
        ):
            result = MODULE.activate_runtime_release(
                env,
                source_policy=policy,
                source_revision=revision,
            )
        self.assertEqual(cursor.commits, 1)
        self.assertEqual(result["snapshot_id"], 17)
        self.assertEqual(result["effective_page_count"], 132)
        self.assertEqual(result["policy_source_sha256"], MODULE._stable_sha256(policy))

    def test_catalog_source_and_platform_release_database_are_separate(self):
        self.assertEqual(
            MODULE.validate_release_databases(
                catalog_source_db="sc_dev_demo",
                platform_release_db="sc_platform_control",
            ),
            {
                "catalog_source_db": "sc_dev_demo",
                "platform_release_db": "sc_platform_control",
            },
        )
        for catalog_source_db, platform_release_db, message in (
            (
                "sc_demo",
                "sc_platform_control",
                "CATALOG_SOURCE_DENIED",
            ),
            (
                "sc_dev_demo",
                "sc_dev_demo",
                "PLATFORM_DATABASE_DENIED",
            ),
        ):
            with self.subTest(
                catalog_source_db=catalog_source_db,
                platform_release_db=platform_release_db,
            ), self.assertRaisesRegex(RuntimeError, message):
                MODULE.validate_release_databases(
                    catalog_source_db=catalog_source_db,
                    platform_release_db=platform_release_db,
                )

    def test_make_entry_acquires_write_lease_and_binds_exact_database(self):
        makefile = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        wrapper = makefile.split(
            "local.dev.product_release.prepare:", 1
        )[1].split("\n\n", 1)[0]
        runner = makefile.split(
            "local.dev.product_release.prepare.run:", 1
        )[1].split("\n\n", 1)[0]
        shell = makefile.split(
            "local.dev.product_release.prepare.shell:", 1
        )[1].split("\n\n", 1)[0]
        self.assertIn("local_dev_write_lease.sh", wrapper)
        self.assertIn("CONFIRM_LOCAL_DEV_PRODUCT_RELEASE", wrapper)
        self.assertIn("local.dev.write_lease.require", runner)
        self.assertIn("PRODUCT_RELEASE_SOURCE_REVISION", runner)
        self.assertIn("DB_NAME=sc_dev_demo", runner)
        self.assertIn("SC_ENVIRONMENT=dev", runner)
        self.assertIn("PRODUCT_RELEASE_SOURCE_REVISION", shell)
        self.assertIn("DB_NAME=sc_dev_demo", shell)
        self.assertIn("SC_ENVIRONMENT=dev", shell)
        self.assertIn(
            "scripts/dev/local_dev_product_release_prepare.py",
            shell,
        )
        self.assertNotRegex(runner + shell, re.compile(r"DB_NAME=sc_demo(?!\w)"))


if __name__ == "__main__":
    unittest.main()
