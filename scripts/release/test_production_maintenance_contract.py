#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import production_maintenance_config as target


ROOT = Path(__file__).resolve().parents[2]


class MaintenanceConfigTest(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, dict[str, str], Path]:
        config = root / "odoo.conf"
        customer = root / "customer" / "customer_module_alpha"
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
            "SC_PRODUCTION_CUSTOMER_MODULES": "customer_module_alpha",
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

    def test_missing_customer_and_legacy_customer_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            config, env, customer = self.fixture(Path(temporary))
            customer.rename(customer.with_name("missing"))
            with self.assertRaisesRegex(target.MaintenanceConfigError, "CUSTOMER_MODULE_MISSING"):
                self.validate_fixture(config, env, customer)
        with tempfile.TemporaryDirectory() as temporary:
            config, env, customer = self.fixture(Path(temporary))
            legacy = customer.parent / "customer_module_alpha_legacy"
            legacy.mkdir()
            (legacy / "__manifest__.py").write_text("{}")
            with self.assertRaisesRegex(target.MaintenanceConfigError, "MODULE_SET"):
                self.validate_fixture(config, env, customer)

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

    def test_operator_contract_is_external_identity_and_single_group_only(self):
        provision = (ROOT / "scripts/tenant_payload/provision_operator.py").read_text()
        self.assertIn('identity_type != "external_xmlid"', provision)
        self.assertIn("env.ref(identity_key", provision)
        self.assertIn("env.ref(target_group_xmlid", provision)
        self.assertIn('"construction.standard"', provision)
        self.assertIn("SC_PRODUCTION_CUSTOMER_MODULES", provision)
        self.assertIn("user_state_after != user_state_before", provision)
        self.assertIn("after_groups - before_groups", provision)
        self.assertNotIn('search([("login"', provision)
        self.assertNotIn("CREATE_OPERATOR", provision)


if __name__ == "__main__":
    unittest.main()
