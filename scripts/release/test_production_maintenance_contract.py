#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import production_maintenance_config as target


ROOT = Path(__file__).resolve().parents[2]
GENERIC_MODULE_PATTERN = "sce_customer_<tenant_key>"


class MaintenanceConfigTest(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, dict[str, str], Path]:
        config = root / "odoo.conf"
        customer = root / "customer" / "sce_customer_tenant_alpha"
        customer.mkdir(parents=True)
        (customer / "__manifest__.py").write_text("{}")
        config.write_text(
            "\n".join(
                (
                    "[options]",
                    "db_host = db",
                    "db_port = 5432",
                    "db_name = sc_production",
                    "dbfilter = ^sc_production$",
                    "list_db = False",
                    "without_demo = True",
                    "data_dir = /opt/sce-runtime",
                    "addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/product-addons,/mnt/customer-addons",
                )
            )
        )
        env = {
            "TARGET_DB": "sc_production",
            "PLATFORM_RELEASE_DB": "sc_production",
            "SC_TENANT_PAYLOAD_TENANT_KEY": "tenant_alpha",
            "SC_PRODUCTION_CUSTOMER_MODULES": "sce_customer_tenant_alpha",
            "SC_MAINTENANCE_HTTP_DISABLED": "1",
        }
        return config, env, customer

    def validate_fixture(self, config: Path, env: dict[str, str], customer: Path):
        with (
            patch.object(target, "EXPECTED_CONFIG", config),
            patch.object(target, "CUSTOMER_ADDONS", customer.parent),
        ):
            return target.validate(config, env)

    def test_valid_maintenance_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, env, customer = self.fixture(Path(temporary))
            self.assertEqual(self.validate_fixture(config, env, customer)["db_name"], "sc_production")

    def test_wrong_database_tenant_and_http_are_rejected(self):
        for key, value, code in (
            ("TARGET_DB", "wrong", "DATABASE"),
            ("PLATFORM_RELEASE_DB", "wrong", "PLATFORM"),
            ("SC_TENANT_PAYLOAD_TENANT_KEY", "Wrong!", "TENANT"),
            ("SC_MAINTENANCE_HTTP_DISABLED", "0", "HTTP"),
        ):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temporary:
                config, env, customer = self.fixture(Path(temporary))
                env[key] = value
                with self.assertRaisesRegex(target.MaintenanceConfigError, code):
                    self.validate_fixture(config, env, customer)

    def test_missing_customer_and_undeclared_history_module_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, env, customer = self.fixture(Path(temporary))
            customer.rename(customer.with_name("missing"))
            with self.assertRaisesRegex(target.MaintenanceConfigError, "CUSTOMER_MODULE_MISSING"):
                self.validate_fixture(config, env, customer)
        with tempfile.TemporaryDirectory() as temporary:
            config, env, customer = self.fixture(Path(temporary))
            legacy = customer.parent / "sce_customer_tenant_alpha_legacy"
            legacy.mkdir()
            (legacy / "__manifest__.py").write_text("{}")
            with self.assertRaisesRegex(target.MaintenanceConfigError, "MODULE_SET"):
                self.validate_fixture(config, env, customer)

    def test_declared_tenant_history_module_is_allowed(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, env, customer = self.fixture(Path(temporary))
            history = customer.parent / "sce_customer_tenant_alpha_legacy"
            history.mkdir()
            (history / "__manifest__.py").write_text("{}")
            env["SC_PRODUCTION_CUSTOMER_MODULES"] += ",sce_customer_tenant_alpha_legacy"
            self.assertEqual(
                self.validate_fixture(config, env, customer)["db_name"],
                "sc_production",
            )

    def test_incomplete_addons_and_legacy_data_dir_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, env, customer = self.fixture(Path(temporary))
            config.write_text(config.read_text().replace(",/mnt/customer-addons", ""))
            with self.assertRaisesRegex(target.MaintenanceConfigError, "ADDONS"):
                self.validate_fixture(config, env, customer)
        with tempfile.TemporaryDirectory() as temporary:
            config, env, customer = self.fixture(Path(temporary))
            config.write_text(config.read_text().replace("/opt/sce-runtime", "/data/odoo/legacy_attachments"))
            with self.assertRaisesRegex(target.MaintenanceConfigError, "DATA_DIR"):
                self.validate_fixture(config, env, customer)

    def test_entrypoints_share_same_container_config_chain(self):
        maintenance = (ROOT / "scripts/release/production_maintenance.sh").read_text()
        operator = (ROOT / "scripts/release/run_production_operator_grant.sh").read_text()
        payload = (ROOT / "scripts/release/run_production_tenant_payload.sh").read_text()
        makefile = (ROOT / "make/release.mk").read_text()
        self.assertIn('CONF="/opt/sce-runtime/config/odoo.conf"', maintenance)
        self.assertLess(maintenance.index("render_odoo_conf.py"), maintenance.index("production_maintenance_config.py"))
        self.assertLess(maintenance.index("production_maintenance_config.py"), maintenance.index("exec odoo shell"))
        self.assertIn("--no-http", maintenance)
        self.assertNotIn("/var/lib/odoo/odoo.conf", operator + payload)
        self.assertIn("/usr/local/bin/production-maintenance", operator)
        self.assertIn("/usr/local/bin/production-maintenance", payload)
        self.assertIn("run_production_operator_grant.sh", makefile)

    def test_customer_runtime_mounts_external_history_read_only(self):
        compose = (ROOT / "docker-compose.production-customer.yml").read_text()
        makefile = (ROOT / "make/release.mk").read_text()
        policy = (ROOT / "docs/ops/prod_command_policy.md").read_text()
        self.assertIn("SC_LEGACY_FILE_ROOTS: /mnt/legacy-files", compose)
        self.assertIn(":/mnt/legacy-files:ro", compose)
        self.assertIn("release.production.customer_runtime.activate", makefile)
        self.assertIn("YES_ACTIVATE_SIGNED_CUSTOMER_RUNTIME", makefile)
        self.assertIn("release.production.customer_runtime.activate", policy)

    def test_payload_runner_mounts_only_immutable_maintenance_validator(self):
        source = (ROOT / "scripts/release/run_production_tenant_payload.sh").read_text()
        compose = (ROOT / "docker-compose.tenant-payload.yml").read_text()
        self.assertIn("SC_PRODUCTION_MAINTENANCE_CONFIG_OVERRIDE", source)
        self.assertIn("/opt/sce/deployment-tools/", source)
        self.assertIn("DEPLOYMENT_TOOL_SHA", source)
        self.assertIn("SC_PRODUCTION_MAINTENANCE_CONFIG_OVERRIDE", compose)
        self.assertIn("/usr/local/bin/production_maintenance_config.py:ro", compose)

    def test_operator_contract_is_external_identity_and_single_group_only(self):
        provision = (ROOT / "scripts/tenant_payload/provision_operator.py").read_text()
        self.assertIn('identity_type != "external_xmlid"', provision)
        self.assertIn("env.ref(identity_key", provision)
        self.assertIn("SC_TENANT_PAYLOAD_DIRECT_GRANT_TARGETS", provision)
        self.assertIn("TPV1_IMPORT_OPERATOR_TRANSITIVE_CLOSURE_DRIFT", provision)
        self.assertIn("TPV1_IMPORT_OPERATOR_DATA_OPERATOR_FORBIDDEN", provision)
        self.assertIn("grant_scope_version != 3", provision)
        self.assertNotIn('target_group_xmlid = _required(', provision)
        self.assertIn('"construction.standard"', provision)
        self.assertIn("SC_PRODUCTION_CUSTOMER_MODULES", provision)
        self.assertIn("user_state_after != user_state_before", provision)
        self.assertIn("after_groups - before_groups", provision)
        self.assertNotIn('search([("login"', provision)
        self.assertNotIn("CREATE_OPERATOR", provision)

    def test_acceptance_tool_reinstall_consumes_archive_before_idempotent_exit(self):
        makefile = (ROOT / "make/release.mk").read_text()
        install = makefile.split(
            "production.acceptance.backup.remote_install:", 1
        )[1].split("production.acceptance.backup.remote_sync:", 1)[0]
        self.assertIn("if test -d \"$$final\"; then tar -tf - >/dev/null", install)


if __name__ == "__main__":
    unittest.main()
