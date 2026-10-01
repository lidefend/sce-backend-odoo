import unittest

from scripts.verify.frontend_professional_base_field_guard import ROOT, validate

# The search-keyword handler opens with the fail-closed guard today. These
# fixtures re-wrap that exact opening without changing what it does, so the
# assertion can be shown to bind to the statement rather than to the layout.
HANDLER_OPEN = (
    "const queryMany2oneInline=(name:string,_descriptor:FieldDescriptor|undefined,value:string,"
    "occurrenceKey?:string)=>{\n    if(!isFieldWritable(name,occurrenceKey))return;"
)
REWRAPPED_GUARDED = (
    "const queryMany2oneInline=(name:string,_descriptor:FieldDescriptor|undefined,value:string,"
    "occurrenceKey?:string)=>\n  {\n"
    "    // re-wrapped while keeping the same fail-closed opening\n"
    "    if( !isFieldWritable( name, occurrenceKey ) ) return;"
)
REWRAPPED_UNGUARDED = (
    "const queryMany2oneInline=(name:string,_descriptor:FieldDescriptor|undefined,value:string,"
    "occurrenceKey?:string)=>\n  {\n"
    "    // re-wrapped and the fail-closed opening is gone\n"
    "    const typedKeyword=resolveProfessionalMany2oneSearchInput(value);"
)
REWRAPPED_GUARD_MOVED = (
    "const queryMany2oneInline=(name:string,_descriptor:FieldDescriptor|undefined,value:string,"
    "occurrenceKey?:string)=>\n  {\n"
    "    // re-wrapped and the guard no longer opens the body\n"
    "    const typedKeyword=resolveProfessionalMany2oneSearchInput(value);\n"
    "    if(!isFieldWritable(name,occurrenceKey))return;"
)


class ProfessionalBaseFieldGuardTest(unittest.TestCase):
    def test_occurrence_authority_cannot_regress_to_field_name_only(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordFormState.ts"):
                self.assertIn("isFieldWritable(name,occurrenceKey)", value)
                return value.replace("isFieldWritable(name,occurrenceKey)", "isFieldWritable(name)")
            return value
        self.assertTrue(any("does not fail closed" in failure for failure in validate(source)))

    def test_repository_passes(self):
        self.assertEqual(validate(), [])

    def test_missing_production_route_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace("<ProfessionalBaseFieldControl", "<LegacyBaseFieldControl") if path.endswith("FormSection.vue") else value

        self.assertTrue(any("does not route" in failure for failure in validate(source)))

    def test_date_range_accessibility_markers_are_required(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace('aria-label="开始日期"', 'aria-label="日期"', 1)
            return value

        self.assertTrue(any("date range accessibility" in failure for failure in validate(source)))

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
                    "const setTextField=(name:string,value:string,occurrenceKey?:string)=>{if(!isFieldWritable(name,occurrenceKey))return;",
                    "const setTextField=(name:string,value:string)=>{",
                )
            return value

        self.assertTrue(any("does not fail closed" in failure for failure in validate(source)))

    def test_duplicate_primitive_inline_padding_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalBaseFieldControl.vue"):
                return value.replace(
                    "min-height: calc(var(--sc-component-input-height-md) * 1px);",
                    "min-height: calc(var(--sc-component-input-height-md) * 1px);\n  padding-inline: calc(var(--sc-component-input-padding-x) * 1px);",
                    1,
                )
            return value

        self.assertTrue(any("duplicate primitive inline padding" in failure for failure in validate(source)))

    def test_html_editor_control_semantics_are_required(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("RestrictedHtmlEditor.vue"):
                return value.replace(':aria-describedby="describedBy"', ':data-missing-describedby="describedBy"', 1)
            return value

        self.assertTrue(any("restricted html editor missing control semantics" in failure for failure in validate(source)))

    def test_html_field_branch_must_pass_control_identity(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalBaseFieldControl.vue"):
                prefix, html_branch = value.split("<RestrictedHtmlEditor", 1)
                return prefix + "<RestrictedHtmlEditor" + html_branch.replace(':id="controlId"', ':data-missing-id="controlId"', 1)
            return value

        self.assertTrue(any("professional html field does not pass through" in failure for failure in validate(source)))

    def test_text_field_branch_must_pass_control_identity(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalBaseFieldControl.vue"):
                prefix, branch = value.split("<ScTextarea", 1)
                return prefix + "<ScTextarea" + branch.replace(':id="controlId"', ':data-missing-id="controlId"', 1)
            return value

        self.assertTrue(any("professional text field does not pass through" in failure for failure in validate(source)))

    def test_number_field_branch_must_pass_error_association(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalBaseFieldControl.vue"):
                prefix, branch = value.split("<ScNumberInput", 1)
                return prefix + "<ScNumberInput" + branch.replace(':described-by="describedBy"', '', 1)
            return value

        self.assertTrue(any("professional number field does not pass through" in failure for failure in validate(source)))

    def test_boolean_field_branch_must_pass_invalid_state(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalBaseFieldControl.vue"):
                prefix, branch = value.split("<ScCheckbox", 1)
                return prefix + "<ScCheckbox" + branch.replace(':invalid="field.invalid"', '', 1)
            return value

        self.assertTrue(any("professional boolean field does not pass through" in failure for failure in validate(source)))

    def test_rewrapped_handler_still_passes(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordFormState.ts"):
                self.assertIn(HANDLER_OPEN, value)
                return value.replace(HANDLER_OPEN, REWRAPPED_GUARDED, 1)
            return value

        self.assertEqual(validate(source), [])

    def test_rewrapped_handler_without_the_guard_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordFormState.ts"):
                return value.replace(HANDLER_OPEN, REWRAPPED_UNGUARDED, 1)
            return value

        self.assertTrue(any("does not fail closed" in failure for failure in validate(source)))

    def test_rewrapped_handler_that_does_not_open_with_the_guard_fails(self):
        def source(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordFormState.ts"):
                return value.replace(HANDLER_OPEN, REWRAPPED_GUARD_MOVED, 1)
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
