#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import copy
import fcntl
import hashlib
import importlib.util
import sys
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

    def test_exact_checkout_uses_reviewed_primary_worktree_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            authority = Path(directory).resolve()
            subprocess.run(
                ["git", "init", "-q"], cwd=authority, check=True, capture_output=True
            )
            with mock.patch.dict(
                os.environ,
                {
                    "SC_PR_MERGE_EXACT_CHECKOUT": "1",
                    "SC_PR_MERGE_AUTHORITY_ROOT": str(authority),
                },
                clear=False,
            ):
                self.assertEqual(PROFILE._primary_worktree(), authority)
                with mock.patch.dict(
                    os.environ,
                    {"SC_PR_MERGE_AUTHORITY_ROOT": "."},
                    clear=False,
                ):
                    with self.assertRaisesRegex(ValueError, "must be absolute"):
                        PROFILE._primary_worktree()

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
        self.assertIn(backend_route, " ".join(server.split()))
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
        self.assertNotIn("backend_acceptance_down.sh", backend_up)
        self.assertNotIn("backend_acceptance_down.sh", backend_replace)
        self.assertLess(
            frontend_up.index("validate_frontend_launch_contract"),
            frontend_up.index("frontend_acceptance_up.sh"),
        )
        self.assertLess(
            backend_up.index("validate_backend_identity"),
            backend_up.index("backend_acceptance_up.sh"),
        )
        self.assertIn("replacing stale backend identity", backend_up)
        self.assertLess(
            backend_down.index("validate_backend_identity"),
            backend_down.index("backend_acceptance_down.sh"),
        )
        self.assertIn("removing stale backend identity", backend_down)
        self.assertLess(
            backend_replace.index("validate_backend_resource_identity"),
            backend_replace.index("backend_acceptance_up.sh"),
        )
        self.assertIn("replacing stale backend resource identity", backend_replace)
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
        config = db_ensure.index("render_odoo_conf.py", carrier)
        refresh = db_ensure.index("frontend_acceptance_db_ensure.sh")
        healthy = db_ensure.index("compose_dev up -d --wait odoo", refresh)
        runtime_check = db_ensure.index("preflight", healthy)
        self.assertLess(infrastructure, carrier)
        self.assertLess(carrier, config)
        self.assertLess(config, refresh)
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

    def test_isolated_acceptance_entry_stamps_identity_and_strips_database_hints(self):
        identity = (ROOT / "config/acceptance/isolated_entry_identity.v1.env").read_text(
            encoding="utf-8"
        )
        for key in (
            "SC_ENTRY_NAMESPACE",
            "SC_ENTRY_AUDIENCE",
            "SC_ENTRY_SHARED_SECRET",
            "SC_ENTRY_ROUTE_VERSION",
        ):
            self.assertRegex(identity, rf"(?m)^{key}=\S+$")

        server = (ROOT / "scripts/release/release_static_server.mjs").read_text(
            encoding="utf-8"
        )
        self.assertIn("process.env.SC_ENTRY_NAMESPACE", server)
        self.assertIn("'x-sc-namespace': entryNamespace", server)
        self.assertIn("'x-sc-entry-secret'", server)
        for database_hint in ("x-odoo-db", "x-odoo-database", "x-db", "x-odoo-db-locked"):
            self.assertIn(f"'{database_hint}'", server)

        operation = (ROOT / "scripts/dev/frontend_acceptance_operation_entry.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("config/acceptance/isolated_entry_identity.v1.env", operation)
        for key in (
            "SC_ENTRY_NAMESPACE",
            "SC_ENTRY_AUDIENCE",
            "SC_ENTRY_SHARED_SECRET",
            "SC_ENTRY_ROUTE_VERSION",
        ):
            self.assertIn(f'{key}=${key}', operation)

        frontend_up = (ROOT / "scripts/dev/frontend_acceptance_up.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("config/acceptance/isolated_entry_identity.v1.env", frontend_up)
        self.assertIn('SC_ENTRY_SHARED_SECRET="$SC_ENTRY_SHARED_SECRET"', frontend_up)

        vite = (ROOT / "frontend/apps/web/vite.config.ts").read_text(encoding="utf-8")
        self.assertIn("process.env.SC_ENTRY_NAMESPACE", vite)
        self.assertIn("'X-SC-Namespace': entryNamespace", vite)
        self.assertIn("'X-SC-Entry-Secret'", vite)


class AcceptanceModuleUpgradeLifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "acceptance_module_upgrade", ROOT / "scripts/dev/frontend_acceptance_module_upgrade.py")
        cls.tool = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {"frontend_acceptance_runtime_profile": PROFILE}):
            spec.loader.exec_module(cls.tool)

    def setUp(self):
        self.profile = PROFILE.resolve("local")
        self.env = dict(self.profile, EXPECTED_HEAD="a" * 40, MODULE="smart_core",
                        SC_FRONTEND_ACCEPTANCE_RUNTIME_ENTRY="operation_entry_v1")
        self.rows = {}
        for index, name in enumerate((self.profile["COMPOSE_PROJECT_NAME"] + "-odoo-1",
                                      self.profile["BACKEND_ACCEPTANCE_NAME"])):
            row = {"Id": str(index + 1) * 64, "Name": "/" + name,
                   "Config": {"Labels": {"com.docker.compose.project": self.profile["COMPOSE_PROJECT_NAME"],
                                          "com.docker.compose.service": "odoo"},
                              "Env": [f"{k}={self.profile[k]}" for k in ("DB_NAME", "ODOO_DB", "ODOO_DBFILTER")]},
                   "Mounts": [{"Destination": "/var/lib/odoo", "Type": "volume", "Name": self.profile["ODOO_DATA"]}],
                   "State": {"Running": True}}
            self.rows[row["Id"]] = row
        self.events = []
        self.fail_upgrade = False
        self.fail_second_stop = False
        self.extra_writer = False
        self.attempt = None

    def inspect(self, identity):
        if self.attempt and identity == self.attempt["Id"]:
            return copy.deepcopy(self.attempt)
        return copy.deepcopy(next(row for row in self.rows.values()
                                  if identity in (row["Id"], row["Name"].lstrip("/"))))

    def command(self, args, **kwargs):
        self.events.append(args)
        if args[:4] == ["docker", "ps", "-a", "--no-trunc"]:
            return self.attempt["Id"] if self.attempt else ""
        if args[:3] == ["docker", "ps", "-a"]:
            return "\n".join(row["Name"].lstrip("/") for row in self.rows.values())
        if args[:2] == ["docker", "ps"]:
            return "\n".join([key for key, row in self.rows.items() if row["State"]["Running"]]
                             + (["f" * 64] if self.extra_writer else []))
        if args[:2] == ["docker", "stop"]:
            if self.attempt and args[2] == self.attempt["Id"]:
                self.attempt["State"]["Running"] = False
                return ""
            self.rows[args[2]]["State"]["Running"] = False
            if self.fail_second_stop and args[2] == "2" * 64:
                raise subprocess.CalledProcessError(1, args)
            return ""
        if args[:2] == ["docker", "start"]:
            self.rows[args[2]]["State"]["Running"] = True
            return ""
        if args[0] == "bash":
            self.assertFalse(any(row["State"]["Running"] for row in self.rows.values()))
            self.assertEqual(args[1], str(ROOT / "scripts/mod/upgrade.sh"))
            if self.fail_upgrade:
                env = kwargs["env"]
                self.attempt = {"Id": "3" * 64, "Name": "/" + env["SC_ACCEPTANCE_UPGRADE_CONTAINER_NAME"],
                                "Config": {"Labels": {"com.docker.compose.project": self.profile["COMPOSE_PROJECT_NAME"],
                                                        "com.docker.compose.service": "odoo",
                                                        "sce.acceptance.module-upgrade": env["SC_ACCEPTANCE_MODULE_UPGRADE_ID"]}},
                                "State": {"Running": True}}
                raise subprocess.CalledProcessError(1, args)
            return ""
        raise AssertionError(args)

    def run_upgrade(self):
        with tempfile.TemporaryDirectory() as temp, \
             mock.patch.object(self.tool, "command", side_effect=self.command), \
             mock.patch.object(self.tool, "inspect", side_effect=self.inspect), \
             mock.patch.object(self.tool, "source_identity", return_value="a" * 40):
            self.tool.upgrade(dict(self.env, XDG_RUNTIME_DIR=temp))

    def test_both_running_writers_stop_before_real_upgrade_entry_and_stay_stopped(self):
        self.run_upgrade()
        self.assertEqual(sum(args[0] == "bash" for args in self.events), 1)
        self.assertEqual(sum(args[:2] == ["docker", "stop"] for args in self.events), 2)
        self.assertFalse(any(row["State"]["Running"] for row in self.rows.values()))
        self.assertFalse(any(args[:2] == ["docker", "start"] for args in self.events))

    def test_upgrade_failure_does_not_restart_old_registry_or_restore_database(self):
        self.fail_upgrade = True
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_upgrade()
        self.assertFalse(any(row["State"]["Running"] for row in self.rows.values()))
        self.assertFalse(any(args[:2] == ["docker", "start"] for args in self.events))
        self.assertFalse(self.attempt["State"]["Running"])
        self.assertIn(["docker", "stop", "3" * 64], self.events)

    def test_stop_failure_before_upgrade_restores_original_states(self):
        self.fail_second_stop = True
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_upgrade()
        self.assertTrue(all(row["State"]["Running"] for row in self.rows.values()))
        self.assertFalse(any(args[0] == "bash" for args in self.events))

    def test_originally_stopped_compose_is_never_started(self):
        self.rows["1" * 64]["State"]["Running"] = False
        self.fail_second_stop = True
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_upgrade()
        self.assertFalse(self.rows["1" * 64]["State"]["Running"])
        self.assertTrue(self.rows["2" * 64]["State"]["Running"])

    def test_absent_artifact_is_valid_and_never_created_by_upgrade(self):
        del self.rows["2" * 64]
        self.run_upgrade()
        self.assertEqual(len(self.rows), 1)
        self.assertFalse(self.rows["1" * 64]["State"]["Running"])

    def test_unknown_running_writer_denied_before_stop(self):
        self.extra_writer = True
        with self.assertRaisesRegex(ValueError, "unknown running writer"):
            self.run_upgrade()
        self.assertFalse(any(args[:2] == ["docker", "stop"] for args in self.events))

    def test_writer_wrong_db_or_volume_is_denied_without_mutation(self):
        for field in ("database", "volume", "project"):
            with self.subTest(field=field):
                original = copy.deepcopy(self.rows)
                if field == "database":
                    self.rows["2" * 64]["Config"]["Env"][0] = "DB_NAME=other"
                elif field == "volume":
                    self.rows["2" * 64]["Mounts"][0]["Name"] = "other"
                else:
                    self.rows["2" * 64]["Config"]["Labels"]["com.docker.compose.project"] = "other"
                with self.assertRaises(ValueError):
                    self.run_upgrade()
                self.assertFalse(any(args[:2] == ["docker", "stop"] for args in self.events))
                self.rows = original

    def test_actual_preview_locks_reject_active_acceptance_on_either_port(self):
        for port in ("5175", "5180"):
            with self.subTest(port=port), tempfile.TemporaryDirectory() as temp:
                target = f"http://127.0.0.1:{port}|http://127.0.0.1:18082|sc_frontend_acceptance"
                directory = Path(temp) / "sce-frontend-acceptance/leases"
                directory.mkdir(parents=True)
                path = directory / (hashlib.sha256(target.encode()).hexdigest() + ".lock")
                with path.open("a") as holder:
                    fcntl.flock(holder.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    with self.assertRaisesRegex(ValueError, "active acceptance lease"):
                        with self.tool.leases(self.profile, {"XDG_RUNTIME_DIR": temp}):
                            self.fail("active reader must deny writer")
                with self.tool.leases(self.profile, {"XDG_RUNTIME_DIR": temp}):
                    pass

    def test_second_upgrade_cannot_hold_same_target_leases(self):
        with tempfile.TemporaryDirectory() as temp:
            env = {"XDG_RUNTIME_DIR": temp}
            with self.tool.leases(self.profile, env):
                with self.assertRaisesRegex(ValueError, "active acceptance lease"):
                    with self.tool.leases(self.profile, env):
                        self.fail("two upgrades must not run together")

    def test_interrupted_upgrade_child_is_reaped_before_lease_release(self):
        child = mock.Mock()
        child.wait.side_effect = [InterruptedError("cancelled"), 0, 0]
        child.pid = 56789
        with mock.patch.object(self.tool.subprocess, "Popen", return_value=child), \
             mock.patch.object(self.tool.os, "killpg") as killpg:
            with self.assertRaises(InterruptedError):
                self.tool.command(["bash", "upgrade"], capture=False)
        self.assertEqual(killpg.call_count, 2)
        self.assertEqual(child.wait.call_count, 3)

    def test_exited_rollback_custody_is_neither_stopped_nor_removed(self):
        original = self.command
        def with_custody(args, **kwargs):
            value = original(args, **kwargs)
            if args == ["docker", "ps", "-a", "--format", "{{.Names}}"]:
                value += "\nsc-backend-odoo-acceptance-rollback-51405bdf3bdc"
            return value
        with mock.patch.object(self, "command", side_effect=with_custody):
            self.run_upgrade()
        self.assertFalse(any("rollback" in str(args) for args in self.events))


    def test_pending_blocks_upgrade_and_recovery_never_replays_upgrade(self):
        with tempfile.TemporaryDirectory() as temp:
            env = dict(self.env, XDG_RUNTIME_DIR=temp)
            token = "f" * 32
            name = self.profile["COMPOSE_PROJECT_NAME"] + "-module-upgrade-" + token
            record = self.tool.pending_record(self.profile, env, "a" * 40, name, token)
            with self.tool.leases(self.profile, env):
                self.tool.write_pending(record, self.profile, env)
            with mock.patch.object(self.tool, "command", side_effect=self.command), \
                 mock.patch.object(self.tool, "inspect", side_effect=self.inspect), \
                 mock.patch.object(self.tool, "source_identity", return_value="a" * 40):
                with self.assertRaisesRegex(ValueError, "recovery pending"):
                    self.tool.upgrade(env)
                self.assertEqual(self.events, [])
                self.tool.upgrade(dict(env, ACCEPTANCE_UPGRADE_RECOVER="1"))
            self.assertFalse(any(args[0] == "bash" for args in self.events))
            self.assertFalse(any(path.exists() for path in self.tool.pending_paths(self.profile, env)))

    def test_pending_unknown_damaged_or_source_mismatch_remains_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            env = dict(self.env, XDG_RUNTIME_DIR=temp)
            paths = self.tool.pending_paths(self.profile, env)
            paths[0].parent.mkdir(parents=True)
            for content in ('bad-json', '{}', '[1]', json.dumps({"attempt_id": "f" * 32})):
                paths[0].write_text(content)
                with self.subTest(content=content), self.assertRaises(ValueError):
                    self.tool.recover_pending(self.profile, env, "a" * 40)
                with self.assertRaisesRegex(ValueError, 'recovery pending'):
                    self.tool.check_pending(self.profile, env)
                self.assertTrue(paths[0].exists())
            paths[0].unlink()
            paths[0].symlink_to(paths[0].parent / 'missing')
            with self.assertRaisesRegex(ValueError, 'identity invalid'):
                self.tool.recover_pending(self.profile, env, "a" * 40)

    def test_unreachable_daemon_retains_pending_after_failed_upgrade(self):
        self.fail_upgrade = True
        with tempfile.TemporaryDirectory() as temp:
            env = dict(self.env, XDG_RUNTIME_DIR=temp)
            with mock.patch.object(self.tool, "command", side_effect=self.command), \
                 mock.patch.object(self.tool, "inspect", side_effect=self.inspect), \
                 mock.patch.object(self.tool, "source_identity", return_value="a" * 40), \
                 mock.patch.object(self.tool, 'stop_upgrade_container', side_effect=OSError('unavailable')):
                with self.assertRaises(OSError):
                    self.tool.upgrade(env)
            self.assertTrue(all(path.exists() for path in self.tool.pending_paths(self.profile, env)))
            with self.assertRaisesRegex(ValueError, 'recovery pending'):
                self.tool.check_pending(self.profile, env)
            self.assertTrue(self.attempt['State']['Running'])

    def test_upgrade_container_label_mismatch_is_not_stopped(self):
        self.attempt = {'Id': '3' * 64, 'Name': '/expected', 'Config': {'Labels': {}},
                        'State': {'Running': True}}
        with mock.patch.object(self.tool, 'command', side_effect=self.command), \
             mock.patch.object(self.tool, 'inspect', side_effect=self.inspect):
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                self.tool.stop_upgrade_container('expected', 'f' * 32, self.profile)
        self.assertTrue(self.attempt['State']['Running'])
        self.assertFalse(any(args[:2] == ['docker', 'stop'] for args in self.events))

    def test_browser_actual_lease_refuses_pending_without_parsing_it(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            marker = root / 'target.module-upgrade-pending.json'
            marker.write_text('deliberately-invalid-pending')
            script = f"""
import {{ acquireAcceptanceLease }} from {json.dumps((ROOT / 'scripts/verify/lib/frontend_acceptance_lease.mjs').as_uri())};
try {{
  await acquireAcceptanceLease({{environment: {{concurrency: {{leaseRoot: {json.dumps(temp)}, targetKey: 'target'}}, artifacts: {{runRoot: {json.dumps(temp)}, runId: 'offline'}}}}, root: {json.dumps(temp)}}});
  process.exitCode = 9;
}} catch (error) {{
  if (!error.message.includes('module upgrade recovery pending')) throw error;
  console.log('pending-denied');
}}
"""
            result = subprocess.run(['node', '--input-type=module', '-e', script],
                                    capture_output=True, text=True, timeout=10, check=True)
            self.assertEqual(result.stdout.strip(), 'pending-denied')
            self.assertTrue(marker.exists())


    def test_real_upgrade_shell_passes_exact_attempt_name_and_label(self):
        source = (ROOT / 'scripts/mod/upgrade.sh').read_text()
        block = source[source.index('acceptance_attempt_args=()'):]
        token = 'f' * 32
        env = dict(os.environ, **self.env, SC_ACCEPTANCE_MODULE_UPGRADE_ID=token,
                   SC_ACCEPTANCE_UPGRADE_CONTAINER_NAME='sc-fe-r2-p1-01-module-upgrade-' + token,
                   ODOO_ADDONS_PATH='/synthetic/addons', ODOO_CONF='/synthetic/config',
                   DB_USER='synthetic', DB_PASSWORD='synthetic-not-a-secret')
        result = subprocess.run(['bash', '-c', 'set -eu; compose_dev() { printf "%s\\n" "$@"; }; ' + block],
                                env=env, check=True, capture_output=True, text=True)
        args = result.stdout.splitlines()
        self.assertEqual(args[args.index('--name') + 1], env['SC_ACCEPTANCE_UPGRADE_CONTAINER_NAME'])
        self.assertEqual(args[args.index('--label') + 1], 'sce.acceptance.module-upgrade=' + token)
        self.assertEqual(args[args.index('-u') + 1], 'smart_core')
        self.assertIn('--stop-after-init', args)
        self.assertIn('--max-cron-threads=0', args)
        env['SC_ACCEPTANCE_UPGRADE_CONTAINER_NAME'] = 'unowned-container'
        result = subprocess.run(['bash', '-c', 'set -eu; compose_dev() { exit 99; }; ' + block],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_backend_raw_replacement_and_reuse_both_check_pending(self):
        runtime = (ROOT / 'scripts/dev/frontend_acceptance_runtime.sh').read_text()
        block = runtime.split('  backend-up)\n', 1)[1].split('    ;;', 1)[0]
        self.assertLess(block.index('--check-pending'), block.index('validate_backend_identity'))
        source = (ROOT / 'scripts/dev/backend_acceptance_up.sh').read_text()
        self.assertLess(source.index('.module-upgrade-pending.json'), source.index('docker stop'))
        self.assertIn('-L "$lock_root/$key.module-upgrade-pending.json"', source)

    def test_wrong_profile_or_identity_is_rejected(self):
        for key, value in (("SC_ACCEPTANCE_RUNTIME_PROFILE", "candidate"),
                           ("DB_NAME", "other"), ("SC_ACCEPTANCE_STANDARD_PREVIEW_PORT", "9999")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.tool.profile_identity(dict(self.env, **{key: value}))

    def test_exact_clean_head_and_explicit_modules_required(self):
        def git(args, **kwargs):
            return "a" * 40 if args[1] == "rev-parse" else ""
        with mock.patch.object(self.tool, "command", side_effect=git):
            self.assertEqual(self.tool.source_identity(self.env), "a" * 40)
            for key, value in (("EXPECTED_HEAD", "b" * 40), ("SC_ACCEPTANCE_SOURCE_SHA", "b" * 40),
                               ("MODULE", "all"), ("MODULE", "smart_core,smart_core"),
                               ("MODULE", "smart_core;-i"), ("MODULE", "unknown_local_module"),
                               ("ODOO_ARGS", "--db_host=other")):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.tool.source_identity(dict(self.env, **{key: value}))
        with mock.patch.object(self.tool, "command", side_effect=["a" * 40, " M addons/example.py"]):
            with self.assertRaisesRegex(ValueError, "clean checkout"):
                self.tool.source_identity(self.env)

    def test_local_snapshot_uses_existing_isolated_shell_without_compose_exec(self):
        runtime = (ROOT / "scripts/dev/frontend_acceptance_runtime.sh").read_text()
        block = runtime.split("  release-snapshot)\n", 1)[1].split("    ;;", 1)[0]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts/ops").mkdir(parents=True)
            (root / "scripts/dev").mkdir(parents=True)
            (root / "scripts/dev/frontend_acceptance_module_upgrade.py").write_text("# offline pending check stub\n")
            (root / "scripts/test").mkdir(parents=True)
            (root / "scripts/test/frontend_acceptance_release_snapshot.py").write_text("fixture")
            (root / "scripts/ops/odoo_shell_exec.sh").write_text('echo "mode=${ODOO_SHELL_RUN_ISOLATED:-exec}"\n')
            for profile, expected in (("local", "mode=1"), ("candidate", "mode=exec")):
                result = subprocess.run(["bash", "-c", "preflight() { :; }; " + block],
                                        env={**os.environ, "ROOT_DIR": str(root), "PROFILE": profile},
                                        check=True, capture_output=True, text=True)
                self.assertEqual(result.stdout.strip(), expected)
        upgrade = runtime.split("  module-upgrade)\n", 1)[1].split("    ;;", 1)[0]
        self.assertIn('python3 "$ROOT_DIR/scripts/dev/frontend_acceptance_module_upgrade.py"', upgrade)
        make = (ROOT / "make/runtime_ops.mk").read_text()
        self.assertIn('EXPECTED_HEAD="$(EXPECTED_HEAD)" ACCEPTANCE_UPGRADE_RECOVER="$(ACCEPTANCE_UPGRADE_RECOVER)"', make)


if __name__ == "__main__":
    unittest.main()
