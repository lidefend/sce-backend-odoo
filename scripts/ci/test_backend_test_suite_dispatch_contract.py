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


if __name__ == "__main__":
    unittest.main()
