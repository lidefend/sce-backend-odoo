import unittest

from scripts.verify.frontend_collection_summary_strip_guard import LIST_PAGE, SUMMARY, SUMMARY_CSS, validate


class CollectionSummaryStripGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.list_source = LIST_PAGE.read_text(encoding="utf-8")
        cls.summary_source = SUMMARY.read_text(encoding="utf-8")
        cls.css_source = SUMMARY_CSS.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.list_source, self.summary_source, self.css_source), [])

    def test_inline_legacy_card_fails(self):
        altered = self.list_source + '\n<article class="summary-card">legacy</article>\n'
        self.assertTrue(any("legacy" in item for item in validate(altered, self.summary_source, self.css_source)))

    def test_duplicate_adapter_fails(self):
        altered = self.list_source + '\n<CollectionSummaryStrip />\n'
        self.assertTrue(any("exactly one" in item for item in validate(altered, self.summary_source, self.css_source)))

    def test_missing_semantic_owner_fails(self):
        altered = self.summary_source.replace('data-semantic-component="CollectionSummaryStrip"', '')
        self.assertTrue(any("semantic-component" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_accessible_label_fails(self):
        altered = self.summary_source.replace(':aria-label="ariaLabel"', '')
        self.assertTrue(any("aria-label" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_tone_authority_fails(self):
        altered = self.summary_source.replace("resolveCollectionSummaryTone", "legacyTone")
        self.assertTrue(any("resolveCollectionSummaryTone" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_mobile_single_column_fails(self):
        altered = self.css_source.replace("max-width: 420px", "max-width: 320px")
        self.assertTrue(any("420px" in item for item in validate(self.list_source, self.summary_source, altered)))


if __name__ == "__main__":
    unittest.main()
