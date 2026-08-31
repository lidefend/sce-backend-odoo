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

    def test_many2one_command_cannot_regress_to_private_button(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalMany2oneFieldControl.vue"):
                return value.replace('<ScButton\n                type="button"', '<button\n                type="button"', 1)
            return value
        self.assertTrue(any("five shared ScButton" in item for item in validate(read_text)))

    def test_many2one_option_cannot_regress_to_private_button(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalMany2oneFieldControl.vue"):
                return value.replace('<ScButton\n                type="button"', '<button\n                type="button"', 1)
            return value
        self.assertTrue(any("listbox options" in item for item in validate(read_text)))

    def test_many2one_command_cannot_override_primitive_hover(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return f"{value}\n.many2one-action:hover {{ background: red; }}" if path.endswith("ProfessionalMany2oneFieldControl.vue") else value
        self.assertTrue(any("override" in item for item in validate(read_text)))

    def test_field_label_editor_cannot_regress_to_private_input(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace('<ScInput\n              v-else-if="fieldConfigEditable"', '<input\n              v-else-if="fieldConfigEditable"', 1)
        self.assertTrue(any("label editor" in item for item in validate(read_text)))


if __name__ == "__main__":
    unittest.main()
