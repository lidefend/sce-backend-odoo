import unittest

from scripts.verify.frontend_professional_business_value_guard import validate


class ProfessionalBusinessValueGuardTests(unittest.TestCase):
    def test_current_sources_pass(self):
        self.assertEqual(validate(), [])

    def test_missing_component_marker_fails(self):
        def read_text(path):
            value = (self._root() / path).read_text(encoding="utf-8")
            return value.replace('data-professional-field-family="business-value"', "data-family-removed")

        self.assertTrue(any("missing marker" in item for item in validate(read_text)))

    def test_model_special_case_fails(self):
        def read_text(path):
            value = (self._root() / path).read_text(encoding="utf-8")
            return value + "\n// payment.request\n" if path.endswith("professionalBusinessValueModel.ts") else value

        self.assertTrue(any("forbidden product special case" in item for item in validate(read_text)))

    def test_missing_generated_frontend_key_fails(self):
        """The projected frontend table, not the registry module, holds the keys."""

        def read_text(path):
            value = (self._root() / path).read_text(encoding="utf-8")
            if path.endswith("presentation/semantic_registry.generated.ts"):
                return value.replace("'sc.value.money'", "'sc.value.removed'")
            return value

        failures = validate(read_text)
        self.assertTrue(
            any("frontend business value authority is incomplete for sc.value.money" in item for item in failures),
            failures,
        )

    def test_missing_runtime_carrier_key_fails(self):
        """The vocabulary must survive the projection from the declaration."""

        def read_text(path):
            value = (self._root() / path).read_text(encoding="utf-8")
            if path.endswith("contract_runtime/semantic_registry_generated.py"):
                return value.replace("'sc.value.money'", "'sc.value.removed'")
            return value

        failures = validate(read_text)
        self.assertTrue(any("runtime carrier is missing business value key" in item for item in failures), failures)

    def test_assembler_bypassing_the_registry_fails(self):
        def read_text(path):
            value = (self._root() / path).read_text(encoding="utf-8")
            if path.endswith("unified_page_contract_v2_assembler.py"):
                return value.replace("contract_runtime.semantic_resolver", "removed_semantic_resolver")
            return value

        failures = validate(read_text)
        self.assertTrue(
            any("does not resolve component keys through the contract registry" in item for item in failures),
            failures,
        )

    def test_visible_money_label_fails(self):
        """A shared style that no longer clips turns the accessible name into a visible duplicate."""

        def read_text(path):
            value = (self._root() / path).read_text(encoding="utf-8")
            if path.endswith("styles/product-patterns.css"):
                return value.replace("clip-path: inset(50%) !important;", "")
            return value

        failures = validate(read_text)
        self.assertTrue(any("clip-path: inset(50%) !important" in item for item in failures), failures)

    def test_dropped_accessible_name_fails(self):
        """Removing the label carrier silences the screen reader instead of fixing the layout."""

        def read_text(path):
            value = (self._root() / path).read_text(encoding="utf-8")
            if path.endswith("design-system/ScMoney.vue"):
                return value.replace('class="sc-visually-hidden"', 'class="sc-design-money__label"')
            return value

        failures = validate(read_text)
        self.assertTrue(any("accessible label carrier" in item for item in failures), failures)

    @staticmethod
    def _root():
        from pathlib import Path
        return Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    unittest.main()
