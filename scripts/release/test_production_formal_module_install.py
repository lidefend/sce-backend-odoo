#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/release/production_formal_module_install.py"
SPEC = importlib.util.spec_from_file_location(
    "production_formal_module_install", SCRIPT
)
assert SPEC and SPEC.loader
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def valid_env() -> dict[str, str]:
    return {
        "ENV": "prod",
        "PROD_DANGER": "1",
        "TARGET_DB": "sc_production",
        "PRODUCTION_COMPOSE_PROJECT": "sc_production",
        "DEPLOYMENT_MODE": "FIRST_FRESH_DEPLOY",
        "CONFIRM_FORMAL_MODULE_INSTALL": "YES_INSTALL_MISSING_FORMAL_MODULES",
        "EXPECTED_RELEASE_SHA": tool.EXPECTED_SOURCE_SHA,
        "EXPECTED_IMAGE_DIGEST": tool.EXPECTED_IMAGE_DIGEST,
        "ODOO_IMAGE_REF": tool.EXPECTED_IMAGE_REFERENCE,
        "NGINX_IMAGE_REF": tool.EXPECTED_IMAGE_REFERENCE,
        "BACKUP_CONFIG_SOURCE": str(tool.BACKUP_CONFIG_PATH),
        "BACKUP_ROOT": tool.BACKUP_ROOT,
        "BACKUP_TARGET_DB": "sc_production",
        "BACKUP_DB_CONTAINER": "sc_production-db-1",
        "BACKUP_ODOO_CONTAINER": "sc_production-odoo-1",
        "BACKUP_DB_USER": "odoo",
        "BACKUP_FILESTORE_ROOT": "/opt/sce-runtime/filestore",
    }


def valid_state(*, installed_targets: tuple[str, ...] = ()) -> dict:
    formal = tool._load_product_modules()
    states = {name: "installed" for name in formal}
    for name in tool.TARGET_MODULES:
        if name not in installed_targets:
            states[name] = "uninstalled"
    manifests = {}
    for name in tool.TARGET_MODULES:
        manifests[name] = {
            "source_exists": True,
            "installable": True,
            "depends": list(tool.EXPECTED_DEPENDENCIES[name]),
            "data": list(tool.EXPECTED_DATA_FILES[name]),
            "demo": [],
            "xml_operations": [],
        }
    manifests["smart_construction_seed"]["xml_operations"] = [
        {
            "file": "data/sc_seed_dictionary_contract.xml",
            "kind": "record",
            "model": "sc.dictionary",
            "name": "",
        }
        for _index in range(5)
    ] + [
        {
            "file": "data/sc_seed_tax.xml",
            "kind": "function",
            "model": "construction.contract",
            "name": "_sc_ensure_contract_tax_seeds",
        }
    ]
    return {
        "database": "sc_production",
        "formal_modules": list(formal),
        "module_states": states,
        "pending_module_operations": 0,
        "demo_fixture_module_count": 0,
        "business_record_counts": {
            name: 0 for name in tool.BUSINESS_MODELS
        },
        "historical_data_imported": False,
        "admin_login": "admin",
        "active_admin_count": 1,
        "active_admin_is_target": True,
        "seed_enabled": "0",
        "seed_profile_configured": False,
        "seed_runtime_overrides": [],
        "target_manifests": manifests,
        "host": {
            "compose_project": "sc_production",
            "healthy_containers": list(tool.PRODUCTION_CONTAINERS),
            "volume_count": 6,
            "image_digest_match": True,
            "oci_revision_match": True,
            "container_revision_match": True,
        },
    }


class FakeOperations:
    def __init__(
        self,
        before=None,
        after=None,
        *,
        backup_error=False,
        nginx_after="same",
    ):
        self.before = before or valid_state()
        self.after = after or valid_state(installed_targets=tool.TARGET_MODULES)
        self.backup_error = backup_error
        self.nginx_after = nginx_after
        self.collect_calls = 0
        self.backup_calls = 0
        self.install_calls = []
        self.nginx_calls = 0
        self.events = []

    def collect_state(self, _formal):
        self.collect_calls += 1
        return copy.deepcopy(self.before if self.collect_calls == 1 else self.after)

    def backup(self):
        self.backup_calls += 1
        self.events.append("backup")
        if self.backup_error:
            raise tool.FormalModuleInstallError("backup failed")
        return "/var/backups/scems/production/sc_production-test"

    def install(self, modules):
        self.events.append("install")
        self.install_calls.append(tuple(modules))

    def nginx_fingerprint(self):
        self.nginx_calls += 1
        return "same" if self.nginx_calls == 1 else self.nginx_after


class InvocationGuardTests(unittest.TestCase):
    def _write_backup_config(self, directory: str, content: str) -> Path:
        path = Path(directory) / "production-backup.env"
        path.write_text(content, encoding="utf-8")
        path.chmod(0o600)
        return path

    def _valid_backup_config(self) -> str:
        return "\n".join(
            (
                f"BACKUP_ROOT={tool.BACKUP_ROOT}",
                "BACKUP_TARGET_DB=sc_production",
                "BACKUP_DB_CONTAINER=sc_production-db-1",
                "BACKUP_ODOO_CONTAINER=sc_production-odoo-1",
                "BACKUP_DB_USER=odoo",
                "BACKUP_FILESTORE_ROOT=/opt/sce-runtime/filestore",
                "",
            )
        )

    def test_fixed_backup_configuration_is_loaded_without_shell_evaluation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_backup_config(
                directory, self._valid_backup_config()
            )
            original_path = tool.BACKUP_CONFIG_PATH
            tool.BACKUP_CONFIG_PATH = path
            try:
                resolved = tool.load_backup_configuration(
                    path,
                    {"ENV": "prod"},
                    expected_uid=os.getuid(),
                    expected_gid=os.getgid(),
                )
            finally:
                tool.BACKUP_CONFIG_PATH = original_path
            self.assertEqual(resolved["BACKUP_ROOT"], tool.BACKUP_ROOT)
            self.assertEqual(resolved["BACKUP_DB_USER"], "odoo")
            self.assertEqual(resolved["BACKUP_CONFIG_SOURCE"], str(path))

    def test_versioned_backup_configuration_template_matches_fixed_contract(self):
        template = (
            ROOT / "deploy/production-backup/production-backup.env.example"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            set(
                line.split("=", 1)[0]
                for line in template.splitlines()
                if line
            ),
            set(tool.BACKUP_CONFIG_KEYS),
        )
        self.assertIn(f"BACKUP_ROOT={tool.BACKUP_ROOT}", template)
        self.assertIn("BACKUP_DB_CONTAINER=sc_production-db-1", template)
        self.assertIn("BACKUP_ODOO_CONTAINER=sc_production-odoo-1", template)

    def test_backup_configuration_rejects_process_override(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_backup_config(
                directory, self._valid_backup_config()
            )
            original_path = tool.BACKUP_CONFIG_PATH
            tool.BACKUP_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(
                    tool.FormalModuleInstallError, "override"
                ):
                    tool.load_backup_configuration(
                        path,
                        {"BACKUP_ROOT": "/tmp/override"},
                        expected_uid=os.getuid(),
                        expected_gid=os.getgid(),
                    )
            finally:
                tool.BACKUP_CONFIG_PATH = original_path

    def test_backup_configuration_rejects_unsafe_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_backup_config(
                directory, self._valid_backup_config()
            )
            path.chmod(0o640)
            original_path = tool.BACKUP_CONFIG_PATH
            tool.BACKUP_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(
                    tool.FormalModuleInstallError, "0600"
                ):
                    tool.load_backup_configuration(
                        path,
                        {},
                        expected_uid=os.getuid(),
                        expected_gid=os.getgid(),
                    )
            finally:
                tool.BACKUP_CONFIG_PATH = original_path

    def test_backup_configuration_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            target = self._write_backup_config(
                directory, self._valid_backup_config()
            )
            path = Path(directory) / "linked.env"
            path.symlink_to(target)
            original_path = tool.BACKUP_CONFIG_PATH
            tool.BACKUP_CONFIG_PATH = path
            try:
                with self.assertRaisesRegex(
                    tool.FormalModuleInstallError, "non-symlink"
                ):
                    tool.load_backup_configuration(
                        path,
                        {},
                        expected_uid=os.getuid(),
                        expected_gid=os.getgid(),
                    )
            finally:
                tool.BACKUP_CONFIG_PATH = original_path

    def test_backup_configuration_rejects_unknown_duplicate_and_missing_keys(self):
        invalid_values = (
            self._valid_backup_config() + "UNEXPECTED=value\n",
            self._valid_backup_config() + f"BACKUP_ROOT={tool.BACKUP_ROOT}\n",
            "BACKUP_ROOT=" + tool.BACKUP_ROOT + "\n",
        )
        for content in invalid_values:
            with self.subTest(content=content):
                with tempfile.TemporaryDirectory() as directory:
                    path = self._write_backup_config(directory, content)
                    original_path = tool.BACKUP_CONFIG_PATH
                    tool.BACKUP_CONFIG_PATH = path
                    try:
                        with self.assertRaises(tool.FormalModuleInstallError):
                            tool.load_backup_configuration(
                                path,
                                {},
                                expected_uid=os.getuid(),
                                expected_gid=os.getgid(),
                            )
                    finally:
                        tool.BACKUP_CONFIG_PATH = original_path

    def test_backup_configuration_rejects_identity_drift(self):
        for old, new in (
            (tool.BACKUP_ROOT, "/tmp/backup"),
            ("sc_production-db-1", "other-db-1"),
            ("sc_production", "sc_prod"),
            ("/opt/sce-runtime/filestore", "/var/lib/odoo"),
        ):
            with self.subTest(value=new):
                with tempfile.TemporaryDirectory() as directory:
                    path = self._write_backup_config(
                        directory, self._valid_backup_config().replace(old, new)
                    )
                    original_path = tool.BACKUP_CONFIG_PATH
                    tool.BACKUP_CONFIG_PATH = path
                    try:
                        with self.assertRaises(tool.FormalModuleInstallError):
                            tool.load_backup_configuration(
                                path,
                                {},
                                expected_uid=os.getuid(),
                                expected_gid=os.getgid(),
                            )
                    finally:
                        tool.BACKUP_CONFIG_PATH = original_path

    def test_missing_prod_danger_is_rejected(self):
        active = valid_env()
        active.pop("PROD_DANGER")
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.validate_invocation(active)

    def test_non_production_environment_is_rejected(self):
        active = valid_env()
        active["ENV"] = "test"
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.validate_invocation(active)

    def test_database_drift_is_rejected(self):
        active = valid_env()
        active["TARGET_DB"] = "other"
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.validate_invocation(active)

    def test_confirmation_must_be_exact(self):
        for value in ("", "yes", "YES_INSTALL_MODULES"):
            active = valid_env()
            active["CONFIRM_FORMAL_MODULE_INSTALL"] = value
            with self.assertRaises(tool.FormalModuleInstallError):
                tool.validate_invocation(active)

    def test_caller_cannot_inject_a_fourth_module(self):
        for variable in tool.CALLER_MODULE_VARIABLES:
            active = valid_env()
            active[variable] = "unexpected_module"
            with self.assertRaises(tool.FormalModuleInstallError):
                tool.validate_invocation(active)


class ModuleBoundaryTests(unittest.TestCase):
    def test_allowlist_is_exactly_three_modules(self):
        self.assertEqual(
            set(tool.TARGET_MODULES),
            {
                "sc_norm_engine",
                "smart_construction_bootstrap",
                "smart_construction_seed",
            },
        )

    def test_bootstrap_precedes_seed_by_manifest_topology(self):
        order = tool.validate_source_boundary(valid_state())
        self.assertLess(
            order.index("smart_construction_bootstrap"),
            order.index("smart_construction_seed"),
        )

    def test_already_installed_target_is_safely_skipped(self):
        before = valid_state(
            installed_targets=("smart_construction_bootstrap",)
        )
        operations = FakeOperations(before=before)
        tool.orchestrate(valid_env(), operations)
        self.assertNotIn(
            "smart_construction_bootstrap", operations.install_calls[0]
        )

    def test_unexpected_module_state_is_rejected(self):
        state = valid_state()
        state["module_states"]["sc_norm_engine"] = "to install"
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.validate_before(state, tool._load_product_modules())

    def test_pending_module_operation_is_rejected(self):
        state = valid_state()
        state["pending_module_operations"] = 1
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.validate_before(state, tool._load_product_modules())

    def test_historical_data_is_rejected(self):
        state = valid_state()
        state["historical_data_imported"] = True
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.validate_before(state, tool._load_product_modules())

    def test_business_records_are_rejected(self):
        state = valid_state()
        state["business_record_counts"]["project.project"] = 1
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.validate_before(state, tool._load_product_modules())

    def test_seed_enabled_is_rejected(self):
        state = valid_state()
        state["seed_enabled"] = "1"
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.validate_before(state, tool._load_product_modules())

    def test_dynamic_seed_override_is_rejected(self):
        state = valid_state()
        state["seed_runtime_overrides"] = ["SC_SEED_ENABLED"]
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.validate_before(state, tool._load_product_modules())

    def test_demo_or_fixture_risk_is_rejected(self):
        state = valid_state()
        state["target_manifests"]["smart_construction_seed"]["demo"] = [
            "demo/example.xml"
        ]
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.validate_before(state, tool._load_product_modules())

    def test_seed_business_data_boundary_is_exact(self):
        state = valid_state()
        state["target_manifests"]["smart_construction_seed"][
            "xml_operations"
        ][0]["model"] = "project.project"
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.validate_before(state, tool._load_product_modules())


class OrchestrationTests(unittest.TestCase):
    def test_backup_failure_causes_zero_install_calls(self):
        operations = FakeOperations(backup_error=True)
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.orchestrate(valid_env(), operations)
        self.assertEqual(operations.install_calls, [])

    def test_one_install_call_contains_only_ordered_missing_modules(self):
        operations = FakeOperations()
        result = tool.orchestrate(valid_env(), operations)
        self.assertEqual(len(operations.install_calls), 1)
        self.assertEqual(
            set(operations.install_calls[0]), set(tool.TARGET_MODULES)
        )
        self.assertEqual(result["formal_modules_installed"], 10)
        self.assertEqual(operations.events, ["backup", "install"])

    def test_postflight_requires_ten_of_ten(self):
        after = valid_state(installed_targets=tool.TARGET_MODULES)
        after["module_states"]["sc_norm_engine"] = "uninstalled"
        operations = FakeOperations(after=after)
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.orchestrate(valid_env(), operations)

    def test_postflight_rejects_pending_state(self):
        after = valid_state(installed_targets=tool.TARGET_MODULES)
        after["pending_module_operations"] = 1
        operations = FakeOperations(after=after)
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.orchestrate(valid_env(), operations)

    def test_complete_state_is_a_noop_without_backup(self):
        complete = valid_state(installed_targets=tool.TARGET_MODULES)
        operations = FakeOperations(before=complete)
        result = tool.orchestrate(valid_env(), operations)
        self.assertEqual(operations.backup_calls, 0)
        self.assertEqual(operations.install_calls, [])
        self.assertEqual(result["backup"], "NOT_REQUIRED_ALREADY_COMPLETE")

    def test_nginx_fingerprint_change_is_rejected(self):
        operations = FakeOperations(nginx_after="changed")
        with self.assertRaises(tool.FormalModuleInstallError):
            tool.orchestrate(valid_env(), operations)

    def test_static_source_forbids_broad_install_and_side_effects(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("-i all", source)
        self.assertNotIn(" -u ", source)
        self.assertNotIn(".execute(", source)
        self.assertNotIn("FORMAL_ACCEPTANCE_PASSWORD", source)
        self.assertNotIn("SC_BOOTSTRAP_ADMIN_PASSWORD", source)
        self.assertNotIn("nginx -s reload", source)
        self.assertNotIn("systemctl reload", source)
        self.assertEqual(source.count("operations.install(ordered_missing)"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
