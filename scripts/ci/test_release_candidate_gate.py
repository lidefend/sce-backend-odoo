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
            "types: [labeled]",
            self.workflow,
        )
        self.assertIn("cron: '0 18 * * *'", self.workflow)
        self.assertNotIn("  push:\n    branches: [main]", self.workflow)

    def test_release_gate_waits_for_exact_head_candidate_checks(self) -> None:
        self.assertIn("Wait for exact-head candidate checks", self.workflow)
        self.assertIn("public_guard.yml", self.workflow)
        self.assertIn("professional_quality_gate.yml", self.workflow)
        self.assertIn("frontend_release_gate.yml", self.workflow)
        self.assertIn("merge_policy_gate.yml", self.workflow)
        self.assertIn("select_authoritative_workflow_run.py", self.workflow)
        self.assertNotIn('--event "$GITHUB_EVENT_NAME"', self.workflow)
        self.assertIn('--aggregate-event "$GITHUB_EVENT_NAME"', self.workflow)
        self.assertIn('--head-branch "$expected_head_branch"', self.workflow)
        self.assertIn('--head-repository "$GITHUB_REPOSITORY"', self.workflow)
        self.assertIn("--workflow-dispatch-producer workflow_dispatch", self.workflow)
        self.assertIn('schedule|pull_request|workflow_dispatch) producer_event="${GITHUB_EVENT_NAME}"', self.workflow)
        self.assertIn("MISSING_DEPENDENCY_GRACE_ATTEMPTS", self.workflow)
        self.assertIn("Missing Candidate Dependencies", self.workflow)
        self.assertIn("candidate workflow failed", self.workflow)
        self.assertIn("timed out waiting for exact-head candidate checks", self.workflow)
        self.assertIn("required-runs.ndjson", self.workflow)

    def test_release_gate_publishes_release_summary(self) -> None:
        self.assertIn("Publish release-candidate summary", self.workflow)
        self.assertIn("The scheduled mainline release condition is satisfied", self.workflow)
        self.assertIn("does not authorize deployment", self.workflow)
        self.assertIn("GITHUB_STEP_SUMMARY", self.workflow)
        self.assertIn("release_candidate_gate", self.workflow)

    def test_mainline_dependency_selection_includes_auxiliary_without_expanding_pr(self) -> None:
        workflow = yaml.safe_load(self.workflow)
        step = next(row for row in workflow["jobs"]["wait_for_candidate_checks"]["steps"]
                    if row.get("name") == "Wait for exact-head candidate checks")
        selection = 'required=' + step["run"].split('required=', 1)[1].split('runs_file=', 1)[0]
        for event in ("schedule", "workflow_dispatch", "pull_request"):
            with self.subTest(event=event):
                result = subprocess.run(
                    ["bash", "-ec", selection + '\n printf "%s\\n" "${required[@]}"'],
                    env={**os.environ, "GITHUB_EVENT_NAME": event}, text=True, capture_output=True,
                    check=True,
                )
                names = set(result.stdout.splitlines())
                self.assertEqual("auxiliary_backend_suite.yml" in names, event != "pull_request")
                self.assertEqual(len(names), 4 if event == "pull_request" else 5)

    def test_release_gate_materializes_exact_machine_readable_condition(self) -> None:
        self.assertIn("scripts/ci/release_condition.py", self.workflow)
        self.assertIn("release-condition.json", self.workflow)
        self.assertIn("actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02", self.workflow)
        self.assertIn("--scheduled-slot", self.workflow)

    def test_mainline_condition_requires_current_remote_main(self) -> None:
        self.assertIn("Prove validated main is still authoritative", self.workflow)
        self.assertIn(
            'gh api "repos/${GITHUB_REPOSITORY}/git/ref/heads/main"',
            self.workflow,
        )
        self.assertIn(
            'if [ "${current_main}" != "${HEAD_SHA}" ]; then',
            self.workflow,
        )
        self.assertIn("STALE_MAIN", self.workflow)
        self.assertIn('echo "CURRENT_MAIN_SHA=${current_main}" >> "${GITHUB_ENV}"', self.workflow)
        materialize_index = self.workflow.index("Materialize exact formal release condition")
        prove_index = self.workflow.index("Prove validated main is still authoritative")
        self.assertLess(prove_index, materialize_index)
        self.assertIn('--current-main "${CURRENT_MAIN_SHA}"', self.workflow)

    def test_current_main_probe_executes_pass_and_stale_negative(self) -> None:
        workflow = yaml.safe_load(self.workflow)
        step = next(
            row for row in workflow["jobs"]["wait_for_candidate_checks"]["steps"]
            if row.get("name") == "Prove validated main is still authoritative"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            gh = fake_bin / "gh"
            gh.write_text("#!/bin/sh\nprintf '%s\\n' \"${STUB_CURRENT_MAIN}\"\n", encoding="utf-8")
            gh.chmod(0o755)
            head = "a" * 40
            for current, passed in ((head, True), ("b" * 40, False), ("main", False)):
                with self.subTest(current=current):
                    env = root / f"env-{current[:3]}"
                    env.unlink(missing_ok=True)
                    result = subprocess.run(
                        ["bash", "-ec", step["run"]],
                        env={
                            **os.environ,
                            "PATH": f"{fake_bin}:{os.environ['PATH']}",
                            "GITHUB_REPOSITORY": "lidefend/sce-backend-odoo",
                            "HEAD_SHA": head,
                            "GITHUB_ENV": str(env),
                            "STUB_CURRENT_MAIN": current,
                        },
                        text=True,
                        capture_output=True,
                    )
                    self.assertEqual(passed, result.returncode == 0, result.stderr)
                    if passed:
                        self.assertEqual(
                            f"CURRENT_MAIN_SHA={head}",
                            env.read_text(encoding="utf-8").strip(),
                        )
                    else:
                        self.assertFalse(env.exists())

    def test_candidate_summary_distinguishes_pass_skip_and_failure(self) -> None:
        workflow = yaml.safe_load(self.workflow)
        script = workflow['jobs']['release_candidate_gate']['steps'][0]['run']
        with tempfile.TemporaryDirectory() as directory:
            summary = Path(directory) / 'summary'
            for result, passed, message in [
                ('success', True, 'Candidate validation: executed and passed'),
                ('skipped', True, 'not applicable (not executed)'),
                ('failure', False, 'pending or failed'),
                ('cancelled', False, 'pending or failed'),
            ]:
                with self.subTest(result=result):
                    summary.unlink(missing_ok=True)
                    rendered = (
                        script
                        .replace('${{ needs.wait_for_candidate_checks.result }}', result)
                        .replace('${{ github.event_name }}', 'pull_request')
                    )
                    proc = subprocess.run(['bash', '-ec', rendered],
                        env=dict(os.environ, GITHUB_STEP_SUMMARY=str(summary)),
                        text=True, capture_output=True)
                    self.assertEqual(proc.returncode == 0, passed, proc.stderr)
                    self.assertIn(message, summary.read_text())
            summary.write_text('')
            rendered = (
                script
                .replace('${{ needs.wait_for_candidate_checks.result }}', 'success')
                .replace('${{ github.event_name }}', 'schedule')
            )
            proc = subprocess.run(['bash', '-ec', rendered],
                env=dict(os.environ, GITHUB_STEP_SUMMARY=str(summary)),
                text=True, capture_output=True)
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertIn('Formal mainline release condition: satisfied', summary.read_text())
            self.assertIn('deployment not authorized', summary.read_text())


if __name__ == "__main__":
    unittest.main()
