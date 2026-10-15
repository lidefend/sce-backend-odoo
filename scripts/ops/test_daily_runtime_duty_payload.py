#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "daily_runtime_duty_payload",
    ROOT / "scripts/ops/daily_runtime_duty_payload.py",
)
assert SPEC and SPEC.loader
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)

DECLARATION = ROOT / "config/ops/daily_runtime_database_duties.v1.json"
CUSTOMER_DUTY = "customer_tenant_dev"
DEMO_DUTY = "demo"


def write_checksums(root: Path, entries: dict[str, bytes]) -> str:
    """Materialise a payload-shaped tree and return its approved checksum."""
    lines = []
    for relative, content in sorted(entries.items()):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        lines.append(
            "%s  %s" % (hashlib.sha256(content).hexdigest(), relative)
        )
    checksums = ("\n".join(lines) + "\n").encode("utf-8")
    (root / "checksums.sha256").write_bytes(checksums)
    return hashlib.sha256(checksums).hexdigest()


def payload_manifest(checksum: str, tenant_key: str = "baosheng") -> dict:
    return {
        "schema_version": "tenant_payload_v1",
        "payload_id": "baosheng-rc01-test",
        "tenant_key": tenant_key,
        "payload_checksum": checksum,
        "customer_module": "sce_customer_baosheng",
        "customer_module_version": "17.0.2.7.0",
        "created_at_utc": "2026-08-11T01:28:57Z",
    }


class DutyResolutionTests(unittest.TestCase):
    def test_a_customer_duty_is_required(self):
        duty = ENTRY.resolve_duty(CUSTOMER_DUTY)
        self.assertEqual(duty["database"], "sc_tenant_baosheng_dev")
        self.assertEqual(duty["database_role"], "sc_tenant_baosheng_dev_app")
        self.assertEqual(duty["tenant_key"], "baosheng")
        self.assertEqual(duty["data_purpose"], "customer")

    def test_non_customer_duties_may_not_receive_a_payload(self):
        for name in (DEMO_DUTY, "platform_control"):
            with self.subTest(duty=name):
                with self.assertRaisesRegex(ENTRY.PayloadEntryError, "not customer"):
                    ENTRY.resolve_duty(name)

    def test_undeclared_duty_is_rejected(self):
        with self.assertRaisesRegex(ENTRY.PayloadEntryError, "undeclared duty"):
            ENTRY.resolve_duty("customer_tenant_nowhere")

    def test_entry_hardcodes_no_duty_identity(self):
        source = (ROOT / "scripts/ops/daily_runtime_duty_payload.py").read_text()
        duties = json.loads(DECLARATION.read_text())["duties"]
        for duty in duties:
            for key in ("database", "database_role", "dbfilter"):
                value = duty[key]
                if re.fullmatch(r"[a-z]+", value):
                    # A single lowercase word is a shared infrastructure
                    # convention -- the demo duty runs inside the cluster's own
                    # `odoo` role -- so it cannot identify one duty.
                    continue
                self.assertNotIn(value, source, "%s.%s" % (duty["duty"], key))
            for section, key in (
                ("cluster", "container"),
                ("cluster", "data_volume"),
                ("cluster", "compose_project"),
                ("storage", "odoo_data_volume"),
                ("storage", "backup_namespace"),
            ):
                self.assertNotIn(
                    duty[section][key], source, "%s.%s.%s" % (duty["duty"], section, key)
                )


class DutyEnvironmentTests(unittest.TestCase):
    def _env(self, **overrides):
        values = {
            "DUTY_NAME": ENTRY.resolve_duty(CUSTOMER_DUTY)["duty"],
            "COMPOSE_PROJECT_NAME": "sc-tenant-baosheng-dev",
            "DB_NAME": "sc_tenant_baosheng_dev",
            "DB_USER": "sc_tenant_baosheng_dev_app",
            "DB_DATA": "sc_tenant_baosheng_dev_db_data",
            "ODOO_DATA": "sc_tenant_baosheng_dev_odoo_data",
            "ODOO_IMAGE": "odoo17-odoo:latest",
        }
        values.update(overrides)
        return values

    def test_a_rendered_environment_is_read_and_must_agree(self):
        duty = ENTRY.resolve_duty(CUSTOMER_DUTY)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "customer_tenant_dev.env"
            path.write_text(
                "".join("%s=%s\n" % row for row in self._env().items()),
                encoding="utf-8",
            )
            with mock.patch.object(ENTRY, "assert_private_file"):
                values = ENTRY.read_duty_env(path, duty)
        self.assertEqual(values["DB_NAME"], "sc_tenant_baosheng_dev")

    def test_an_environment_naming_another_database_is_refused(self):
        duty = ENTRY.resolve_duty(CUSTOMER_DUTY)
        for key, value in (
            ("DB_NAME", "sc_demo"),
            ("DB_USER", "odoo"),
            ("COMPOSE_PROJECT_NAME", "sc-backend-odoo-dev"),
            ("DB_DATA", "sc_dev_db_data"),
            ("DUTY_NAME", "demo"),
        ):
            with self.subTest(key=key):
                values = self._env(**{key: value})
                with self.assertRaises(ENTRY.PayloadEntryError):
                    ENTRY.assert_env_declares_duty(values, duty)

    def test_a_missing_key_is_refused(self):
        duty = ENTRY.resolve_duty(CUSTOMER_DUTY)
        values = self._env()
        values.pop("ODOO_IMAGE")
        with self.assertRaises(ENTRY.PayloadEntryError):
            ENTRY.assert_env_declares_duty(values, duty)

    def test_an_unreadable_environment_is_refused(self):
        duty = ENTRY.resolve_duty(CUSTOMER_DUTY)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "customer_tenant_dev.env"
            path.write_text("DB_NAME=sc_tenant_baosheng_dev\n", encoding="utf-8")
            os.chmod(path, 0o644)
            with self.assertRaisesRegex(ENTRY.PayloadEntryError, "0600"):
                ENTRY.read_duty_env(path, duty)


class StackDiscoveryTests(unittest.TestCase):
    def test_exactly_one_rendered_stack_is_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ENTRY.PayloadEntryError, "exactly one"):
                ENTRY.stack_compose_path(root)
            (root / "duty-stack-1a5ca02d60da.yml").write_text("services: {}\n")
            self.assertEqual(
                ENTRY.stack_compose_path(root).name, "duty-stack-1a5ca02d60da.yml"
            )
            (root / "duty-stack-deadbeef0000.yml").write_text("services: {}\n")
            with self.assertRaisesRegex(ENTRY.PayloadEntryError, "exactly one"):
                ENTRY.stack_compose_path(root)


class PayloadIdentityTests(unittest.TestCase):
    def test_unsafe_payload_identity_is_refused(self):
        for payload_id in ("", "..", "../../etc", "Payload", "a"):
            with self.subTest(payload_id=payload_id):
                with self.assertRaises(ENTRY.PayloadEntryError):
                    ENTRY.payload_paths(payload_id)

    def test_manifest_must_match_duty_and_approved_checksum(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            approved = write_checksums(root, {"records/projects.jsonl": b"{}\n"})
            (root / "manifest.json").write_text(
                json.dumps(payload_manifest(approved))
            )
            manifest = ENTRY.load_manifest(root, "baosheng", approved)
            self.assertEqual(manifest["customer_module"], "sce_customer_baosheng")
            with self.assertRaisesRegex(ENTRY.PayloadEntryError, "tenant"):
                ENTRY.load_manifest(root, "other", approved)
            with self.assertRaisesRegex(ENTRY.PayloadEntryError, "approved checksum"):
                ENTRY.load_manifest(root, "baosheng", "0" * 64)
            with self.assertRaises(ENTRY.PayloadEntryError):
                ENTRY.load_manifest(root, "baosheng", "not-a-checksum")


class PayloadStagingTests(unittest.TestCase):
    def setUp(self):
        self.duty = ENTRY.resolve_duty(CUSTOMER_DUTY)
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.approved = write_checksums(
            self.source,
            {
                "records/projects.jsonl": b'{"external_key":"p1"}\n',
                "filestore/abc": b"binary",
            },
        )
        (self.source / "manifest.json").write_text(json.dumps(payload_manifest(self.approved)))
        (self.source / "signature").write_bytes(b"signature-bytes")
        self.patcher = mock.patch.multiple(
            ENTRY,
            STAGE_ROOT=str(self.root / "stage"),
            KEY_STAGE_ROOT=str(self.root / "keys"),
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self._temporary.cleanup()

    def test_staged_copy_is_verified_and_reused(self):
        first = ENTRY._stage_payload(self.source, self.duty, self.approved)
        self.assertFalse(first["reused"])
        staged = Path(first["root"])
        self.assertTrue((staged / "manifest.json").is_file())
        self.assertTrue((staged / "filestore/abc").is_file())
        second = ENTRY._stage_payload(self.source, self.duty, self.approved)
        self.assertTrue(second["reused"])
        self.assertEqual(first["root"], second["root"])

    def test_staged_copy_is_readable_by_another_identity(self):
        stage = ENTRY._stage_payload(self.source, self.duty, self.approved)
        staged = Path(stage["root"])
        for path in [staged, *staged.rglob("*")]:
            self.assertTrue(
                path.stat().st_mode & 0o044, "%s is not group/other readable" % path
            )

    def test_a_symlink_in_the_source_is_refused(self):
        (self.source / "filestore/link").symlink_to("/etc/passwd")
        with self.assertRaisesRegex(ENTRY.PayloadEntryError, "symlink"):
            ENTRY._stage_payload(self.source, self.duty, self.approved)

    def test_a_different_checksum_for_the_same_payload_is_refused(self):
        ENTRY._stage_payload(self.source, self.duty, self.approved)
        with self.assertRaises(ENTRY.PayloadEntryError):
            ENTRY._stage_payload(self.source, self.duty, "1" * 64)

    def test_a_tampered_staged_tree_is_rejected_at_creation(self):
        (self.source / "records/projects.jsonl").write_bytes(b'{"external_key":"x"}\n')
        with self.assertRaises(ENTRY.PayloadEntryError):
            ENTRY._stage_payload(self.source, self.duty, self.approved)

    def test_public_key_is_staged_readable(self):
        key = self.root / "public.pem"
        key.write_bytes(b"key-material")
        staged = ENTRY._stage_public_key(key, self.duty)
        self.assertEqual(Path(staged["path"]).read_bytes(), b"key-material")
        self.assertTrue(Path(staged["path"]).stat().st_mode & 0o044)


class MaintenanceCommandTests(unittest.TestCase):
    def _command(self, action="plan"):
        duty = ENTRY.resolve_duty(CUSTOMER_DUTY)
        base = ["docker", "compose", "--project-name", duty["compose_project"]]
        return duty, ENTRY.maintenance_command(
            duty,
            base,
            action=action,
            approved_checksum="a" * 64,
            chunk_size=100,
            resume_failed=action == "import",
            capability="c" * 64,
            staged_payload=Path("/opt/sce/payload-staging/customer_tenant_dev/p"),
            staged_key=Path("/opt/sce/payload-keys/customer_tenant_dev/p.pem"),
        )

    def test_the_command_runs_the_duty_definition_as_its_own_user(self):
        duty, command = self._command()
        self.assertEqual(command[:3], ["docker", "compose", "--project-name"])
        self.assertIn("run", command)
        self.assertIn("--no-deps", command)
        self.assertIn("--rm", command)
        self.assertNotIn("--user", command)
        self.assertNotIn("docker", command[3:])
        self.assertNotIn("--network", command)
        self.assertEqual(command[command.index("--entrypoint") + 1], "odoo")

    def test_the_shell_targets_the_declared_database_and_conf(self):
        duty, command = self._command()
        entrypoint = command.index("--entrypoint")
        self.assertEqual(command[entrypoint + 1], ENTRY.APPLICATION_ENTRY)
        self.assertEqual(command[entrypoint + 2], ENTRY.APPLICATION_ENTRY)
        self.assertEqual(command[entrypoint + 3], "shell")
        self.assertEqual(command[command.index("-c") + 1], "/var/lib/odoo/odoo.conf")
        self.assertEqual(command[command.index("-d") + 1], duty["database"])
        self.assertIn("--no-http", command)

    def test_the_payload_is_mounted_read_only(self):
        _, command = self._command()
        mounts = [
            command[index + 1]
            for index, value in enumerate(command)
            if value == "--volume"
        ]
        self.assertEqual(len(mounts), 2)
        for mount in mounts:
            self.assertTrue(mount.endswith(":ro"), mount)
        self.assertIn(
            "/opt/sce/payload-staging/customer_tenant_dev/p:/mnt/tenant-payload:ro",
            mounts,
        )

    def test_the_action_contract_binds_the_duty_database(self):
        duty, command = self._command()
        for expected in (
            "SC_TENANT_PAYLOAD_DB_ALLOWLIST=%s" % duty["database"],
            "SC_TENANT_PAYLOAD_TENANT_KEY=%s" % duty["tenant_key"],
            'SC_TENANT_PAYLOAD_DIRECT_GRANT_TARGETS=["%s"]' % ENTRY.IMPORTER_GROUP,
            "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_TYPE=external_xmlid",
            "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_KEY=base.user_admin",
            "SC_TENANT_PAYLOAD_PUBLIC_KEY=/mnt/tenant-payload-public-key",
        ):
            self.assertIn(expected, command)
        self.assertNotIn("SC_TENANT_PAYLOAD_RESUME_FAILED=1", command)

    def test_only_the_import_action_resumes_a_failed_batch(self):
        _, command = self._command("import")
        self.assertIn("SC_TENANT_PAYLOAD_RESUME_FAILED=1", command)


class ActionGuardTests(unittest.TestCase):
    def test_unsupported_action_is_refused(self):
        with self.assertRaisesRegex(ENTRY.PayloadEntryError, "unsupported"):
            ENTRY.execute(
                CUSTOMER_DUTY,
                action="drop",
                payload_id="baosheng-rc01-test",
                approved_checksum="a" * 64,
                chunk_size=100,
            )

    def test_import_requires_the_exact_confirmation(self):
        with mock.patch.object(ENTRY, "resolve_duty", return_value=_duty()), mock.patch.object(
            ENTRY, "read_duty_env", return_value={}
        ), mock.patch.object(
            ENTRY, "stack_compose_path", return_value=Path("/tmp/stack.yml")
        ), mock.patch.object(
            ENTRY, "inspect_odoo_container", return_value={}
        ), mock.patch.object(
            ENTRY, "payload_paths", return_value=(Path("/tmp/p"), Path("/tmp/k"))
        ), mock.patch.object(
            ENTRY, "load_manifest", return_value={}
        ), mock.patch.object(
            ENTRY, "_stage_payload", return_value={"root": Path("/tmp/s"), "reused": False, "files": 0, "checksums_sha256": ""}
        ), mock.patch.object(
            ENTRY, "_stage_public_key", return_value={"path": Path("/tmp/sk"), "sha256": ""}
        ), mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ENTRY.PayloadEntryError, "CONFIRM_DAILY_DUTY"):
                ENTRY.execute(
                    CUSTOMER_DUTY,
                    action="import",
                    payload_id="baosheng-rc01-test",
                    approved_checksum="a" * 64,
                    chunk_size=100,
                )

    def test_plan_needs_no_confirmation(self):
        with mock.patch.object(ENTRY, "resolve_duty", return_value=_duty()), mock.patch.object(
            ENTRY, "read_duty_env", return_value={}
        ), mock.patch.object(
            ENTRY, "stack_compose_path", return_value=Path("/tmp/stack.yml")
        ), mock.patch.object(
            ENTRY, "inspect_odoo_container", return_value={}
        ), mock.patch.object(
            ENTRY, "payload_paths", return_value=(Path("/tmp/p"), Path("/tmp/k"))
        ), mock.patch.object(
            ENTRY, "load_manifest", return_value={}
        ), mock.patch.object(
            ENTRY, "_stage_payload", return_value={"root": Path("/tmp/s"), "reused": False, "files": 0, "checksums_sha256": ""}
        ), mock.patch.object(
            ENTRY, "_stage_public_key", return_value={"path": Path("/tmp/sk"), "sha256": ""}
        ), mock.patch.dict(os.environ, {}, clear=True):
            # It fails later, on the tool root, and never on a confirmation.
            with self.assertRaises(ENTRY.PayloadEntryError) as caught:
                ENTRY.execute(
                    CUSTOMER_DUTY,
                    action="plan",
                    payload_id="baosheng-rc01-test",
                    approved_checksum="a" * 64,
                    chunk_size=100,
                    tool_root=Path("/nonexistent-tool-root"),
                )
            self.assertIn("tenant payload action", str(caught.exception))


def _duty() -> dict:
    return {
        "duty": CUSTOMER_DUTY,
        "database": "sc_tenant_baosheng_dev",
        "database_role": "sc_tenant_baosheng_dev_app",
        "compose_project": "sc-tenant-baosheng-dev",
        "odoo_container": "sc-tenant-baosheng-dev-odoo-1",
        "tenant_key": "baosheng",
        "data_purpose": "customer",
        "environment_id": "daily-dev-baosheng",
    }


if __name__ == "__main__":
    unittest.main()
