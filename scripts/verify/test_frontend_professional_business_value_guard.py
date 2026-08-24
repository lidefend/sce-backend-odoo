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

    @staticmethod
    def _root():
        from pathlib import Path
        return Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    unittest.main()
