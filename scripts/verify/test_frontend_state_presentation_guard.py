import unittest

from scripts.verify.frontend_state_presentation_guard import FILES, validate


class FrontendStatePresentationGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {key: path.read_text(encoding="utf-8") for key, path in FILES.items()}

    def altered(self, key: str, old: str, new: str = "") -> dict[str, str]:
        sources = dict(self.sources)
        sources[key] = sources[key].replace(old, new, 1)
        return sources

    def test_repository_surfaces_pass(self):
        self.assertEqual(validate(self.sources), [])

    def test_activity_loading_primitive_is_required(self):
        self.assertTrue(any("ScLoading" in error for error in validate(self.altered("activity", "<ScLoading"))))

    def test_activity_error_primitive_is_required(self):
        self.assertTrue(any("ScErrorState" in error for error in validate(self.altered("activity", "<ScErrorState"))))

    def test_activity_focus_state_is_required(self):
        self.assertTrue(any("surface-tile" in error for error in validate(self.altered("activity", 'appearance="surface-tile"'))))

    def test_activity_adapter_focus_authority_is_required(self):
        self.assertTrue(any("focus authority" in error for error in validate(self.altered("theme", ".sc-btn:focus-visible"))))

    def test_activity_deterministic_state_is_required(self):
        self.assertTrue(any("data-state" in error for error in validate(self.altered("activity", ':data-state="loading ?'))))

    def test_status_actions_cannot_regress_to_native_buttons(self):
        sources = self.altered("status", "<ScButton", "<button")
        self.assertTrue(any("governed buttons" in error or "private action" in error for error in validate(sources)))

    def test_status_reduced_motion_is_required(self):
        self.assertTrue(any("reduced-motion" in error for error in validate(self.altered("status", "prefers-reduced-motion"))))

    def test_status_deterministic_state_is_required(self):
        self.assertTrue(any("semantic-state-surface" in error for error in validate(self.altered("status", 'data-semantic-state-surface="page"'))))

    def test_activity_tabs_require_tdesign_component(self):
        self.assertTrue(any("TDesignTabs" in error for error in validate(self.altered("tabs", "<TDesignTabs"))))

    def test_activity_tabs_require_tab_panel(self):
        self.assertTrue(any("TDesignTabPanel" in error for error in validate(self.altered("tabs", "<TDesignTabPanel"))))

    def test_activity_tabs_require_primitive_bridge(self):
        self.assertTrue(any("tdesignPrimitiveBridge" in error for error in validate(self.altered("tabs", "tdesignPrimitiveBridge"))))

    def test_activity_tabs_require_change_handler(self):
        self.assertTrue(any("handleChange" in error for error in validate(self.altered("tabs", '@change="handleChange"'))))

    def test_activity_tablist_rejects_nested_close_button(self):
        sources = self.altered("tabs", '</TDesignTabs>', '<button class="activity-tab-close">x</button></TDesignTabs>')
        self.assertTrue(any("non-tab close button" in error for error in validate(sources)))

    def test_activity_draft_dirty_state_must_publish_synchronously(self):
        sources = self.altered("contract_form", "flush: 'sync'", "flush: 'post'")
        self.assertTrue(any("published synchronously" in error for error in validate(sources)))


if __name__ == "__main__":
    unittest.main()
