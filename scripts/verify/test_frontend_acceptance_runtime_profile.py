#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/dev/frontend_acceptance_runtime_profile.py"
SPEC = importlib.util.spec_from_file_location("acceptance_runtime_profile", MODULE_PATH)
assert SPEC and SPEC.loader
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)


class AcceptanceRuntimeProfileTest(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(
            (ROOT / "config/frontend/acceptance_environments_v1.json").read_text(encoding="utf-8")
        )

    def resolve_policy(self, policy):
        with tempfile.TemporaryDirectory() as directory:
            policy_path = Path(directory) / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            with mock.patch.object(PROFILE, "POLICY", policy_path), mock.patch.object(
                PROFILE, "_primary_worktree", return_value=ROOT
            ):
                return PROFILE.resolve("local")

    def test_resolves_complete_locked_identity(self):
        values = self.resolve_policy(self.policy)
        self.assertEqual(values["DB_NAME"], "sc_frontend_acceptance")
        self.assertEqual(values["ODOO_DBFILTER"], "^sc_frontend_acceptance$")
        self.assertEqual(values["DB_DATA"], "sc_fe_r2_p1_01_db")
        self.assertEqual(values["SC_ACCEPTANCE_CREDENTIAL_CONTAINER"], "sc-fe-r2-p1-01-odoo-1")
        self.assertEqual(values["BACKEND_ACCEPTANCE_PORT"], "18082")
        self.assertEqual(values["FRONTEND_ACCEPTANCE_PORT"], "5175")

    def test_rejects_database_filter_drift(self):
        self.policy["profiles"]["local"]["managed_runtime"]["database_filter"] = "^sc_demo$"
        with self.assertRaisesRegex(ValueError, "database_filter"):
            self.resolve_policy(self.policy)

    def test_rejects_shared_volume_identity(self):
        runtime = self.policy["profiles"]["local"]["managed_runtime"]
        runtime["volumes"]["redis"] = runtime["volumes"]["database"]
        with self.assertRaisesRegex(ValueError, "three distinct"):
            self.resolve_policy(self.policy)

    def test_rejects_frontend_port_drift(self):
        self.policy["profiles"]["local"]["managed_runtime"]["services"]["frontend_port"] = 5199
        with self.assertRaisesRegex(ValueError, "base_url"):
            self.resolve_policy(self.policy)

    def test_rejects_profile_without_managed_runtime(self):
        with self.assertRaisesRegex(ValueError, "no managed_runtime"):
            PROFILE.resolve("test")

    def test_runtime_entry_validates_reused_process_identity(self):
        runtime = (ROOT / "scripts/dev/frontend_acceptance_runtime.sh").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(runtime.count("validate_backend_identity"), 4)
        self.assertGreaterEqual(runtime.count("validate_backend_runtime"), 2)
        self.assertGreaterEqual(runtime.count("validate_frontend_runtime"), 5)
        for marker in (
            "/mnt/source-addons",
            "SC_SOURCE_REVISION",
            "SC_SOURCE_FINGERPRINT",
            "SC_PRODUCT_VERSION",
            "ODOO_DBFILTER",
            "LIST_DB",
            "docker port",
            "/var/lib/odoo",
            "/proc/$pid/environ",
            "/proc/$pid/cmdline",
            "ss -H -ltnp",
            "VITE_API_PROXY_TARGET",
            "VITE_ODOO_DB_LOCKED=1",
            "release_static_server.mjs",
            "STATIC_ROOT=",
            "STATIC_PORT=",
            "API_PROXY_TARGET=",
            "POSTGRES_PASSWORD",
        ):
            self.assertIn(marker, runtime)

    def test_release_static_server_proxies_odoo_web_assets_before_spa_fallback(self):
        server = (ROOT / "scripts/release/release_static_server.mjs").read_text(
            encoding="utf-8"
        )
        backend_route = "requestPath === '/web' || requestPath.startsWith('/web/')"
        self.assertIn(backend_route, server)
        self.assertLess(server.index("if (isBackendRoute)"), server.index("const raw ="))

    def test_runtime_mutators_validate_existing_resource_identity_before_change(self):
        runtime = (ROOT / "scripts/dev/frontend_acceptance_runtime.sh").read_text(
            encoding="utf-8"
        )
        backend_up = runtime.split("  backend-up)", 1)[1].split("    ;;", 1)[0]
        backend_down = runtime.split("  backend-down)", 1)[1].split("    ;;", 1)[0]
        backend_replace = runtime.split("  backend-replace-stale)", 1)[1].split("    ;;", 1)[0]
        backend_logs = runtime.split("  backend-logs)", 1)[1].split("    ;;", 1)[0]
        frontend_up = runtime.split("  frontend-up)", 1)[1].split("    ;;", 1)[0]
        frontend_down = runtime.split("  frontend-down)", 1)[1].split("    ;;", 1)[0]
        self.assertNotIn("docker rm", backend_up)
        self.assertLess(
            frontend_up.index("validate_frontend_launch_contract"),
            frontend_up.index("frontend_acceptance_up.sh"),
        )
        self.assertLess(
            backend_up.index("validate_backend_identity"),
            backend_up.index("backend_acceptance_up.sh"),
        )
        self.assertLess(
            backend_down.index("validate_backend_identity"),
            backend_down.index("backend_acceptance_down.sh"),
        )
        self.assertLess(
            backend_replace.index("validate_backend_resource_identity"),
            backend_replace.index("backend_acceptance_down.sh"),
        )
        self.assertIn("validate_backend_runtime", backend_replace)
        self.assertNotIn("validate_backend_identity ||", backend_replace)
        self.assertLess(
            backend_logs.index("validate_backend_identity"),
            backend_logs.index("docker exec"),
        )
        self.assertIn("/opt/sce-runtime/logs/odoo.log", backend_logs)
        self.assertIn("docker logs --tail 200", backend_logs)
        self.assertLess(
            frontend_up.index("validate_frontend_runtime"),
            frontend_up.index("frontend_acceptance_up.sh"),
        )
        self.assertLess(
            frontend_down.index("validate_frontend_runtime"),
            frontend_down.index("frontend_acceptance_down.sh"),
        )
        for key in (
            "SC_SOURCE_REVISION",
            "SC_SOURCE_FINGERPRINT",
            "ODOO_DB",
            "DB_NAME",
            "ODOO_DBFILTER",
            "LIST_DB",
        ):
            self.assertRegex(
                runtime,
                rf'require_container_env \"\$container\" {key} .* \|\| return 1',
            )
        self.assertIn("REUSED governed pid=", runtime)

    def test_make_exposes_governed_stale_backend_replacement(self):
        dev_make = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        target = dev_make.split("backend.acceptance.replace-stale:", 1)[1].split(
            "backend.acceptance.down:", 1
        )[0]
        self.assertIn("guard.prod.forbid", target)
        self.assertIn("frontend_acceptance_operation_entry.sh backend-replace-stale", target)

    def test_local_db_ensure_starts_http_carrier_after_baseline_refresh(self):
        runtime = (ROOT / "scripts/dev/frontend_acceptance_runtime.sh").read_text(
            encoding="utf-8"
        )
        db_ensure = runtime.split("  db-ensure)", 1)[1].split("    ;;", 1)[0]
        infrastructure = db_ensure.index("compose_dev up -d --wait db redis")
        carrier = db_ensure.index("compose_dev create odoo", infrastructure)
        refresh = db_ensure.index("frontend_acceptance_db_ensure.sh")
        healthy = db_ensure.index("compose_dev up -d --wait odoo", refresh)
        runtime_check = db_ensure.index("preflight", healthy)
        self.assertLess(infrastructure, carrier)
        self.assertLess(carrier, refresh)
        self.assertNotIn("compose_dev restart odoo", db_ensure)
        self.assertLess(healthy, runtime_check)

    def test_source_fingerprint_covers_dirty_and_untracked_addons(self):
        helper = ROOT / "scripts/dev/acceptance_source_fingerprint.sh"
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / "addons").mkdir()
            tracked = repo / "addons/example.py"
            tracked.write_text("VALUE = 1\n", encoding="utf-8")
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Acceptance Test"], cwd=repo, check=True)
            subprocess.run(["git", "add", "addons/example.py"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "fixture"], cwd=repo, check=True, capture_output=True)

            def fingerprint() -> str:
                env = dict(os.environ, ROOT_DIR=str(repo))
                return subprocess.run(
                    ["bash", str(helper)],
                    check=True,
                    capture_output=True,
                    text=True,
                    env=env,
                ).stdout.strip()

            clean = fingerprint()
            tracked.write_text("VALUE = 2\n", encoding="utf-8")
            dirty = fingerprint()
            subprocess.run(["git", "add", "addons/example.py"], cwd=repo, check=True)
            staged = fingerprint()
            (repo / "addons/untracked.xml").write_text("<odoo/>\n", encoding="utf-8")
            untracked = fingerprint()

            self.assertNotEqual(clean, dirty)
            self.assertEqual(dirty, staged)
            self.assertNotEqual(staged, untracked)


if __name__ == "__main__":
    unittest.main()
