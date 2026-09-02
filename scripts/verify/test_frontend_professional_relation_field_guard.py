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

    def test_readonly_one2many_cannot_show_empty_before_hydration_finishes(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace("adapter.isOne2manyHydrating(field.name)", "adapter.busy", 1)
            return value
        self.assertTrue(any("readonly one2many loading semantics" in item for item in validate(read_text)))

    def test_one2many_hydration_state_must_reset_on_failure(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordRelationshipFields.ts"):
                return value.replace("finally {", "if (false) {", 1)
            return value
        self.assertTrue(any("hydration lifecycle" in item for item in validate(read_text)))

    def test_many2many_inline_create_default_allow_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("relationDescriptor.ts"):
                return value.replace(
                    "entry?.canCreate === true && entry.inlineCreate?.enabled",
                    "entry?.canCreate !== false && entry.inlineCreate?.enabled",
                )
            return value

        self.assertTrue(any("does not fail closed" in item for item in validate(read_text)))

    def test_unguarded_many2many_quick_create_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordFormState.ts"):
                return value.replace("entry?.canCreate!==true||!relation", "!relation")
            return value

        self.assertTrue(any("handler does not independently" in item for item in validate(read_text)))

    def test_frontend_relation_model_inference_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordActionPresentation.ts"):
                return value + "\nconst fallbackMap: Record<string, string> = { tag_ids: 'res.partner.category' };\n"
            return value

        self.assertTrue(any("field/model inference" in item for item in validate(read_text)))

    def test_unguarded_professional_many2many_create_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordActionPresentation.ts"):
                return value.replace(
                    "entry?.canCreate !== true || !inline.enabled || !inline.createOnNoMatch || !relation",
                    "!relation",
                )
            return value

        self.assertTrue(any("professional many2many" in item for item in validate(read_text)))

    def test_unguarded_many2one_quick_create_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordRelationshipNavigation.ts"):
                return value.replace(
                    "entry?.canCreate !== true || !inline.enabled || !inline.createOnNoMatch",
                    "false",
                )
            return value

        self.assertTrue(any("many2one quick-create" in item for item in validate(read_text)))

    def test_relation_search_dialog_without_read_authority_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordRelationships.ts"):
                return value.replace(
                    "if (relationEntry(resolvedDescriptor)?.canRead !== true) return;",
                    "",
                )
            return value

        self.assertTrue(any("search read authority" in item for item in validate(read_text)))

    def test_relation_search_rows_fail_open_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordRelationships.ts"):
                return value.replace(
                    "if (entry?.canRead !== true) return [];",
                    "if (entry && entry.canRead === false) return [];",
                )
            return value

        self.assertTrue(any("fail-open read authority" in item for item in validate(read_text)))

    def test_relation_ids_without_field_write_authority_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordFormState.ts"):
                return value.replace(
                    "const setRelationIds=(name:string,ids:number[])=>{if(!isFieldWritable(name))return;",
                    "const setRelationIds=(name:string,ids:number[])=>{",
                )
            return value

        self.assertTrue(any("selection write authority" in item for item in validate(read_text)))

    def test_relation_search_selection_without_canonical_write_authority_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordRelationships.ts"):
                return value.replace(
                    "canonicalWritable === false || (canonicalWritable !== true && (!layoutField || layoutField.readonly))",
                    "false",
                )
            return value

        self.assertTrue(any("canonical write authority" in item for item in validate(read_text)))


if __name__ == "__main__":
    unittest.main()
