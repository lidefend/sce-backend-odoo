import unittest

from scripts.verify.frontend_professional_base_field_guard import ROOT, validate


class ProfessionalBaseFieldGuardTest(unittest.TestCase):
    def test_repository_passes(self):
        self.assertEqual(validate(), [])

    def test_missing_production_route_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace("<ProfessionalBaseFieldControl", "<LegacyBaseFieldControl") if path.endswith("FormSection.vue") else value

        self.assertTrue(any("does not route" in failure for failure in validate(source)))

    def test_missing_semantic_marker_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace('data-professional-field-family="base"', 'data-family-removed="base"') if path.endswith("ProfessionalBaseFieldControl.vue") else value

        self.assertTrue(any("data-professional-field-family" in failure for failure in validate(source)))

    def test_unguarded_text_handler_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordFormState.ts"):
                return value.replace(
                    "const setTextField=(name:string,value:string)=>{if(!isFieldWritable(name))return;",
                    "const setTextField=(name:string,value:string)=>{",
                )
            return value

        self.assertTrue(any("does not fail closed" in failure for failure in validate(source)))

    def test_filename_companion_using_public_text_handler_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordActionPresentation.ts"):
                return value.replace(
                    "setTechnicalCompanionTextField(filenameField, payload.fileName);",
                    "setTextField(filenameField, payload.fileName);",
                )
            return value

        self.assertTrue(any("technical write path" in failure for failure in validate(source)))


if __name__ == "__main__":
    unittest.main()
