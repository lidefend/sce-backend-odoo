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

    def test_fast_and_full_are_disjoint_and_fail_closed(self) -> None:
        self.assertIn("needs.classify.outputs.lane == 'FAST'", self.workflow)
        self.assertIn("needs.classify.outputs.lane != 'FAST'", self.workflow)
        self.assertIn("Enforce exactly one merge lane", self.workflow)
        self.assertIn("test \"${{ needs.fast.result }}\" != \"${{ needs.full.result }}\"", self.workflow)
        self.assertIn("--base", self.workflow)
        self.assertIn("--head", self.workflow)

    def test_full_binds_existing_checks_to_the_exact_head(self) -> None:
        for workflow in (
            "public_guard.yml",
            "professional_quality_gate.yml",
            "frontend_release_gate.yml",
        ):
            self.assertIn(workflow, self.workflow)
        self.assertIn("select_authoritative_workflow_run.py", self.workflow)
        self.assertIn("--workflow-path", self.workflow)
        self.assertIn("--repository", self.workflow)
        self.assertIn("--event", self.workflow)
        self.assertNotIn('test "$count" = 1', self.workflow)
        self.assertIn("full workflow failed", self.workflow)

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

    def test_ruleset_requires_only_the_aggregate_without_bypass(self) -> None:
        self.assertIn('readonly required_checks="merge_policy_gate"', self.ruleset)
        self.assertIn('{context: "merge_policy_gate"}', self.ruleset)
        self.assertIn("bypass_actors: []", self.ruleset)
        self.assertNotIn('{context: "public_guard"}', self.ruleset)


if __name__ == "__main__":
    unittest.main()
