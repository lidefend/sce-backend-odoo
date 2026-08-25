import unittest

from scripts.verify.frontend_collection_mobile_record_row_guard import (
    LIST_CSS,
    LIST_PAGE,
    MOBILE_CSS,
    ROW,
    ROW_CSS,
    VISUAL_SMOKE,
    validate,
)


class CollectionMobileRecordRowGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.list_source = LIST_PAGE.read_text(encoding="utf-8")
        cls.row_source = ROW.read_text(encoding="utf-8")
        cls.row_css = ROW_CSS.read_text(encoding="utf-8")
        cls.legacy_css = LIST_CSS.read_text(encoding="utf-8") + MOBILE_CSS.read_text(encoding="utf-8")
        cls.visual_source = VISUAL_SMOKE.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(), [])

    def test_duplicate_adapter_fails(self):
        altered = self.list_source + "\n<CollectionMobileRecordRow />\n"
        self.assertTrue(any("exactly one" in item for item in validate(altered, self.row_source, self.row_css, self.legacy_css)))

    def test_inline_card_fails(self):
        altered = self.list_source + "\n<ScMobileRecordCard />\n"
        self.assertTrue(any("inline" in item for item in validate(altered, self.row_source, self.row_css, self.legacy_css)))

    def test_missing_semantic_owner_fails(self):
        altered = self.row_source.replace('data-semantic-component="CollectionMobileRecordRow"', "")
        self.assertTrue(any("semantic-component" in item for item in validate(self.list_source, altered, self.row_css, self.legacy_css)))

    def test_missing_selection_passthrough_fails(self):
        altered = self.list_source.replace('@selection-change="onRowCheckboxChange(row, $event)"', "")
        self.assertTrue(any("selection-change" in item for item in validate(altered, self.row_source, self.row_css, self.legacy_css)))

    def test_missing_open_passthrough_fails(self):
        altered = self.list_source.replace('@open="handleRow(row)"', "")
        self.assertTrue(any("handleRow" in item for item in validate(altered, self.row_source, self.row_css, self.legacy_css)))

    def test_missing_touch_target_fails(self):
        altered = self.row_css.replace("var(--sc-touch-target-min)", "40px")
        self.assertTrue(any("touch-target" in item for item in validate(self.list_source, self.row_source, altered, self.legacy_css)))

    def test_legacy_style_fails(self):
        altered = self.legacy_css + "\n.mobile-record-card__head {}\n"
        self.assertTrue(any("legacy" in item for item in validate(self.list_source, self.row_source, self.row_css, altered)))

    def test_missing_browser_identity_evidence_fails(self):
        altered = self.visual_source.replace("row.openAriaLabel.includes(row.identity)", "Boolean(row.openAriaLabel)")
        self.assertTrue(any("openAriaLabel" in item for item in validate(
            self.list_source, self.row_source, self.row_css, self.legacy_css, altered,
        )))


if __name__ == "__main__":
    unittest.main()
