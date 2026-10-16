#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
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
# The governed binding of a customer duty lives outside the git checkout, so this
# module resolves the tracked template against the synthetic fixture through the
# one explicit override the resolver supports. No production path reads it.
SYNTHETIC_INSTANCES = ROOT / "scripts/ops/synthetic_duty_instances.sample.json"
_SYNTHETIC_OVERRIDE = mock.patch.dict(
    os.environ, {"SC_DAILY_RUNTIME_DUTY_INSTANCES": str(SYNTHETIC_INSTANCES)}
)


def setUpModule():
    _SYNTHETIC_OVERRIDE.start()


def tearDownModule():
    _SYNTHETIC_OVERRIDE.stop()


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
            "attachment_inventory": {
                "referenced_attachment_count": 1,
                "referenced_body_count": 1,
                "maintenance_marker_count": 1,
                "unknown_entry_count": 0,
                "missing_count": 0,
                "checksum_mismatch_count": 0,
                "referenced_body_path_digest": "0" * 64,
                "referenced_body_content_digest": "0" * 64,
                "maintenance_marker_digest": "0" * 64,
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


TENANT_CONTRACT_PATH = (
    ROOT / "scripts/ops/daily_runtime_tenant_recovery_contract_v1.json"
)


class DutyIdentityTests(unittest.TestCase):
    """Runtime identity has exactly one owner: the duty declaration."""

    def test_tenant_duty_identity_comes_from_the_declaration(self):
        contract = CONTINUITY._load_contract(TENANT_CONTRACT_PATH)
        self.assertEqual(contract["duty"], "customer_tenant_dev")
        self.assertEqual(contract["database"], "sc_tenant_sample_dev")
        self.assertEqual(
            contract["database_role"], "sc_tenant_sample_dev_app"
        )
        self.assertEqual(
            contract["database_container"], "sc-tenant-sample-dev-db-1"
        )
        self.assertEqual(
            contract["odoo_container"], "sc-tenant-sample-dev-odoo-1"
        )
        self.assertEqual(
            contract["backup_root"], "/data/backups/daily-tenant-sample-dev"
        )
        self.assertEqual(contract["filestore_scope"], "sc_tenant_sample_dev")
        self.assertEqual(
            contract["source_repository"], "/opt/projects/repos/sce-product-odoo"
        )

    def test_undeclared_duty_is_rejected(self):
        payload = json.loads(TENANT_CONTRACT_PATH.read_text())
        payload["duty"] = "customer_tenant_prod"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "contract.json"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(CONTINUITY.ContinuityError, "undeclared duty"):
                CONTINUITY._load_contract(path)

    def test_contract_may_not_restate_another_duty_role(self):
        payload = json.loads(TENANT_CONTRACT_PATH.read_text())
        payload["database_role"] = "odoo"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "contract.json"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(
                CONTINUITY.ContinuityError, "identity mismatch: database_role"
            ):
                CONTINUITY._load_contract(path)

    def test_contract_may_not_restate_another_duty_database(self):
        payload = json.loads(TENANT_CONTRACT_PATH.read_text())
        payload["database"] = "sc_tenant_other_dev"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "contract.json"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(
                CONTINUITY.ContinuityError, "identity mismatch: database"
            ):
                CONTINUITY._load_contract(path)

    def test_contract_may_not_restate_another_backup_root(self):
        payload = json.loads(TENANT_CONTRACT_PATH.read_text())
        payload["backup_root"] = "/data/backups/daily_candidate"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "contract.json"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(
                CONTINUITY.ContinuityError, "identity mismatch: backup_root"
            ):
                CONTINUITY._load_contract(path)

    def test_backup_identifier_is_bound_to_the_contract_prefix(self):
        tenant = CONTINUITY._load_contract(TENANT_CONTRACT_PATH)
        self.assertTrue(
            tenant["backup_id"].fullmatch(
                "sc_tenant_sample_dev-20261015T000000Z-deadbeef"
            )
        )
        self.assertIsNone(
            tenant["backup_id"].fullmatch("sc_demo-20261015T000000Z-deadbeef")
        )
        demo = CONTINUITY._load_contract(CONTRACT_PATH)
        self.assertIsNone(
            demo["backup_id"].fullmatch(
                "sc_tenant_sample_dev-20261015T000000Z-deadbeef"
            )
        )

    def test_relationship_sample_is_declared_per_duty(self):
        contract = CONTINUITY._load_contract(TENANT_CONTRACT_PATH)
        key, sql = CONTINUITY._relation_sample_sql(contract)
        self.assertEqual(key, "payment_request_relation_sample_digest")
        self.assertIn("FROM payment_request ORDER BY id LIMIT 100", sql)
        self.assertIn("COALESCE(project_id::text, '')", sql)
        self.assertIn("COALESCE(contract_id::text, '')", sql)

    def test_relationship_sample_cannot_inject_sql(self):
        contract = CONTINUITY._load_contract(TENANT_CONTRACT_PATH)
        contract = dict(contract)
        contract["relation_sample"] = {
            "table": "payment_request; DROP TABLE res_users",
            "columns": ["project_id"],
            "limit": 100,
        }
        with self.assertRaisesRegex(CONTINUITY.ContinuityError, "sample table"):
            CONTINUITY._relation_sample_sql(contract)

    def test_missing_relationship_sample_is_rejected(self):
        contract = CONTINUITY._load_contract(TENANT_CONTRACT_PATH)
        contract = dict(contract)
        contract.pop("relation_sample")
        with self.assertRaisesRegex(CONTINUITY.ContinuityError, "relationship sample"):
            CONTINUITY._relation_sample_sql(contract)

    def test_live_reads_use_the_duty_application_role(self):
        contract = CONTINUITY._load_contract(TENANT_CONTRACT_PATH)
        with mock.patch.object(CONTINUITY, "_run", return_value=b"1") as run:
            CONTINUITY._psql(contract, "SELECT 1;")
        argv = run.call_args.args[0]
        self.assertEqual(argv[:3], ["docker", "exec", contract["database_container"]])
        self.assertIn("sc_tenant_sample_dev_app", argv)

    def test_isolated_drill_uses_the_drill_own_role(self):
        contract = CONTINUITY._load_contract(TENANT_CONTRACT_PATH)
        with mock.patch.object(CONTINUITY, "_run", return_value=b"1") as run:
            CONTINUITY._psql(contract, "SELECT 1;", container="drill", role="odoo")
        argv = run.call_args.args[0]
        self.assertEqual(argv[:3], ["docker", "exec", "drill"])
        self.assertIn("odoo", argv)
        self.assertNotIn("sc_tenant_sample_dev_app", argv)

    def test_declaration_is_the_only_identity_source_in_the_tool(self):
        source = (
            ROOT / "scripts/ops/daily_candidate_data_continuity.py"
        ).read_text()
        shared = (
            ROOT / "scripts/ops/daily_runtime_duty_identity.py"
        ).read_text()
        # The tool holds no duty fact of its own: it resolves through the one
        # shared resolver, and the declaration literal lives in exactly one
        # module. A tool that re-declares the path would drift from it.
        self.assertIn("daily_runtime_duty_identity", source)
        self.assertNotIn("daily_runtime_database_duties.v1.json", source)
        self.assertIn("daily_runtime_database_duties.v1.json", shared)
        for name, text in (
            ("tool", source),
            ("shared identity module", shared),
        ):
            self.assertNotIn('"sc-backend-odoo-dev-db-1"', text, name)
            self.assertNotIn("/data/backups/daily_candidate", text, name)
            self.assertNotIn("FROM payment_request", text, name)

    def test_shared_identity_module_hardcodes_no_duty(self):
        # The declaration is the only owner of a duty's database, role, volume,
        # compose project, filestore scope and backup namespace. A literal in
        # the resolver would silently outrank the declaration.
        #
        # A bare lowercase token such as the legacy ``odoo`` database role is
        # an infrastructure convention shared across profiles, not a duty
        # identity, so it may legitimately appear as a constant. Everything
        # that names a specific duty (database, filter, container, volumes,
        # compose project, storage scopes, namespaced roles) must not.
        shared = (
            ROOT / "scripts/ops/daily_runtime_duty_identity.py"
        ).read_text()
        declaration = CONTINUITY._load_duties()
        self.assertTrue(declaration)
        fields = (
            ("duty", "database"),
            ("duty", "database_role"),
            ("duty", "dbfilter"),
            ("cluster", "container"),
            ("cluster", "data_volume"),
            ("cluster", "compose_project"),
            ("storage", "odoo_data_volume"),
            ("storage", "filestore_scope"),
            ("storage", "backup_namespace"),
        )
        generic = re.compile(r"[a-z]+")
        distinctive: set[str] = set()
        for duty in declaration.values():
            for section, key in fields:
                source = duty if section == "duty" else (duty.get(section) or {})
                value = source.get(key)
                if isinstance(value, str) and value and not generic.fullmatch(value):
                    distinctive.add(value)
        self.assertTrue(distinctive)
        for value in sorted(distinctive):
            self.assertNotIn(value, shared, value)

    def test_remote_bundle_ships_every_module_its_tools_import(self):
        # The remote tool tree is a explicit file list, not the whole
        # repository: a tool that imports a local module which is not shipped
        # fails on the server with ModuleNotFoundError after the local tests
        # passed. Derive the requirement from the shipped tools themselves so
        # the list cannot drift again.
        make = (ROOT / "make/daily_candidate.mk").read_text()
        recipe = make.split("daily.candidate.continuity.remote_install:", 1)[1]
        recipe = recipe.split("\n\n", 1)[0]
        shipped = set(
            re.findall(r"^\t\t(\S+) \\$", recipe, flags=re.MULTILINE)
        )
        self.assertTrue(shipped)
        ops_root = ROOT / "scripts/ops"
        required: set[str] = set()
        for path in sorted(shipped):
            if not path.endswith(".py"):
                continue
            local = ROOT / path
            self.assertTrue(local.is_file(), path)
            tree = ast.parse(local.read_text(encoding="utf-8"), filename=path)
            names: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.update(alias.name.split(".")[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names.add(node.module.split(".")[0])
            for name in names:
                sibling = f"scripts/ops/{name}.py"
                if (ops_root / f"{name}.py").is_file():
                    required.add(sibling)
        missing = sorted(required - shipped)
        self.assertEqual(missing, [], f"remote bundle misses imported modules: {missing}")

    def test_duty_recovery_entries_run_the_tool_with_the_duty_contract(self):
        # The entry must execute the tool, not the contract JSON, and it must
        # name the duty contract explicitly: the tool defaults to the demo
        # contract, so an omitted --contract would quietly capture the wrong
        # database.
        make = (ROOT / "make/daily_candidate.mk").read_text()
        self.assertIn(
            "DAILY_DUTY_RECOVERY_TOOL ?= "
            "$(DAILY_CONTINUITY_REMOTE_ROOT)/scripts/ops/"
            "daily_candidate_data_continuity.py",
            make,
        )
        self.assertIn(
            "DAILY_DUTY_RECOVERY_CONTRACT_PATH ?= "
            "$(DAILY_CONTINUITY_REMOTE_ROOT)/$(DAILY_DUTY_RECOVERY_CONTRACT)",
            make,
        )
        for target in (
            "daily.runtime.duty.recovery.remote_baseline:",
            "daily.runtime.duty.recovery.remote_backup:",
            "daily.runtime.duty.recovery.remote_validate:",
            "daily.runtime.duty.recovery.remote_restore_drill:",
        ):
            body = make.split(target, 1)[1].split("\n\n", 1)[0]
            self.assertIn('"$(DAILY_DUTY_RECOVERY_TOOL)"', body, target)
            self.assertIn(
                '--contract "$(DAILY_DUTY_RECOVERY_CONTRACT_PATH)"', body, target
            )


class FilestoreClassificationTests(unittest.TestCase):
    """The filestore guard separates bodies, GC markers and unexplained files.

    Odoo 17 writes an empty ``filestore/<db>/checklist/<store name>`` marker from
    ``_mark_for_gc`` for every written or deleted store name, so a marker is a
    maintenance artifact and not an attachment orphan. The guard may therefore
    not compare "files on disk" with "distinct store_fname"; it has to classify.
    """

    BODY_A = "ab/abcdef0123456789abcdef0123456789abcdef01"
    BODY_B = "cd/cdef0123456789abcdef0123456789abcdef0123"

    def _scan(self, files, irregular=()):
        return {
            "root": "/var/lib/odoo/filestore/sc_demo",
            "root_present": True,
            "files": [
                {"path": path, "size": size, "sha1": digest}
                for path, size, digest in files
            ],
            "irregular": [{"path": path, "kind": kind} for path, kind in irregular],
        }

    def _rows(self, *paths):
        return [(path, path.rsplit("/", 1)[-1]) for path in paths]

    def test_legal_gc_marker_is_not_an_orphan(self):
        scan = self._scan(
            [
                (self.BODY_A, 12, self.BODY_A.rsplit("/", 1)[-1]),
                ("checklist/" + self.BODY_A, 0, ""),
            ]
        )
        report = CONTINUITY._classify_filestore(scan, self._rows(self.BODY_A))
        self.assertEqual(report["referenced_body_count"], 1)
        self.assertEqual(report["maintenance_marker_count"], 1)
        self.assertEqual(report["unknown_entry_count"], 0)
        self.assertEqual(report["missing_count"], 0)
        CONTINUITY._assert_filestore_inventory(report)

    def test_non_empty_checklist_entry_cannot_escape_as_a_marker(self):
        scan = self._scan(
            [
                (self.BODY_A, 12, self.BODY_A.rsplit("/", 1)[-1]),
                ("checklist/" + self.BODY_A, 4, ""),
            ]
        )
        report = CONTINUITY._classify_filestore(scan, self._rows(self.BODY_A))
        self.assertEqual(report["maintenance_marker_count"], 0)
        self.assertEqual(report["unknown_entry_count"], 1)
        with self.assertRaisesRegex(CONTINUITY.ContinuityError, "unknown filestore entries"):
            CONTINUITY._assert_filestore_inventory(report)

    def test_checklist_entry_without_a_store_name_shape_is_unknown(self):
        for path in ("checklist/notes.txt", "checklist/xx/not-a-sha", "checklist/ab/../ab"):
            with self.subTest(path=path):
                scan = self._scan([(path, 0, "")])
                report = CONTINUITY._classify_filestore(scan, [])
                self.assertEqual(report["maintenance_marker_count"], 0, path)
                self.assertEqual(report["unknown_entry_count"], 1, path)

    def test_marker_shape_outside_the_checklist_is_unknown(self):
        scan = self._scan([(self.BODY_A, 0, "")])
        report = CONTINUITY._classify_filestore(scan, [])
        self.assertEqual(report["unknown_entry_count"], 1)
        self.assertEqual(report["maintenance_marker_count"], 0)

    def test_unreferenced_store_shaped_file_is_unknown(self):
        scan = self._scan([(self.BODY_B, 9, self.BODY_B.rsplit("/", 1)[-1])])
        report = CONTINUITY._classify_filestore(scan, self._rows(self.BODY_A))
        self.assertEqual(report["unknown_entry_count"], 1)
        self.assertEqual(report["missing_count"], 1)
        with self.assertRaisesRegex(CONTINUITY.ContinuityError, "missing"):
            CONTINUITY._assert_filestore_inventory(report)

    def test_missing_referenced_attachment_fails(self):
        scan = self._scan([])
        report = CONTINUITY._classify_filestore(scan, self._rows(self.BODY_A))
        self.assertEqual(report["missing_count"], 1)
        with self.assertRaisesRegex(CONTINUITY.ContinuityError, "missing"):
            CONTINUITY._assert_filestore_inventory(report)

    def test_corrupted_attachment_content_fails(self):
        scan = self._scan([(self.BODY_A, 12, "0" * 40)])
        report = CONTINUITY._classify_filestore(scan, self._rows(self.BODY_A))
        self.assertEqual(report["checksum_mismatch_count"], 1)
        with self.assertRaisesRegex(CONTINUITY.ContinuityError, "checksum"):
            CONTINUITY._assert_filestore_inventory(report)

    def test_store_name_that_is_not_the_content_digest_fails(self):
        # The name is the row's store_fname, but the bytes under it hash to
        # something else: the row would silently serve the wrong content.
        scan = self._scan([(self.BODY_A, 12, "1" * 40)])
        report = CONTINUITY._classify_filestore(
            scan, [(self.BODY_A, "1" * 40)]
        )
        self.assertEqual(report["checksum_mismatch_count"], 1)
        self.assertEqual(report["referenced_body_count"], 0)

    def test_non_regular_entry_is_unknown(self):
        scan = self._scan(
            [(self.BODY_A, 12, self.BODY_A.rsplit("/", 1)[-1])],
            irregular=[("ab/sneaky", "symlink")],
        )
        report = CONTINUITY._classify_filestore(scan, self._rows(self.BODY_A))
        self.assertEqual(report["unknown_entry_count"], 1)
        with self.assertRaisesRegex(CONTINUITY.ContinuityError, "unknown filestore entries"):
            CONTINUITY._assert_filestore_inventory(report)

    def test_clean_pair_is_accepted_and_digests_are_order_independent(self):
        raw = [
            (self.BODY_B, 9, self.BODY_B.rsplit("/", 1)[-1]),
            ("checklist/" + self.BODY_A, 0, ""),
            (self.BODY_A, 12, self.BODY_A.rsplit("/", 1)[-1]),
            ("checklist/" + self.BODY_B, 0, ""),
        ]
        rows = self._rows(self.BODY_A, self.BODY_B)
        report = CONTINUITY._classify_filestore(self._scan(raw), rows)
        shuffled = CONTINUITY._classify_filestore(
            self._scan(list(reversed(raw))), list(reversed(rows))
        )
        CONTINUITY._assert_filestore_inventory(report)
        self.assertEqual(report, shuffled)
        self.assertEqual(report["referenced_body_count"], 2)
        self.assertEqual(report["maintenance_marker_count"], 2)

    def test_restore_content_closure_is_not_a_count_comparison(self):
        # One body on each side, but not the same body: a count-only assertion
        # ("one referenced attachment came back") would pass and miss this.
        source = CONTINUITY._classify_filestore(
            self._scan([(self.BODY_A, 12, self.BODY_A.rsplit("/", 1)[-1])]),
            self._rows(self.BODY_A),
        )
        restored = CONTINUITY._classify_filestore(
            self._scan([(self.BODY_B, 12, self.BODY_B.rsplit("/", 1)[-1])]),
            self._rows(self.BODY_B),
        )
        self.assertEqual(restored["referenced_body_count"], source["referenced_body_count"])
        self.assertNotEqual(
            restored["referenced_body_content_digest"],
            source["referenced_body_content_digest"],
        )

if __name__ == "__main__":
    unittest.main(verbosity=2)
