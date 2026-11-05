#!/usr/bin/env python3
from __future__ import annotations

import unittest
import subprocess
import tempfile
import os
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ReleaseCandidateGateContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = (
            ROOT / ".github/workflows/release_candidate_gate.yml"
        ).read_text(encoding="utf-8")

    def test_only_explicit_candidate_paths_can_run_release_gate(self) -> None:
        self.assertIn("name: release_candidate_gate", self.workflow)
        self.assertIn("github.event_name != 'pull_request'", self.workflow)
        self.assertIn("github.event.action == 'labeled' && github.event.label.name == 'ci:candidate'", self.workflow)
        self.assertIn(
            "types: [opened, reopened, synchronize, labeled]",
            self.workflow,
        )
        self.assertIn("cron: '30 18 * * *'", self.workflow)
        self.assertNotIn("  push:\n    branches: [main]", self.workflow)

    def test_release_gate_waits_for_exact_head_candidate_checks(self) -> None:
        self.assertIn("Wait for exact-head candidate checks", self.workflow)
        self.assertIn("public_guard.yml", self.workflow)
        self.assertIn("professional_quality_gate.yml", self.workflow)
        self.assertIn("frontend_release_gate.yml", self.workflow)
        self.assertIn("merge_policy_gate.yml", self.workflow)
        self.assertIn("select_authoritative_workflow_run.py", self.workflow)
        self.assertNotIn("event=${GITHUB_EVENT_NAME}", self.workflow)
        self.assertIn("candidate workflow failed", self.workflow)
        self.assertIn("timed out waiting for exact-head candidate checks", self.workflow)

    def test_release_gate_publishes_release_summary(self) -> None:
        self.assertIn("Publish release-candidate summary", self.workflow)
        self.assertIn("This exact head passed merge eligibility and explicit candidate validation.", self.workflow)
        self.assertIn("GITHUB_STEP_SUMMARY", self.workflow)
        self.assertIn("release_candidate_gate", self.workflow)

    def test_candidate_summary_distinguishes_pass_skip_and_failure(self) -> None:
        workflow = yaml.safe_load(self.workflow)
        script = workflow['jobs']['release_candidate_gate']['steps'][0]['run']
        with tempfile.TemporaryDirectory() as directory:
            summary = Path(directory) / 'summary'
            for result, passed, message in [
                ('success', True, 'executed and passed'),
                ('skipped', True, 'not applicable (not executed)'),
                ('failure', False, 'pending or failed'),
                ('cancelled', False, 'pending or failed'),
            ]:
                with self.subTest(result=result):
                    summary.unlink(missing_ok=True)
                    proc = subprocess.run(['bash', '-ec', script.replace(
                        '${{ needs.wait_for_candidate_checks.result }}', result)],
                        env=dict(os.environ, GITHUB_STEP_SUMMARY=str(summary)),
                        text=True, capture_output=True)
                    self.assertEqual(proc.returncode == 0, passed, proc.stderr)
                    self.assertIn(message, summary.read_text())


if __name__ == "__main__":
    unittest.main()
