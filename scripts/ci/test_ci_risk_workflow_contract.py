#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CIRiskWorkflowContractTests(unittest.TestCase):
    def text(self, name: str) -> str:
        return (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")

    def test_merge_policy_gate_is_the_single_required_aggregation_job(self) -> None:
        contracts = {
            "public_guard.yml": ("  public_guard:", "    name: public_guard"),
            "professional_quality_gate.yml": (
                "  professional_authorization:",
                "    name: professional_authorization",
                "  professional_quality_gate:",
                "    name: professional_quality_gate",
            ),
            "frontend_release_gate.yml": (
                "  frontend_release_gate:",
                "    name: frontend_release_gate",
            ),
        }
        for workflow, required in contracts.items():
            text = self.text(workflow)
            self.assertNotIn("\n    paths:", text)
            self.assertNotIn("\n    paths-ignore:", text)
            self.assertIn("cancel-in-progress: true", text)
            for item in required:
                self.assertIn(item, text)
        aggregate = self.text("merge_policy_gate.yml")
        self.assertIn("name: merge_policy_gate", aggregate)
        self.assertIn("name: merge_policy_gate", aggregate)
        self.assertIn("needs: [fast, full]", aggregate)
        self.assertIn("Wait for exact-head full checks", aggregate)
        self.assertNotIn("continue-on-error:", aggregate)

    def test_candidate_checks_run_once_per_explicit_candidate_head(self) -> None:
        workflows = (
            "merge_policy_gate.yml",
            "public_guard.yml",
            "professional_quality_gate.yml",
            "frontend_release_gate.yml",
        )
        for workflow in workflows:
            text = self.text(workflow)
            self.assertIn("types: [opened, reopened, ready_for_review]", text)
            self.assertNotIn("synchronize", text)
            self.assertIn("workflow_dispatch:", text)
            self.assertIn("expected_head:", text)
            self.assertIn("expected_base:", text)
            self.assertIn("inputs.expected_head", text)
            self.assertIn("inputs.expected_base", text)
            self.assertIn(
                "github.event_name == 'workflow_dispatch' && 'pull_request'",
                text,
            )

        makefile = (ROOT / "make/codex.mk").read_text(encoding="utf-8")
        dispatch = makefile.split("candidate.required_checks.dispatch:", 1)[1].split(
            "candidate.mirror.gitee:", 1
        )[0]
        self.assertIn("exactly_one_open_pr_required", dispatch)
        self.assertIn("pr_head_mismatch", dispatch)
        self.assertIn("invalid_pr_base", dispatch)
        self.assertIn('expected_head="$$expected"', dispatch)
        self.assertIn('expected_base="$$base_sha"', dispatch)
        for workflow in workflows:
            self.assertIn(workflow, dispatch)

    def test_frontend_lane_commands_are_explicit(self) -> None:
        text = self.text("frontend_release_gate.yml")
        self.assertIn("frontend_mode == 'full'", text)
        self.assertIn("frontend_mode == 'standard'", text)
        self.assertIn("frontend_mode != 'full'", text)
        self.assertIn("pnpm test:release", text)
        self.assertIn("pnpm -C frontend/apps/web lint:src", text)
        self.assertIn("pnpm -C frontend/apps/web typecheck:strict", text)
        self.assertIn("pnpm -C frontend/apps/web build", text)
        self.assertIn("python3 scripts/ci/frontend_professional_extension_guard.py", text)
        self.assertNotIn("continue-on-error:", text)
        self.assertNotIn("|| true", text)

    def test_public_guard_skips_history_scan_only_for_fast_lane(self) -> None:
        text = self.text("public_guard.yml")
        self.assertIn("name: public_guard_classify", text)
        self.assertIn("steps.risk.outputs.lane", text)
        self.assertIn("if: needs.classify.outputs.lane != 'FAST'", text)
        self.assertIn("Scan governed product history", text)
        self.assertIn('"${GITHUB_EVENT_NAME}" = "workflow_dispatch"', text)
        self.assertIn('repository_clean_history_guard.py --trusted-base "${BASE_SHA}"', text)
        self.assertIn("make verify.repository.clean_history", text)

    def test_professional_lane_commands_are_explicit(self) -> None:
        text = self.text("professional_quality_gate.yml")
        self.assertIn("PROFESSIONAL_MODE == 'full'", text)
        self.assertIn("PROFESSIONAL_MODE == 'standard_backend'", text)
        self.assertIn("PROFESSIONAL_MODE == 'fast'", text)
        self.assertIn("PROFESSIONAL_MODE == 'mainline'", text)
        self.assertIn("github.event_name != 'push'", text)
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertIn("make ci.professional.backend", text)
        self.assertNotIn("run: make ci\n", text)
        self.assertIn("steps.risk.outputs.backend_changed == 'true'", text)
        self.assertNotIn("pnpm -C frontend install", text)
        self.assertIn("make test.unit test.contract test.e2e.preflight", text)
        self.assertIn("make verify.product.release.version", text)
        fast_section = text.split("- name: Run Fast lightweight quality gate", 1)[1].split(
            "- name: Run standard frontend quality gate", 1
        )[0]
        self.assertIn("if: env.PROFESSIONAL_MODE == 'fast'", fast_section)
        self.assertNotIn("verify.contract.lint", fast_section)
        self.assertNotIn("verify.guard.registry", fast_section)
        standard_frontend_section = text.split(
            "- name: Run standard frontend quality gate", 1
        )[1].split("- name: Clean isolated runner state", 1)[0]
        self.assertIn("if: env.PROFESSIONAL_MODE == 'standard_frontend'", standard_frontend_section)
        self.assertNotIn("verify.contract.lint", standard_frontend_section)
        self.assertNotIn("verify.guard.registry", standard_frontend_section)
        self.assertIn("python3 scripts/ci/frontend_professional_extension_guard.py", standard_frontend_section)
        self.assertNotIn("continue-on-error:", text)
        self.assertNotIn("|| true", text)
        mainline_section = text.split("- name: Run mainline integrity gate", 1)[1].split(
            "- name: Run standard backend quality gate", 1
        )[0]
        self.assertIn("test_ci_risk_workflow_contract.py", mainline_section)
        self.assertIn("github_actions_security_guard.py", mainline_section)
        self.assertIn("ci.generated_reports.guard", mainline_section)
        self.assertNotIn("ci.professional.backend", mainline_section)

        makefile = (ROOT / "make/ci.mk").read_text(encoding="utf-8")
        professional_target = makefile.split("ci.professional.backend:", 1)[1].split("\n", 1)[0]
        self.assertIn("verify.unified_page_contract.v2.professional_backend", professional_target)
        self.assertNotIn("verify.unified_page_contract.v2.frontend_static", professional_target)

    def test_cache_keys_bind_lockfile_and_runtime(self) -> None:
        text = self.text("frontend_release_gate.yml")
        self.assertIn("actions/cache@0057852bfaa89a56745cba8c7296529d2fc39830", text)
        self.assertIn("actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020", text)
        self.assertIn("node-version: 22.17.0", text)
        self.assertIn("hashFiles('frontend/pnpm-lock.yaml')", text)
        self.assertIn("node22.17.0", text)

    def test_frontend_full_policy_is_surface_specific(self) -> None:
        policy = json.loads(
            (ROOT / "config/ci/risk_tiering_v1.json").read_text(encoding="utf-8")
        )
        patterns = set(policy["frontend_full_paths"])
        self.assertIn("frontend/pnpm-lock.yaml", patterns)
        self.assertIn(".github/workflows/frontend_release_gate.yml", patterns)
        self.assertNotIn("scripts/release/**", patterns)

    def test_professional_frontend_extension_surface_is_narrow_and_standard(self) -> None:
        policy = json.loads(
            (ROOT / "config/ci/risk_tiering_v1.json").read_text(encoding="utf-8")
        )
        owned = set(policy["standard_frontend_owned_paths"])
        self.assertEqual(
            owned,
            {
                "make/frontend_professional_extensions.mk",
                "scripts/verify/frontend_professional_*",
                "scripts/verify/test_frontend_professional_*",
            },
        )
        overrides = set(policy["high_risk_override_paths"])
        self.assertEqual(overrides, {"make/frontend_professional_extensions.mk"})
        self.assertNotIn("make/frontend.mk", owned)
        self.assertNotIn("make/**", overrides)

    def test_high_risk_policy_contains_mandatory_surfaces(self) -> None:
        policy = json.loads(
            (ROOT / "config/ci/risk_tiering_v1.json").read_text(encoding="utf-8")
        )
        patterns = set(policy["high_risk_paths"])
        required = {
            ".github/workflows/**",
            "**/security/**",
            "**/ir.model.access.csv",
            "**/*tenant*payload*",
            "migrations/**",
            "deployment/**",
            "release/**",
            "Dockerfile*",
            "docker-compose*",
            "**/*identity*lock*",
            "**/pnpm-lock.yaml",
        }
        self.assertEqual(policy["default_lane"], "HIGH_RISK")
        self.assertFalse(required - patterns)

    def test_github_is_the_only_automatic_heavy_validator(self) -> None:
        duplicated = [
            path
            for path in ROOT.glob(".gitee/**/*")
            if path.is_file() and path.suffix in {".yml", ".yaml"}
        ]
        self.assertEqual(duplicated, [])


if __name__ == "__main__":
    unittest.main()
