#!/usr/bin/env python3
"""Unit tests for boq_dual_role_five_viewport_evidence_guard (hermetic).

The guard's main() reads repository-relative paths; these tests exercise the
validation functions against synthetic payloads so failures are detected
without touching the real evidence file or the dev Odoo/nginx runtime.
"""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import boq_dual_role_five_viewport_evidence_guard as guard  # noqa: E402


def _valid_top_level() -> dict:
    return {
        "schema": "frontend_acceptance_evidence_contract.v1",
        "baseline": {
            "baseline_sha": "b" * 40,
            "baseline_sha_source": "unit test fixture",
            "capability_inventory_path": "docs/planning/custom-frontend-integration/G1_CAPABILITY_INVENTORY.md",
        },
        "environment_assets": {
            "profiles_present": ["daily", "local", "production", "test"],
            "assets": [
                {"path": "config/frontend/acceptance_environments_v1.json", "sha256": "a" * 64},
                {"path": "config/frontend/acceptance_tool_matrix_v1.json", "sha256": "a" * 64},
                {"path": "config/frontend/acceptance_evidence_contract_v1.schema.json", "sha256": "a" * 64},
                {"path": "scripts/verify/boq_dual_role_five_viewport_browser_acceptance.mjs", "sha256": "a" * 64},
            ],
        },
        "toolchain": {"node": "v22.22.2", "playwright": "playwright-runtime.mjs"},
        "collected_at": "2026-09-04T10:32:14Z",
        "browser_evidence_contract": {
            "required_fields": sorted(guard.MANDATORY_BROWSER_EVIDENCE_FIELDS),
            "cross_env_reuse_forbidden": True,
        },
        "matrix_spec": {
            "roles": sorted(guard.EXPECTED_ROLES),
            "viewports": sorted(guard.EXPECTED_VIEWPORTS),
            "datasets": sorted(guard.EXPECTED_DATASETS),
            "cell_count": guard.EXPECTED_CELL_COUNT,
        },
    }


def _valid_cell(role: str, dataset: str, viewport: str, digest: str | None = None) -> dict:
    return {
        "environment_id": "local",
        "dataset_id": dataset,
        "role": role,
        "normalized_route": f"/s/project.management?project_id={42 if dataset == 'boq_1k' else 99}",
        "browser_url": f"http://127.0.0.1:18083/s/project.management?project_id={42 if dataset == 'boq_1k' else 99}",
        "viewport": viewport,
        "capture_mode": "readonly",
        "browser_full_version": "Chromium 138.0.7204.100",
        "screenshot_digest": digest or f"{role}_{dataset}_{viewport}_digest".ljust(64, "a")[:64],
        "product_service_static_shas": {
            "frontend_sha": "f" * 40,
            "backend_sha": "b" * 40,
            "contract_schema_sha": "c" * 40,
        },
        "collected_at_and_tool_version": "2026-09-04T10:32:14Z|boq-dual-role-five-viewport-acceptance.mjs@0.1.0",
    }


def _valid_full_evidence() -> dict:
    """Build a 20-cell evidence package with unique screenshot digests per cell."""
    evidence = _valid_top_level()
    cells = []
    counter = 0
    for role in sorted(guard.EXPECTED_ROLES):
        for dataset in sorted(guard.EXPECTED_DATASETS):
            for viewport in sorted(guard.EXPECTED_VIEWPORTS):
                counter += 1
                digest = ("d" * 60 + f"{counter:04d}")[:64]
                cells.append(_valid_cell(role, dataset, viewport, digest))
    evidence["cells"] = cells
    return evidence


class StructuralValidationTests(unittest.TestCase):
    def test_valid_payload_has_no_errors(self) -> None:
        errors: list[str] = []
        guard._validate_evidence(_valid_full_evidence(), errors)
        self.assertEqual(errors, [], msg=f"unexpected errors: {errors}")

    def test_wrong_schema_const_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["schema"] = "something.else.v2"
        errors: list[str] = []
        guard._validate_evidence(evidence, errors)
        self.assertTrue(any("schema" in e for e in errors))

    def test_missing_profile_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["environment_assets"]["profiles_present"] = ["local", "test", "daily"]
        errors: list[str] = []
        guard._validate_evidence(evidence, errors)
        self.assertTrue(any("profiles_present" in e for e in errors))

    def test_short_baseline_sha_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["baseline"]["baseline_sha"] = "abc123"
        errors: list[str] = []
        guard._validate_evidence(evidence, errors)
        self.assertTrue(any("baseline_sha" in e for e in errors))

    def test_missing_mandatory_browser_field_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        fields = evidence["browser_evidence_contract"]["required_fields"]
        evidence["browser_evidence_contract"]["required_fields"] = fields[:-1]
        errors: list[str] = []
        guard._validate_evidence(evidence, errors)
        self.assertTrue(any("mandatory fields" in e for e in errors))

    def test_cross_env_reuse_must_be_true(self) -> None:
        evidence = _valid_full_evidence()
        evidence["browser_evidence_contract"]["cross_env_reuse_forbidden"] = False
        errors: list[str] = []
        guard._validate_evidence(evidence, errors)
        self.assertTrue(any("cross_env_reuse_forbidden" in e for e in errors))

    def test_bad_digest_format_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["environment_assets"]["assets"][0]["sha256"] = "z" * 64
        errors: list[str] = []
        guard._validate_evidence(evidence, errors)
        self.assertTrue(any("sha256" in e for e in errors))

    def test_toolchain_node_missing_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["toolchain"].pop("node")
        errors: list[str] = []
        guard._validate_evidence(evidence, errors)
        self.assertTrue(any("toolchain.node" in e for e in errors))


class MatrixSpecValidationTests(unittest.TestCase):
    def test_default_matrix_spec_is_accepted(self) -> None:
        evidence = _valid_full_evidence()
        errors: list[str] = []
        guard._validate_matrix_spec(evidence, errors)
        self.assertEqual(errors, [], msg=errors)

    def test_wrong_role_set_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["matrix_spec"]["roles"] = ["cost_manager_only"]
        errors: list[str] = []
        guard._validate_matrix_spec(evidence, errors)
        self.assertTrue(any("matrix_spec.roles" in e for e in errors))

    def test_wrong_viewport_set_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["matrix_spec"]["viewports"] = ["1440x900", "1280x800"]
        errors: list[str] = []
        guard._validate_matrix_spec(evidence, errors)
        self.assertTrue(any("matrix_spec.viewports" in e for e in errors))

    def test_wrong_cell_count_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["matrix_spec"]["cell_count"] = 19
        errors: list[str] = []
        guard._validate_matrix_spec(evidence, errors)
        self.assertTrue(any("cell_count" in e for e in errors))


class CellValidationTests(unittest.TestCase):
    def test_full_20_cell_evidence_passes(self) -> None:
        errors: list[str] = []
        guard._validate_cells(_valid_full_evidence(), errors)
        self.assertEqual(errors, [], msg=errors)

    def test_wrong_cell_count_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["cells"] = evidence["cells"][:-1]  # 19 cells
        errors: list[str] = []
        guard._validate_cells(evidence, errors)
        self.assertTrue(any("must contain exactly 20" in e for e in errors))

    def test_duplicate_screenshot_digest_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        # overwrite the last two cells' digests to collide
        evidence["cells"][-1]["screenshot_digest"] = evidence["cells"][-2]["screenshot_digest"]
        errors: list[str] = []
        guard._validate_cells(evidence, errors)
        self.assertTrue(any("cross_env_reuse_forbidden" in e for e in errors))

    def test_missing_cell_combination_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        # drop the cell at index 0 (cost_manager × boq_1k × 1024x768)
        evidence["cells"] = evidence["cells"][1:]
        # pad to keep cell_count = 20 by duplicating an existing cell (this also triggers
        # the duplicate combo check, but we want to assert the missing combo is reported)
        evidence["cells"].append(evidence["cells"][0])
        errors: list[str] = []
        guard._validate_cells(evidence, errors)
        self.assertTrue(any("missing cell combinations" in e for e in errors))

    def test_bad_role_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["cells"][0]["role"] = "admin"
        errors: list[str] = []
        guard._validate_cells(evidence, errors)
        self.assertTrue(any("cell[0].role" in e for e in errors))

    def test_bad_viewport_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["cells"][0]["viewport"] = "1920x1080"
        errors: list[str] = []
        guard._validate_cells(evidence, errors)
        self.assertTrue(any("cell[0].viewport" in e for e in errors))

    def test_wrong_capture_mode_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["cells"][0]["capture_mode"] = "writable"
        errors: list[str] = []
        guard._validate_cells(evidence, errors)
        self.assertTrue(any("capture_mode" in e for e in errors))

    def test_missing_mandatory_field_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["cells"][0].pop("screenshot_digest")
        errors: list[str] = []
        guard._validate_cells(evidence, errors)
        self.assertTrue(any("missing mandatory fields" in e for e in errors))

    def test_short_screenshot_digest_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["cells"][0]["screenshot_digest"] = "abc"
        errors: list[str] = []
        guard._validate_cells(evidence, errors)
        self.assertTrue(any("screenshot_digest" in e for e in errors))

    def test_missing_static_sha_subkey_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["cells"][0]["product_service_static_shas"].pop("frontend_sha")
        errors: list[str] = []
        guard._validate_cells(evidence, errors)
        self.assertTrue(any("frontend_sha" in e for e in errors))

    def test_collected_at_without_pipe_separator_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["cells"][0]["collected_at_and_tool_version"] = "2026-09-04T10:32:14Z"
        errors: list[str] = []
        guard._validate_cells(evidence, errors)
        self.assertTrue(any("collected_at_and_tool_version" in e for e in errors))

    def test_non_project_management_route_is_rejected(self) -> None:
        evidence = _valid_full_evidence()
        evidence["cells"][0]["normalized_route"] = "/s/other-scene"
        errors: list[str] = []
        guard._validate_cells(evidence, errors)
        self.assertTrue(any("normalized_route" in e for e in errors))


class ReproducibilityValidationTests(unittest.TestCase):
    def test_fingerprint_drift_is_detected(self) -> None:
        evidence = _valid_full_evidence()
        # Use a non-existent asset path to keep the run hermetic
        evidence["environment_assets"]["assets"] = [
            {"path": "config/frontend/does_not_exist_xyz.json", "sha256": "a" * 64}
        ]
        errors: list[str] = []
        guard._validate_reproducibility(evidence, errors)
        self.assertTrue(any("missing on disk" in e for e in errors))


class ProfileConfigValidationTests(unittest.TestCase):
    def test_real_config_has_four_profiles(self) -> None:
        import json

        config = json.loads(guard.ENVIRONMENTS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(set(config.get("profiles") or {}), guard.EXPECTED_PROFILES)


class IntegrationSanityTests(unittest.TestCase):
    def test_full_validation_pipeline_passes_for_valid_fixture(self) -> None:
        """The full _validate_* pipeline must accept a complete 20-cell fixture."""
        evidence = _valid_full_evidence()
        errors: list[str] = []
        guard._validate_evidence(evidence, errors)
        guard._validate_matrix_spec(evidence, errors)
        guard._validate_cells(evidence, errors)
        # skip _validate_reproducibility — fixture uses fake digests
        # skip _baseline_ancestor_check — fixture uses fake baseline SHA
        # skip _validate_profiles_against_config — reads real env config
        # skip _validate_schema_selfcheck — reads real schema
        self.assertEqual(errors, [], msg=errors)


if __name__ == "__main__":
    unittest.main()
