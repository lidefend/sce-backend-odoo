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
        self.assertTrue(any("focus-visible" in error for error in validate(self.altered("activity", ".activity-card:focus-visible"))))

    def test_activity_deterministic_state_is_required(self):
        self.assertTrue(any("data-state" in error for error in validate(self.altered("activity", ':data-state="loading ?'))))

    def test_status_actions_cannot_regress_to_native_buttons(self):
        sources = self.altered("status", "<ScButton", "<button")
        self.assertTrue(any("governed buttons" in error or "private action" in error for error in validate(sources)))

    def test_status_reduced_motion_is_required(self):
        self.assertTrue(any("reduced-motion" in error for error in validate(self.altered("status", "prefers-reduced-motion"))))

    def test_status_deterministic_state_is_required(self):
        self.assertTrue(any("semantic-state-surface" in error for error in validate(self.altered("status", 'data-semantic-state-surface="page"'))))

    def test_activity_tabs_require_roving_tabindex(self):
        self.assertTrue(any("tabindex" in error for error in validate(self.altered("tabs", ":tabindex="))))

    def test_activity_tabs_require_keyboard_navigation(self):
        self.assertTrue(any("activateFromKeyboard" in error for error in validate(self.altered("tabs", '@keydown="activateFromKeyboard'))))

    def test_activity_tabs_require_delete_shortcut(self):
        self.assertTrue(any("Delete" in error for error in validate(self.altered("tabs", 'aria-keyshortcuts="Delete"'))))

    def test_activity_tablist_rejects_nested_close_button(self):
        sources = self.altered("tabs", '<span\n          class="activity-tab-close"', '<button class="activity-tab-close"')
        self.assertTrue(any("non-tab close button" in error for error in validate(sources)))


if __name__ == "__main__":
    unittest.main()
