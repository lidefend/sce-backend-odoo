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

    def test_many2one_panel_actions_cannot_drop_the_shared_button(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalMany2oneFieldControl.vue"):
                return value.replace("<ScButton", "<div", 1)
            return value
        self.assertTrue(any("five shared ScButton" in item for item in validate(read_text)))

    def test_many2one_panel_actions_cannot_regress_to_a_private_button(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalMany2oneFieldControl.vue"):
                return value.replace("<ScButton", "<button", 1)
            return value
        self.assertTrue(any("private button element" in item for item in validate(read_text)))

    def test_many2one_command_cannot_override_primitive_hover(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return f"{value}\n.many2one-action:hover {{ background: red; }}" if path.endswith("ProfessionalMany2oneFieldControl.vue") else value
        self.assertTrue(any("override" in item for item in validate(read_text)))


    def test_many2one_cannot_rebuild_a_second_keyboard_index(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalMany2oneFieldControl.vue"):
                return f"{value}\nconst activeIndex = ref(-1);\n"
            return value

        self.assertTrue(any("reimplements official select interaction: activeIndex" in item for item in validate(read_text)))

    def test_many2one_cannot_rebuild_a_second_popup(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalMany2oneFieldControl.vue"):
                return f"{value}\n// ScPopover\n"
            return value

        self.assertTrue(any("reimplements official select interaction: ScPopover" in item for item in validate(read_text)))

    def test_many2one_cannot_restore_a_delayed_blur(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalMany2oneFieldControl.vue"):
                return f"{value}\nwindow.setTimeout(() => inputEl.blur(), 0);\n"
            return value

        self.assertTrue(any("reimplements official select interaction: blur()" in item for item in validate(read_text)))

    def test_many2one_must_keep_the_explicit_query_channel(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalMany2oneFieldControl.vue"):
                return value.replace('@update:query-value="onQueryValueChange"', "", 1)
            return value

        self.assertTrue(any("state channel is incomplete" in item for item in validate(read_text)))

    def test_relation_primitive_must_delegate_to_the_official_driver(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("design-system/ScRelationField.vue"):
                return value.replace("<TDesignSelect", "<TDesignInput", 1)
            return value

        self.assertTrue(any("delegate to the official select driver" in item for item in validate(read_text)))

    def test_relation_primitive_cannot_keep_the_retired_driver(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("design-system/ScRelationField.vue"):
                return f"{value}\n// TDesignAutoComplete\n"
            return value

        self.assertTrue(any("retains a retired hand-written interaction" in item for item in validate(read_text)))

    def test_relation_primitive_cannot_forge_a_dom_event(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("design-system/ScRelationField.vue"):
                return f"{value}\nemit('change', {{ target: {{}} }} as unknown as Event);\n"
            return value

        self.assertTrue(any("retains a retired hand-written interaction" in item for item in validate(read_text)))

    def test_many2one_must_consume_projected_display_value(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalMany2oneFieldControl.vue"):
                return value.replace(
                    "resolveProfessionalMany2oneDisplayValue(props.field)",
                    "''",
                    1,
                )
            return value

        self.assertTrue(any("projected display value" in item for item in validate(read_text)))

    def test_many2one_must_consume_the_runtime_keyword_channel(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalMany2oneFieldControl.vue"):
                return value.replace(
                    "resolveProfessionalMany2oneQueryKeyword(props.field)",
                    "''",
                    1,
                )
            return value

        self.assertTrue(any("runtime search keyword channel" in item for item in validate(read_text)))

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

    def test_many2many_create_without_field_write_authority_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordActionPresentation.ts"):
                return value.replace(
                    "quickCreateRelationMany: async (fieldName: string) => {\n      if (!isFieldWritable(fieldName)) return;",
                    "quickCreateRelationMany: async (fieldName: string) => {",
                )
            return value

        self.assertTrue(any("create handler" in item for item in validate(read_text)))

    def test_many2many_cannot_reintroduce_a_blur_timer(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalManyToManySelect.vue"):
                return value.replace(
                    '      @popup-visible-change="onPopupVisibleChange"\n',
                    '      @popup-visible-change="onPopupVisibleChange"\n      @blur="onBlur"\n',
                ).replace(
                    "function onPopupVisibleChange(visible: boolean) {",
                    "function onBlur() {\n  setTimeout(() => resetKeyword(), 200);\n}\n\nfunction onPopupVisibleChange(visible: boolean) {",
                )
            return value

        failures = validate(read_text)
        self.assertTrue(any("many2many reimplements official select interaction: setTimeout" in item for item in failures))
        self.assertTrue(any("many2many reimplements official select interaction: @blur=" in item for item in failures))

    def test_many2many_must_follow_the_official_close_signal(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalManyToManySelect.vue"):
                return value.replace('@popup-visible-change="onPopupVisibleChange"', "")
            return value

        self.assertTrue(any("many2many state channel is incomplete" in item for item in validate(read_text)))

    def test_many2many_must_keep_the_official_keyboard_commit_channel(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalManyToManySelect.vue"):
                return value.replace(':tag-input-props="tagInputProps"', "").replace(
                    "const tagInputProps = { max: -1 };", ""
                )
            return value

        failures = validate(read_text)
        self.assertTrue(any("official keyboard commit channel is incomplete: :tag-input-props=\"tagInputProps\"" in item for item in failures))
        self.assertTrue(any("official keyboard commit channel is incomplete: const tagInputProps = { max: -1 }" in item for item in failures))

    def test_many2many_must_keep_the_official_channel_rationale_and_exit(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalManyToManySelect.vue"):
                return value.replace("// official-enter-keyword:", "// ").replace(
                    "// official-enter-keyword-exit:", "// "
                )
            return value

        failures = validate(read_text)
        self.assertTrue(any("official keyboard commit channel is incomplete: official-enter-keyword:" in item for item in failures))
        self.assertTrue(any("official keyboard commit channel is incomplete: official-enter-keyword-exit:" in item for item in failures))

    def test_many2many_must_not_return_to_the_recorded_gap_note(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalManyToManySelect.vue"):
                return value.replace("// official-enter-keyword:", "// upstream-gap: m2m-enter-with-keyword", 1)
            return value

        self.assertTrue(any("records a retired keyboard gap note" in item for item in validate(read_text)))

    def test_many2many_must_not_hand_roll_a_second_keyboard_loop(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalManyToManySelect.vue"):
                return f"{value}\nfunction handleKeydown(event: KeyboardEvent) {{}}\n"
            return value

        self.assertTrue(any("many2many reimplements official select interaction: handleKeydown" in item for item in validate(read_text)))

    def test_many2many_must_keep_the_official_panel_width_ceiling(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("ProfessionalManyToManySelect.vue"):
                return value.replace(":popup-props=\"popupProps\"", "")
            return value

        self.assertTrue(any(":popup-props=\"popupProps\"" in item for item in validate(read_text)))


if __name__ == "__main__":
    unittest.main()
