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
            ("presentCollectionKanbanCell", "semanticValueByField")
            if path == "pages/KanbanPage.vue"
            else None,
        ))
        self.assertTrue(any("field names" in failure for failure in failures))

    def test_local_status_tone_table_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            ("export function isProfessionalBusinessValueField", "export function statusSemantic(value: unknown) { return 'info'; }\n\nexport function isProfessionalBusinessValueField")
            if path == "components/professional-fields/professionalBusinessValueModel.ts"
            else None,
        ))
        self.assertTrue(any("second status tone" in failure for failure in failures))

    def test_numeric_zero_empty_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            ("missing) text = emptyText", "missing) text = '0'")
            if path == "pages/listPage/listCellPresentation.ts"
            else None,
        ))
        self.assertTrue(any("missing numeric" in failure for failure in failures))

    def test_local_money_formatter_fails(self):
        failures = guard.validate(lambda path: source(
            path,
            ("return formatMonetaryDisplayValue(", "return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(")
            if path == "components/FieldValue.vue"
            else None,
        ))
        self.assertTrue(any("second monetary formatter" in failure for failure in failures))

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
