import unittest
from pathlib import Path

from scripts.verify.frontend_professional_relation_field_guard import validate

ROOT = Path(__file__).resolve().parents[2]


class ProfessionalRelationFieldGuardTests(unittest.TestCase):
    def test_current_sources_pass(self):
        self.assertEqual(validate(), [])

    def test_missing_semantic_marker_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace('data-professional-field-family="relation"', "data-family-removed")
        self.assertTrue(any("missing marker" in item for item in validate(read_text)))

    def test_model_special_case_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value + "\n// project.project\n" if path.endswith("professionalRelationFieldModel.ts") else value
        self.assertTrue(any("forbidden product special case" in item for item in validate(read_text)))


if __name__ == "__main__":
    unittest.main()
