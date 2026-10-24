"""Independent contract oracles and negative controls for the presentation gate."""
import sys
import unittest
from unittest.mock import patch

import form_container_presentation_consumption_guard as guard


class FramelessRuleTests(unittest.TestCase):
    def source(self, body):
        return f"""<style scoped>
.unrelated {{ grid-column: auto; container-type: normal; }}
.template-form-section--frameless {{ {body} }}
.template-form-section--compact-summary {{ container-type: normal; }}
</style>"""

    def test_valid_target_rule(self):
        self.assertEqual([], guard._frameless_rule_errors(
            self.source("grid-column: auto; container-type: normal;")))

    def test_unrelated_rule_cannot_mask_containment_mutation(self):
        errors = guard._frameless_rule_errors(
            self.source("grid-column: auto; container-type: inline-size;"))
        self.assertTrue(any("container-type" in error for error in errors))

    def test_unrelated_rule_cannot_supply_grid_placement(self):
        self.assertTrue(guard._frameless_rule_errors(
            self.source("grid-column: 1 / -1; container-type: normal;")))

    def test_comment_cannot_supply_declaration(self):
        self.assertTrue(guard._frameless_rule_errors(self.source(
            "grid-column: auto; /* container-type: normal; */")))

    def test_later_conflicting_declaration_is_detected(self):
        self.assertTrue(guard._frameless_rule_errors(self.source(
            "grid-column: auto; container-type: normal; container-type: inline-size;")))

    def test_duplicate_rules_fail_closed(self):
        rule = ".template-form-section--frameless { grid-column: auto; container-type: normal; }"
        self.assertTrue(guard._frameless_rule_errors(f"<style>{rule}{rule}</style>"))

    def test_current_component_and_original_mutation(self):
        source = guard.FORM_SECTION_PATH.read_text()
        self.assertEqual([], guard._frameless_rule_errors(source))
        mutated = source.replace("container-type: normal;", "container-type: inline-size;", 1)
        self.assertIn("container-type: normal;", mutated)
        self.assertTrue(guard._frameless_rule_errors(mutated))


class DeclaredGridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projection = guard._load_projection()

    def test_formal_default_and_explicit_layout_cases(self):
        # Spec: native_view_reuse_frontend_spec_v1.md:371, not observed output.
        self.assertEqual([], guard._declared_layout_span_errors(self.projection))

    def test_default_changed_to_one_column_is_detected(self):
        assembler = sys.modules[self.projection.declare_container_columns.__module__]
        with patch.object(assembler, "CONTAINER_GRID_COLUMNS_DEFAULT", 1):
            errors = guard._declared_layout_span_errors(self.projection)
        self.assertTrue(any("default columns=2" in error for error in errors))

    def test_missing_column_declaration_is_detected_even_with_correct_span(self):
        original = self.projection.normalize_post_projected_container_tree

        def missing_columns(*args):
            tree = original(*args)
            for node in tree:
                node.pop("columns", None)
            return tree

        with patch.object(self.projection, "normalize_post_projected_container_tree", missing_columns):
            errors = guard._declared_layout_span_errors(self.projection)
        self.assertTrue(any("default columns=2" in error for error in errors))


class LegacyAlertConsumptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.projection = guard._load_projection()
        cls.renderer = guard.RENDERER_PATH.read_text(encoding="utf-8")
        cls.native_text = guard.NATIVE_TEXT_PATH.read_text(encoding="utf-8")

    def test_current_runtime_and_native_boundary_is_closed(self):
        self.assertEqual(
            [],
            guard._legacy_feedback_consumption_errors(
                self.projection, self.renderer, self.native_text,
            ),
        )

    def test_feedback_tokens_are_published_but_not_layout_vocabulary(self):
        self.assertEqual(
            guard.LEGACY_ALERT_TOKENS,
            set(self.projection.FORM_PRESENTATION_LEGACY_FEEDBACK_TOKENS),
        )
        self.assertFalse(
            guard.LEGACY_ALERT_TOKENS & set(self.projection.FORM_PRESENTATION_LAYOUT_TOKENS)
        )
        for token in guard.LEGACY_ALERT_TOKENS:
            self.assertIn(
                token,
                self.projection.declared_presentation_tokens(
                    {"type": "div", "attributes": {"class": token}}, f"test.{token}",
                ),
            )

    def test_missing_explicit_component_exemption_is_detected(self):
        mutated = self.native_text.replace("if (node.nodeComponent) return;", "", 1)
        self.assertNotEqual(mutated, self.native_text)
        self.assertTrue(guard._legacy_feedback_consumption_errors(
            self.projection, self.renderer, mutated,
        ))

    def test_hidden_or_empty_validation_cannot_be_removed(self):
        mutated = self.renderer.replace(
            "validateNativePresentationDeclarations(nodes);", "", 1,
        )
        self.assertNotEqual(mutated, self.renderer)
        self.assertTrue(guard._legacy_feedback_consumption_errors(
            self.projection, mutated, self.native_text,
        ))

    def test_qweb_and_oca_are_not_classified_as_vue(self):
        self.assertEqual(
            "qweb_native",
            guard.classify_presentation_consumer(
                "addons/smart_construction_core/views/web_login_views.xml",
            ),
        )
        self.assertEqual(
            "oca_qweb_injection",
            guard.classify_presentation_consumer(
                "addons_external/oca_server_ux/base_tier_validation/templates/"
                "tier_validation_templates.xml",
            ),
        )
        self.assertEqual(
            "oca_component",
            guard.classify_presentation_consumer(
                "addons_external/oca_server_ux/base_tier_validation/static/src/components/"
                "tier_review_widget/tier_review_widget.xml",
            ),
        )
        self.assertEqual(
            "generated_historical_snapshot",
            guard.classify_presentation_consumer(
                "contracts/generated/product_view_structure_contract.json",
            ),
        )

    def test_generated_or_test_tokens_never_satisfy_vue_consumption(self):
        self.assertEqual(
            "generated_historical_snapshot",
            guard.classify_presentation_consumer("contracts/generated/example.json"),
        )
        self.assertEqual(
            "test_fixture",
            guard.classify_presentation_consumer(
                "frontend/apps/web/scripts/native_text_presentation_test.ts",
            ),
        )


if __name__ == "__main__":
    unittest.main()
