#!/usr/bin/env python3
from __future__ import annotations

import unittest

from ci_risk_classifier import classify


class CIRiskClassifierTests(unittest.TestCase):
    def lane(self, *paths: str, event: str = "pull_request", ref: str = "") -> str:
        return classify(paths, event_name=event, ref=ref).lane

    def test_documentation_is_fast(self) -> None:
        self.assertEqual(self.lane("docs/ops/runbook.md"), "FAST")

    def test_agent_workflow_metadata_is_fast(self) -> None:
        result = classify(
            [
                ".agent/workflows/frontend-professionalization.yaml",
                "docs/ops/iterations/delivery_context_switch_log_v1.md",
            ],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "FAST")
        self.assertEqual(result.frontend_mode, "skip")
        self.assertEqual(result.professional_mode, "fast")

    def test_other_agent_authority_remains_fail_closed(self) -> None:
        self.assertEqual(self.lane(".agent/context.yaml"), "HIGH_RISK")
        self.assertEqual(self.lane(".agent/decisions/runtime-authority.yaml"), "HIGH_RISK")

    def test_version_only_change_is_fast_but_not_unclassified(self) -> None:
        result = classify(["VERSION"], event_name="pull_request")
        self.assertEqual(result.lane, "FAST")
        self.assertEqual(result.professional_mode, "fast")
        self.assertEqual(result.frontend_mode, "skip")

    def test_frontend_is_standard(self) -> None:
        result = classify(
            ["frontend/apps/web/src/pages/ProjectListPage.vue"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "STANDARD")
        self.assertEqual(result.frontend_mode, "standard")

    def test_backend_is_standard(self) -> None:
        result = classify(
            ["addons/smart_construction_core/models/project.py"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "STANDARD")
        self.assertEqual(result.professional_mode, "standard_backend")

    def test_security_xml_is_high_risk(self) -> None:
        self.assertEqual(
            self.lane("addons/smart_core/security/smart_core_groups.xml"),
            "HIGH_RISK",
        )

    def test_importer_is_high_risk(self) -> None:
        self.assertEqual(
            self.lane("addons/smart_core/services/tenant_payload_importer.py"),
            "HIGH_RISK",
        )

    def test_migration_is_high_risk(self) -> None:
        self.assertEqual(self.lane("migrations/18.0.1/post.py"), "HIGH_RISK")

    def test_workflow_is_high_risk(self) -> None:
        result = classify(
            [".github/workflows/professional_quality_gate.yml"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "skip")

    def test_frontend_gate_workflow_requires_full_frontend_release(self) -> None:
        result = classify(
            [".github/workflows/frontend_release_gate.yml"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "full")

    def test_ci_risk_policy_change_is_high_risk_without_product_frontend_release(self) -> None:
        result = classify(
            [
                "config/ci/risk_tiering_v1.json",
                "scripts/ci/test_ci_risk_classifier.py",
            ],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.professional_mode, "full")
        self.assertEqual(result.frontend_mode, "skip")

    def test_docker_and_release_are_high_risk_on_pr(self) -> None:
        self.assertEqual(self.lane("Dockerfile"), "HIGH_RISK")
        result = classify(["scripts/release/publish.py"], event_name="pull_request")
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "skip")
        self.assertEqual(result.professional_mode, "full")

    def test_frontend_release_image_is_full(self) -> None:
        result = classify(
            ["Dockerfile.production-frontend-builder"],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "full")

    def test_mixed_change_uses_highest_risk(self) -> None:
        self.assertEqual(
            self.lane("docs/readme.md", "addons/smart_core/security/ir.model.access.csv"),
            "HIGH_RISK",
        )

    def test_unknown_path_fails_closed(self) -> None:
        self.assertEqual(self.lane("unexpected/new-surface.bin"), "HIGH_RISK")

    def test_empty_change_set_fails_closed(self) -> None:
        self.assertEqual(self.lane(), "HIGH_RISK")

    def test_dispatch_and_tag_are_release(self) -> None:
        self.assertEqual(self.lane(event="workflow_dispatch"), "RELEASE")
        self.assertEqual(
            self.lane("docs/release.md", event="push", ref="refs/tags/v1.0.0"),
            "RELEASE",
        )

    def test_lockfiles_are_high_risk(self) -> None:
        result = classify(["frontend/pnpm-lock.yaml"], event_name="pull_request")
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "full")

    def test_mixed_backend_risk_and_frontend_source_is_standard_frontend(self) -> None:
        result = classify(
            [
                "addons/smart_core/security/ir.model.access.csv",
                "frontend/apps/web/src/App.vue",
            ],
            event_name="pull_request",
        )
        self.assertEqual(result.lane, "HIGH_RISK")
        self.assertEqual(result.frontend_mode, "standard")

    def test_path_escape_fails_closed(self) -> None:
        self.assertEqual(self.lane("../security.xml"), "HIGH_RISK")


if __name__ == "__main__":
    unittest.main()
