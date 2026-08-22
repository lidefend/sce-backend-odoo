#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CIRiskWorkflowContractTests(unittest.TestCase):
    def text(self, name: str) -> str:
        return (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")

    def test_required_checks_are_unconditional_workflow_jobs(self) -> None:
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

    def test_frontend_lane_commands_are_explicit(self) -> None:
        text = self.text("frontend_release_gate.yml")
        self.assertIn("frontend_mode == 'full'", text)
        self.assertIn("frontend_mode == 'standard'", text)
        self.assertIn("frontend_mode != 'full'", text)
        self.assertIn("pnpm test:release", text)
        self.assertIn("pnpm -C frontend/apps/web lint:src", text)
        self.assertIn("pnpm -C frontend/apps/web typecheck:strict", text)
        self.assertIn("pnpm -C frontend/apps/web build", text)
        self.assertNotIn("continue-on-error:", text)
        self.assertNotIn("|| true", text)

    def test_professional_lane_commands_are_explicit(self) -> None:
        text = self.text("professional_quality_gate.yml")
        self.assertIn("PROFESSIONAL_MODE == 'full'", text)
        self.assertIn("PROFESSIONAL_MODE == 'standard_backend'", text)
        self.assertIn("PROFESSIONAL_MODE == 'fast'", text)
        self.assertIn("make ci.professional.backend", text)
        self.assertNotIn("run: make ci\n", text)
        self.assertIn("steps.risk.outputs.backend_changed == 'true'", text)
        self.assertIn("actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020", text)
        self.assertIn("node-version: 22.17.0", text)
        self.assertIn("corepack prepare pnpm@9.12.3 --activate", text)
        self.assertIn("pnpm -C frontend install --frozen-lockfile", text)
        self.assertIn("make test.unit test.contract test.e2e.preflight", text)
        self.assertIn("make verify.product.release.version", text)
        self.assertNotIn("continue-on-error:", text)
        self.assertNotIn("|| true", text)

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
