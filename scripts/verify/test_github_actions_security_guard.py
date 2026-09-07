#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
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

    def test_professional_artifact_writers_must_remain_serialized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow = root / ".github/workflows/professional_quality_gate.yml"
            workflow.parent.mkdir(parents=True)
            source = (ROOT / workflow.relative_to(root)).read_text(encoding="utf-8")
            workflow.write_text(
                source.replace(
                    "make ci.professional.backend.shard-verify\n",
                    "make ci.professional.backend.shard-verify &\n",
                    1,
                ),
                encoding="utf-8",
            )
            classes = {item.classification for item in guard.scan(root)}
            self.assertIn("PROFESSIONAL_ARTIFACT_WRITERS_NOT_SERIALIZED", classes)

    def test_professional_artifact_root_must_be_host_owned_before_orm(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow = root / ".github/workflows/professional_quality_gate.yml"
            workflow.parent.mkdir(parents=True)
            source = (ROOT / workflow.relative_to(root)).read_text(encoding="utf-8")
            preparation = """      - name: Prepare host-owned artifact root before container checks
        if: env.PROFESSIONAL_MODE == 'full'
        run: python3 scripts/verify/ci_artifact_host_write_guard.py

"""
            self.assertIn(preparation, source)
            workflow.write_text(source.replace(preparation, "", 1), encoding="utf-8")
            classes = {item.classification for item in guard.scan(root)}
            self.assertIn("PROFESSIONAL_ARTIFACT_WRITERS_NOT_SERIALIZED", classes)

    def test_backend_suite_dynamic_secrets_must_remain_masked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow = root / ".github/workflows/backend_test_suite.yml"
            workflow.parent.mkdir(parents=True)
            source = (ROOT / workflow.relative_to(root)).read_text(encoding="utf-8")
            workflow.write_text(
                source.replace('echo "::add-mask::${demo_password}"\n', "", 1),
                encoding="utf-8",
            )
            classes = {item.classification for item in guard.scan(root)}
            self.assertIn("BACKEND_SUITE_DYNAMIC_SECRET_MASKING_INCOMPLETE", classes)

    def test_backend_suite_module_isolation_and_nonzero_evidence_are_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow = root / ".github/workflows/backend_test_suite.yml"
            workflow.parent.mkdir(parents=True)
            source = (ROOT / workflow.relative_to(root)).read_text(encoding="utf-8")

            workflow.write_text(
                source.replace("scope_test_tags()", "scope_all_test_tags()", 1),
                encoding="utf-8",
            )
            classes = {item.classification for item in guard.scan(root)}
            self.assertIn("BACKEND_SUITE_MODULE_ISOLATION_INCOMPLETE", classes)

            workflow.write_text(
                source.replace("NON_ZERO_RESULT_RE=", "UNTRUSTED_RESULT_RE=", 1),
                encoding="utf-8",
            )
            classes = {item.classification for item in guard.scan(root)}
            self.assertIn("BACKEND_SUITE_NONZERO_EVIDENCE_INCOMPLETE", classes)

    def backend_suite_functions(self) -> str:
        source = (ROOT / ".github/workflows/backend_test_suite.yml").read_text(encoding="utf-8")
        start = source.index("          NON_ZERO_RESULT_RE=")
        end = source.index("\n          failed=0", start)
        return textwrap.dedent(source[start:end])

    def run_backend_suite_function(self, command: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            environment = os.environ.copy()
            environment.update({"RUNNER_TEMP": directory, "GITHUB_RUN_ID": "12345"})
            return subprocess.run(
                ["bash", "-c", f"set -uo pipefail\n{self.backend_suite_functions()}\n{command}"],
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=environment,
            )

    def test_backend_suite_default_and_override_selectors_stay_in_module(self) -> None:
        result = self.run_backend_suite_function(
            "test \"$(scope_test_tags smart_core '')\" = 'sc_smoke/smart_core' && "
            "test \"$(scope_test_tags smart_construction_core '')\" = "
            "'sc_install/smart_construction_core' && "
            "test \"$(scope_test_tags smart_construction_scene '')\" = "
            "'/smart_construction_scene' && "
            "test \"$(scope_test_tags smart_core 'sc_smoke,sc_gate')\" = "
            "'sc_smoke/smart_core,sc_gate/smart_core' && "
            "test \"$(scope_test_tags smart_core '-slow')\" = '-slow/smart_core' && "
            "test \"$(scope_test_tags smart_core '.test_one')\" = "
            "'/smart_core.test_one'"
        )
        self.assertEqual(result.returncode, 0, result.stdout)

        result = self.run_backend_suite_function(
            "scope_test_tags smart_core 'sc_gate/smart_construction_core'"
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("escapes target module smart_core", result.stdout)

    def test_backend_suite_default_selectors_reference_real_module_tests(self) -> None:
        expected = {
            "sc_norm_engine": "sc_regression",
            "smart_construction_acceptance_fixture": "acceptance_fixture_gate",
            "smart_construction_bootstrap": "locale_baseline",
            "smart_construction_core": "sc_install",
            "smart_construction_demo": "demo_gate",
            "smart_construction_portal": "contract_dashboard",
            "smart_construction_seed": "sc_smoke",
            "smart_core": "sc_smoke",
            "smart_license_core": "tier_gate",
            "smart_owner_bundle": "registry_consistency",
            "smart_owner_core": "extension_contract",
            "smart_scene": "scene_resolver",
        }
        for module, tag in expected.items():
            with self.subTest(module=module):
                result = self.run_backend_suite_function(f"scope_test_tags {module} ''")
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual(result.stdout.strip(), f"{tag}/{module}")
                module_root = ROOT / ("demo_addons" if module == "smart_construction_demo" else "addons") / module
                test_source = "\n".join(
                    path.read_text(encoding="utf-8")
                    for path in sorted((module_root / "tests").glob("test_*.py"))
                )
                self.assertRegex(test_source, rf"['\"]{tag}['\"]")

        for module in ("smart_construction_bundle", "smart_construction_scene"):
            with self.subTest(module=module):
                result = self.run_backend_suite_function(f"scope_test_tags {module} ''")
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertEqual(result.stdout.strip(), f"/{module}")
                self.assertTrue(list((ROOT / "addons" / module / "tests").glob("test_*.py")))

    def test_common_tag_normalizer_emits_only_odoo_module_scoped_selectors(self) -> None:
        command = """
source scripts/_lib/common.sh
test "$(normalize_test_tags smart_core 'sc_smoke,sc_gate,-slow')" = \
  'sc_smoke/smart_core,sc_gate/smart_core,-slow/smart_core'
test "$(normalize_test_tags smart_core 'sc_install/smart_core,/smart_core:TestCase,.test_one')" = \
  'sc_install/smart_core,/smart_core:TestCase,/smart_core.test_one'
"""
        result = subprocess.run(
            ["bash", "-c", command],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_backend_suite_rejects_zero_test_summary(self) -> None:
        command = """
make() { printf '%s\n' '0 failed, 0 error(s) of 0 tests'; }
run_module_test smart_core sc_suite_ci_smart_core /tmp/fake.env /smart_core
"""
        result = self.run_backend_suite_function(command)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("produced no non-zero passing test summary", result.stdout)

    def test_backend_suite_accepts_nonzero_passing_summary(self) -> None:
        command = """
make() { printf '%s\n' '0 failed, 0 error(s) of 14 tests'; }
run_module_test smart_core sc_suite_ci_smart_core /tmp/fake.env /smart_core
"""
        result = self.run_backend_suite_function(command)
        self.assertEqual(result.returncode, 0, result.stdout)

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
