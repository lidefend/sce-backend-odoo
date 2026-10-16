#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).with_name("daily_runtime_tenant_topology_inventory.py")
SPEC = importlib.util.spec_from_file_location(
    "daily_runtime_tenant_topology_inventory", SCRIPT
)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

SHA = "10bf72ef4bb060556bd2844598b58f9806392d34"


def database(name, *, modules=None, companies=None, registrations=None, business=None, error=None):
    entry = {
        "database": name,
        "resolved_database": name,
        "installed_modules": 10,
        "product_modules": modules or {},
        "companies": companies or [{"id": 1, "name": "Main"}],
        "registrations": registrations or [],
        "business_rows": business or {},
    }
    if error:
        entry["error"] = error
    return entry


def carrier(name="sc_demo", *, industry="17.0.0.171", registrations=None, rows=None):
    return database(
        name,
        modules={module.KERNEL_MODULE: {"installed_version": "17.0.1.1.14"},
                 module.INDUSTRY_MODULE: {"installed_version": industry}},
        registrations=registrations if registrations is not None
        else [{"company_id": 1, "data_purpose": "demo"}],
        business=rows if rows is not None
        else {module.BUSINESS_MODELS[0][0]: [{"company_id": 1, "rows": 10}]},
    )


def platform(name="sc_platform_core"):
    return database(
        name,
        modules={module.KERNEL_MODULE: {"installed_version": "17.0.1.0"}},
        registrations=[],
        business={},
    )


def payload(observation):
    return {"databases": list(observation), "observation": observation, "writes": False}


class PreflightTests(unittest.TestCase):
    def test_accepts_declared_input_shapes(self):
        self.assertTrue(module.FULL_SHA.fullmatch(SHA))
        self.assertTrue(module.SSH_HOST.fullmatch("sc-root"))
        self.assertEqual(module.parse_databases("sc_demo, sc_odoo"), ["sc_demo", "sc_odoo"])

    def test_rejects_unsafe_database_identities(self):
        for bad in ("sc_demo; rm -rf /", "sc-demo", "", "sc_demo,sc_demo"):
            with self.assertRaises(module.InventoryError):
                module.parse_databases(bad)

    def test_marker_round_trip(self):
        line = module.MARKER + '{"a": 1}'
        self.assertEqual(module.marker_payload("noise\n" + line), {"a": 1})
        self.assertIsNone(module.marker_payload("noise only"))

    def test_program_is_read_only(self):
        for forbidden in ("unlink", ".write(", "create(", "commit("):
            self.assertNotIn(forbidden, module.PROGRAM_TEMPLATE)

    def test_program_uses_the_governed_shell_entry(self):
        self.assertEqual(module.REMOTE_ROOT, "/opt/projects/repos/sce-product-odoo")
        self.assertIn("odoo.shell.exec", Path(SCRIPT).read_text(encoding="utf-8"))


class VerdictTests(unittest.TestCase):
    def test_separated_duties_pass(self):
        observation = {
            "sc_demo": carrier(),
            "sc_platform_core": platform(),
            "sc_odoo": database("sc_odoo", business={}),
        }
        verdict = module.evaluate(list(observation), payload(observation))
        self.assertTrue(verdict["passed"], [r for r in verdict["assertions"] if not r["passed"]])
        self.assertEqual(len(verdict["business_volume_carriers"]), 1)
        self.assertEqual(verdict["platform_only_databases"], ["sc_platform_core"])

    def test_platform_only_database_with_business_rows_fails(self):
        observation = {
            "sc_demo": carrier(),
            "sc_platform_core": database(
                "sc_platform_core",
                modules={module.KERNEL_MODULE: {"installed_version": "17.0.1.0"}},
                business={module.BUSINESS_MODELS[0][0]: [{"company_id": 1, "rows": 5}]},
            ),
        }
        verdict = module.evaluate(list(observation), payload(observation))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("platform_only_database_carries_no_business_rows", failed)

    def test_unregistered_owning_company_fails_closed(self):
        observation = {
            "sc_demo": carrier(registrations=[]),
            "sc_platform_core": platform(),
        }
        verdict = module.evaluate(list(observation), payload(observation))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("every_business_owning_company_is_registered", failed)

    def test_unowned_rows_are_reported_but_do_not_excuse_registration(self):
        observation = {
            "sc_demo": carrier(
                registrations=[{"company_id": 1, "data_purpose": "demo"}],
                rows={module.BUSINESS_MODELS[1][0]: [{"company_id": None, "rows": 12194}]},
            ),
            "sc_platform_core": platform(),
        }
        verdict = module.evaluate(list(observation), payload(observation))
        self.assertTrue(verdict["passed"], [r for r in verdict["assertions"] if not r["passed"]])
        carriers = verdict["business_volume_carriers"]
        self.assertEqual(carriers[0]["by_owner"], {"unowned": 12194})

    def test_two_volume_carriers_fail_closed(self):
        observation = {
            "sc_demo": carrier(),
            "sc_odoo": carrier("sc_odoo"),
            "sc_platform_core": platform(),
        }
        verdict = module.evaluate(list(observation), payload(observation))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("single_business_volume_carrier", failed)

    def test_industry_revision_drift_fails_closed(self):
        observation = {
            "sc_demo": carrier(),
            "sc_odoo": carrier("sc_odoo", industry="17.0.0.160"),
            "sc_platform_core": platform(),
        }
        verdict = module.evaluate(list(observation), payload(observation))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("industry_product_line_revision_aligned", failed)

    def test_unreachable_database_fails_closed(self):
        observation = {
            "sc_demo": carrier(),
            "sc_platform_core": platform(),
            "sc_odoo": database("sc_odoo", error="OperationalError:boom"),
        }
        verdict = module.evaluate(list(observation), payload(observation))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("every_declared_database_reachable", failed)

    def test_writes_are_reported(self):
        observation = {"sc_demo": carrier(), "sc_platform_core": platform()}
        verdict = module.evaluate(list(observation), payload({**observation}) | {"writes": True})
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("inventory_is_read_only", failed)


class TenantTopologyDutyBindingTests(unittest.TestCase):
    """A database *name* stops being a target identity once two carriers share it.

    The refusal is read from the shipped declaration, not from a stub: it now
    names the rebuilt demo duty and the preserved historic source with the same
    ``sc_demo``, so an entry that receives only ``--database`` would otherwise
    have to guess which carrier it is measuring.
    """

    instances = Path(__file__).with_name("synthetic_duty_instances.sample.json")

    def reader(self, _path: str) -> str:
        return self.instances.read_text(encoding="utf-8")

    def options(self, **overrides):
        options = mock.Mock()
        options.duty = ""
        options.database = "sc_demo"
        options.ssh_host = "sc-root"
        for key, value in overrides.items():
            setattr(options, key, value)
        return options

    def test_a_bare_database_name_no_longer_binds_a_carrier(self) -> None:
        with self.assertRaisesRegex(module.InventoryError, "DUTY_IDENTITY_DATABASE_AMBIGUOUS:sc_demo"):
            module.bind_target(self.options(), instances_reader=self.reader)

    def test_naming_the_duty_binds_the_rebuilt_demo_carrier(self) -> None:
        binding = module.bind_target(
            self.options(duty="demo"), instances_reader=self.reader
        )
        self.assertEqual(binding["database"], "sc_demo")
        self.assertEqual(binding["database_role"], "sc_demo_app")
        self.assertEqual(binding["compose_project"], "sc-demo-dev")
        self.assertEqual(binding["database_container"], "sc-demo-dev-db-1")
        self.assertEqual(binding["database_volume"], "sc_demo_db_data")
        self.assertEqual(binding["data_purpose"], "demo")


if __name__ == "__main__":
    unittest.main()
