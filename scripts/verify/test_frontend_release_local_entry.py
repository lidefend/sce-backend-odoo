#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class FrontendReleaseLocalEntryTest(unittest.TestCase):
    def test_cached_restore_is_offline_frozen_and_script_free(self) -> None:
        source = (ROOT / "scripts/dev/frontend_cached_dependencies_restore.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("--offline --frozen-lockfile --ignore-scripts", source)
        self.assertIn('sha256sum "$lockfile"', source)
        self.assertIn("frontend/node_modules/.pnpm", source)
        self.assertIn("frontend/apps/web/node_modules/.bin/eslint", source)

    def test_local_release_entry_orders_cache_preflight_and_real_audit(self) -> None:
        source = (ROOT / "make/frontend.mk").read_text(encoding="utf-8")
        block = source.split("verify.frontend.release.local:", 1)[1].split("\n\n", 1)[0]
        self.assertIn("fe.install.cached", block)
        self.assertLess(block.index("release-preflight"), block.index("fe.install.cached"))
        self.assertIn("frontend_acceptance_runtime.sh release-audit", block)
        runtime = (ROOT / "scripts/dev/frontend_acceptance_runtime.sh").read_text(
            encoding="utf-8"
        )
        audit = runtime.split("release-audit)", 1)[1].split(";;", 1)[0]
        self.assertLess(audit.index("preflight"), audit.index("verify.frontend.release.audit"))
        self.assertIn("frontend_acceptance_make_identity.sh", audit)
        self.assertIn("frontend_acceptance_make verify.frontend.release.audit", audit)
        release_preflight = runtime.split("release-preflight)", 1)[1].split(";;", 1)[0]
        self.assertIn("frontend lifecycle is active owner=", release_preflight)
        self.assertIn("untracked frontend listener", release_preflight)

    def test_nested_database_make_calls_keep_managed_project_identity(self) -> None:
        source = (ROOT / "scripts/test/frontend_acceptance_db_ensure.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("frontend_acceptance_make_identity.sh", source)
        self.assertIn("frontend_acceptance_make db.create", source)
        self.assertIn("frontend_acceptance_make mod.install", source)
        adapter = (ROOT / "scripts/common/frontend_acceptance_make_identity.sh").read_text(
            encoding="utf-8"
        )
        required = (
            '"PROJECT=$COMPOSE_PROJECT_NAME"',
            '"COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME"',
            '"ENV_FILE=$ENV_FILE"',
            '"DB_USER=$DB_USER"',
            '"DB_PASSWORD=$DB_PASSWORD"',
            '"DB_NAME=$DB_NAME"',
            '"ODOO_DB=$ODOO_DB"',
            '"ODOO_DBFILTER=$ODOO_DBFILTER"',
            '"DB_DATA=$DB_DATA"',
            '"REDIS_DATA=$REDIS_DATA"',
            '"ODOO_DATA=$ODOO_DATA"',
        )
        for item in required:
            self.assertIn(item, adapter)
        self.assertNotIn("make --no-print-directory -e", adapter)

    def test_browser_login_failure_is_fail_fast_and_secret_free(self) -> None:
        source = (
            ROOT / "scripts/verify/frontend_delivery_hardening_browser.mjs"
        ).read_text(encoding="utf-8")
        login = source.split("async function login(", 1)[1].split(
            "async function logout(", 1
        )[0]
        self.assertIn("page.waitForResponse", login)
        self.assertIn("login intent rejected http=", login)
        self.assertIn("error_code=", login)
        self.assertNotIn("postData()", login.split("login intent rejected", 1)[1])
        self.assertNotIn("PASSWORD", login.split("login intent rejected", 1)[1])


if __name__ == "__main__":
    unittest.main()
