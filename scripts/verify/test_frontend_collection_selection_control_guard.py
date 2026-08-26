import unittest

from scripts.verify.frontend_collection_selection_control_guard import CONTROL, CONTROL_CSS, LIST_PAGE, MOBILE_ROW, VISUAL_SMOKE, validate


class CollectionSelectionControlGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.list_source = LIST_PAGE.read_text(encoding="utf-8")
        cls.control_source = CONTROL.read_text(encoding="utf-8")
        cls.css_source = CONTROL_CSS.read_text(encoding="utf-8")
        cls.visual_source = VISUAL_SMOKE.read_text(encoding="utf-8")
        cls.mobile_row_source = MOBILE_ROW.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.list_source, self.control_source, self.css_source, self.visual_source, self.mobile_row_source), [])

    def test_parallel_native_checkbox_fails(self):
        altered = self.list_source + '\n<input type="checkbox" />\n'
        self.assertIn("ListPage retains parallel native checkbox DOM", validate(altered, self.control_source, self.css_source))

    def test_missing_desktop_adapter_fails(self):
        altered = self.list_source.replace(':columns="collectionTableColumns(group.key)"', ':columns="legacyColumns"', 1)
        self.assertTrue(any("exactly two" in item for item in validate(altered, self.control_source, self.css_source)))

    def test_missing_professional_header_selection_fails(self):
        altered = self.list_source.replace('title: () => h(CollectionSelectionControl', 'title: () => h(ScCheckbox', 1)
        self.assertTrue(any("header and one row" in item or "title:" in item for item in validate(altered, self.control_source, self.css_source)))

    def test_missing_page_selection_authority_fails(self):
        altered = self.list_source.replace('props.onToggleSelectionAll?.(selectionIds, checked)', 'noop()', 1)
        self.assertTrue(any("onToggleSelectionAll" in item for item in validate(altered, self.control_source, self.css_source)))

    def test_missing_row_selection_authority_fails(self):
        altered = self.list_source.replace('onRowCheckboxChange(row, checked)', 'noop()', 1)
        self.assertTrue(any("onRowCheckboxChange" in item for item in validate(altered, self.control_source, self.css_source)))

    def test_missing_mobile_touch_adapter_fails(self):
        altered = self.mobile_row_source.replace("<CollectionSelectionControl", "<LegacySelectionControl", 1)
        self.assertTrue(any("mobile row" in item for item in validate(self.list_source, self.control_source, self.css_source, self.visual_source, altered)))

    def test_missing_indeterminate_property_fails(self):
        altered = self.control_source.replace(':indeterminate="indeterminate"', ':indeterminate="false"')
        self.assertTrue(any("indeterminate" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_boolean_event_contract_fails(self):
        altered = self.control_source.replace("@change=\"emit('change', $event)\"", "@change=\"emit('change', false)\"")
        self.assertTrue(any("emit('change'" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_mobile_adapter_cannot_regress_to_raw_checkbox(self):
        altered = self.control_source.replace('<ScCheckbox', '<input type="checkbox"', 1)
        self.assertTrue(any("ScCheckbox" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_browser_mixed_state_fails(self):
        altered = self.visual_source.replace("selectedHeaderState === 'mixed'", "selectedHeaderState === 'checked'")
        self.assertTrue(any("browser evidence" in item for item in validate(self.list_source, self.control_source, self.css_source, altered)))


if __name__ == "__main__":
    unittest.main()
