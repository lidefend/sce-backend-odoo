#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
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
        self.assertIn("confirm.frontend.release.audit", block.splitlines()[0])
        self.assertIn("fe.install.cached", block)
        self.assertLess(block.index("release-preflight"), block.index("fe.install.cached"))
        self.assertIn("frontend_acceptance_operation_entry.sh release-audit", block)
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

    def test_local_release_entry_requires_explicit_frozen_lane_confirmation(self) -> None:
        source = (ROOT / "make/frontend.mk").read_text(encoding="utf-8")
        confirmation = source.split("confirm.frontend.release.audit:", 1)[1].split(
            "verify.frontend.release.local:", 1
        )[0]
        self.assertIn("CONFIRM_FRONTEND_RELEASE_AUDIT", confirmation)
        self.assertIn("RUN_FROZEN_FRONTEND_RELEASE_AUDIT", confirmation)
        self.assertIn("not a daily-development target", confirmation)

    def test_direct_runtime_is_denied_before_any_mutator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "docker-called"
            fake_docker = root / "docker"
            fake_docker.write_text(
                f"#!/bin/sh\ntouch '{marker}'\nexit 0\n", encoding="utf-8"
            )
            fake_docker.chmod(0o755)
            environment = dict(os.environ)
            environment.pop("SC_FRONTEND_ACCEPTANCE_RUNTIME_ENTRY", None)
            environment["PATH"] = f"{root}:{environment['PATH']}"
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/dev/frontend_acceptance_runtime.sh"), "db-ensure"],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("governed frontend acceptance Make target", result.stderr)
            self.assertFalse(marker.exists())

    def test_empty_fixture_password_is_denied_before_lock_side_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            isolated_root = Path(temporary)
            environment = dict(os.environ)
            environment.update(
                {
                    "ROOT_DIR": str(isolated_root),
                    "SC_ACCEPTANCE_FIXTURE_PASSWORD": "",
                }
            )
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/test/frontend_productization_fixture.sh")],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 24)
            self.assertFalse((isolated_root / ".runtime").exists())

    def test_collection_lifecycle_reuses_canonical_governed_targets(self) -> None:
        source = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        expected = {
            "backend.collection.acceptance.up": "backend.acceptance.up",
            "backend.collection.acceptance.down": "backend.acceptance.down",
            "frontend.collection.acceptance.up": "frontend.acceptance.up",
            "frontend.collection.acceptance.down": "frontend.acceptance.down",
        }
        for target, canonical in expected.items():
            self.assertIn(f"{target}: {canonical}", source)
        self.assertNotIn("BACKEND_ACCEPTANCE_PORT=18102", source)
        self.assertNotIn("FRONTEND_ACCEPTANCE_PORT=5192", source)
        browser = (
            ROOT / "scripts/verify/collection_view_semantics_browser.mjs"
        ).read_text(encoding="utf-8")
        self.assertIn("http://127.0.0.1:5175", browser)
        self.assertNotIn("http://127.0.0.1:5192", browser)

    def test_nested_database_make_calls_keep_managed_project_identity(self) -> None:
        source = (ROOT / "scripts/test/frontend_acceptance_db_ensure.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("frontend_acceptance_make_identity.sh", source)
        self.assertIn("frontend_acceptance_make db.create", source)
        self.assertIn("frontend_acceptance_make mod.install", source)
        smart_core_upgrade = source.index(
            "frontend_acceptance_make mod.upgrade \\\n  MODULE=smart_core"
        )
        construction_upgrade = source.index(
            "frontend_acceptance_make mod.upgrade \\\n  MODULE=smart_construction_core"
        )
        fixture_probe = source.index("DB_NAME=\"$DB_NAME\" bash scripts/ops/odoo_shell_exec.sh")
        self.assertLess(smart_core_upgrade, construction_upgrade)
        self.assertLess(construction_upgrade, fixture_probe)
        self.assertIn("CODEX_MODULES=smart_core,smart_construction_core", source)
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
            '"ODOO_DB=$DB_NAME"',
            '"ODOO_DBFILTER=$ODOO_DBFILTER"',
            '"DB_DATA=$DB_DATA"',
            '"REDIS_DATA=$REDIS_DATA"',
            '"ODOO_DATA=$ODOO_DATA"',
            '"LIST_DB=false"',
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

    def test_release_probes_fixture_and_http_credentials_before_frontend(self) -> None:
        fixture = (ROOT / "scripts/test/frontend_productization_fixture.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('env["res.users"].sudo().authenticate(', fixture)
        self.assertIn("[acceptance.frontend.fixture.auth] PASS", fixture)
        self.assertNotIn("print(os.environ", fixture)

        source = (ROOT / "make/runtime_ops.mk").read_text(encoding="utf-8")
        for target in (
            "verify.frontend.page_identity.browser:",
            "verify.frontend.delivery_hardening.release.browser:",
        ):
            block = source.rsplit(target, 1)[1].split("\n\n", 1)[0]
            backend = block.index("backend.acceptance.up")
            login_probe = block.index("frontend_acceptance_login_probe.py")
            frontend = block.index("frontend.acceptance.up")
            cleanup = block.index("trap '")
            self.assertLess(cleanup, backend, target)
            self.assertLess(backend, login_probe, target)
            self.assertLess(login_probe, frontend, target)

    def test_ci_starts_http_carrier_after_install_and_stops_after_first_browser_failure(self) -> None:
        operation = (
            ROOT / "scripts/dev/frontend_acceptance_operation_entry.sh"
        ).read_text(encoding="utf-8")
        db_ensure = operation.split("  db-ensure)", 1)[1].split("    ;;", 1)[0]
        infrastructure = db_ensure.index("compose_dev up -d --wait db redis")
        carrier = db_ensure.index("compose_dev create odoo", infrastructure)
        install = db_ensure.index("frontend_acceptance_db_ensure.sh")
        pre_restart_identity = db_ensure.index(
            'validate_frozen_frontend_release_ci_resources "$ROOT_DIR" required',
            install,
        )
        healthy = db_ensure.index("compose_dev up -d --wait odoo", install)
        final_identity = db_ensure.index(
            'validate_frozen_frontend_release_ci_resources "$ROOT_DIR" required',
            healthy,
        )
        self.assertLess(infrastructure, carrier)
        self.assertLess(carrier, install)
        self.assertLess(install, pre_restart_identity)
        self.assertLess(pre_restart_identity, healthy)
        self.assertLess(healthy, final_identity)
        self.assertNotIn("compose_dev restart odoo", db_ensure)

        runtime = (ROOT / "make/runtime_ops.mk").read_text(encoding="utf-8")
        audit = runtime.split("verify.frontend.release.audit:", 1)[1].split("\n\n", 1)[0]
        page = audit.index("verify.frontend.page_identity.browser")
        second_gate = audit.index('if [ "$$status" -eq 0 ]', page)
        delivery = audit.index("verify.frontend.delivery_hardening.release.browser")
        self.assertLess(page, second_gate)
        self.assertLess(second_gate, delivery)

    def test_make_adapter_derives_aliases_and_rejects_external_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            capture = root / "make-args"
            fake_make = root / "make"
            fake_make.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$CAPTURE\"\n",
                encoding="utf-8",
            )
            fake_make.chmod(0o755)
            managed = {
                "COMPOSE_PROJECT_NAME": "sc-fe-release-123-1",
                "ENV_FILE": str(root / "acceptance.env"),
                "DB_USER": "odoo",
                "DB_PASSWORD": "secret",
                "DB_NAME": "sc_frontend_acceptance",
                "ODOO_DBFILTER": "^sc_frontend_acceptance$",
                "ODOO_PORT": "18082",
                "DB_DATA": "sc-fe-release-123-1-db-data",
                "REDIS_DATA": "sc-fe-release-123-1-redis-data",
                "ODOO_DATA": "sc-fe-release-123-1-odoo-data",
                "SC_ENVIRONMENT": "acceptance",
                "SC_ALLOW_DEMO_DATA": "1",
                "CAPTURE": str(capture),
                "PATH": f"{root}:{os.environ['PATH']}",
            }
            command = (
                f'source "{ROOT / "scripts/common/frontend_acceptance_make_identity.sh"}"; '
                "frontend_acceptance_make db.create; "
                "frontend_acceptance_make mod.install MODULE=smart_core"
            )
            clean_environment = dict(os.environ)
            clean_environment.pop("ODOO_DB", None)
            clean_environment.pop("LIST_DB", None)
            result = subprocess.run(
                ["/bin/bash", "-c", command], env={**clean_environment, **managed},
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = capture.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(calls), 2)
            for call in calls:
                self.assertIn("PROJECT=sc-fe-release-123-1", call)
                self.assertIn("DB_NAME=sc_frontend_acceptance", call)
                self.assertIn("ODOO_DB=sc_frontend_acceptance", call)
                self.assertIn("LIST_DB=false", call)
                self.assertIn("DB_DATA=sc-fe-release-123-1-db-data", call)
                self.assertIn("REDIS_DATA=sc-fe-release-123-1-redis-data", call)
                self.assertIn("ODOO_DATA=sc-fe-release-123-1-odoo-data", call)

            for drift in ({"ODOO_DB": "foreign"}, {"LIST_DB": "0"}):
                capture.unlink(missing_ok=True)
                rejected = subprocess.run(
                    ["/bin/bash", "-c", command],
                    env={**clean_environment, **managed, **drift}, text=True, capture_output=True,
                )
                self.assertEqual(rejected.returncode, 2, rejected.stderr)
                self.assertFalse(capture.exists())


if __name__ == "__main__":
    unittest.main()
