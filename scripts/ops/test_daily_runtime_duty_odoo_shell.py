#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "daily_runtime_duty_odoo_shell", ROOT / "scripts/ops/daily_runtime_duty_odoo_shell.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)

DOCUMENT = {
    "duties": [
        {
            "duty": "demo",
            "database": "sc_demo",
            "cluster": {"compose_project": "sc-demo-dev"},
            "stack": {"services": ["db", "redis", "odoo", "nginx"]},
        }
    ]
}


class DutyOdooShellTest(unittest.TestCase):
    def test_duty_resolution_and_container_binding(self):
        duty = MODULE.resolve_duty(DOCUMENT, "demo")
        self.assertEqual(duty["database"], "sc_demo")
        self.assertEqual(MODULE.odoo_container(duty), "sc-demo-dev-odoo-1")

    def test_unknown_duty_is_refused(self):
        with self.assertRaises(MODULE.DutyShellError):
            MODULE.resolve_duty(DOCUMENT, "missing")

    def test_database_mismatch_is_refused_by_main(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            declaration = Path(folder) / "duties.json"
            declaration.write_text(__import__("json").dumps(DOCUMENT), encoding="utf-8")
            code = MODULE.main(
                ["--duty", "demo", "--database", "sc_other", "--declaration", str(declaration)]
            )
        self.assertEqual(code, 2)

    def test_command_carries_duty_database_and_forwarded_environment(self):
        duty = MODULE.resolve_duty(DOCUMENT, "demo")
        command = MODULE.build_command(
            duty,
            "sc-demo-dev-odoo-1",
            odoo_config="/var/lib/odoo/odoo.conf",
            environment={"PRODUCT_MENU_CATALOG_PRODUCT_KEYS": "construction.standard"},
        )
        self.assertEqual(command[:4], ["docker", "exec", "-i", "-e"])
        self.assertIn("PRODUCT_MENU_CATALOG_PRODUCT_KEYS=construction.standard", command)
        self.assertIn("sc-demo-dev-odoo-1", command)
        self.assertIn("odoo", command)
        self.assertIn("shell", command)
        self.assertEqual(command[command.index("-d") + 1], "sc_demo")

    def test_restart_waits_for_health(self):
        with mock.patch.object(MODULE.subprocess, "run") as run, mock.patch.object(
            MODULE.time, "sleep"
        ):
            run.side_effect = [
                mock.Mock(returncode=0, stdout="sc-demo-dev-odoo-1\n", stderr=""),
                mock.Mock(returncode=0, stdout="starting\n", stderr=""),
                mock.Mock(returncode=0, stdout="healthy\n", stderr=""),
            ]
            self.assertEqual(MODULE.restart_container("sc-demo-dev-odoo-1"), "healthy")
        self.assertEqual(run.call_args_list[0].args[0], ["docker", "restart", "sc-demo-dev-odoo-1"])

    def test_restart_refuses_unhealthy_container(self):
        with mock.patch.object(MODULE.subprocess, "run") as run, mock.patch.object(
            MODULE.time, "sleep"
        ):
            run.side_effect = [
                mock.Mock(returncode=0, stdout="sc-demo-dev-odoo-1\n", stderr=""),
                mock.Mock(returncode=0, stdout="unhealthy\n", stderr=""),
            ]
            with self.assertRaises(MODULE.DutyShellError):
                MODULE.restart_container("sc-demo-dev-odoo-1")


if __name__ == "__main__":
    unittest.main()
