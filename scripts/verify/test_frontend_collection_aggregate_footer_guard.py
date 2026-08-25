import unittest

from scripts.verify.frontend_collection_aggregate_footer_guard import FOOTER, FOOTER_CSS, LIST_PAGE, PRESENTATION, VISUAL_SMOKE, validate


class CollectionAggregateFooterGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.list_source = LIST_PAGE.read_text(encoding="utf-8")
        cls.footer_source = FOOTER.read_text(encoding="utf-8")
        cls.css_source = FOOTER_CSS.read_text(encoding="utf-8")
        cls.visual_source = VISUAL_SMOKE.read_text(encoding="utf-8")
        cls.presentation_source = PRESENTATION.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.list_source, self.footer_source, self.css_source), [])

    def test_parallel_footer_fails(self):
        altered = self.list_source + "\n<tfoot><tr><td>legacy</td></tr></tfoot>\n"
        self.assertTrue(any("parallel" in item for item in validate(altered, self.footer_source, self.css_source)))

    def test_missing_group_adapter_fails(self):
        altered = self.list_source.replace('context="group"', 'context="flat"')
        self.assertTrue(any('context="group"' in item for item in validate(altered, self.footer_source, self.css_source)))

    def test_missing_scope_marker_fails(self):
        altered = self.footer_source.replace(':data-aggregate-scope="row.scope"', '')
        self.assertTrue(any("aggregate-scope" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_row_header_semantics_fails(self):
        altered = self.footer_source.replace('scope="row"', '').replace('data-aggregate-row-label', '')
        self.assertTrue(any('scope="row"' in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_mobile_summary_adapter_fails(self):
        altered = self.list_source.replace('layout="summary"', 'layout="table"')
        self.assertTrue(any('layout="summary"' in item for item in validate(altered, self.footer_source, self.css_source)))

    def test_missing_total_tone_fails(self):
        altered = self.css_source.replace("[data-aggregate-scope='total']", ".legacy-total")
        self.assertTrue(any("aggregate-scope" in item for item in validate(self.list_source, self.footer_source, altered)))

    def test_missing_tabular_numbers_fails(self):
        altered = self.css_source.replace("font-variant-numeric: tabular-nums", "font-variant-numeric: normal")
        self.assertTrue(any("tabular-nums" in item for item in validate(self.list_source, self.footer_source, altered)))

    def test_missing_browser_evidence_fails(self):
        altered = self.visual_source.replace("misalignedNumericCells", "legacyAlignment")
        self.assertTrue(any("misalignedNumericCells" in item for item in validate(
            self.list_source, self.footer_source, self.css_source, altered,
        )))

    def test_missing_display_field_authority_fails(self):
        altered = self.presentation_source.replace("aggregates[displayKey]", "aggregates[sourceKey]")
        self.assertTrue(any("displayKey" in item for item in validate(
            self.list_source, self.footer_source, self.css_source, self.visual_source, altered,
        )))


if __name__ == "__main__":
    unittest.main()
