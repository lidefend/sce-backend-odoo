from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path


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
