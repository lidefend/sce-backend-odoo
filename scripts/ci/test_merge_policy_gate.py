#!/usr/bin/env python3
"""Static contract for the single required Fast/Full merge gate."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class MergePolicyGateContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = (ROOT / ".github/workflows/merge_policy_gate.yml").read_text(encoding="utf-8")
        self.ruleset = (ROOT / "scripts/ops/configure_github_mirror_ruleset.sh").read_text(encoding="utf-8")

    def test_fast_and_required_paths_are_disjoint_and_fail_closed(self) -> None:
        self.assertIn("needs.classify.outputs.lane == 'FAST'", self.workflow)
        self.assertIn("Resolve merge-policy lane once", self.workflow)
        self.assertIn('if [ "${{ needs.classify.outputs.lane }}" = "FAST" ]', self.workflow)
        self.assertIn('test "${{ needs.fast.result }}" = skipped', self.workflow)
        self.assertNotIn("  full:", self.workflow)
        self.assertIn("--base", self.workflow)
        self.assertIn("--head", self.workflow)

    def test_merge_gate_does_not_poll_sibling_workflows(self) -> None:
        merge_job = self.workflow.split("  merge_policy_gate:", 1)[1]
        self.assertNotIn("select_authoritative_workflow_run.py", merge_job)
        self.assertNotIn("actions/workflows/${workflow}/runs", merge_job)
        self.assertNotIn("sleep 10", merge_job)

    def test_summary_publishes_effective_daily_vs_candidate_lane(self) -> None:
        self.assertIn("Publish lane summary", self.workflow)
        self.assertIn("GITHUB_STEP_SUMMARY", self.workflow)
        self.assertIn("needs.classify.outputs.frontend_mode", self.workflow)
        self.assertIn("needs.classify.outputs.professional_mode", self.workflow)
        self.assertIn("needs.classify.outputs.candidate_requested", self.workflow)
        self.assertIn('if [ "${CANDIDATE_REQUESTED}" != "true" ]; then', self.workflow)
        self.assertIn('effective_professional="governance"', self.workflow)
        self.assertIn("Ordinary PR governance changes were downgraded", self.workflow)
        self.assertIn("Explicit candidate validation was requested for this exact head.", self.workflow)

    def test_ruleset_requires_each_authoritative_check_without_bypass(self) -> None:
        self.assertIn(
            'readonly required_checks="frontend_release_gate merge_policy_gate professional_quality_gate public_guard"',
            self.ruleset,
        )
        for check in (
            "frontend_release_gate",
            "merge_policy_gate",
            "professional_quality_gate",
            "public_guard",
        ):
            self.assertIn(f'{{context: "{check}"}}', self.ruleset)
        self.assertIn("bypass_actors: []", self.ruleset)


if __name__ == "__main__":
    unittest.main()
