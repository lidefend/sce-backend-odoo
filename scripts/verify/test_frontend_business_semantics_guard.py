from __future__ import annotations

import unittest
from pathlib import Path

from scripts.verify import frontend_business_semantics_guard as guard

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend/apps/web/src"


def source(path: str, replacement: tuple[str, str] | None = None):
    value = (FRONTEND / path).read_text(encoding="utf-8")
    if replacement is not None:
        value = value.replace(*replacement, 1)
    return value


class FrontendBusinessSemanticsGuardTest(unittest.TestCase):
    def test_repository_is_clean(self):
        self.assertEqual(guard.validate(), [])

    def test_kanban_field_name_inference_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            ("function rowTitle(", "const semanticValueByField = true;\nfunction rowTitle(")
            if path == "pages/KanbanPage.vue"
            else None,
        ))
        self.assertTrue(any("field names" in failure for failure in failures))

    def test_kanban_undeclared_title_fallback_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "return presentCollectionKanbanTitle({",
                "return formatValue(row.name, 'name'); presentCollectionKanbanTitle({",
            )
            if path == "pages/KanbanPage.vue"
            else None,
        ))
        self.assertTrue(any("undeclared fallback" in failure for failure in failures))

    def test_local_status_tone_table_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            ("export function isProfessionalBusinessValueField", "export function statusSemantic(value: unknown) { return 'info'; }\n\nexport function isProfessionalBusinessValueField")
            if path == "components/professional-fields/professionalBusinessValueModel.ts"
            else None,
        ))
        self.assertTrue(any("second status tone" in failure for failure in failures))

    def test_selection_backed_status_fail_open_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "if (statusType === 'selection' && !selection.length)",
                "if (selection.length)",
            )
            if path == guard.AUTHORITY
            else None,
        ))
        self.assertTrue(any("selection-backed status does not fail closed" in failure for failure in failures))

    def test_datatype_cannot_override_native_type(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "if (nativeType !== 'unknown') return nativeType;",
                "if (false) return nativeType;",
            )
            if path == guard.AUTHORITY
            else None,
        ))
        self.assertTrue(any("dataType fallback" in failure for failure in failures))

    def test_status_identity_requires_selection_or_char(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "if (statusType !== 'selection' && statusType !== 'char')",
                "if (false)",
            )
            if path == guard.AUTHORITY
            else None,
        ))
        self.assertTrue(any("status type identity" in failure for failure in failures))

    def test_empty_status_value_cannot_bypass_contract_validation(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "const statusContract = kind === 'status'\n"
                "    ? resolveDeclaredStatusContract(input.field)\n"
                "    : null;",
                "const statusContract = null;",
            )
            if path == guard.AUTHORITY
            else None,
        ))
        self.assertTrue(any("precede empty-value return" in failure for failure in failures))

    def test_numeric_zero_empty_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "const presentation = presentDeclaredBusinessValue({",
                "String(raw); const presentation = presentDeclaredBusinessValue({",
            )
            if path == "pages/listPage/listCellPresentation.ts"
            else None,
        ))
        self.assertTrue(any("[CFG-002]" in failure and "String(raw)" in failure for failure in failures))

    def test_local_money_formatter_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "return presentDeclaredBusinessValue({",
                "return formatDisplayValue(props.value, props.field); presentDeclaredBusinessValue({",
            )
            if path == "components/FieldValue.vue"
            else None,
        ))
        self.assertTrue(any("[CFG-004]" in failure for failure in failures))

    def test_generic_display_bypass_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "presentDeclaredBusinessValue({",
                "legacyDeclaredValue({",
            )
            if path == "utils/display.ts"
            else None,
        ))
        self.assertTrue(any("[CFG-001]" in failure for failure in failures))

    def test_generic_display_undeclared_fallback_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "missing: 'fieldDescriptor'",
                "missing: 'legacyValue'",
            )
            if path == "utils/display.ts"
            else None,
        ))
        self.assertTrue(any("undeclared value-formatting fallback" in failure for failure in failures))

    def test_field_value_attachment_appearance_inference_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "hasDeclaredAttachmentIdentity(props.field)",
                "true",
            )
            if path == "components/FieldValue.vue"
            else None,
        ))
        self.assertTrue(any("[CFG-010]" in failure for failure in failures))

    def test_list_attachment_appearance_inference_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "return hasDeclaredAttachmentIdentity(columnSemanticInput(field));",
                "return true;",
            )
            if path == "pages/ListPage.vue"
            else None,
        ))
        self.assertTrue(any("[CFG-010]" in failure for failure in failures))

    def test_percentage_precision_fallback_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "function requireDeclaredBusinessDigits(",
                "function legacyDeclaredDigits(",
            )
            if path == guard.AUTHORITY
            else None,
        ))
        self.assertTrue(any("require declared precision" in failure for failure in failures))

    def test_currency_code_precision_fallback_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "return declaredDigits[1];",
                "return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).resolvedOptions().maximumFractionDigits;",
            )
            if path == guard.AUTHORITY
            else None,
        ))
        self.assertTrue(any("currency-code metadata" in failure for failure in failures))

    def test_my_work_money_precision_fallback_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "normalizeDeclaredDigits([20, Number(value)])",
                "normalizeDeclaredDigits([20, 2])",
            )
            if path == "app/presentation/productMyWorkPresentation.ts"
            else None,
        ))
        self.assertTrue(any("my-work money facts do not require declared digits" in failure for failure in failures))

    def test_list_selection_raw_fallback_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            ("function semanticCell(", "function selectionLabel() { return ''; }\nfunction semanticCell(")
            if path == "pages/ListPage.vue"
            else None,
        ))
        self.assertTrue(any("[CFG-002]" in failure for failure in failures))

    def test_field_value_component_key_drop_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            ("componentKey: props.componentKey", "componentKey: undefined")
            if path == "components/FieldValue.vue"
            else None,
        ))
        self.assertTrue(any(
            "[CFG-004]" in failure and "componentKey: props.componentKey" in failure
            for failure in failures
        ))

    def test_relation_locale_resolution_drop_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            (
                "value = resolveLocalizedDisplayValue(value, locale);",
                "value = String(value);",
            )
            if path == guard.AUTHORITY
            else None,
        ))
        self.assertTrue(any("resolveLocalizedDisplayValue(" in failure for failure in failures))

    def test_local_empty_text_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            ("fallback = FIELD_VALUE_EMPTY_TEXT", "fallback = '—'")
            if path == "components/professional-fields/professionalBaseFieldModel.ts"
            else None,
        ))
        self.assertTrue(any("local em dash" in failure for failure in failures))

    def test_native_canvas_local_unfilled_text_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            ("resolveReadonlyEmptyText(field)", "resolveReadonlyEmptyText(field, '未填写')")
            if path == "pages/contractForm/ContractFormNativeCanvas.vue"
            else None,
        ))
        self.assertTrue(any("Native form canvas uses a local unfilled text" in failure for failure in failures))

    def test_detail_collection_em_dash_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            ("return text || FIELD_VALUE_EMPTY_TEXT;", "return text || '—';")
            if path == "components/template/X2ManyRelationRenderer.vue"
            else None,
        ))
        self.assertTrue(any("Detail collection cells" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
