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


if __name__ == "__main__":
    unittest.main()
