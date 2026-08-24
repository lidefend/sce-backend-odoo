from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/verify"))

import design_token_system as system  # type: ignore


class DesignTokenSystemTests(unittest.TestCase):
    def test_phase0_inventory_is_fully_classified(self):
        authority = system.load_authority()
        names = system.phase0_inventory_names()
        self.assertEqual(len(names), 131)
        self.assertTrue(all(system.classify_legacy_name(name, authority) for name in names))

    def test_authority_has_the_four_formal_layers(self):
        self.assertEqual(system.validate_authority(), [])

    def test_token_references_have_no_missing_target_or_cycle(self):
        self.assertEqual(system.token_reference_errors(), [])

    def test_missing_token_reference_is_rejected(self):
        self.assertEqual(
            system.reference_graph_errors({"--sc-pattern-example": "var(--sc-semantic-missing)"}),
            ["--sc-pattern-example references undefined token(s): --sc-semantic-missing"],
        )

    def test_token_alias_cycle_is_rejected(self):
        errors = system.reference_graph_errors({
            "--sc-pattern-a": "var(--sc-pattern-b)",
            "--sc-pattern-b": "var(--sc-pattern-a)",
        })
        self.assertTrue(any("token alias cycle" in error for error in errors))

    def test_deprecated_selector_lookalikes_are_not_token_capabilities(self):
        record = system.classify_legacy_name("--readonly")
        self.assertIsNotNone(record)
        self.assertEqual(record["status"], "deprecated")
        self.assertEqual(record["allowedConsumerScope"], [])

    def test_business_style_cannot_add_a_global_or_primitive_consumer(self):
        errors = system.boundary_errors_for(
            system.WEB / "pages/example.css",
            "--sc-unregistered: 1px;\n.example { gap: var(--sc-base-space-md); }",
        )
        self.assertTrue(any("global CSS variable" in error for error in errors))
        self.assertTrue(any("primitive token" in error for error in errors))

    def test_tdesign_and_brand_values_are_restricted_to_registered_sources(self):
        errors = system.boundary_errors_for(
            system.WEB / "components/example.css",
            ".example { --td-brand-color: #0052a9; z-index: 9; }",
        )
        self.assertTrue(any("TDesign theme variable" in error for error in errors))
        self.assertTrue(any("hardcoded color" in error for error in errors))
        self.assertTrue(any("unregistered z-index" in error for error in errors))

    def test_incremental_boundary_guard_accepts_the_registered_token_sources(self):
        self.assertEqual(system.incremental_boundary_errors(), [])


if __name__ == "__main__":
    unittest.main()
