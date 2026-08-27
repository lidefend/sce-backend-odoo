from __future__ import annotations

import unittest

from scripts.verify.frontend_page_pattern_reference_parity_guard import REQUIREMENTS, ROOT, validate


class FrontendPagePatternReferenceParityGuardTest(unittest.TestCase):
    def source_map(self) -> dict[str, str]:
        return {source: (ROOT / source).read_text(encoding="utf-8") for source in REQUIREMENTS}

    def test_current_sources_pass(self) -> None:
        self.assertEqual(validate(), [])

    def test_readonly_fact_must_not_fall_back_to_full_form_card(self) -> None:
        values = self.source_map()
        target = "frontend/apps/web/src/components/template/FormSection.vue"
        values[target] = values[target].replace(
            ":appearance=\"preferReadonlyFacts ? 'fact' : 'form-section'\"",
            'appearance="form-section"',
        )
        failures = validate(lambda source: values[source])
        self.assertTrue(any("parity requirement missing" in failure and target in failure for failure in failures))

    def test_intrinsic_page_tracks_are_required(self) -> None:
        values = self.source_map()
        target = "frontend/apps/web/src/pages/contractForm/ObjectTaskPage.vue"
        values[target] = values[target].replace("grid-auto-rows: max-content", "grid-auto-rows: auto")
        failures = validate(lambda source: values[source])
        self.assertTrue(any("parity requirement missing" in failure and target in failure for failure in failures))

    def test_product_specific_hint_is_rejected(self) -> None:
        values = self.source_map()
        target = "frontend/apps/web/src/components/design-system/ScCard.vue"
        values[target] += "/* payment.request */"
        failures = validate(lambda source: values[source])
        self.assertTrue(any("product-specific routing hint" in failure and target in failure for failure in failures))

    def test_sidebar_must_be_capped_to_the_viewport(self) -> None:
        values = self.source_map()
        target = "frontend/apps/web/src/layouts/AppShell.css"
        values[target] = values[target].replace("max-height: 100dvh", "max-height: none", 1)
        failures = validate(lambda source: values[source])
        self.assertTrue(any("parity requirement missing" in failure and target in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
