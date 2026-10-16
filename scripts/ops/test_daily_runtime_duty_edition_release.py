#!/usr/bin/env python3
from __future__ import annotations

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
    "daily_runtime_duty_edition_release",
    ROOT / "scripts/ops/daily_runtime_duty_edition_release.py",
)
assert SPEC and SPEC.loader
ENTRY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENTRY)

SUPPORT_SPEC = importlib.util.spec_from_file_location(
    "duty_identity_test_support",
    ROOT / "scripts/ops/duty_identity_test_support.py",
)
assert SUPPORT_SPEC and SUPPORT_SPEC.loader
SUPPORT = importlib.util.module_from_spec(SUPPORT_SPEC)
SUPPORT_SPEC.loader.exec_module(SUPPORT)

DECLARATION = ROOT / "config/ops/daily_runtime_database_duties.v1.json"


def setUpModule():
    """Resolve the tracked template against the synthetic customer binding."""
    override = SUPPORT.synthetic_instances_override()
    override.start()
    unittest.addModuleCleanup(override.stop)


def governed_declaration() -> dict:
    """The tracked declaration with its managed customer binding merged in.

    The result is self-contained: the ``managed_duty_instances`` pointer is
    dropped, so a test that writes it to a temporary path reads back one
    complete declaration instead of reaching for the governed directory again.
    """
    payload = ENTRY.duty_identity.load_declaration(DECLARATION)
    payload = json.loads(json.dumps(payload, ensure_ascii=False))
    payload.pop("managed_duty_instances", None)
    return payload
CUSTOMER_DUTY = "customer_tenant_dev"
DEMO_DUTY = "demo"
PLATFORM_DUTY = "platform_control"
STANDARD = "construction.standard"
PREVIEW = "construction.preview"
REVISION = "10bf72ef4bb060556bd2844598b58f9806392d34"
STACK = "duty-stack-1a5ca02d60da.yml"


def _declaration(**overrides) -> dict:
    payload = governed_declaration()
    duties = {entry["duty"]: entry for entry in payload["duties"]}
    for name, change in overrides.items():
        target = duties[name]
        if change is None:
            target.pop("edition", None)
        else:
            target["edition"] = change
    return payload


class DutyResolutionTests(unittest.TestCase):
    def test_a_declared_customer_duty_is_accepted(self):
        duty = ENTRY.resolve_release_duty(CUSTOMER_DUTY)
        self.assertEqual(duty["database"], "sc_tenant_sample_dev")
        self.assertEqual(duty["database_role"], "sc_tenant_sample_dev_app")
        self.assertEqual(duty["tenant_key"], "sample")
        self.assertEqual(duty["data_purpose"], "customer")
        self.assertEqual(duty["edition"]["allowed_product_keys"], [STANDARD])
        self.assertEqual(duty["edition"]["version_prefix"], "daily-navigation")

    def test_the_platform_control_duty_is_refused(self):
        # The parameter names the database that *carries* the effective release
        # snapshot; it is not the platform's publication authority.
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "platform control plane"):
            ENTRY.resolve_release_duty(PLATFORM_DUTY)

    def test_an_undeclared_duty_is_refused(self):
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "undeclared duty"):
            ENTRY.resolve_release_duty("customer_tenant_nowhere")

    def test_an_unusable_duty_name_is_refused(self):
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "safe identifier"):
            ENTRY.resolve_release_duty("../sc_demo")

    def test_a_duty_without_an_edition_block_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "declaration.json"
            path.write_text(json.dumps(_declaration(customer_tenant_dev=None)), encoding="utf-8")
            with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "no edition block"):
                ENTRY.resolve_release_duty(CUSTOMER_DUTY, path)

    def test_a_duty_that_does_not_carry_a_snapshot_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "declaration.json"
            path.write_text(
                json.dumps(
                    _declaration(
                        customer_tenant_dev={
                            "carrier": "platform_publication_authority",
                            "allowed_product_keys": [STANDARD],
                            "version_prefix": "daily-navigation",
                        }
                    )
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "effective release snapshot"):
                ENTRY.resolve_release_duty(CUSTOMER_DUTY, path)

    def test_an_unusable_declared_product_key_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "declaration.json"
            path.write_text(
                json.dumps(
                    _declaration(
                        customer_tenant_dev={
                            "carrier": "effective_release_snapshot",
                            "allowed_product_keys": ["construction.standard; drop"],
                            "version_prefix": "daily-navigation",
                        }
                    )
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "unusable edition product key"):
                ENTRY.resolve_release_duty(CUSTOMER_DUTY, path)

    def test_an_empty_declared_product_key_list_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "declaration.json"
            path.write_text(
                json.dumps(
                    _declaration(
                        customer_tenant_dev={
                            "carrier": "effective_release_snapshot",
                            "allowed_product_keys": [],
                            "version_prefix": "daily-navigation",
                        }
                    )
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "no allowed edition product keys"):
                ENTRY.resolve_release_duty(CUSTOMER_DUTY, path)

    def test_an_unusable_version_prefix_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "declaration.json"
            path.write_text(
                json.dumps(
                    _declaration(
                        customer_tenant_dev={
                            "carrier": "effective_release_snapshot",
                            "allowed_product_keys": [STANDARD],
                            "version_prefix": "daily/navigation",
                        }
                    )
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "unusable edition version prefix"):
                ENTRY.resolve_release_duty(CUSTOMER_DUTY, path)

    def test_entry_hardcodes_no_duty_identity(self):
        source = (ROOT / "scripts/ops/daily_runtime_duty_edition_release.py").read_text()
        duties = governed_declaration()["duties"]
        for duty in duties:
            for key in ("database", "database_role", "dbfilter"):
                value = duty[key]
                if re.fullmatch(r"[a-z]+", value):
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


class AllowedEditionTests(unittest.TestCase):
    def test_only_the_declared_edition_may_be_published(self):
        duty = ENTRY.resolve_release_duty(CUSTOMER_DUTY)
        self.assertEqual(ENTRY.assert_declared_product_key(duty, STANDARD), STANDARD)
        # preview is never widened automatically: a customer duty that does not
        # declare it cannot have it published into it.
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "does not declare edition"):
            ENTRY.assert_declared_product_key(duty, PREVIEW)

    def test_a_demo_duty_may_declare_and_publish_its_own_editions(self):
        duty = ENTRY.resolve_release_duty(DEMO_DUTY)
        self.assertEqual(
            sorted(duty["edition"]["allowed_product_keys"]), [PREVIEW, STANDARD]
        )

    def test_an_unsafe_product_key_is_refused(self):
        duty = ENTRY.resolve_release_duty(CUSTOMER_DUTY)
        for candidate in ("con struction.standard", "construction.standard;", "*", ""):
            with self.subTest(candidate=candidate):
                with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "safe declared key"):
                    ENTRY.assert_declared_product_key(duty, candidate)

    def test_the_version_follows_the_declared_prefix_and_served_revision(self):
        duty = ENTRY.resolve_release_duty(CUSTOMER_DUTY)
        self.assertEqual(
            ENTRY.expected_version(duty, STANDARD, REVISION),
            "daily-navigation-standard-10bf72ef4bb0",
        )

    def test_a_duty_without_a_usable_revision_is_refused(self):
        duty = ENTRY.resolve_release_duty(CUSTOMER_DUTY)
        for revision in ("", "10bf72ef", "z" * 40):
            with self.subTest(revision=revision):
                with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "source revision"):
                    ENTRY.expected_version(duty, STANDARD, revision)


class ReleaseStateTests(unittest.TestCase):
    def setUp(self):
        self.duty = ENTRY.resolve_release_duty(CUSTOMER_DUTY)

    def test_release_state_reads_the_parameters_and_the_snapshots(self):
        with mock.patch.object(
            ENTRY.duty_runtime,
            "psql",
            side_effect=[
                "sc.tenant.bound_tenant_key=sample\nsmart_core.platform_release_db=sc_tenant_sample_dev\n",
                "7|construction.standard|v1|released|t|t\n",
            ],
        ):
            state = ENTRY.release_state(self.duty)
        self.assertEqual(len(state["parameters"]), 2)
        self.assertEqual(state["snapshots"], ["7|construction.standard|v1|released|t|t"])

    def test_the_snapshot_sql_uses_the_physical_table_not_the_model_name(self):
        # The ORM model sc.edition.release.snapshot is only addressable through
        # env[...]; raw SQL must use sc_edition_release_snapshot, or PostgreSQL
        # refuses the statement with "improper qualified name".
        seen = []

        def _capture(_duty, sql):
            seen.append(sql)
            return ""

        with mock.patch.object(ENTRY.duty_runtime, "psql", side_effect=_capture):
            ENTRY.release_state(self.duty)
            ENTRY.released_active(self.duty)
        self.assertEqual(len(seen), 3)
        # The first statement reads ir_config_parameter; the other two read the
        # snapshot rows and must name the physical table.
        for sql in seen:
            self.assertNotIn(ENTRY.SNAPSHOT_MODEL, sql)
        for sql in seen[1:]:
            self.assertIn(ENTRY.SNAPSHOT_TABLE, sql)
        self.assertEqual(ENTRY.SNAPSHOT_TABLE, "sc_edition_release_snapshot")
        self.assertNotEqual(ENTRY.SNAPSHOT_TABLE, ENTRY.SNAPSHOT_MODEL)

    def test_released_active_parses_product_and_version(self):
        with mock.patch.object(
            ENTRY.duty_runtime,
            "psql",
            return_value="construction.standard|daily-navigation-standard-10bf72ef4bb0\n",
        ):
            rows = ENTRY.released_active(self.duty)
        self.assertEqual(
            rows, [{"product_key": STANDARD, "version": "daily-navigation-standard-10bf72ef4bb0"}]
        )


class ReleaseCommandTests(unittest.TestCase):
    def _command(self, action="publish"):
        duty = ENTRY.resolve_release_duty(CUSTOMER_DUTY)
        base = ["docker", "compose", "--project-name", duty["compose_project"]]
        entry_root = Path("/opt/sce/deployment-tools/deadbeef")
        if action == "publish":
            return duty, ENTRY.publish_command(
                duty,
                base,
                entry_root,
                product_key=STANDARD,
                version="daily-navigation-standard-10bf72ef4bb0",
            )
        return duty, ENTRY.readback_command(duty, base, entry_root)

    def test_the_release_run_uses_the_duty_definition_as_its_own_user(self):
        _, command = self._command()
        self.assertEqual(command[:3], ["docker", "compose", "--project-name"])
        self.assertIn("run", command)
        self.assertIn("--rm", command)
        self.assertIn("--no-deps", command)
        self.assertNotIn("--user", command)
        self.assertNotIn("--network", command)

    def test_the_release_entry_is_mounted_read_only(self):
        _, command = self._command()
        mounts = [
            command[index + 1] for index, value in enumerate(command) if value == "--volume"
        ]
        self.assertEqual(len(mounts), 1)
        self.assertTrue(mounts[0].endswith(":ro"), mounts[0])
        self.assertTrue(mounts[0].endswith("%s:ro" % ENTRY.RELEASE_ENTRY_MOUNT))

    def test_the_shell_targets_the_declared_database_and_conf(self):
        duty, command = self._command()
        entrypoint = command.index("--entrypoint")
        self.assertEqual(command[entrypoint + 1], ENTRY.APPLICATION_ENTRY)
        self.assertEqual(command[entrypoint + 3], "shell")
        self.assertEqual(command[command.index("-c") + 1], "/var/lib/odoo/odoo.conf")
        self.assertEqual(command[command.index("-d") + 1], duty["database"])
        self.assertIn("--no-http", command)

    def test_publish_acknowledges_both_governed_entries(self):
        duty, command = self._command("publish")
        for expected in (
            "PLATFORM_RELEASE_DB=%s" % duty["database"],
            "PLATFORM_RELEASE_PRODUCT_KEY=%s" % STANDARD,
            "PLATFORM_RELEASE_VERSION=daily-navigation-standard-10bf72ef4bb0",
            "SC_COLOCATED_PLATFORM_CONFIG_APPLY=%s" % ENTRY.CONFIG_APPLY_ACK,
            "SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY=%s" % ENTRY.SNAPSHOT_APPLY_ACK,
        ):
            self.assertIn(expected, command)

    def test_readback_sets_no_apply_acknowledgement(self):
        _, command = self._command("readback")
        self.assertFalse([row for row in command if row.startswith("PLATFORM_RELEASE_")])
        self.assertFalse([row for row in command if "APPLY=" in row])


class PublishReceiptTests(unittest.TestCase):
    def setUp(self):
        self.duty = ENTRY.resolve_release_duty(CUSTOMER_DUTY)
        self.configure = {
            "status": "PASS",
            "database": self.duty["database"],
            "parameter": ENTRY.PARAMETER,
            "value": self.duty["database"],
            "changed": True,
        }
        self.snapshot = {
            "status": "PASS",
            "database": self.duty["database"],
            "product_key": STANDARD,
            "version": "daily-navigation-standard-10bf72ef4bb0",
            "snapshot_id": 12,
        }

    def _output(self, *reports):
        return "\n".join(
            ["Running migration scripts..."]
            + [json.dumps(report, sort_keys=True) for report in reports]
        )

    def test_publish_requires_both_governed_receipts(self):
        reports = ENTRY.publish_reports(self._output(self.configure, self.snapshot), self.duty)
        self.assertEqual(reports["snapshot"]["snapshot_id"], 12)
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "platform parameter entry"):
            ENTRY.publish_reports(self._output(self.snapshot), self.duty)
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "snapshot entry emitted no receipt"):
            ENTRY.publish_reports(self._output(self.configure), self.duty)

    def test_a_receipt_for_another_database_is_refused(self):
        other = dict(self.snapshot, database="sc_demo")
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "another database"):
            ENTRY.publish_reports(self._output(self.configure, other), self.duty)

    def test_a_receipt_that_did_not_pass_is_refused(self):
        blocked = dict(self.snapshot, status="BLOCKED")
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "did not pass"):
            ENTRY.publish_reports(self._output(self.configure, blocked), self.duty)

    def test_an_unexpected_parameter_write_is_refused(self):
        wrong = dict(self.configure, parameter="smart_core.something_else")
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "unexpected parameter"):
            ENTRY.publish_reports(self._output(wrong, self.snapshot), self.duty)
        wrong = dict(self.configure, value="sc_demo")
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "unexpected value"):
            ENTRY.publish_reports(self._output(wrong, self.snapshot), self.duty)


class ReadbackAssertionTests(unittest.TestCase):
    def setUp(self):
        self.duty = ENTRY.resolve_release_duty(CUSTOMER_DUTY)
        self.report = {
            "mode": "read_only",
            "writes": 0,
            "database": self.duty["database"],
            "platform_release_db": self.duty["database"],
            "bound_tenant_key": "sample",
            "snapshot_count": 1,
            "released_active": [
                {"product_key": STANDARD, "version": "daily-navigation-standard-10bf72ef4bb0"}
            ],
        }

    def test_the_readback_marker_is_required(self):
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "no report"):
            ENTRY.readback_report("noise\n" + json.dumps(self.report))
        output = "%s%s\n" % (ENTRY.READBACK_MARKER, json.dumps(self.report))
        self.assertEqual(ENTRY.readback_report(output)["database"], self.duty["database"])
        # The tool's own evidence marker is not a readback report.
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "no report"):
            ENTRY.readback_report("%s%s\n" % (ENTRY.MARKER, json.dumps(self.report)))

    def test_readback_targeting_another_database_is_refused(self):
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "another database"):
            ENTRY.assert_readback(
                dict(self.report, database="sc_demo"), self.duty, product_key=STANDARD
            )

    def test_a_readback_that_wrote_something_is_refused(self):
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "read-only"):
            ENTRY.assert_readback(
                dict(self.report, writes=1), self.duty, product_key=STANDARD
            )

    def test_a_carrier_naming_another_database_is_refused(self):
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "names another database"):
            ENTRY.assert_readback(
                dict(self.report, platform_release_db="sc_demo"), self.duty
            )

    def test_a_tenant_binding_naming_another_tenant_is_refused(self):
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "names another tenant"):
            ENTRY.assert_readback(
                dict(self.report, bound_tenant_key="someone-else"), self.duty
            )

    def test_an_unbound_tenant_key_is_not_invented(self):
        # The demo duty carries another tenant's stale binding today; the entry
        # must not turn that into a precondition it cannot satisfy.
        ENTRY.assert_readback(dict(self.report, bound_tenant_key=""), self.duty)

    def test_exactly_one_released_active_snapshot_is_required(self):
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "exactly one"):
            ENTRY.assert_readback(dict(self.report, released_active=[]), self.duty, product_key=STANDARD)
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "exactly one"):
            ENTRY.assert_readback(
                dict(
                    self.report,
                    released_active=[
                        {"product_key": STANDARD, "version": "a"},
                        {"product_key": STANDARD, "version": "b"},
                    ],
                ),
                self.duty,
                product_key=STANDARD,
            )

    def test_a_released_snapshot_naming_another_version_is_refused(self):
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "another version"):
            ENTRY.assert_readback(
                self.report, self.duty, product_key=STANDARD, version="daily-navigation-standard-000000000000"
            )

    def test_an_unpublished_duty_is_readable_without_a_carrier(self):
        # Before publication the duty legitimately carries no parameter yet.
        ENTRY.assert_readback(dict(self.report, platform_release_db=""), self.duty)


class EntryTests(unittest.TestCase):
    def _patch(self, *, state=None, released=None, output=None):
        duty = ENTRY.resolve_release_duty(CUSTOMER_DUTY)
        stack = Path("/opt/projects/secure/daily-runtime-duties") / STACK
        return duty, [
            mock.patch.object(
                ENTRY.duty_identity, "load_declaration", return_value={"ops_root": "/opt/projects/secure/daily-runtime-duties"}
            ),
            mock.patch.object(
                ENTRY.duty_runtime,
                "read_duty_env",
                return_value={"DB_NAME": duty["database"], "SC_SOURCE_REVISION": REVISION},
            ),
            mock.patch.object(ENTRY.duty_runtime, "stack_compose_path", return_value=stack),
            mock.patch.object(ENTRY.duty_runtime, "inspect_odoo_container", return_value={"container": "x"}),
            mock.patch.object(ENTRY.duty_runtime, "compose_base", return_value=["docker", "compose"]),
            mock.patch.object(ENTRY, "release_state", side_effect=state),
            mock.patch.object(ENTRY, "released_active", side_effect=released),
            mock.patch.object(ENTRY, "run_script", side_effect=output),
        ]

    def _tool_root(self, temporary: Path) -> Path:
        root = temporary / "deadbeef"
        release = root / ENTRY.RELEASE_ENTRY_DIRECTORY
        release.mkdir(parents=True)
        for name in ENTRY.RELEASE_ENTRY_SCRIPTS:
            (release / name).write_text("# %s\n" % name, encoding="utf-8")
        return root

    def test_unsupported_action_is_refused(self):
        with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "unsupported"):
            ENTRY.execute(CUSTOMER_DUTY, action="drop")

    def test_publish_requires_the_exact_confirmation(self):
        duty, patchers = self._patch()
        with mock.patch.object(ENTRY, "resolve_release_duty", return_value=duty):
            for patcher in patchers:
                patcher.start()
                self.addCleanup(patcher.stop)
            with mock.patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "CONFIRM_DAILY_DUTY_EDITION_RELEASE"):
                    ENTRY.execute(CUSTOMER_DUTY, action="publish", product_key=STANDARD)

    def test_readback_needs_no_confirmation_and_proves_it_wrote_nothing(self):
        state = {"parameters": [], "snapshots": []}
        report = {
            "mode": "read_only",
            "writes": 0,
            "database": "sc_tenant_sample_dev",
            "platform_release_db": "",
            "bound_tenant_key": "sample",
            "snapshot_count": 0,
            "released_active": [],
        }
        output = "%s%s\n" % (ENTRY.READBACK_MARKER, json.dumps(report))
        duty, patchers = self._patch(state=[state, state], released=[[], []], output=[output])
        with tempfile.TemporaryDirectory() as temporary:
            tool_root = self._tool_root(Path(temporary))
            with mock.patch.object(ENTRY, "resolve_release_duty", return_value=duty):
                for patcher in patchers:
                    patcher.start()
                    self.addCleanup(patcher.stop)
                with mock.patch.dict(os.environ, {}, clear=True):
                    evidence = ENTRY.execute(
                        CUSTOMER_DUTY, action="readback", tool_root=tool_root
                    )
        self.assertEqual(evidence["action"], "readback")
        self.assertEqual(evidence["database"], "sc_tenant_sample_dev")
        self.assertEqual(evidence["product_key"], "")
        self.assertEqual(
            evidence["release_state_digest_before"], evidence["release_state_digest_after"]
        )

    def test_readback_is_refused_when_the_duty_changed(self):
        first = {"parameters": [], "snapshots": []}
        second = {"parameters": ["smart_core.platform_release_db=sc_tenant_sample_dev"], "snapshots": []}
        report = {
            "mode": "read_only",
            "writes": 0,
            "database": "sc_tenant_sample_dev",
            "platform_release_db": "",
            "bound_tenant_key": "sample",
            "released_active": [],
        }
        output = "%s%s\n" % (ENTRY.READBACK_MARKER, json.dumps(report))
        duty, patchers = self._patch(state=[first, second], released=[[], []], output=[output])
        with tempfile.TemporaryDirectory() as temporary:
            tool_root = self._tool_root(Path(temporary))
            with mock.patch.object(ENTRY, "resolve_release_duty", return_value=duty):
                for patcher in patchers:
                    patcher.start()
                    self.addCleanup(patcher.stop)
                with mock.patch.dict(os.environ, {}, clear=True):
                    with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "changed the duty's release state"):
                        ENTRY.execute(CUSTOMER_DUTY, action="readback", tool_root=tool_root)

    def test_publish_binds_the_declared_edition_and_version(self):
        before = {"parameters": [], "snapshots": []}
        after = {
            "parameters": [
                "sc.tenant.bound_tenant_key=sample",
                "smart_core.platform_release_db=sc_tenant_sample_dev",
            ],
            "snapshots": ["12|construction.standard|daily-navigation-standard-10bf72ef4bb0|released|t|t"],
        }
        configure = json.dumps(
            {
                "status": "PASS",
                "database": "sc_tenant_sample_dev",
                "parameter": ENTRY.PARAMETER,
                "value": "sc_tenant_sample_dev",
                "changed": True,
            },
            sort_keys=True,
        )
        snapshot = json.dumps(
            {
                "status": "PASS",
                "database": "sc_tenant_sample_dev",
                "product_key": STANDARD,
                "version": "daily-navigation-standard-10bf72ef4bb0",
                "snapshot_id": 12,
            },
            sort_keys=True,
        )
        report = {
            "mode": "read_only",
            "writes": 0,
            "database": "sc_tenant_sample_dev",
            "platform_release_db": "sc_tenant_sample_dev",
            "bound_tenant_key": "sample",
            "snapshot_count": 1,
            "released_active": [
                {"product_key": STANDARD, "version": "daily-navigation-standard-10bf72ef4bb0"}
            ],
        }
        output = [
            "%s\n%s\n" % (configure, snapshot),
            "%s%s\n" % (ENTRY.READBACK_MARKER, json.dumps(report)),
        ]
        duty, patchers = self._patch(
            state=[before, after],
            released=[[], [{"product_key": STANDARD, "version": "daily-navigation-standard-10bf72ef4bb0"}]],
            output=output,
        )
        with tempfile.TemporaryDirectory() as temporary:
            tool_root = self._tool_root(Path(temporary))
            with mock.patch.object(ENTRY, "resolve_release_duty", return_value=duty):
                for patcher in patchers:
                    patcher.start()
                    self.addCleanup(patcher.stop)
                with mock.patch.dict(
                    os.environ,
                    {"CONFIRM_DAILY_DUTY_EDITION_RELEASE": "RELEASE_DECLARED_EDITION_INTO_DAILY_DUTY"},
                    clear=True,
                ):
                    evidence = ENTRY.execute(
                        CUSTOMER_DUTY,
                        action="publish",
                        product_key=STANDARD,
                        tool_root=tool_root,
                    )
        self.assertEqual(evidence["product_key"], STANDARD)
        self.assertEqual(evidence["version"], "daily-navigation-standard-10bf72ef4bb0")
        self.assertEqual(evidence["source_revision"], REVISION)
        self.assertEqual(evidence["publish_reports"]["snapshot"]["snapshot_id"], 12)
        self.assertEqual(
            sorted(evidence["release_entry_scripts"]), sorted(ENTRY.RELEASE_ENTRY_SCRIPTS)
        )

    def test_a_missing_immutable_release_entry_is_refused(self):
        duty, patchers = self._patch()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "deadbeef"
            (root / ENTRY.RELEASE_ENTRY_DIRECTORY).mkdir(parents=True)
            with mock.patch.object(ENTRY, "resolve_release_duty", return_value=duty):
                for patcher in patchers:
                    patcher.start()
                    self.addCleanup(patcher.stop)
                with mock.patch.dict(os.environ, {}, clear=True):
                    with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "immutable release entry"):
                        ENTRY.execute(
                            CUSTOMER_DUTY, action="readback", tool_root=root
                        )

    def test_an_undeclared_edition_cannot_be_published(self):
        before = {"parameters": [], "snapshots": []}
        duty, patchers = self._patch(state=[before], released=[[]], output=[])
        with mock.patch.object(ENTRY, "resolve_release_duty", return_value=duty):
            for patcher in patchers:
                patcher.start()
                self.addCleanup(patcher.stop)
            with mock.patch.dict(
                os.environ,
                {"CONFIRM_DAILY_DUTY_EDITION_RELEASE": "RELEASE_DECLARED_EDITION_INTO_DAILY_DUTY"},
                clear=True,
            ):
                with self.assertRaisesRegex(ENTRY.EditionReleaseEntryError, "does not declare edition"):
                    ENTRY.execute(CUSTOMER_DUTY, action="publish", product_key=PREVIEW)


class MakeTargetTests(unittest.TestCase):
    def setUp(self):
        self.make = (ROOT / "make/daily_candidate.mk").read_text(encoding="utf-8")

    def test_the_entry_is_declaration_driven_on_the_daily_host(self):
        self.assertIn(
            "DAILY_DUTY_EDITION_TOOL ?= $(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/"
            "daily_runtime_duty_edition_release.py",
            self.make,
        )
        self.assertIn("DAILY_DUTY_EDITION_DUTY ?= customer_tenant_dev", self.make)
        for target in (
            "daily.runtime.duty.edition_release.remote_readback:",
            "daily.runtime.duty.edition_release.remote_publish:",
        ):
            body = self.make.split(target, 1)[1].split("\n\n", 1)[0]
            self.assertIn('python3 "$(DAILY_DUTY_EDITION_TOOL)"', body, target)
            self.assertIn('--duty "$(DAILY_DUTY_EDITION_DUTY)"', body, target)
            # The recipe may not carry a database or container name of its own.
            self.assertNotIn("sc_tenant_sample_dev", body, target)
            self.assertNotIn("sc_demo", body, target)

    def test_publish_requires_the_exact_confirmation_on_the_entry(self):
        body = self.make.split("daily.runtime.duty.edition_release.remote_publish:", 1)[1]
        body = body.split("\n\n", 1)[0]
        self.assertIn("CONFIRM_DAILY_DUTY_EDITION_RELEASE", body)
        self.assertIn("RELEASE_DECLARED_EDITION_INTO_DAILY_DUTY", body)
        readback = self.make.split(
            "daily.runtime.duty.edition_release.remote_readback:", 1
        )[1].split("\n\n", 1)[0]
        self.assertNotIn("CONFIRM_DAILY_DUTY_EDITION_RELEASE", readback)

    def test_the_release_entries_are_inside_the_immutable_tool_tree(self):
        recipe = self.make.split("daily.candidate.continuity.remote_install:", 1)[1]
        recipe = recipe.split("\n\n", 1)[0]
        for path in (
            "scripts/ops/daily_runtime_duty_edition_release.py",
            "scripts/release/configure_colocated_platform_core.py",
            "scripts/release/initialize_colocated_platform_snapshot.py",
        ):
            self.assertIn(path, recipe, path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
