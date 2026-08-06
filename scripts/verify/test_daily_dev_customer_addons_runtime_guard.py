from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("daily_dev_customer_addons_runtime_guard.py")
SPEC = importlib.util.spec_from_file_location("daily_dev_customer_addons_runtime_guard", SCRIPT)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GUARD
SPEC.loader.exec_module(GUARD)


class FakeRunner:
    def __init__(
        self,
        root: Path,
        *,
        state: str = "installed",
        resolved: bool = True,
        mounted: bool = True,
        writable: bool = False,
        db_version: str = "17.0.1.1",
        runtime_version: str = "17.0.1.1",
        mount_source: Path | None = None,
        container_ids: str = "container-id",
    ):
        self.root = root
        self.state = state
        self.resolved = resolved
        self.mounted = mounted
        self.writable = writable
        self.db_version = db_version
        self.runtime_version = runtime_version
        self.mount_source = mount_source or root
        self.container_ids = container_ids

    def __call__(self, args: list[str], input_text: str | None = None) -> str:
        del input_text
        if args[-3:] == ["ps", "-q", "odoo"]:
            return self.container_ids
        if args[:2] == ["docker", "inspect"]:
            mounts = []
            if self.mounted:
                mounts.append(
                    {
                        "Source": str(self.mount_source),
                        "Destination": "/mnt/customer-addons",
                        "RW": self.writable,
                    }
                )
            return json.dumps(mounts)
        if "psql" in args:
            return json.dumps({"state": self.state, "latest_version": self.db_version})
        if "shell" in args:
            path = "/mnt/customer-addons/smart_construction_custom" if self.resolved else False
            return GUARD.RESOLUTION_MARKER + json.dumps({"path": path, "version": self.runtime_version})
        raise AssertionError(args)


class DailyCustomerAddonsRuntimeGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        module = self.root / "smart_construction_custom"
        module.mkdir()
        (module / "__manifest__.py").write_text("{'version': '17.0.1.1'}\n", encoding="utf-8")
        self.config = GUARD.Config(
            compose_bin="docker compose",
            compose_files="-f docker-compose.yml",
            compose_project="sc-backend-odoo-dev",
            db_name="sc_demo",
            db_user="odoo",
            odoo_conf="/var/lib/odoo/odoo.conf",
            customer_root=self.root,
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_passes_only_when_mount_database_and_registry_align(self) -> None:
        payload = GUARD.audit(self.config, FakeRunner(self.root))
        self.assertEqual(payload["status"], "PASS")
        self.assertEqual(payload["installed_version"], "17.0.1.1")

    def test_missing_customer_mount_blocks(self) -> None:
        with self.assertRaisesRegex(GUARD.GuardError, "exactly one"):
            GUARD.audit(self.config, FakeRunner(self.root, mounted=False))

    def test_wrong_customer_mount_host_source_blocks(self) -> None:
        wrong_source = self.root / "wrong-customer-root"
        wrong_source.mkdir()
        with self.assertRaisesRegex(GUARD.GuardError, "source differs"):
            GUARD.audit(self.config, FakeRunner(self.root, mount_source=wrong_source))

    def test_pending_customer_module_blocks(self) -> None:
        with self.assertRaisesRegex(GUARD.GuardError, "expected 'installed'"):
            GUARD.audit(self.config, FakeRunner(self.root, state="to upgrade"))

    def test_writable_customer_mount_blocks(self) -> None:
        with self.assertRaisesRegex(GUARD.GuardError, "read-only"):
            GUARD.audit(self.config, FakeRunner(self.root, writable=True))

    def test_database_package_version_drift_blocks(self) -> None:
        with self.assertRaisesRegex(GUARD.GuardError, "database version differs"):
            GUARD.audit(self.config, FakeRunner(self.root, db_version="17.0.1.0"))

    def test_registry_package_version_drift_blocks(self) -> None:
        with self.assertRaisesRegex(GUARD.GuardError, "resolved customer version differs"):
            GUARD.audit(self.config, FakeRunner(self.root, runtime_version="17.0.1.0"))

    def test_multiple_odoo_service_containers_block(self) -> None:
        with self.assertRaisesRegex(GUARD.GuardError, "missing or ambiguous"):
            GUARD.audit(self.config, FakeRunner(self.root, container_ids="container-a\ncontainer-b"))

    def test_unresolved_customer_module_blocks(self) -> None:
        with self.assertRaisesRegex(GUARD.GuardError, "resolved from"):
            GUARD.audit(self.config, FakeRunner(self.root, resolved=False))


if __name__ == "__main__":
    unittest.main()
