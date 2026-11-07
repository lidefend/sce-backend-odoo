import unittest

from scripts.verify.frontend_expression_guard import ROOT, validate


TARGET = "frontend/apps/web/src/components/business/MyWorkApprovalWorkspace.vue"


def _read(rel: str) -> str:
    text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
    return text


class FrontendExpressionGuardTest(unittest.TestCase):
    def test_repository_passes(self):
        self.assertEqual(validate(), [])

    def test_money_formatter_redefinition_fails(self):
        def source(rel):
            if rel == TARGET:
                return _read(rel) + "\nexport function formatMonetaryDisplayValue(){ return ''; }\n"
            return None

        self.assertTrue(any("G1 money formatter" in failure for failure in validate(source)))

    def test_local_fmt_money_outside_adapter_fails(self):
        def source(rel):
            if rel == TARGET:
                return _read(rel) + "\nfunction fmtMoney(value){ return Number(value).toFixed(2); }\n"
            return None

        self.assertTrue(any("G1 local fmtMoney" in failure for failure in validate(source)))

    def test_direct_date_primitive_bypass_fails(self):
        def source(rel):
            if rel == TARGET:
                return _read(rel) + "\n<TDesignDatePicker v-model=\"x\" />\n"
            return None

        self.assertTrue(any("G2 TDesignDatePicker" in failure for failure in validate(source)))

    def test_empty_text_redefinition_fails(self):
        def source(rel):
            if rel == TARGET:
                return _read(rel) + "\nexport const BUSINESS_EMPTY_TEXT = '--';\n"
            return None

        self.assertTrue(any("G3 an EMPTY_TEXT" in failure for failure in validate(source)))

    def test_status_tone_redefinition_fails(self):
        def source(rel):
            if rel == TARGET:
                return _read(rel) + "\nexport function resolveStatusTone(){ return 'neutral'; }\n"
            return None

        self.assertTrue(any("G4 resolveStatusTone" in failure for failure in validate(source)))

    def test_direct_execute_dispatch_fails(self):
        def source(rel):
            if rel == TARGET:
                return _read(rel) + "\nintentRequest({ intent: 'execute', params: {} });\n"
            return None

        self.assertTrue(any("G9 direct intent 'execute'" in failure for failure in validate(source)))

    def test_platform_industry_token_fails(self):
        def source(rel):
            if rel == TARGET:
                return _read(rel) + "\nconst key = 'sc.payment.settlement_detail_collection';\n"
            return None

        self.assertTrue(any("G10 platform file references" in failure for failure in validate(source)))

    def test_professional_control_import_outside_dispatcher_fails(self):
        def source(rel):
            if rel == TARGET:
                return _read(rel) + "\nimport ProfessionalBaseFieldControl from '../../components/professional-fields/ProfessionalBaseFieldControl.vue';\n"
            return None

        self.assertTrue(any("G-field-render-a" in failure for failure in validate(source)))

    def test_industry_control_import_outside_registration_fails(self):
        def source(rel):
            if rel == TARGET:
                return _read(rel) + "\nimport PaymentSettlementDetailCollectionControl from '../../components/professional-fields/PaymentSettlementDetailCollectionControl.vue';\n"
            return None

        self.assertTrue(any("G-field-render-c" in failure for failure in validate(source)))


if __name__ == "__main__":
    unittest.main()
