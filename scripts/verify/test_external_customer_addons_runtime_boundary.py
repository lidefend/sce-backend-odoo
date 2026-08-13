from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ExternalCustomerAddonsRuntimeBoundaryTests(unittest.TestCase):
    def _make_compose_files(self, *assignments: str) -> str:
        result = subprocess.run(
            [
                "make",
                "--no-print-directory",
                "-s",
                "ENV=guard-test-no-env-file",
                *assignments,
                "env.print.compose_files",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_make_default_without_customer_root_remains_base_only(self):
        self.assertEqual(self._make_compose_files("SC_CUSTOMER_ADDONS_ROOT="), "-f docker-compose.yml")

    def test_make_default_with_customer_root_includes_customer_overlay(self):
        self.assertEqual(
            self._make_compose_files("SC_CUSTOMER_ADDONS_ROOT=/tmp/customer-addons"),
            "-f docker-compose.yml -f docker-compose.customer-addons.yml",
        )

    def test_explicit_compose_files_override_wins(self):
        self.assertEqual(
            self._make_compose_files(
                "SC_CUSTOMER_ADDONS_ROOT=/tmp/customer-addons",
                "COMPOSE_FILES=-f explicit.yml",
            ),
            "-f explicit.yml",
        )

    def test_live_customer_guard_is_only_bound_to_daily_runtime_preflight(self):
        text = (ROOT / "make/guards.mk").read_text(encoding="utf-8")
        invocations = [
            line.strip()
            for line in text.splitlines()
            if "verify.daily_dev.customer_addons.runtime" in line
            and not line.startswith(".PHONY:")
            and not line.startswith("verify.daily_dev.customer_addons.runtime:")
        ]
        self.assertEqual(
            invocations,
            ["@$(MAKE) --no-print-directory verify.daily_dev.customer_addons.runtime"],
        )

    def test_compose_override_is_opt_in(self):
        text = (ROOT / "scripts/common/compose.sh").read_text(encoding="utf-8")
        condition = 'if [[ -n "${SC_CUSTOMER_ADDONS_ROOT:-}" ]]; then'
        override = 'docker-compose.customer-addons.yml'
        self.assertIn(condition, text)
        self.assertIn(override, text)
        self.assertLess(text.index(condition), text.index(override))

    def test_module_operations_do_not_require_customer_mount_for_product(self):
        base_path = "/usr/lib/python3/dist-packages/odoo/addons,/mnt/source-addons,$ADDONS_EXTERNAL_MOUNT"
        for relative in ("scripts/mod/install.sh", "scripts/mod/upgrade.sh"):
            with self.subTest(script=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn(f'ODOO_ADDONS_PATH="{base_path}"', text)
                self.assertNotIn("/mnt/extra-addons", text)
                self.assertIn('if [[ -n "${SC_CUSTOMER_ADDONS_ROOT:-}" ]]; then', text)
                self.assertIn('ODOO_ADDONS_PATH="${ODOO_ADDONS_PATH},/mnt/customer-addons"', text)
                self.assertIn('--addons-path="$ODOO_ADDONS_PATH"', text)

    def test_customer_rename_confirmation_can_reach_odoo_shell(self):
        text = (ROOT / "scripts/ops/odoo_shell_exec.sh").read_text(encoding="utf-8")
        self.assertIn("SC_CONFIRM_*", text)

    def test_odoo_shell_uses_rendered_production_config(self):
        text = (ROOT / "scripts/ops/odoo_shell_exec.sh").read_text(encoding="utf-8")
        self.assertIn('if [[ "${ENV:-}" == "prod" ]]', text)
        self.assertIn('ODOO_SHELL_CONFIG="/opt/sce-runtime/config/odoo.conf"', text)
        self.assertEqual(text.count('-c "$ODOO_SHELL_CONFIG"'), 2)

    def test_p0_defaults_match_product_runtime_fallbacks(self):
        text = (ROOT / "scripts/verify/p0_base.sh").read_text(encoding="utf-8")
        self.assertIn("key='sc.login.custom_enabled'),'1'", text)
        self.assertIn("key='sc.login.env'),'prod'", text)


if __name__ == "__main__":
    unittest.main()
