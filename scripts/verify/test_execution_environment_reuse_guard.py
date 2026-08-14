from __future__ import annotations

import copy
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts.verify import execution_environment_reuse_guard as guard


class ExecutionEnvironmentReuseGuardTest(unittest.TestCase):
    def test_inventory_reuses_frozen_acceptance_identity(self):
        report = guard.inventory()
        self.assertEqual(report["decision"], "REUSE_EXISTING_GOVERNED_ENVIRONMENT")
        managed = report["capabilities"]["managed_acceptance"]
        self.assertEqual(managed["database"], "sc_frontend_acceptance")
        self.assertEqual(managed["database_filter"], "^sc_frontend_acceptance$")
        self.assertEqual(managed["backend_port"], 18082)
        self.assertEqual(managed["frontend_port"], 5175)
        self.assertIn("make acceptance.module.upgrade", managed["entries"])
        self.assertEqual(managed["role_bindings"]["finance"], "fixture_role_finance")
        self.assertIn("isolated-write", managed["allowed_operations"])
        self.assertIn(
            "form-system-audit",
            report["capabilities"]["browser_coordination"]["governed_tools"],
        )
        self.assertIn("make local.clean.install", report["capabilities"]["install_upgrade_gates"])
        isolated_release = report["capabilities"]["isolated_frontend_release_ci"]
        self.assertEqual(isolated_release["entry"], "make db.frontend.acceptance.ensure")
        self.assertEqual(isolated_release["compose_project_pattern"], "sc-fe-release-${GITHUB_RUN_ID}")
        self.assertEqual(isolated_release["database"], "sc_frontend_acceptance")

    def test_repository_reuse_markers_are_complete(self):
        self.assertEqual(guard.verify(), [])

    def test_isolated_frontend_release_orders_identity_before_first_side_effect(self):
        source = (
            guard.ROOT / "scripts/dev/frontend_acceptance_db_ensure_entry.sh"
        ).read_text(encoding="utf-8")
        identity_at = source.index('validate_frontend_release_ci_identity "$ROOT_DIR"')
        compose_at = source.index("compose_dev up -d --wait db redis odoo")
        ensure_at = source.index("SC_GOVERNED_FRONTEND_DB_ENSURE_LOWER_ENTRY=1")
        self.assertLess(identity_at, compose_at)
        self.assertLess(compose_at, ensure_at)

    def test_identity_drift_fails_closed(self):
        cases = (
            ("database", "sc_ad_hoc", "managed acceptance database drift"),
            ("database_filter", "^sc_ad_hoc$", "managed acceptance database filter drift"),
            ("backend_port", 18102, "managed acceptance port drift"),
            ("frontend_port", 5192, "managed acceptance port drift"),
            ("compose_project", "parallel_project", "managed acceptance compose project drift"),
        )
        for key, value, expected in cases:
            with self.subTest(key=key):
                drifted = copy.deepcopy(guard.inventory())
                drifted["capabilities"]["managed_acceptance"][key] = value
                with mock.patch.object(guard, "inventory", return_value=drifted):
                    self.assertIn(expected, guard.verify())
        drifted = copy.deepcopy(guard.inventory())
        drifted["capabilities"]["managed_acceptance"]["volumes"] = {
            "database": "parallel_db", "redis": "parallel_redis", "odoo": "parallel_odoo"
        }
        with mock.patch.object(guard, "inventory", return_value=drifted):
            self.assertIn("managed acceptance volume identity drift", guard.verify())

    def run_script(self, relative, *args, env=None):
        return subprocess.run(
            ["bash", str(guard.ROOT / relative), *args],
            cwd=guard.ROOT,
            env={**os.environ, **(env or {})},
            capture_output=True,
            text=True,
        )

    def test_direct_entry_bypasses_fail_before_side_effects(self):
        cases = (
            ("scripts/ci/run_ci.sh", (), "direct run_ci.sh execution is forbidden"),
            ("scripts/ci/install_gate.sh", (), "direct install_gate.sh execution is forbidden"),
            ("scripts/ci/upgrade_gate.sh", (), "direct upgrade_gate.sh execution is forbidden"),
            ("scripts/dev/frontend_acceptance_runtime.sh", ("preflight",), "direct runtime script execution is forbidden"),
            ("scripts/dev/frontend_acceptance_db_ensure_entry.sh", (), "direct entry execution is forbidden"),
            ("scripts/test/frontend_acceptance_db_ensure.sh", (), "direct database ensure execution is forbidden"),
            ("scripts/dev/backend_acceptance_up.sh", (), "direct backend acceptance startup is forbidden"),
            ("scripts/dev/backend_acceptance_down.sh", (), "direct backend acceptance shutdown is forbidden"),
            ("scripts/dev/frontend_acceptance_up.sh", (), "direct frontend acceptance startup is forbidden"),
            ("scripts/dev/frontend_acceptance_down.sh", (), "direct frontend acceptance shutdown is forbidden"),
        )
        with tempfile.TemporaryDirectory() as directory:
            marker = os.path.join(directory, "external-command-called")
            for command in ("docker", "curl", "psql", "node", "pnpm"):
                path = os.path.join(directory, command)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(f"#!/bin/sh\necho {command} >> '{marker}'\nexit 99\n")
                os.chmod(path, 0o755)
            env = {"PATH": f"{directory}:{os.environ['PATH']}"}
            for relative, args, message in cases:
                with self.subTest(relative=relative):
                    result = self.run_script(relative, *args, env=env)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(message, result.stderr)
            self.assertFalse(os.path.exists(marker), "a denied bypass invoked an external side-effect command")

    def test_governed_ci_token_passes_entry_guard(self):
        result = self.run_script("scripts/ci/run_ci.sh", env={"SC_GOVERNED_CI_ENTRY": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("direct run_ci.sh execution is forbidden", result.stderr)
        self.assertIn("requires a governed repository Make target", result.stderr)

    def test_forged_lower_token_cannot_bypass_make_ancestry(self):
        cases = (
            ("scripts/dev/backend_acceptance_up.sh", {"SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY": "1", "BACKEND_ACCEPTANCE_PORT": "18102"}),
            ("scripts/dev/backend_acceptance_down.sh", {"SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY": "1", "BACKEND_ACCEPTANCE_NAME": "parallel-backend"}),
            ("scripts/dev/frontend_acceptance_up.sh", {"SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY": "1", "FRONTEND_ACCEPTANCE_PORT": "5192"}),
            ("scripts/dev/frontend_acceptance_down.sh", {"SC_GOVERNED_ACCEPTANCE_LOWER_ENTRY": "1", "FRONTEND_ACCEPTANCE_PIDFILE": "/tmp/parallel.pid"}),
            ("scripts/dev/frontend_acceptance_db_ensure_entry.sh", {"SC_GOVERNED_FRONTEND_DB_ENSURE_ENTRY": "1"}),
            ("scripts/test/frontend_acceptance_db_ensure.sh", {"SC_GOVERNED_FRONTEND_DB_ENSURE_LOWER_ENTRY": "1"}),
        )
        for relative, env in cases:
            with self.subTest(relative=relative):
                result = self.run_script(relative, env=env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("requires a governed repository Make target", result.stderr)

    def test_isolated_frontend_release_ci_identity_accepts_only_frozen_workflow_topology(self):
        with tempfile.TemporaryDirectory() as runner_temp:
            run_id = "31761525749"
            project = f"sc-fe-release-{run_id}"
            env_file = os.path.join(runner_temp, "frontend-release.env")
            values = {
                "ENV": "test",
                "ENV_FILE": env_file,
                "COMPOSE_PROJECT_NAME": project,
                "DB_USER": "odoo",
                "DB_PASSWORD": "a" * 64,
                "DB_NAME": "sc_frontend_acceptance",
                "ADMIN_PASSWD": "b" * 64,
                "JWT_SECRET": "c" * 64,
                "SC_BOOTSTRAP_SECRET": "d" * 64,
                "SC_BOOTSTRAP_LOGIN": "frontend_release_ci",
                "SCENE_CHANNEL": "stable",
                "SCENE_USE_PINNED": "0",
                "SCENE_ROLLBACK": "0",
                "ODOO_DBFILTER": "^sc_frontend_acceptance$",
                "DB_DATA": f"{project}-db-data",
                "REDIS_DATA": f"{project}-redis-data",
                "ODOO_DATA": f"{project}-odoo-data",
                "SC_ENVIRONMENT": "acceptance",
                "SC_ALLOW_DEMO_DATA": "1",
            }
            with open(env_file, "w", encoding="utf-8") as handle:
                for key, value in values.items():
                    handle.write(f"{key}={value}\n")
            os.chmod(env_file, 0o600)
            base_env = {
                **values,
                "GITHUB_ACTIONS": "true",
                "CI": "true",
                "GITHUB_REPOSITORY": "lidefend/sce-backend-odoo",
                "GITHUB_WORKSPACE": str(guard.ROOT),
                "GITHUB_RUN_ID": run_id,
                "CI_PROJECT_NAME": project,
                "RUNNER_TEMP": runner_temp,
                "CHECKOUT_SHA": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=guard.ROOT, text=True
                ).strip(),
            }
            command = (
                "source scripts/common/frontend_release_ci_identity.sh; "
                "validate_frontend_release_ci_identity \"$PWD\""
            )
            accepted = subprocess.run(
                ["bash", "-c", command], cwd=guard.ROOT, env={**os.environ, **base_env},
                capture_output=True, text=True,
            )
            self.assertEqual(accepted.returncode, 0, accepted.stderr)
            for key, value in (
                ("COMPOSE_PROJECT_NAME", "parallel-project"),
                ("DB_DATA", "parallel-db"),
                ("DB_NAME", "sc_parallel"),
                ("CHECKOUT_SHA", "0" * 40),
            ):
                with self.subTest(key=key):
                    rejected = subprocess.run(
                        ["bash", "-c", command], cwd=guard.ROOT,
                        env={**os.environ, **base_env, key: value},
                        capture_output=True, text=True,
                    )
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertIn("DENY:", rejected.stderr)
            with open(env_file, "a", encoding="utf-8") as handle:
                handle.write("ENV=prod\n")
            duplicate = subprocess.run(
                ["bash", "-c", command], cwd=guard.ROOT, env={**os.environ, **base_env},
                capture_output=True, text=True,
            )
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn("unknown or duplicate keys", duplicate.stderr)
            with open(env_file, "w", encoding="utf-8") as handle:
                for env_key, env_value in values.items():
                    handle.write(f"{env_key}={env_value}\n")
                handle.write("COMPOSE_BIN=bash/tmp/payload.sh\n")
            os.chmod(env_file, 0o600)
            payload = subprocess.run(
                ["bash", "-c", command], cwd=guard.ROOT, env={**os.environ, **base_env},
                capture_output=True, text=True,
            )
            self.assertNotEqual(payload.returncode, 0)
            self.assertIn("unknown or duplicate keys", payload.stderr)
            with open(env_file, "w", encoding="utf-8") as handle:
                for env_key, env_value in values.items():
                    handle.write(f"{env_key}={env_value}\n")
            os.chmod(env_file, 0o600)
            route_override = subprocess.run(
                ["bash", "-c", command], cwd=guard.ROOT,
                env={**os.environ, **base_env, "COMPOSE_BIN": "bash /tmp/payload.sh"},
                capture_output=True, text=True,
            )
            self.assertNotEqual(route_override.returncode, 0)
            self.assertIn("compose command override", route_override.stderr)

    def test_runner_cleanup_rejects_cross_run_project_before_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = os.path.join(directory, "workspace")
            runner_temp = os.path.join(directory, "runner-temp")
            fake_bin = os.path.join(directory, "bin")
            os.makedirs(workspace)
            os.makedirs(runner_temp)
            os.makedirs(fake_bin)
            marker = os.path.join(directory, "side-effect")
            for command_name in ("docker", "find"):
                command_path = os.path.join(fake_bin, command_name)
                with open(command_path, "w", encoding="utf-8") as handle:
                    handle.write(f"#!/bin/sh\necho {command_name} >> '{marker}'\nexit 99\n")
                os.chmod(command_path, 0o755)
            result = self.run_script(
                "scripts/ci/self_hosted_runner_cleanup.sh",
                env={
                    "PATH": f"{fake_bin}:{os.environ['PATH']}",
                    "CI_PROJECT_NAME": "sc-fe-release-199",
                    "GITHUB_RUN_ID": "200",
                    "GITHUB_ACTIONS": "true",
                    "GITHUB_REPOSITORY": "lidefend/sce-backend-odoo",
                    "GITHUB_WORKSPACE": workspace,
                    "RUNNER_TEMP": runner_temp,
                },
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid project scope", result.stderr)
            self.assertFalse(os.path.exists(marker))

    def test_runner_cleanup_rejects_parent_workspace_before_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_bin = os.path.join(directory, "bin")
            runner_temp = os.path.join(directory, "_temp")
            os.makedirs(fake_bin)
            os.makedirs(runner_temp)
            marker = os.path.join(directory, "side-effect")
            for command_name in ("docker", "find"):
                command_path = os.path.join(fake_bin, command_name)
                with open(command_path, "w", encoding="utf-8") as handle:
                    handle.write(f"#!/bin/sh\necho {command_name} >> '{marker}'\nexit 99\n")
                os.chmod(command_path, 0o755)
            result = self.run_script(
                "scripts/ci/self_hosted_runner_cleanup.sh",
                env={
                    "PATH": f"{fake_bin}:{os.environ['PATH']}",
                    "CI_PROJECT_NAME": "sc-fe-release-200",
                    "GITHUB_RUN_ID": "200",
                    "GITHUB_ACTIONS": "true",
                    "GITHUB_REPOSITORY": "lidefend/sce-backend-odoo",
                    "GITHUB_WORKSPACE": str(guard.ROOT.parent),
                    "RUNNER_TEMP": runner_temp,
                },
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid workspace scope", result.stderr)
            self.assertFalse(os.path.exists(marker))

    def test_frontend_release_make_does_not_parse_workflow_env_file(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = os.path.join(directory, "prevalidate-marker")
            env_file = os.path.join(directory, "malicious.env")
            with open(env_file, "w", encoding="utf-8") as handle:
                handle.write(f"$(shell touch {marker})\n")
            result = subprocess.run(
                ["make", "environment.capability.inventory"],
                cwd=guard.ROOT,
                env={
                    **os.environ,
                    "GITHUB_ACTIONS": "true",
                    "GITHUB_REPOSITORY": "lidefend/sce-backend-odoo",
                    "GITHUB_RUN_ID": "200",
                    "CI_PROJECT_NAME": "sc-fe-release-200",
                    "ENV_FILE": env_file,
                },
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(os.path.exists(marker))

    def test_upgrade_gate_propagates_governed_token(self):
        result = self.run_script("scripts/ci/upgrade_gate.sh", env={"SC_GOVERNED_GATE_ENTRY": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires a governed repository Make target", result.stderr)

    def test_governed_make_paths_expand_without_execution(self):
        cases = (
            ("backend.acceptance.up", "SC_GOVERNED_ACCEPTANCE_ENTRY=1"),
            ("frontend.acceptance.up", "SC_GOVERNED_ACCEPTANCE_ENTRY=1"),
            ("acceptance.module.upgrade", "SC_GOVERNED_ACCEPTANCE_ENTRY=1"),
            ("db.frontend.acceptance.ensure", "SC_GOVERNED_FRONTEND_DB_ENSURE_ENTRY=1"),
            ("test-upgrade-gate", "scripts/ci/upgrade_gate.sh"),
            ("test-install-gate", "SC_GOVERNED_GATE_ENTRY=1"),
        )
        for target, marker in cases:
            with self.subTest(target=target):
                result = subprocess.run(
                    ["make", "--dry-run", target, "CODEX_MODE=gate", "MODULE=smart_core"],
                    cwd=guard.ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("execution_environment_reuse_guard.py --inventory", result.stdout)
                self.assertIn(marker, result.stdout)

    def test_make_ancestry_probe_runs_only_through_repository_make(self):
        for args in (
            ["make", "environment.make_ancestry.probe"],
            ["make", "-j", "1", "environment.make_ancestry.probe"],
            ["make", "--jobs", "1", "environment.make_ancestry.probe"],
        ):
            with self.subTest(args=args):
                result = subprocess.run(
                    args,
                    cwd=guard.ROOT,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_custom_makefile_cannot_impersonate_governed_target(self):
        with tempfile.TemporaryDirectory() as directory:
            makefile = os.path.join(directory, "Makefile")
            with open(makefile, "w", encoding="utf-8") as handle:
                handle.write(
                    "test-upgrade-gate:\n"
                    f"\t@SC_GOVERNED_GATE_ENTRY=1 bash '{guard.ROOT / 'scripts/ci/upgrade_gate.sh'}'\n"
                )
            result = subprocess.run(
                ["make", "-f", makefile, "test-upgrade-gate"],
                cwd=guard.ROOT,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires a governed repository Make target", result.stderr)

    def test_makefiles_injection_and_variable_goal_text_cannot_impersonate_target(self):
        with tempfile.TemporaryDirectory() as directory:
            injected = os.path.join(directory, "injected.mk")
            with open(injected, "w", encoding="utf-8") as handle:
                handle.write(
                    "evil_gate:\n"
                    "\t@SC_GOVERNED_GATE_ENTRY=1 bash scripts/ci/install_gate.sh\n"
                )
            result = subprocess.run(
                ["make", "DUMMY= test-install-gate ", "evil_gate"],
                cwd=guard.ROOT,
                env={**os.environ, "MAKEFILES": injected},
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires a governed repository Make target", result.stderr)

    def test_short_eval_and_extra_goal_cannot_impersonate_governed_target(self):
        result = subprocess.run(
            [
                "make",
                "-E",
                "evil_gate:;SC_GOVERNED_GATE_ENTRY=1 bash scripts/ci/install_gate.sh",
                "evil_gate",
                "test-install-gate",
            ],
            cwd=guard.ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires a governed repository Make target", result.stderr)

    def test_attached_and_alias_makefile_options_cannot_impersonate_target(self):
        with tempfile.TemporaryDirectory() as directory:
            makefile = os.path.join(directory, "injected.mk")
            with open(makefile, "w", encoding="utf-8") as handle:
                handle.write(
                    "test-upgrade-gate:\n"
                    "\t@SC_GOVERNED_GATE_ENTRY=1 bash scripts/ci/upgrade_gate.sh\n"
                )
            for option in (
                f"-f{makefile}",
                f"--makefile={makefile}",
                f"--makef={makefile}",
            ):
                with self.subTest(option=option):
                    result = subprocess.run(
                        ["make", option, "test-upgrade-gate"],
                        cwd=guard.ROOT,
                        capture_output=True,
                        text=True,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("requires a governed repository Make target", result.stderr)

    def test_collection_environment_rejects_legacy_topology_override_without_writes(self):
        with tempfile.TemporaryDirectory(dir=guard.ROOT) as directory:
            result = subprocess.run(
                ["make", "verify.frontend.collection_view_semantics.browser"],
                cwd=guard.ROOT,
                env={
                    **os.environ,
                    "SC_COLLECTION_ENVIRONMENT_PROBE": "1",
                    "FRONTEND_URL": "http://127.0.0.1:5192",
                    "DB_NAME": "sc_parallel",
                    "SC_ACCEPTANCE_ARTIFACT_ROOT": directory,
                },
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertRegex(result.stderr, "aliases conflict|canonical managed acceptance identity")
            self.assertEqual(os.listdir(directory), [])

    def test_collection_environment_ignores_api_url_lease_split(self):
        with tempfile.TemporaryDirectory(dir=guard.ROOT) as directory:
            result = subprocess.run(
                ["make", "verify.frontend.collection_view_semantics.browser"],
                cwd=guard.ROOT,
                env={
                    **os.environ,
                    "SC_COLLECTION_ENVIRONMENT_PROBE": "1",
                    "SC_ACCEPTANCE_API_URL": "http://127.0.0.1:5192",
                    "SC_ACCEPTANCE_ARTIFACT_ROOT": directory,
                },
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload_line = next(
                line for line in reversed(result.stdout.splitlines()) if '"baseUrl"' in line
            )
            payload = __import__("json").loads(payload_line)
            self.assertEqual(payload["baseUrl"], "http://127.0.0.1:5175")
            self.assertEqual(payload["apiUrl"], "http://127.0.0.1:5175")
            self.assertEqual(payload["database"], "sc_frontend_acceptance")
            self.assertEqual(os.listdir(directory), [])

    def test_collection_browser_direct_execution_is_denied_before_side_effects(self):
        with tempfile.TemporaryDirectory(dir=guard.ROOT) as directory:
            result = subprocess.run(
                ["node", "scripts/verify/collection_view_semantics_browser.mjs"],
                cwd=guard.ROOT,
                env={
                    **os.environ,
                    "SC_GOVERNED_BROWSER_ENTRY": "1",
                    "SC_COLLECTION_ENVIRONMENT_PROBE": "1",
                    "SC_ACCEPTANCE_ARTIFACT_ROOT": directory,
                },
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requires a governed repository Make target", result.stderr)
            self.assertEqual(os.listdir(directory), [])

    def test_collection_down_aliases_refuse_implicit_shared_shutdown(self):
        for target in ("backend.collection.acceptance.down", "frontend.collection.acceptance.down"):
            result = subprocess.run(
                ["make", "--dry-run", target], cwd=guard.ROOT, capture_output=True, text=True
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("no separate collection", result.stdout)
            self.assertNotIn("backend.acceptance.down\n", result.stdout)
            self.assertNotIn("frontend.acceptance.down\n", result.stdout)


if __name__ == "__main__":
    unittest.main()
