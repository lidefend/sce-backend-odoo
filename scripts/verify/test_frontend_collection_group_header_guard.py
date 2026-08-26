import unittest

from scripts.verify.frontend_collection_group_header_guard import HEADER, HEADER_CSS, LIST_PAGE, THEME, VISUAL_SMOKE, validate


class CollectionGroupHeaderGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.list_source = LIST_PAGE.read_text(encoding="utf-8")
        cls.header_source = HEADER.read_text(encoding="utf-8")
        cls.css_source = HEADER_CSS.read_text(encoding="utf-8")
        cls.visual_source = VISUAL_SMOKE.read_text(encoding="utf-8")
        cls.theme_source = THEME.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.list_source, self.header_source, self.css_source), [])

    def test_legacy_toggle_fails(self):
        altered = self.list_source + '\n<button class="group-toggle">legacy</button>\n'
        self.assertTrue(any("legacy" in item for item in validate(altered, self.header_source, self.css_source)))

    def test_missing_expanded_state_fails(self):
        altered = self.header_source.replace(':aria-expanded="!collapsed"', '')
        self.assertTrue(any("aria-expanded" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_open_authority_fails(self):
        altered = self.list_source.replace(':open-enabled="Boolean(onOpenGroup)"', ':open-enabled="true"')
        self.assertTrue(any("open-enabled" in item for item in validate(altered, self.header_source, self.css_source)))

    def test_missing_pagination_slot_fails(self):
        altered = self.header_source.replace('<slot name="pagination" />', '')
        self.assertTrue(any("pagination" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_touch_target_fails(self):
        altered = self.css_source.replace("var(--sc-touch-target-min)", "32px")
        self.assertTrue(any("touch-target" in item for item in validate(self.list_source, self.header_source, altered)))

    def test_missing_reduced_motion_fails(self):
        altered = self.css_source.replace("prefers-reduced-motion", "legacy-motion")
        self.assertTrue(any("reduced-motion" in item for item in validate(self.list_source, self.header_source, altered)))

    def test_missing_adapter_focus_authority_fails(self):
        altered = self.theme_source.replace(".sc-btn:focus-visible", ".legacy-btn:focus-visible")
        self.assertTrue(any("adapter theme" in item for item in validate(
            self.list_source, self.header_source, self.css_source, self.visual_source, altered,
        )))

    def test_missing_browser_state_evidence_fails(self):
        altered = self.visual_source.replace("toggledExpanded", "legacyExpanded")
        self.assertTrue(any("toggledExpanded" in item for item in validate(
            self.list_source, self.header_source, self.css_source, altered,
        )))


if __name__ == "__main__":
    unittest.main()
