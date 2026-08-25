import unittest

from scripts.verify.frontend_collection_selection_control_guard import CONTROL, CONTROL_CSS, LIST_PAGE, VISUAL_SMOKE, validate


class CollectionSelectionControlGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.list_source = LIST_PAGE.read_text(encoding="utf-8")
        cls.control_source = CONTROL.read_text(encoding="utf-8")
        cls.css_source = CONTROL_CSS.read_text(encoding="utf-8")
        cls.visual_source = VISUAL_SMOKE.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.list_source, self.control_source, self.css_source, self.visual_source), [])

    def test_parallel_native_checkbox_fails(self):
        altered = self.list_source + '\n<input type="checkbox" />\n'
        self.assertIn("ListPage retains parallel native checkbox DOM", validate(altered, self.control_source, self.css_source))

    def test_missing_adapter_fails(self):
        altered = self.list_source.replace("<CollectionSelectionControl", "<LegacySelectionControl", 1)
        self.assertTrue(any("exactly five" in item for item in validate(altered, self.control_source, self.css_source)))

    def test_missing_indeterminate_property_fails(self):
        altered = self.control_source.replace("inputRef.value.indeterminate = props.indeterminate", "void props.indeterminate")
        self.assertTrue(any("indeterminate" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_boolean_event_contract_fails(self):
        altered = self.control_source.replace("emit('change', Boolean((event.target as HTMLInputElement | null)?.checked))", "emit('change', false)")
        self.assertTrue(any("emit('change'" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_mixed_visual_state_fails(self):
        altered = self.css_source.replace("[data-selection-state='mixed']", "[data-selection-state='partial']")
        self.assertTrue(any("mixed" in item for item in validate(self.list_source, self.control_source, altered)))

    def test_missing_focus_contract_fails(self):
        altered = self.css_source.replace(":focus-within", ":hover")
        self.assertTrue(any("focus-within" in item for item in validate(self.list_source, self.control_source, altered)))

    def test_missing_browser_mixed_state_fails(self):
        altered = self.visual_source.replace("selectedHeaderState === 'mixed'", "selectedHeaderState === 'checked'")
        self.assertTrue(any("browser evidence" in item for item in validate(self.list_source, self.control_source, self.css_source, altered)))


if __name__ == "__main__":
    unittest.main()
