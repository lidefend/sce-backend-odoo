from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/dev/local_dev_frontend_quick.py"
SPEC = importlib.util.spec_from_file_location("local_dev_frontend_quick", MODULE_PATH)
assert SPEC and SPEC.loader
QUICK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(QUICK)


class LocalDevFrontendQuickTest(unittest.TestCase):
    def _authority_fixture(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        primary = base / "primary"
        linked = base / "linked"
        common = primary / ".git"
        common.mkdir(parents=True)
        linked.mkdir()
        authority = primary / ".env.dev"
        authority.write_text("ENV=dev\nDB_PASSWORD=not-printed\n", encoding="utf-8")
        authority.chmod(0o600)
        return temporary, primary, linked, authority

    def _git_identity(self, primary: Path, linked: Path):
        common = (primary / ".git").resolve()

        def output(repo: Path, *args: str) -> str:
            repo = repo.resolve()
            if args == ("rev-parse", "--show-toplevel"):
                return str(linked if repo == linked.resolve() else primary)
            if args == (
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            ):
                return str(common)
            raise AssertionError((repo, args))

        return output

    def test_linked_worktree_resolves_only_primary_authority(self):
        _temporary, primary, linked, authority = self._authority_fixture()
        with mock.patch.object(QUICK, "_git_output", self._git_identity(primary, linked)), mock.patch.dict(
            os.environ,
            {"ENV_FILE": "/tmp/untrusted", "LOCAL_DEV_ENV_FILE": "/tmp/untrusted"},
        ):
            self.assertEqual(QUICK.resolve_authority_env(linked), authority)

    def test_git_identity_lookup_rejects_inherited_git_overrides(self):
        completed = subprocess.CompletedProcess(
            ["git", "rev-parse", "--show-toplevel"],
            0,
            stdout="/governed/root\n",
            stderr="",
        )
        with mock.patch.dict(
            os.environ,
            {"GIT_DIR": "/tmp/untrusted", "GIT_WORK_TREE": "/tmp/untrusted"},
        ), mock.patch.object(subprocess, "run", return_value=completed) as run:
            self.assertEqual(
                QUICK._git_output(Path("/governed/root"), "rev-parse", "--show-toplevel"),
                "/governed/root",
            )
        invoked_environment = run.call_args.kwargs["env"]
        self.assertNotIn("GIT_DIR", invoked_environment)
        self.assertNotIn("GIT_WORK_TREE", invoked_environment)

    def test_missing_symlink_and_wrong_permissions_fail_closed(self):
        _temporary, primary, linked, authority = self._authority_fixture()
        git_identity = self._git_identity(primary, linked)
        authority.unlink()
        with mock.patch.object(QUICK, "_git_output", git_identity):
            with self.assertRaisesRegex(QUICK.LocalDevAuthorityError, "missing"):
                QUICK.resolve_authority_env(linked)

        target = primary / "real-env"
        target.write_text("ENV=dev\n", encoding="utf-8")
        target.chmod(0o600)
        authority.symlink_to(target)
        with mock.patch.object(QUICK, "_git_output", git_identity):
            with self.assertRaisesRegex(QUICK.LocalDevAuthorityError, "regular file"):
                QUICK.resolve_authority_env(linked)

        authority.unlink()
        authority.write_text("ENV=dev\n", encoding="utf-8")
        authority.chmod(0o640)
        with mock.patch.object(QUICK, "_git_output", git_identity):
            with self.assertRaisesRegex(QUICK.LocalDevAuthorityError, "0600"):
                QUICK.resolve_authority_env(linked)

    def test_ready_failure_stops_before_quick_and_does_not_log_credentials(self):
        _temporary, _primary, linked, authority = self._authority_fixture()
        calls: list[list[str]] = []

        def runner(command, **_kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 2)

        output = io.StringIO()
        with mock.patch.object(QUICK, "resolve_authority_env", return_value=authority), contextlib.redirect_stdout(output):
            result = QUICK.run_gate(linked, runner=runner)
        self.assertEqual(result, 2)
        self.assertEqual(len(calls), 1)
        self.assertIn("local.dev.ready", calls[0])
        self.assertNotIn("not-printed", output.getvalue())

    def test_ready_success_runs_original_quick_with_fixed_dev_authority(self):
        _temporary, _primary, linked, authority = self._authority_fixture()
        calls: list[tuple[list[str], dict[str, str]]] = []

        def runner(command, **kwargs):
            calls.append((command, kwargs["env"]))
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(QUICK, "resolve_authority_env", return_value=authority), mock.patch.dict(
            os.environ,
            {
                "ENV": "prod",
                "ENV_FILE": "/tmp/untrusted",
                "LOCAL_DEV_ENV_FILE": "/tmp/untrusted",
                "MAKEFLAGS": "ENV_FILE=/tmp/untrusted",
                "GIT_DIR": "/tmp/untrusted",
            },
        ):
            self.assertEqual(QUICK.run_gate(linked, runner=runner), 0)

        self.assertEqual(len(calls), 2)
        self.assertIn("local.dev.ready", calls[0][0])
        self.assertIn("verify.frontend.quick.gate", calls[1][0])
        self.assertIn("ENV=dev", calls[1][0])
        self.assertIn(f"ENV_FILE={authority}", calls[1][0])
        for _command, environment in calls:
            self.assertNotIn("ENV_FILE", environment)
            self.assertNotIn("LOCAL_DEV_ENV_FILE", environment)
            self.assertNotIn("MAKEFLAGS", environment)
            self.assertNotIn("GIT_DIR", environment)

    def test_wrong_profile_is_rejected_by_existing_local_dev_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env.dev"
            env_file.write_text(
                "\n".join(
                    (
                        "ENV=dev",
                        "COMPOSE_PROJECT_NAME=sc-local-sample",
                        "DB_NAME=sc_dev_sample",
                        "DB_USER=synthetic",
                        "DB_PASSWORD=synthetic",
                        "ADMIN_PASSWD=synthetic",
                        "JWT_SECRET=synthetic",
                        "ODOO_DBFILTER=^sc_dev_sample$",
                        "DB_DATA=sc_local_sample_db_data",
                        "REDIS_DATA=sc_local_sample_redis_data",
                        "ODOO_DATA=sc_local_sample_odoo_data",
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            env_file.chmod(0o600)
            environment = QUICK._isolated_environment()
            environment.update(ENV="dev", ENV_FILE=str(env_file), ROOT_DIR=str(ROOT))
            result = subprocess.run(
                ["bash", str(ROOT / "scripts/dev/local_dev_readiness.sh")],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("identity mismatch", result.stderr)

    def test_original_quick_and_static_build_semantics_remain_unchanged(self):
        frontend_make = (ROOT / "make/frontend.mk").read_text(encoding="utf-8")
        dev_make = (ROOT / "make/dev.mk").read_text(encoding="utf-8")
        self.assertNotIn("verify.local.dev.frontend.quick.gate", frontend_make)
        self.assertIn("verify.frontend.quick.gate: guard.prod.forbid", frontend_make)
        self.assertIn("verify.frontend.build", frontend_make)
        local_frontend = dev_make.split("local.dev.frontend:", 1)[1].split("\n\n", 1)[0]
        self.assertIn("local.dev.ready", local_frontend)
        self.assertIn("frontend_static_build.sh", local_frontend)

    def test_terminal_frontend_build_recipe_receives_the_authoritative_env_file(self):
        """The final shell recipe, not only Python's make arguments, carries authority."""
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Path(directory)
            authority = sandbox / "primary.env.dev"
            authority.write_text("ENV=dev\n", encoding="utf-8")
            capture = sandbox / "terminal-env.txt"
            bin_dir = sandbox / "bin"
            bin_dir.mkdir()
            fake_bash = bin_dir / "bash"
            fake_bash.write_text(
                "#!/bin/sh\n"
                "case \"$*\" in *scripts/dev/frontend_static_build.sh*)\n"
                "  printf '%s\\n%s\\n%s\\n' \"${ENV:-}\" \"${ENV_FILE:-}\" \"${ROOT_DIR:-}\" > \"$TERMINAL_ENV_CAPTURE\"\n"
                "esac\n",
                encoding="utf-8",
            )
            fake_bash.chmod(0o755)
            environment = os.environ.copy()
            environment.update(
                PATH=f"{bin_dir}:{environment['PATH']}",
                TERMINAL_ENV_CAPTURE=str(capture),
                ENV="untrusted",
                ENV_FILE="/tmp/untrusted",
                ROOT_DIR="/tmp/untrusted",
            )
            result = subprocess.run(
                [
                    "make",
                    "--no-print-directory",
                    f"PATH={bin_dir}:{environment['PATH']}",
                    f"TERMINAL_ENV_CAPTURE={capture}",
                    "ENV=dev",
                    f"ENV_FILE={authority}",
                    f"ROOT_DIR={ROOT}",
                    "verify.frontend.build",
                ],
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(capture.read_text(encoding="utf-8").splitlines(), ["dev", str(authority), str(ROOT)])

    def test_frontend_build_recipe_forwards_only_its_resolved_make_authority(self):
        frontend_make = (ROOT / "make/frontend.mk").read_text(encoding="utf-8")
        recipe = frontend_make.split("verify.frontend.build: guard.prod.forbid", 1)[1].split("\n\n", 1)[0]
        self.assertIn('ENV="$(ENV)"', recipe)
        self.assertIn('ENV_FILE="$(ENV_FILE)"', recipe)
        self.assertIn('ROOT_DIR="$(ROOT_DIR)"', recipe)
        self.assertIn("bash scripts/dev/frontend_static_build.sh", recipe)

    def test_new_governance_sources_contain_no_machine_specific_path_or_env_mutation(self):
        sources = [MODULE_PATH, ROOT / "scripts/verify/test_local_dev_frontend_quick.py"]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in sources)
        self.assertNotIn("/" + "home/", combined)
        self.assertNotIn("lide" + "fend", combined)
        self.assertNotIn("shutil." + "copy", combined)
        self.assertNotIn("os." + "symlink", combined)


if __name__ == "__main__":
    unittest.main()
