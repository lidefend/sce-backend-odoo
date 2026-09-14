import unittest
from pathlib import Path

from scripts.verify.frontend_professional_detail_collection_guard import validate

ROOT = Path(__file__).resolve().parents[2]


class ProfessionalDetailCollectionGuardTests(unittest.TestCase):
    def test_current_sources_pass(self):
        self.assertEqual(validate(), [])

    def test_missing_marker_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value.replace('data-professional-field-family="detail-collection"', "data-family-removed")
        self.assertTrue(any("missing marker" in item for item in validate(read_text)))

    def test_model_special_case_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            return value + "\n// payment.request\n" if path.endswith("professionalDetailCollectionModel.ts") else value
        self.assertTrue(any("forbidden product special case" in item for item in validate(read_text)))

    def test_page_scoped_amount_total_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace(
                    "return one2manyRows.value.reduce",
                    "return paginatedOne2manyRows.value.reduce",
                )
            return value

        failures = validate(read_text)
        self.assertTrue(any("current page" in item for item in failures))

    def test_zero_amount_total_hidden_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace(
                    "if (!amountColumns.length || !one2manyRows.value.length) return [];",
                    "if (!o2mAmountTotal.value) return [];",
                )
            return value

        failures = validate(read_text)
        self.assertTrue(any("when it is zero" in item for item in failures))

    def test_amount_total_without_scope_label_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace(
                    "_stateLabel: `全部 ${one2manyRows.value.length} 条合计`,",
                    "_stateLabel: '',",
                )
            return value

        failures = validate(read_text)
        self.assertTrue(any("aggregate scope" in item for item in failures))

    def test_first_monetary_column_only_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace(".filter(isO2mAmountColumn)", ".find(isO2mAmountColumn)")
            return value

        failures = validate(read_text)
        self.assertTrue(any("first monetary column" in item for item in failures))

    def test_missing_unlink_authority_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace('v-if="adapter.one2manyCanUnlink(field.name)"', '')
            return value

        failures = validate(read_text)
        self.assertTrue(any("without unlink authority" in item for item in failures))

    def test_unlink_policy_default_allow_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("one2manyUtils.ts"):
                return value.replace("return policies.can_unlink === true;", "return policies.can_unlink !== false;")
            return value

        failures = validate(read_text)
        self.assertTrue(any("does not fail closed" in item for item in failures))

    def test_unguarded_remove_handler_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordActionPresentation.ts"):
                return value.replace("if (!one2manyCanUnlink(fieldName)) return;", "")
            return value

        failures = validate(read_text)
        self.assertTrue(any("handler does not fail closed" in item for item in failures))

    def test_removal_labels_must_come_from_policy(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("relationField.types.ts"):
                return value.replace(
                    "one2manyRemovalLabels: (name: string, removedCount?: number)",
                    "removedLabels: (name: string, removedCount?: number)",
                    1,
                )
            return value

        failures = validate(read_text)
        self.assertTrue(any("authoritative removal labels" in item for item in failures))

    def test_inline_edit_policy_default_allow_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("one2manyUtils.ts"):
                return value.replace("return policies.inline_edit === true;", "return policies.inline_edit !== false;")
            return value

        failures = validate(read_text)
        self.assertTrue(any("inline-edit authority does not fail closed" in item for item in failures))

    def test_input_without_inline_edit_authority_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("One2ManyCellEditor.vue"):
                return value.replace(" || !adapter.one2manyCanInlineEdit(fieldName)", "", 1)
            return value

        failures = validate(read_text)
        self.assertTrue(any("inputs do not consistently" in item for item in failures))

    def test_desktop_and_mobile_cell_logic_cannot_diverge(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace("<One2ManyCellEditor", "<RemovedCellEditor", 1)
            return value

        self.assertTrue(any("same cell editor" in item for item in validate(read_text)))

    def test_cell_feedback_cannot_reference_absent_error(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("One2ManyCellEditor.vue"):
                return value.replace("errorText.value ? props.errorId", "props.errorId", 1)
            return value

        self.assertTrue(any("cell feedback association" in item for item in validate(read_text)))

    def test_responsive_cell_controls_require_unique_identities(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace(
                    ":control-id=\"one2manyCellControlId(field.name, row.key, column.name, 'mobile')\"",
                    ':control-id="one2manyCellControlId(field.name, row.key, column.name)"',
                    1,
                )
            return value

        self.assertTrue(any("layout-scoped identities" in item for item in validate(read_text)))

    def test_mobile_cell_label_must_target_visible_control(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace(
                    ":for=\"one2manyCellControlId(field.name, row.key, column.name, 'mobile')\"",
                    '',
                    1,
                )
            return value

        self.assertTrue(any("mobile detail labels" in item for item in validate(read_text)))

    def test_row_specific_readonly_modifier_cannot_be_dropped(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace(
                    "adapter.one2manyEffectiveColumn(field.name, row._row, column)",
                    "column",
                    1,
                )
            return value

        self.assertTrue(any("row-specific modifiers" in item for item in validate(read_text)))

    def test_readonly_table_cannot_restore_draft_change_column(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace(
                    "const readonlyO2mTableColumns = computed(() => {\n  return [",
                    "const readonlyO2mTableColumns = computed(() => {\n  const stateColumn = [{ colKey: '_stateLabel', title: '行变更' }];\n  return [...stateColumn,",
                    1,
                )
            return value

        self.assertTrue(any("draft row-change status as a primary column" in item for item in validate(read_text)))

    def test_readonly_mobile_card_cannot_restore_draft_change_label(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace(
                    "第 {{ (one2manyPage - 1) * one2manyPageSize + rowIndex + 1 }} 条",
                    "{{ adapter.one2manyRowStateLabel(row) }}",
                    1,
                )
            return value

        self.assertTrue(any("readonly mobile detail cards expose draft" in item for item in validate(read_text)))

    def test_editable_controls_cannot_use_text_ellipsis(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace(
                    "detailCollectionColumnPresentation(column, columnIndex, false)",
                    "detailCollectionColumnPresentation(column, columnIndex, true)",
                    1,
                )
            return value

        self.assertTrue(any("TDesign text ellipsis" in item for item in validate(read_text)))

    def test_readonly_truncation_must_preserve_complete_value(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace("<ScPopover", "<RemovedPopover", 1)
            return value

        self.assertTrue(any("complete-value" in item for item in validate(read_text)))

    def test_readonly_mobile_trailing_facts_require_actionable_disclosure(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace("<ScDisclosure", "<RemovedDisclosure", 1)
            return value

        self.assertTrue(any("trailing facts" in item for item in validate(read_text)))

    def test_readonly_collection_title_cannot_return_to_external_field_label(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("FormSection.vue"):
                return value.replace(
                    "if (!props.relationAdapter) return false;",
                    "if (field.readonly || !props.relationAdapter) return false;",
                    1,
                )
            return value

        self.assertTrue(any("duplicate the collection-owned title" in item for item in validate(read_text)))

    def test_missing_column_label_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace("title: column.label", "title: ''")
            return value

        self.assertTrue(any("authoritative labels" in item for item in validate(read_text)))

    def test_unguarded_inline_update_handler_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordActionPresentation.ts"):
                return value.replace("if (!one2manyCanInlineEdit(fieldName)) return;", "")
            return value

        failures = validate(read_text)
        self.assertTrue(any("field update handler" in item for item in failures))

    def test_create_policy_default_allow_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("one2manyUtils.ts"):
                return value.replace("return policies.can_create === true;", "return policies.can_create !== false;")
            return value

        failures = validate(read_text)
        self.assertTrue(any("create authority does not fail closed" in item for item in failures))

    def test_unguarded_create_handler_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordActionPresentation.ts"):
                return value.replace("if (!one2manyCanCreate(fieldName)) return;", "")
            return value

        failures = validate(read_text)
        self.assertTrue(any("row creation handler" in item for item in failures))

    def test_row_creation_cannot_wait_for_optional_column_hydration(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordActionPresentation.ts"):
                return value.replace(
                    "addOne2manyRow(fieldName);",
                    "Promise.resolve(dependencies.ensureRelationFieldDescriptors?.(fieldName)).then(() => addOne2manyRow(fieldName));",
                    1,
                )
            return value

        self.assertTrue(any("optional column hydration" in item for item in validate(read_text)))

    def test_missing_row_open_authority_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace('v-if="adapter.one2manyCanOpenRow(field.name, row._row)"', '')
            return value

        self.assertTrue(any("hide row-open" in item for item in validate(read_text)))

    def test_unguarded_row_open_handler_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("useRecordActionPresentation.ts"):
                return value.replace("recordId <= 0 || !dependencies.canOpenRelationRecord(", "recordId <= 0 || false && dependencies.canOpenRelationRecord(")
            return value

        self.assertTrue(any("row-open handler" in item for item in validate(read_text)))

    def test_stale_relation_request_can_never_become_authoritative(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace("return relationQueryAuthority.isCurrent(key, revision)", "return true", 1)
            return value

        self.assertTrue(any("latest-condition" in item for item in validate(read_text)))

    def test_unrelated_row_values_cannot_drive_relation_queries(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace("rowKey: row.key,", "rowKey: `${row.key}:${JSON.stringify(row.values)}`,", 1)
            return value

        self.assertTrue(any("unrelated row values" in item for item in validate(read_text)))

    def test_relation_search_must_preserve_selected_label(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace("preserveSelectedOne2manyRelationOption", "discardSelectedRelationOption")
            return value

        self.assertTrue(any("selected relation label" in item for item in validate(read_text)))

    def test_relation_candidates_cannot_load_before_popup_interaction(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("X2ManyRelationRenderer.vue"):
                return value.replace(
                    "relationPopupAuthority.isOpen(key) && relationColumnCanQuery",
                    "relationColumnCanQuery",
                    1,
                )
            return value

        self.assertTrue(any("before interaction" in item for item in validate(read_text)))

    def test_relation_failure_without_retry_fails(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("One2ManyCellEditor.vue"):
                return value.replace("@click=\"$emit('retry')\"", "")
            return value

        self.assertTrue(any("does not expose retry" in item for item in validate(read_text)))

    def test_unsupported_relation_domain_must_fail_closed(self):
        def read_text(path):
            value = (ROOT / path).read_text(encoding="utf-8")
            if path.endswith("one2manyUtils.ts"):
                return value.replace("relationDomainSupported: domainAnalysis.supported,", "")
            return value

        self.assertTrue(any("do not fail closed" in item for item in validate(read_text)))


if __name__ == "__main__":
    unittest.main()
