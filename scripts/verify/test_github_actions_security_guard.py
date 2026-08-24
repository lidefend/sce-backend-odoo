#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import github_actions_security_guard as guard


PIN = "11bd71901bbe5b1630ceea73d27597364c9af683"
ROOT = Path(__file__).resolve().parents[2]


class GitHubActionsSecurityGuardTests(unittest.TestCase):
    def write(self, root: Path, name: str, content: str) -> None:
        target = root / ".github/workflows" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def test_safe_public_guard_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(
                root,
                "public_guard.yml",
                f"""name: public_guard
on:
  pull_request:
permissions:
  contents: read
jobs:
  public_guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{PIN}
""",
            )
            self.assertEqual(guard.scan(root), [])

    def test_pull_request_target_and_floating_action_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(
                root,
                "public_guard.yml",
                """name: unsafe
on:
  pull_request_target:
permissions:
  contents: write
jobs:
  public_guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
""",
            )
            classes = {item.classification for item in guard.scan(root)}
            self.assertIn("PULL_REQUEST_TARGET_FORBIDDEN", classes)
            self.assertIn("ACTION_NOT_PINNED_TO_SHA", classes)
            self.assertIn("MISSING_READ_ONLY_PERMISSIONS", classes)

    def test_self_hosted_fork_boundary_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(
                root,
                "professional_quality_gate.yml",
                """name: unsafe professional
on:
  pull_request:
permissions:
  contents: read
jobs:
  professional_quality_gate:
    runs-on: [self-hosted]
    steps:
      - run: make ci
""",
            )
            classes = {item.classification for item in guard.scan(root)}
            self.assertIn("SELF_HOSTED_REPOSITORY_GATE_MISSING", classes)
            self.assertIn("SELF_HOSTED_OWNER_DISPATCH_GATE_MISSING", classes)
            self.assertIn("SELF_HOSTED_FORK_GATE_MISSING", classes)
            self.assertIn("PROFESSIONAL_TRUST_BOUNDARY_INCOMPLETE", classes)

    def test_authorization_accepts_same_repository_pull_request(self) -> None:
        self.assertTrue(
            guard.authorization_allowed(
                event_name="pull_request",
                repository="lidefend/sce-backend-odoo",
                repository_owner="lidefend",
                actor="contributor",
                head_repository="lidefend/sce-backend-odoo",
            )
        )

    def test_authorization_rejects_legacy_and_unexpected_repositories(self) -> None:
        for repository, owner in (
            ("Leedefend/sce-product-odoo", "Leedefend"),
            ("unexpected/example", "unexpected"),
        ):
            with self.subTest(repository=repository):
                self.assertFalse(
                    guard.authorization_allowed(
                        event_name="pull_request",
                        repository=repository,
                        repository_owner=owner,
                        actor=owner,
                        head_repository=repository,
                    )
                )

    def test_authorization_rejects_fork_and_unsupported_system_actor(self) -> None:
        self.assertFalse(
            guard.authorization_allowed(
                event_name="pull_request",
                repository="lidefend/sce-backend-odoo",
                repository_owner="lidefend",
                actor="dependabot[bot]",
                head_repository="dependabot-fork/sce-backend-odoo",
            )
        )
        self.assertFalse(
            guard.authorization_allowed(
                event_name="schedule",
                repository="lidefend/sce-backend-odoo",
                repository_owner="lidefend",
                actor="github-actions[bot]",
            )
        )

    def test_dispatch_requires_current_repository_owner(self) -> None:
        common = {
            "event_name": "workflow_dispatch",
            "repository": "lidefend/sce-backend-odoo",
            "repository_owner": "lidefend",
        }
        self.assertTrue(guard.authorization_allowed(actor="lidefend", **common))
        self.assertFalse(guard.authorization_allowed(actor="collaborator", **common))

    def test_push_requires_exact_main_ref(self) -> None:
        common = {
            "event_name": "push",
            "repository": "lidefend/sce-backend-odoo",
            "repository_owner": "lidefend",
            "actor": "lidefend",
        }
        self.assertTrue(
            guard.authorization_allowed(ref="refs/heads/main", **common)
        )
        self.assertFalse(
            guard.authorization_allowed(
                ref="refs/heads/fix/not-main",
                **common,
            )
        )

    def test_frontend_release_workflow_contract_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(
                root,
                "frontend_release_gate.yml",
                f"""name: frontend_release_gate
on:
  pull_request:
permissions:
  contents: read
jobs:
  frontend_release_gate:
    name: frontend_release_gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{PIN}
""",
            )
            classes = {item.classification for item in guard.scan(root)}
            self.assertIn("FRONTEND_RELEASE_TRUST_BOUNDARY_INCOMPLETE", classes)

    def test_backend_suite_cleanup_identity_and_failure_visibility_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow = root / ".github/workflows/backend_test_suite.yml"
            workflow.parent.mkdir(parents=True)
            source = (ROOT / ".github/workflows/backend_test_suite.yml").read_text(encoding="utf-8")
            workflow.write_text(
                source.replace("      CI_PROJECT_NAME: sc-suite-${{ github.run_id }}\n", "", 1),
                encoding="utf-8",
            )
            classes = {item.classification for item in guard.scan(root)}
            self.assertIn("BACKEND_SUITE_CLEANUP_SCOPE_INCOMPLETE", classes)

            workflow.write_text(
                source.replace(
                    "bash scripts/ci/self_hosted_runner_cleanup.sh\n",
                    "bash scripts/ci/self_hosted_runner_cleanup.sh || true\n",
                    1,
                ),
                encoding="utf-8",
            )
            classes = {item.classification for item in guard.scan(root)}
            self.assertIn("BACKEND_SUITE_CLEANUP_FAILURE_MASKED", classes)

    def run_cleanup_fixture(self, project: str) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory)
            root = fixture / "repo"
            runner_temp = fixture / "_temp"
            fake_bin = fixture / "bin"
            script_dir = root / "scripts/ci"
            script_dir.mkdir(parents=True)
            runner_temp.mkdir()
            fake_bin.mkdir()
            shutil.copy(ROOT / "scripts/ci/self_hosted_runner_cleanup.sh", script_dir)

            docker_log = fixture / "docker.log"
            fake_docker = fake_bin / "docker"
            fake_docker.write_text(
                "#!/usr/bin/env bash\n"
                "printf '%s\\n' \"$*\" >> \"$DOCKER_CALL_LOG\"\n",
                encoding="utf-8",
            )
            fake_docker.chmod(0o755)
            environment = os.environ.copy()
            environment.update(
                {
                    "PATH": f"{fake_bin}:{environment['PATH']}",
                    "DOCKER_CALL_LOG": str(docker_log),
                    "GITHUB_ACTIONS": "true",
                    "GITHUB_REPOSITORY": "lidefend/sce-backend-odoo",
                    "GITHUB_RUN_ID": "12345",
                    "GITHUB_RUN_ATTEMPT": "1",
                    "GITHUB_WORKSPACE": str(root),
                    "RUNNER_TEMP": str(runner_temp),
                    "CI_PROJECT_NAME": project,
                }
            )
            result = subprocess.run(
                ["bash", str(script_dir / "self_hosted_runner_cleanup.sh")],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            calls = docker_log.read_text(encoding="utf-8") if docker_log.exists() else ""
            return result, calls

    def test_backend_suite_cleanup_accepts_only_exact_run_project(self) -> None:
        result, calls = self.run_cleanup_fixture("sc-suite-12345")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[self_hosted_cleanup] PASS project=sc-suite-12345", result.stdout)
        self.assertIn("compose -p sc-suite-12345 down -v --remove-orphans", calls)
        self.assertIn("label=com.docker.compose.project=sc-suite-12345", calls)

        for project in (
            "sc-suite-1234",
            "sc-suite-12345-extra",
            "sc-suite-${GITHUB_RUN_ID}",
        ):
            with self.subTest(project=project):
                result, calls = self.run_cleanup_fixture(project)
                self.assertEqual(result.returncode, 2)
                self.assertIn("invalid project scope", result.stderr)
                self.assertEqual(calls, "")


if __name__ == "__main__":
    unittest.main()
