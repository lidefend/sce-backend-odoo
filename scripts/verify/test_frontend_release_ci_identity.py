#!/usr/bin/env python3
from __future__ import annotations

import os
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts/common/frontend_release_ci_identity.sh"


class FrontendReleaseCIIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runner_temp = Path(self.temp.name) / "_temp"
        self.runner_temp.mkdir()
        self.run_id = "987654321"
        self.run_attempt = "3"
        self.project = f"sc-fe-release-{self.run_id}-{self.run_attempt}"
        self.head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        self.env_file = self.runner_temp / f"sce-ci-{self.run_id}-{self.run_attempt}-frontend-release.env"
        self.identity_file = self.runner_temp / f"sce-ci-{self.run_id}-{self.run_attempt}-frontend-release.identity"
        secret = "a" * 64
        self.values = {
            "ENV": "test",
            "ENV_FILE": str(self.env_file),
            "COMPOSE_PROJECT_NAME": self.project,
            "DB_USER": "odoo",
            "DB_PASSWORD": secret,
            "DB_NAME": "sc_frontend_acceptance",
            "ADMIN_PASSWD": secret,
            "JWT_SECRET": secret,
            "SC_BOOTSTRAP_SECRET": secret,
            "SC_BOOTSTRAP_LOGIN": "frontend_release_ci",
            "SCENE_CHANNEL": "stable",
            "SCENE_USE_PINNED": "0",
            "SCENE_ROLLBACK": "0",
            "ODOO_DBFILTER": "^sc_frontend_acceptance$",
            "ODOO_PORT": "18082",
            "SC_SOURCE_REVISION": self.head,
            "DB_DATA": f"{self.project}-db-data",
            "REDIS_DATA": f"{self.project}-redis-data",
            "ODOO_DATA": f"{self.project}-odoo-data",
            "SC_ENVIRONMENT": "acceptance",
            "SC_ALLOW_DEMO_DATA": "1",
        }
        self.write_env()

    def write_env(self, extra: str = "") -> None:
        content = "".join(f"{key}={value}\n" for key, value in self.values.items()) + extra
        self.env_file.write_text(content, encoding="utf-8")
        self.env_file.chmod(0o600)

    def run_validator(self, overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            **self.values,
            "GITHUB_ACTIONS": "true",
            "CI": "true",
            "GITHUB_REPOSITORY": "lidefend/sce-backend-odoo",
            "GITHUB_WORKSPACE": str(ROOT),
            "GITHUB_RUN_ID": self.run_id,
            "GITHUB_RUN_ATTEMPT": self.run_attempt,
            "CI_PROJECT_NAME": self.project,
            "CHECKOUT_SHA": self.head,
            "RUNNER_TEMP": str(self.runner_temp),
            "SC_FRONTEND_RELEASE_IDENTITY_FILE": str(self.identity_file),
        }
        for key in (
            "COMPOSE_BIN", "PROJECT", "SC_CUSTOMER_ADDONS_ROOT", "COMPOSE_FILE", "COMPOSE_FILES",
            "COMPOSE_FILE_BASE", "COMPOSE_TEST_FILES", "COMPOSE_CI_FILES", "CI_FILES",
            "COMPOSE_PROFILES", "COMPOSE_ENV_FILES", "DOCKER_HOST", "DOCKER_CONTEXT",
        ):
            env.pop(key, None)
        env.update(overrides or {})
        return subprocess.run(
            ["bash", "-c", f'source "{VALIDATOR}"; validate_frontend_release_ci_identity "{ROOT}"'],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )

    def test_exact_identity_passes(self) -> None:
        self.assertEqual(self.run_validator().returncode, 0)

    def run_identity_command(self, command: str, overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = {
            **os.environ,
            **self.values,
            "GITHUB_ACTIONS": "true",
            "CI": "true",
            "GITHUB_REPOSITORY": "lidefend/sce-backend-odoo",
            "GITHUB_WORKSPACE": str(ROOT),
            "GITHUB_RUN_ID": self.run_id,
            "GITHUB_RUN_ATTEMPT": self.run_attempt,
            "CI_PROJECT_NAME": self.project,
            "CHECKOUT_SHA": self.head,
            "RUNNER_TEMP": str(self.runner_temp),
            "SC_FRONTEND_RELEASE_IDENTITY_FILE": str(self.identity_file),
        }
        for key in (
            "COMPOSE_BIN", "PROJECT", "SC_CUSTOMER_ADDONS_ROOT", "COMPOSE_FILE", "COMPOSE_FILES",
            "COMPOSE_FILE_BASE", "COMPOSE_TEST_FILES", "COMPOSE_CI_FILES", "CI_FILES",
            "COMPOSE_PROFILES", "COMPOSE_ENV_FILES", "DOCKER_HOST", "DOCKER_CONTEXT",
        ):
            env.pop(key, None)
        env.update(overrides or {})
        return subprocess.run(
            ["bash", str(VALIDATOR), command, str(ROOT)], cwd=ROOT, env=env,
            text=True, capture_output=True,
        )

    def test_frozen_identity_detects_env_and_attempt_drift(self) -> None:
        self.assertEqual(self.run_identity_command("freeze").returncode, 0)
        self.assertEqual(self.run_identity_command("verify").returncode, 0)
        self.values["DB_PASSWORD"] = "b" * 64
        self.write_env()
        self.assertEqual(self.run_identity_command("verify").returncode, 2)

    def test_duplicate_or_shell_content_is_rejected(self) -> None:
        self.write_env("DB_NAME=sc_frontend_acceptance\n")
        self.assertEqual(self.run_validator().returncode, 2)
        self.write_env("$(touch /tmp/forbidden)=value\n")
        self.assertEqual(self.run_validator().returncode, 2)

    def test_symlink_wide_mode_and_wrong_path_are_rejected(self) -> None:
        self.env_file.chmod(0o644)
        self.assertEqual(self.run_validator().returncode, 2)
        self.write_env()
        real_file = self.runner_temp / "real.env"
        self.env_file.rename(real_file)
        self.env_file.symlink_to(real_file)
        self.assertEqual(self.run_validator().returncode, 2)
        self.env_file.unlink()
        real_file.rename(self.env_file)
        wrong = self.runner_temp / "wrong.env"
        wrong.write_text(self.env_file.read_text(encoding="utf-8"), encoding="utf-8")
        wrong.chmod(0o600)
        self.assertEqual(self.run_validator({"ENV_FILE": str(wrong)}).returncode, 2)

    def test_project_volume_and_sha_drift_are_rejected(self) -> None:
        for override in (
            {"COMPOSE_PROJECT_NAME": "sc-fe-release-1"},
            {"DB_DATA": "foreign-db-data"},
            {"SC_SOURCE_REVISION": "0" * 40},
        ):
            self.assertEqual(self.run_validator(override).returncode, 2)

    def test_route_overrides_are_rejected(self) -> None:
        for key in ("COMPOSE_BIN", "COMPOSE_FILES", "DOCKER_HOST"):
            self.assertEqual(self.run_validator({key: "foreign"}).returncode, 2)

    def test_make_does_not_parse_ci_env_before_validation(self) -> None:
        marker = Path(self.temp.name) / "prevalidate-marker"
        self.env_file.write_text(f"$(shell touch {marker})\n", encoding="utf-8")
        self.env_file.chmod(0o600)
        result = subprocess.run(
            ["make", "--no-print-directory", "-n", "guard.prod.forbid"],
            cwd=ROOT,
            env={
                **os.environ,
                "GITHUB_ACTIONS": "true",
                "GITHUB_REPOSITORY": "lidefend/sce-backend-odoo",
                "GITHUB_RUN_ID": self.run_id,
                "GITHUB_RUN_ATTEMPT": self.run_attempt,
                "CI_PROJECT_NAME": self.project,
                "ENV_FILE": str(self.env_file),
            },
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())

    def test_invalid_identity_stops_before_operation_side_effect(self) -> None:
        bin_dir = Path(self.temp.name) / "bin"
        bin_dir.mkdir()
        marker = Path(self.temp.name) / "docker-called"
        fake_docker = bin_dir / "docker"
        fake_docker.write_text(f"#!/usr/bin/env bash\ntouch '{marker}'\nexit 0\n", encoding="utf-8")
        fake_docker.chmod(0o755)
        result = subprocess.run(
            ["bash", str(ROOT / "scripts/dev/frontend_acceptance_operation_entry.sh"), "db-ensure"],
            cwd=ROOT,
            env={
                **os.environ,
                **self.values,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "SC_FRONTEND_RELEASE_CI_ENTRY": "1",
                "GITHUB_ACTIONS": "true",
                "CI": "true",
                "GITHUB_REPOSITORY": "foreign/repository",
                "GITHUB_WORKSPACE": str(ROOT),
                "GITHUB_RUN_ID": self.run_id,
                "GITHUB_RUN_ATTEMPT": self.run_attempt,
                "CI_PROJECT_NAME": self.project,
                "CHECKOUT_SHA": self.head,
                "RUNNER_TEMP": str(self.runner_temp),
                "SC_FRONTEND_RELEASE_IDENTITY_FILE": str(self.identity_file),
            },
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertFalse(marker.exists())

    def test_local_route_delegates_to_existing_runtime_with_same_operation(self) -> None:
        bin_dir = Path(self.temp.name) / "local-bin"
        bin_dir.mkdir()
        capture = Path(self.temp.name) / "local-delegation"
        fake_bash = bin_dir / "bash"
        fake_bash.write_text(
            f"#!/bin/sh\nprintf '%s|%s|%s' \"$SC_ACCEPTANCE_RUNTIME_PROFILE\" \"$1\" \"$2\" > '{capture}'\n",
            encoding="utf-8",
        )
        fake_bash.chmod(0o755)
        result = subprocess.run(
            ["/bin/bash", str(ROOT / "scripts/dev/frontend_acceptance_operation_entry.sh"), "fixture"],
            cwd=ROOT,
            env={
                **os.environ,
                "PATH": f"{bin_dir}:{os.environ['PATH']}",
                "SC_FRONTEND_RELEASE_CI_ENTRY": "1",
                "SC_ACCEPTANCE_RUNTIME_PROFILE": "local",
                "GITHUB_ACTIONS": "false",
            },
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            capture.read_text(encoding="utf-8"),
            f"local|{ROOT / 'scripts/dev/frontend_acceptance_runtime.sh'}|fixture",
        )

    def test_ci_frontend_lifecycle_is_bound_to_frozen_run_process_identity(self) -> None:
        source = (ROOT / "scripts/dev/frontend_acceptance_operation_entry.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "sce-ci-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}-frontend-release.pid",
            source,
        )
        self.assertIn("validate_ci_frontend_live_process \"$frontend_pid\"", source)
        self.assertIn('"GITHUB_RUN_ID=$GITHUB_RUN_ID"', source)
        self.assertIn('"GITHUB_RUN_ATTEMPT=$GITHUB_RUN_ATTEMPT"', source)
        self.assertIn('"COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT_NAME"', source)
        self.assertIn('"SC_SOURCE_REVISION=$SC_SOURCE_REVISION"', source)
        self.assertIn("export FRONTEND_ACCEPTANCE_ALLOW_REUSE=1", source)
        self.assertLess(
            source.index("validate_ci_frontend_live_process \"$frontend_pid\"", source.index("frontend-down)")),
            source.index('bash "$ROOT_DIR/scripts/dev/frontend_acceptance_down.sh"'),
        )

    def test_ci_operation_projects_validated_database_aliases_before_dispatch(self) -> None:
        source = (ROOT / "scripts/dev/frontend_acceptance_operation_entry.sh").read_text(
            encoding="utf-8"
        )
        verify = source.index('verify_frozen_frontend_release_ci_identity "$ROOT_DIR"')
        project_db = source.index('export ODOO_DB="$DB_NAME"')
        project_list = source.index("export LIST_DB=0")
        dispatch = source.index('case "$operation" in')
        self.assertLess(verify, project_db)
        self.assertLess(project_db, dispatch)
        self.assertLess(project_list, dispatch)
        self.assertIn('"$ODOO_DB" == "$DB_NAME"', source)
        self.assertIn('"$LIST_DB" == "0"', source)

    def install_fake_docker(self, state: dict[str, object]) -> tuple[Path, Path]:
        bin_dir = Path(self.temp.name) / "resource-bin"
        bin_dir.mkdir(exist_ok=True)
        state_file = Path(self.temp.name) / "docker-state.json"
        state_file.write_text(json.dumps(state), encoding="utf-8")
        fake = bin_dir / "docker"
        fake.write_text(
            """#!/usr/bin/env python3
import json, os, sys
s=json.load(open(os.environ['FAKE_DOCKER_STATE'], encoding='utf-8'))
a=sys.argv[1:]
if a[:2] == ['volume', 'ls']:
    print('\\n'.join(s.get('volume_list', [])))
elif a[:2] == ['network', 'ls']:
    print('\\n'.join(s.get('network_list', [])))
elif a[:2] == ['ps', '-aq']:
    print('\\n'.join(s.get('containers', {}).keys()))
elif a[:2] == ['volume', 'inspect']:
    volume=a[2]
    if volume not in s.get('volumes', {}): sys.exit(1)
    template=a[-1] if '--format' in a else ''
    if 'compose.project' in template: print(s['volumes'][volume]['project'])
    elif 'compose.volume' in template: print(s['volumes'][volume]['logical'])
elif a and a[0] == 'inspect':
    container=a[1]; row=s['containers'][container]; template=a[-1]
    if 'compose.service' in template: print(row['service'])
    elif '.Config.Env' in template: print('\\n'.join(row.get('env', [])))
    elif '/var/lib/postgresql/data' in template or '/data' in template or '/var/lib/odoo' in template: print(row['volume'])
    elif '/mnt/source-addons' in template: print(row.get('source', ''))
else:
    sys.exit(3)
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        return bin_dir, state_file

    def valid_resource_state(self) -> dict[str, object]:
        return {
            "volume_list": [self.values["DB_DATA"], self.values["REDIS_DATA"], self.values["ODOO_DATA"]],
            "network_list": [f"{self.project}_default"],
            "volumes": {
                self.values["DB_DATA"]: {"project": self.project, "logical": "db_data"},
                self.values["REDIS_DATA"]: {"project": self.project, "logical": "redis_data"},
                self.values["ODOO_DATA"]: {"project": self.project, "logical": "odoo_data"},
            },
            "containers": {
                "db1": {"service": "db", "env": [f"POSTGRES_DB={self.values['DB_NAME']}"], "volume": self.values["DB_DATA"]},
                "redis1": {"service": "redis", "env": [], "volume": self.values["REDIS_DATA"]},
                "odoo1": {
                    "service": "odoo",
                    "env": [
                        f"DB_NAME={self.values['DB_NAME']}", f"ODOO_DB={self.values['DB_NAME']}",
                        f"ODOO_DBFILTER={self.values['ODOO_DBFILTER']}", f"SC_SOURCE_REVISION={self.head}",
                    ],
                    "volume": self.values["ODOO_DATA"],
                    "source": str(ROOT / "addons"),
                },
            },
        }

    def test_resource_reuse_requires_same_frozen_sha_project_and_volumes(self) -> None:
        self.assertEqual(self.run_identity_command("freeze").returncode, 0)
        state = self.valid_resource_state()
        bin_dir, state_file = self.install_fake_docker(state)
        overrides = {"PATH": f"{bin_dir}:{os.environ['PATH']}", "FAKE_DOCKER_STATE": str(state_file)}
        self.assertEqual(self.run_identity_command("resources", overrides).returncode, 0)
        state["containers"]["odoo1"]["env"][-1] = f"SC_SOURCE_REVISION={'0' * 40}"  # type: ignore[index]
        state_file.write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(self.run_identity_command("resources", overrides).returncode, 2)
        state = self.valid_resource_state()
        state["volume_list"].append("foreign-volume")  # type: ignore[union-attr]
        state_file.write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(self.run_identity_command("resources", overrides).returncode, 2)


if __name__ == "__main__":
    unittest.main()
