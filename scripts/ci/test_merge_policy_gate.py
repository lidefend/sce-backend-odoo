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
        self.assertIn("test \"${{ needs.fast.result }}\" != \"${{ needs.full.result }}\"", self.workflow)
        self.assertIn("--base", self.workflow)
        self.assertIn("--head", self.workflow)

    def test_full_binds_existing_checks_to_the_exact_head(self) -> None:
        for check in ("public_guard", "professional_authorization", "professional_quality_gate", "frontend_release_gate"):
            self.assertIn(check, self.workflow)
        self.assertIn(".head_sha == $sha", self.workflow)
        self.assertIn("sort_by(.id) | last // empty", self.workflow)
        self.assertNotIn('test "$count" = 1', self.workflow)
        self.assertIn("full check failed", self.workflow)

    def test_ruleset_requires_only_the_aggregate_without_bypass(self) -> None:
        self.assertIn('readonly required_checks="merge_policy_gate"', self.ruleset)
        self.assertIn('{context: "merge_policy_gate"}', self.ruleset)
        self.assertIn("bypass_actors: []", self.ruleset)
        self.assertNotIn('{context: "public_guard"}', self.ruleset)


if __name__ == "__main__":
    unittest.main()
