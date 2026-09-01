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
            "release_candidate_gate.yml": (
                "  release_candidate_gate:",
                "    name: release_candidate_gate",
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
        self.assertIn("needs: [classify, fast]", aggregate)
        self.assertIn("Resolve merge-policy lane once", aggregate)
        merge_job = aggregate.split("  merge_policy_gate:", 1)[1]
        self.assertNotIn("select_authoritative_workflow_run.py", merge_job)
        self.assertNotIn("actions/workflows/${workflow}/runs", merge_job)
        self.assertNotIn('test "$count" = 1', aggregate)
        self.assertNotIn("continue-on-error:", aggregate)

    def test_candidate_checks_run_once_per_explicit_candidate_head(self) -> None:
        workflows = (
            "merge_policy_gate.yml",
            "public_guard.yml",
            "professional_quality_gate.yml",
            "frontend_release_gate.yml",
            "release_candidate_gate.yml",
        )
        for workflow in workflows:
            text = self.text(workflow)
            self.assertIn(
                "types: [opened, reopened, synchronize, labeled]",
                text,
            )
            self.assertIn("workflow_dispatch:", text)
            self.assertIn("github.event.label.name == 'ci:candidate'", text)
            self.assertNotIn("inputs.expected_head", text)
            self.assertNotIn("inputs.expected_base", text)
        candidate_gate = self.text("release_candidate_gate.yml")
        self.assertIn('test "$result" = success || test "$result" = skipped', candidate_gate)

        makefile = (ROOT / "make/codex.mk").read_text(encoding="utf-8")
        dispatch = makefile.split("candidate.required_checks.dispatch:", 1)[1].split(
            "candidate.mirror.gitee:", 1
        )[0]
        self.assertIn("exactly_one_open_pr_required", dispatch)
        self.assertIn("pr_head_mismatch", dispatch)
        self.assertIn("invalid_pr_base", dispatch)
        self.assertIn("pr_head_changed_before_dispatch", dispatch)
        self.assertIn("gh label create ci:candidate", dispatch)
        self.assertIn("--force", dispatch)
        self.assertIn("--remove-label ci:candidate", dispatch)
        self.assertIn("--add-label ci:candidate", dispatch)

    def test_frontend_lane_commands_are_explicit(self) -> None:
        text = self.text("frontend_release_gate.yml")
        self.assertIn("CANDIDATE_REQUESTED:", text)
        self.assertIn("Resolve effective frontend lane", text)
        self.assertIn("steps.effective_lane.outputs.frontend_mode", text)
        self.assertIn('[ "${CANDIDATE_REQUESTED}" != "true" ] && [ "${mode}" = "full" ]', text)
        self.assertIn("frontend_mode == 'full'", text)
        self.assertIn("frontend_mode == 'standard'", text)
        self.assertIn("frontend_mode != 'full'", text)
        self.assertIn("pnpm test:release", text)
        self.assertIn("pnpm -C frontend/apps/web lint:src", text)
        self.assertIn("pnpm -C frontend/apps/web typecheck:strict", text)
        self.assertIn("pnpm -C frontend/apps/web build", text)
        self.assertIn("pnpm -C frontend/apps/web test", text)
        self.assertIn("python3 scripts/ci/frontend_professional_extension_guard.py", text)
        self.assertNotIn("continue-on-error:", text)
        self.assertNotIn("|| true", text)

        package = json.loads((ROOT / "frontend/apps/web/package.json").read_text(encoding="utf-8"))
        self.assertIn("verify.frontend.pr.unit", package["scripts"]["test"])
        self.assertIn("verify.frontend.release.audit", package["scripts"]["test:release"])
        makefile = (ROOT / "make/frontend.mk").read_text(encoding="utf-8")
        merge_units = makefile.split("verify.frontend.pr.unit:", 1)[1].split("\n", 1)[0]
        self.assertIn("verify.frontend.component_driver_takeover.unit", merge_units)
        self.assertIn("verify.frontend.primitive_adapter.unit", merge_units)
        self.assertIn("verify.frontend.navigation_shell.unit", merge_units)
        self.assertIn("verify.frontend.state_dashboard.unit", merge_units)
        self.assertNotIn("verify.frontend.professional_audit.unit", merge_units)

    def test_public_guard_skips_history_scan_only_for_fast_lane(self) -> None:
        text = self.text("public_guard.yml")
        self.assertIn("name: public_guard_classify", text)
        self.assertIn("steps.risk.outputs.lane", text)
        self.assertIn("if: needs.classify.outputs.lane != 'FAST'", text)
        self.assertIn("Scan governed product history", text)
        self.assertIn('repository_clean_history_guard.py --trusted-base "${BASE_SHA}"', text)
        self.assertIn("make verify.repository.clean_history", text)

    def test_professional_lane_commands_are_explicit(self) -> None:
        text = self.text("professional_quality_gate.yml")
        self.assertIn("frontend_changed: ${{ steps.risk.outputs.frontend_changed }}", text)
        self.assertIn("backend_changed: ${{ steps.risk.outputs.backend_changed }}", text)
        self.assertIn("candidate_requested:", text)
        self.assertIn("CANDIDATE_REQUESTED:", text)
        self.assertIn("PROFESSIONAL_MODE == 'governance'", text)
        self.assertIn("github.event.action == 'labeled' && github.event.label.name == 'ci:candidate'", text)
        self.assertIn(
            'FRONTEND_CHANGED: ${{ needs.professional_authorization.outputs.frontend_changed }}',
            text,
        )
        self.assertIn(
            'BACKEND_CHANGED: ${{ needs.professional_authorization.outputs.backend_changed }}',
            text,
        )
        self.assertIn("PROFESSIONAL_MODE == 'full'", text)
        self.assertIn("PROFESSIONAL_MODE == 'standard_backend'", text)
        self.assertIn("PROFESSIONAL_MODE == 'fast'", text)
        self.assertIn("PROFESSIONAL_MODE == 'mainline'", text)
        self.assertIn("github.event_name != 'push'", text)
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertIn("make ci.professional.backend", text)
        self.assertNotIn("run: make ci\n", text)
        self.assertIn("env.BACKEND_CHANGED == 'true'", text)
        authorization_section = text.split("  professional_authorization:", 1)[1].split(
            "  python310_runtime_compatibility:", 1
        )[0]
        self.assertNotIn("test.chatter-timeline.authorization.orm", authorization_section)
        self.assertIn("Prove candidate chatter authorization with real ORM", text)
        self.assertIn("env.CANDIDATE_REQUESTED == 'true'", text)
        self.assertNotIn("pnpm -C frontend install", text)
        self.assertIn("make test.unit test.contract test.e2e.preflight", text)
        self.assertIn("make verify.product.release.version", text)
        governance_section = text.split("- name: Run governance-only quality gate", 1)[1].split(
            "- name: Run Fast lightweight quality gate", 1
        )[0]
        self.assertIn("if: env.PROFESSIONAL_MODE == 'governance'", governance_section)
        self.assertIn("test_ci_risk_workflow_contract.py", governance_section)
        self.assertIn("ci.generated_reports.guard", governance_section)
        self.assertNotIn("make ci.professional.backend", governance_section)
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
