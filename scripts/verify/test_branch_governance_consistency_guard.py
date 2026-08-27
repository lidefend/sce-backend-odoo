#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import branch_governance_consistency_guard as guard


ROOT = Path(__file__).resolve().parents[2]
FULL_SHA = "a" * 40
OTHER_SHA = "b" * 40


class BranchGovernanceConsistencyGuardTests(unittest.TestCase):
    def fixture(self, root: Path, *, make_regex: str = guard.CANONICAL_REGEX) -> None:
        (root / "docs/ops").mkdir(parents=True)
        (root / "make").mkdir()
        (root / "scripts/ops").mkdir(parents=True)
        prefixes = ", ".join(f"`{item}`" for item in guard.CANONICAL_PREFIXES)
        bullets = "\n".join(f"* `{item}`" for item in guard.CANONICAL_PREFIXES)
        workspace = "、".join(f"`{item}`" for item in guard.CANONICAL_PREFIXES)
        (root / "AGENTS.md").write_text(
            f"Canonical allowed write branches: {prefixes}.\n{guard.MARKER}\n",
            encoding="utf-8",
        )
        (root / "docs/ops/codex_execution_allowlist.md").write_text(
            f"{guard.MARKER}\n{bullets}\n",
            encoding="utf-8",
        )
        (root / "docs/ops/codex_workspace_execution_rules.md").write_text(
            f"{guard.MARKER}\n{workspace}\n",
            encoding="utf-8",
        )
        (root / "make/codex.mk").write_text(
            "\n".join(
                (
                    f"CODEX_ALLOWED_WRITE_BRANCH_REGEX := {make_regex}",
                    "CODEX_ALLOWED_WRITE_BRANCH_PREFIXES := " + " ".join(guard.CANONICAL_PREFIXES),
                    "a: ; test $(CODEX_ALLOWED_WRITE_BRANCH_REGEX)",
                    "b: ; test $(CODEX_ALLOWED_WRITE_BRANCH_REGEX)",
                    "c: ; test $(CODEX_ALLOWED_WRITE_BRANCH_REGEX)",
                )
            ),
            encoding="utf-8",
        )
        for relative in guard.SHELL_GUARDS:
            (root / relative).write_text(
                f"CANONICAL_ALLOWED_WRITE_BRANCH_REGEX='{guard.CANONICAL_REGEX}'\n"
                "test $CANONICAL_ALLOWED_WRITE_BRANCH_REGEX\n",
                encoding="utf-8",
            )

    def test_consistent_policy_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            self.assertEqual(guard.validate(root), [])

    def test_make_regex_drift_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root, make_regex="^(feature|fix)/.+")
            self.assertIn(
                "make/codex.mk: CODEX_ALLOWED_WRITE_BRANCH_REGEX diverges",
                guard.validate(root),
            )


class ControlledMergeExpectedHeadTests(unittest.TestCase):
    def run_merge(
        self,
        *,
        expected_head: str | None,
        actual_head: str = FULL_SHA,
        method: str = "merge",
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            merge_log = root / "merge.log"
            git = bin_dir / "git"
            git.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [[ \"$1 $2 $3\" == \"rev-parse --abbrev-ref HEAD\" ]]; then\n"
                "  printf '%s\\n' 'fix/controlled-merge-expected-head-guard'\n"
                "else\n"
                "  echo \"unexpected git invocation: $*\" >&2\n"
                "  exit 90\n"
                "fi\n",
                encoding="utf-8",
            )
            gh = bin_dir / "gh"
            gh.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [[ \"$1 $2 ${3:-}\" == \"pr merge --help\" ]]; then\n"
                "  echo '      --match-head-commit SHA'\n"
                "  for index in $(seq 1 10000); do echo \"merge help padding $index\"; done\n"
                "elif [[ \"$1 $2\" == \"pr view\" ]]; then\n"
                "  printf '%s\\n' \"${FAKE_ACTUAL_HEAD:?}\"\n"
                "elif [[ \"$1 $2\" == \"pr merge\" ]]; then\n"
                "  shift 2\n"
                "  printf '%s\\n' \"$@\" >\"${FAKE_MERGE_LOG:?}\"\n"
                "else\n"
                "  echo \"unexpected gh invocation: $*\" >&2\n"
                "  exit 91\n"
                "fi\n",
                encoding="utf-8",
            )
            git.chmod(0o755)
            gh.chmod(0o755)
            environment = dict(os.environ)
            environment.update(
                {
                    "ENV": "test",
                    "PATH": f"{bin_dir}:{environment['PATH']}",
                    "FAKE_ACTUAL_HEAD": actual_head,
                    "FAKE_MERGE_LOG": str(merge_log),
                }
            )
            command = [
                "make",
                "--no-print-directory",
                "pr.merge",
                "PR=30",
                f"PR_MERGE_METHOD={method}",
            ]
            if expected_head is not None:
                command.append(f"EXPECTED_HEAD={expected_head}")
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            arguments = (
                merge_log.read_text(encoding="utf-8").splitlines()
                if merge_log.exists()
                else []
            )
            return completed, arguments

    def test_missing_expected_head_is_rejected_without_merge(self) -> None:
        completed, arguments = self.run_merge(expected_head=None)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("EXPECTED_HEAD must be", completed.stdout)
        self.assertEqual(arguments, [])

    def test_short_and_non_hex_expected_heads_are_rejected_without_merge(self) -> None:
        for value in ("abc123", "g" * 40):
            with self.subTest(value=value):
                completed, arguments = self.run_merge(expected_head=value)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("EXPECTED_HEAD must be", completed.stdout)
                self.assertEqual(arguments, [])

    def test_shell_metacharacters_are_rejected_without_merge(self) -> None:
        completed, arguments = self.run_merge(expected_head=FULL_SHA + ";touch /tmp/x")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("EXPECTED_HEAD must be", completed.stdout)
        self.assertEqual(arguments, [])

    def test_live_head_mismatch_is_rejected_without_merge(self) -> None:
        completed, arguments = self.run_merge(
            expected_head=FULL_SHA,
            actual_head=OTHER_SHA,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn(f"expected_head={FULL_SHA} actual_head={OTHER_SHA}", completed.stdout)
        self.assertEqual(arguments, [])

    def test_matching_head_is_propagated_with_approved_method(self) -> None:
        completed, arguments = self.run_merge(expected_head=FULL_SHA)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(
            arguments,
            [
                "30",
                "--merge",
                "--match-head-commit",
                FULL_SHA,
                "--subject",
                "Merge PR #30",
                "--body",
                "Merged by Codex through make pr.merge.",
            ],
        )
        self.assertNotIn("--auto", arguments)


class ControlledReadyExpectedHeadTests(unittest.TestCase):
    def run_ready(
        self,
        *,
        expected_head: str | None,
        actual_head: str = FULL_SHA,
        is_draft: str = "true",
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir()
            ready_log = root / "ready.log"
            git = bin_dir / "git"
            git.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [[ \"$1 $2 $3\" == \"rev-parse --abbrev-ref HEAD\" ]]; then\n"
                "  printf '%s\\n' 'fix/atomic-release-publication-contract'\n"
                "else\n"
                "  echo \"unexpected git invocation: $*\" >&2\n"
                "  exit 90\n"
                "fi\n",
                encoding="utf-8",
            )
            gh = bin_dir / "gh"
            gh.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [[ \"$1 $2\" == \"pr view\" ]]; then\n"
                "  printf '%s\\t%s\\n' \"${FAKE_ACTUAL_HEAD:?}\" \"${FAKE_IS_DRAFT:?}\"\n"
                "elif [[ \"$1 $2\" == \"pr ready\" ]]; then\n"
                "  printf '%s\\n' \"$@\" >\"${FAKE_READY_LOG:?}\"\n"
                "else\n"
                "  echo \"unexpected gh invocation: $*\" >&2\n"
                "  exit 91\n"
                "fi\n",
                encoding="utf-8",
            )
            git.chmod(0o755)
            gh.chmod(0o755)
            environment = dict(os.environ)
            environment.update(
                {
                    "ENV": "test",
                    "PATH": f"{bin_dir}:{environment['PATH']}",
                    "FAKE_ACTUAL_HEAD": actual_head,
                    "FAKE_IS_DRAFT": is_draft,
                    "FAKE_READY_LOG": str(ready_log),
                }
            )
            command = ["make", "--no-print-directory", "pr.ready", "PR=34"]
            if expected_head is not None:
                command.append(f"EXPECTED_HEAD={expected_head}")
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            arguments = (
                ready_log.read_text(encoding="utf-8").splitlines()
                if ready_log.exists()
                else []
            )
            return completed, arguments

    def test_missing_or_invalid_expected_head_is_rejected(self) -> None:
        for value in (None, "abc123", "g" * 40, FULL_SHA + ";touch /tmp/x"):
            with self.subTest(value=value):
                completed, arguments = self.run_ready(expected_head=value)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn("EXPECTED_HEAD must be", completed.stdout)
                self.assertEqual(arguments, [])

    def test_live_head_mismatch_is_rejected_without_ready_write(self) -> None:
        completed, arguments = self.run_ready(
            expected_head=FULL_SHA,
            actual_head=OTHER_SHA,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn(f"expected_head={FULL_SHA} actual_head={OTHER_SHA}", completed.stdout)
        self.assertEqual(arguments, [])

    def test_non_draft_pr_is_rejected_without_ready_write(self) -> None:
        completed, arguments = self.run_ready(
            expected_head=FULL_SHA,
            is_draft="false",
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("PR is not draft", completed.stdout)
        self.assertEqual(arguments, [])

    def test_matching_draft_head_uses_ready_command_once(self) -> None:
        completed, arguments = self.run_ready(expected_head=FULL_SHA)
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(arguments, ["pr", "ready", "34"])


class MergePrepGateTests(unittest.TestCase):
    """make pr.merge.prep verifies every gate is green on the exact PR head
    and reports the merge_policy_gate commit status so the base-branch
    ruleset (required_status_checks: merge_policy_gate) can see the
    workflow_dispatch runs."""

    def _run_prep(
        self, *, gate_state: str = "success", gate_fail: str = "0"
    ) -> tuple[subprocess.CompletedProcess[str], list[str]]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bin_dir = root / "bin"
            bin_dir.mkdir(parents=True)
            status_log = root / "status.log"
            gh = bin_dir / "gh"
            gh.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [[ \"$1 $2\" == \"pr view\" ]]; then\n"
                "  printf '%s\\n' \"${FAKE_ACTUAL_HEAD:?}\"\n"
                "elif [[ \"$1 $2\" == \"repo view\" ]]; then\n"
                "  printf '%s\\n' 'lidefend/sce-backend-odoo'\n"
                "elif [[ \"$1\" == \"api\" && \"$2\" == *\"/runs?\"* ]]; then\n"
                "  if [ \"${FAKE_GATE_FAIL:-0}\" = 1 ]; then exit 92; fi\n"
                "  printf '%s\\n' \"${FAKE_GATE_STATE:?}\"\n"
                "elif [[ \"$1\" == \"api\" && \"$*\" == *\"statuses/\"* ]]; then\n"
                "  echo \"$*\" >>\"${FAKE_STATUS_LOG:?}\"\n"
                "else\n"
                "  echo \"unexpected gh invocation: $*\" >&2\n"
                "  exit 91\n"
                "fi\n",
                encoding="utf-8",
            )
            gh.chmod(0o755)
            environment = dict(os.environ)
            environment.update(
                {
                    "ENV": "test",
                    "PATH": f"{bin_dir}:{environment['PATH']}",
                    "FAKE_ACTUAL_HEAD": FULL_SHA,
                    "FAKE_GATE_STATE": gate_state,
                    "FAKE_GATE_FAIL": gate_fail,
                    "FAKE_STATUS_LOG": str(status_log),
                }
            )
            completed = subprocess.run(
                ["make", "--no-print-directory", "pr.merge.prep", "PR=30"],
                cwd=ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            status_lines = status_log.read_text(encoding="utf-8").splitlines() if status_log.exists() else []
            return completed, status_lines

    def test_all_gates_success_reports_merge_policy_gate_status(self) -> None:
        completed, status_lines = self._run_prep()
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertEqual(len(status_lines), 1)
        self.assertIn("statuses/", status_lines[0])
        self.assertIn("state=success", status_lines[0])
        self.assertIn("context=merge_policy_gate", status_lines[0])

    def test_failing_gate_is_rejected_without_status(self) -> None:
        completed, status_lines = self._run_prep(gate_state="failure")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("gate frontend_release_gate not success", completed.stdout)
        self.assertEqual(status_lines, [])

    def test_missing_gate_is_rejected_without_status(self) -> None:
        completed, status_lines = self._run_prep(gate_fail="1")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("not success (missing)", completed.stdout)
        self.assertEqual(status_lines, [])


if __name__ == "__main__":
    unittest.main()
