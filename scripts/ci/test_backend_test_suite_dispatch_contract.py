import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class BackendTestSuiteDispatchContractTest(unittest.TestCase):
    def test_dispatch_is_exact_head_and_full_suite_only(self):
        makefile = (ROOT / "make/ci.mk").read_text(encoding="utf-8")
        target = makefile.split("ci.backend_test_suite.dispatch:", 1)[1].split("\n.PHONY:", 1)[0]

        for required in (
            "guard.prod.forbid",
            "EXPECTED_HEAD",
            "git status --porcelain",
            "git rev-parse HEAD",
            "git ls-remote --heads origin",
            "cut -f1",
            "gh pr view --json headRefOid",
            "gh workflow run backend_test_suite.yml",
            '-f "head_ref=$$branch"',
        ):
            self.assertIn(required, target)

        self.assertNotIn("modules=", target)
        self.assertNotIn("test_tags=", target)

    def test_workflow_supports_governed_dispatch_inputs(self):
        workflow = (ROOT / ".github/workflows/backend_test_suite.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("head_ref:", workflow)
        self.assertIn("HEAD_REF: ${{ github.event.inputs.head_ref || github.ref_name }}", workflow)
        self.assertIn("CI_PROJECT_NAME: sc-suite-${{ github.run_id }}", workflow)
        self.assertIn("docker compose down -v --remove-orphans", workflow)


class BackendTestSuiteStepIntegrityTest(unittest.TestCase):
    """The per-module step must not be able to report a truncated scope as a pass.

    2026-10-10 triage: GitHub executes ``shell: bash`` steps with errexit on.
    The step accumulated failures in ``failed`` and asserted it at the end, but
    left errexit enabled, so the first failing module aborted the step and every
    later module - plus the whole ``failed`` accumulation - became dead code.
    The 2026-10-09 nightly reported green from that truncated scope.
    """

    def _step(self) -> str:
        workflow = (ROOT / ".github/workflows/backend_test_suite.yml").read_text(
            encoding="utf-8"
        )
        return workflow.split(
            "- name: Run backend test suite per module", 1
        )[1].split("- name: Dump logs on failure", 1)[0]

    def test_step_declares_the_bash_shell_that_enables_errexit(self) -> None:
        workflow = (ROOT / ".github/workflows/backend_test_suite.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("shell: bash", workflow)

    def test_step_disables_errexit_before_accumulating(self) -> None:
        step = self._step()
        self.assertIn("set +e", step)
        for line in step.splitlines():
            stripped = line.strip()
            if not stripped.startswith("set "):
                continue
            self.assertFalse(
                re.search(r"(?<![\w+])-[a-z]*e", stripped),
                f"errexit must stay disabled in the accumulation loop: {stripped!r}",
            )

    def test_step_asserts_the_executed_scope_equals_the_planned_scope(self) -> None:
        step = self._step()
        self.assertIn("attempted=$((attempted + 1))", step)
        self.assertIn("execution truncated", step)
        self.assertIn('test "${failed}" -eq 0', step)

    def test_step_keeps_the_zero_test_guard(self) -> None:
        step = self._step()
        self.assertIn("0 failed, 0 error\\(s\\) of [1-9][0-9]* tests", step)


if __name__ == "__main__":
    unittest.main()
