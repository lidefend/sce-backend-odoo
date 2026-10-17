#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).with_name("daily_runtime_database_identity_inventory.py")
SPEC = importlib.util.spec_from_file_location(
    "daily_runtime_database_identity_inventory", SCRIPT
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

SHA = "10bf72ef4bb060556bd2844598b58f9806392d34"


def payload(**overrides):
    base = {
        "current_user": "sc_app",
        "session_user": "sc_app",
        "current_database": "sc_demo",
        "databases": [
            {"name": "sc_demo", "owner": "sc_app", "encoding": "UTF8"},
            {"name": "sc_tenant_sample_dev", "owner": "sc_sample", "encoding": "UTF8"},
        ],
        "roles": [
            {"name": "sc_app", "can_login": True, "superuser": False, "createdb": False},
            {"name": "sc_sample", "can_login": True, "superuser": False, "createdb": False},
        ],
        "filestores": {
            "sc_demo": "/var/lib/odoo/filestore/sc_demo",
            "sc_tenant_sample_dev": "/var/lib/odoo/filestore/sc_tenant_sample_dev",
        },
        "data_dir": "/var/lib/odoo",
        "dbfilter": "^sc_demo$",
        "list_db": False,
        "configured_db_name": "sc_demo",
        "server_version": 150000,
        "writes": False,
    }
    base.update(overrides)
    return base


class PreflightTests(unittest.TestCase):
    def test_accepts_declared_input_shapes(self):
        self.assertTrue(module.FULL_SHA.fullmatch(SHA))
        self.assertTrue(module.DATABASE_NAME.fullmatch("sc_tenant_sample_dev"))
        self.assertTrue(module.SSH_HOST.fullmatch("sc-root"))

    def test_rejects_unsafe_shapes(self):
        self.assertIsNone(module.DATABASE_NAME.fullmatch("sc_demo; rm -rf /"))
        self.assertIsNone(module.SSH_HOST.fullmatch("sc-root; rm -rf /"))
        self.assertIsNone(module.FULL_SHA.fullmatch("10bf72ef"))


class MarkerTests(unittest.TestCase):
    def test_marker_round_trip(self):
        line = module.MARKER + '{"databases": []}'
        self.assertEqual(module.marker_payload("noise\n" + line), {"databases": []})

    def test_marker_absent_and_malformed(self):
        self.assertIsNone(module.marker_payload("noise only"))
        self.assertIsNone(module.marker_payload(module.MARKER + "{not json"))


class VerdictTests(unittest.TestCase):
    def test_expected_database_must_be_present(self):
        verdict = module.evaluate("sc_missing", payload())
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("observed_database_present", failed)

    def test_declared_database_passes(self):
        verdict = module.evaluate(
            "sc_tenant_sample_dev",
            payload(
                current_database="sc_tenant_sample_dev",
                dbfilter="^sc_tenant_sample_dev$",
                configured_db_name="sc_tenant_sample_dev",
            ),
        )
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["database_count"], 2)

    def test_an_open_database_selector_fails_closed(self):
        verdict = module.evaluate("sc_demo", payload(list_db=True))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("database_enumeration_closed", failed)
        self.assertFalse(verdict["passed"])

    def test_a_non_exact_dbfilter_fails_closed(self):
        verdict = module.evaluate("sc_demo", payload(dbfilter=".*"))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("database_filter_is_exact", failed)

    def test_a_configured_database_name_for_another_database_fails_closed(self):
        verdict = module.evaluate("sc_demo", payload(configured_db_name="sc_other"))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("configured_database_name_is_the_bound_database", failed)

    def test_an_unset_configured_database_name_is_allowed_on_a_filtered_stack(self):
        verdict = module.evaluate("sc_demo", payload(configured_db_name=""))
        self.assertTrue(verdict["passed"])

    def test_a_read_of_the_other_carrier_is_refused(self):
        # The rebuilt demo duty and the preserved historic source both answer to
        # sc_demo. A catalogue that contains the bound name is not proof that the
        # shell actually read the bound database.
        verdict = module.evaluate("sc_tenant_sample_dev", payload())
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("shell_database_is_the_bound_database", failed)
        self.assertFalse(verdict["passed"])

    def test_a_payload_without_a_live_database_readback_is_refused(self):
        verdict = module.evaluate("sc_demo", payload(current_database=""))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("shell_database_is_the_bound_database", failed)

    def test_shared_filestore_is_reported(self):
        shared = payload(filestores={
            "sc_demo": "/var/lib/odoo/filestore/shared",
            "sc_tenant_sample_dev": "/var/lib/odoo/filestore/shared",
        })
        verdict = module.evaluate("sc_demo", shared)
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("filestore_namespace_per_database", failed)

    def test_filestore_error_is_not_treated_as_shared(self):
        errored = payload(filestores={
            "sc_demo": "error:AccessError",
            "sc_tenant_sample_dev": "error:AccessError",
        })
        verdict = module.evaluate("sc_demo", errored)
        self.assertTrue(verdict["passed"])

    def test_write_capability_is_reported(self):
        verdict = module.evaluate("sc_demo", payload(writes=True))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("inventory_is_read_only", failed)

    def test_no_login_role_fails_closed(self):
        verdict = module.evaluate("sc_demo", payload(roles=[
            {"name": "sc_app", "can_login": False, "superuser": False, "createdb": False}]))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("distinct_login_roles_observed", failed)


class ProgramTests(unittest.TestCase):
    def test_program_is_read_only(self):
        program = module.PROGRAM_TEMPLATE
        for forbidden in ("unlink", ".write(", "create(", "commit(", "DROP", "DELETE"):
            self.assertNotIn(forbidden, program)

    def test_program_uses_the_governed_shell_entry(self):
        self.assertEqual(module.REMOTE_ROOT, "/opt/projects/repos/sce-product-odoo")
        source = Path(SCRIPT).read_text(encoding="utf-8")
        # The catalog must be read from the bound duty's own container through the
        # shared duty-bound entry, never from a bare database name routed by hand.
        self.assertIn("duty_identity.odoo_shell_command", source)
        self.assertNotIn("odoo.shell.exec", source)
        self.assertIn("git rev-parse HEAD", source)

class ExecuteRemoteCleanupTests(unittest.TestCase):
    """The probe file is this entry's temporary carrier on a live host.

    Cleanup that starts only after a successful upload leaves the file behind
    exactly when the transport is already failing, so the upload belongs inside
    the ``try`` that owns the ``finally`` removal.
    """

    class Result:
        def __init__(self, returncode=0, stdout=b"", stderr=b""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def test_the_probe_is_removed_when_the_upload_fails(self):
        calls = []

        def fake_ssh(_host, command, input_bytes=None):
            calls.append(command)
            if command.startswith("cat > "):
                self.assertTrue(input_bytes)
                return self.Result(returncode=1, stderr=b"connection reset by peer")
            if command.startswith("rm -f "):
                return self.Result()
            raise AssertionError("unexpected command: %s" % command)

        with mock.patch.object(module, "ssh", side_effect=fake_ssh):
            with self.assertRaisesRegex(module.InventoryError, "upload failed"):
                module._execute_remote("sc-root", {}, b"print(1)\n")
        self.assertEqual(calls[-1], "rm -f " + module.REMOTE_TMP)

    def test_the_probe_is_removed_when_the_readback_fails(self):
        calls = []

        def fake_ssh(_host, command, input_bytes=None):
            calls.append(command)
            if command.startswith("cat > "):
                return self.Result()
            if command.startswith("rm -f "):
                return self.Result()
            raise AssertionError("unexpected command: %s" % command)

        with mock.patch.object(module, "ssh", side_effect=fake_ssh):
            with mock.patch.object(
                module, "remote_shell", side_effect=RuntimeError("transport lost")
            ):
                with self.assertRaisesRegex(RuntimeError, "transport lost"):
                    module._execute_remote("sc-root", {}, b"print(1)\n")
        self.assertEqual(calls[-1], "rm -f " + module.REMOTE_TMP)


if __name__ == "__main__":
    unittest.main()
