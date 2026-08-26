import unittest

from scripts.verify.frontend_overlay_lifecycle_guard import FILES, validate


class OverlayLifecycleGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {key: path.read_text(encoding="utf-8") for key, path in FILES.items()}

    def altered(self, key: str, old: str, new: str = "") -> dict[str, str]:
        values = dict(self.sources)
        values[key] = values[key].replace(old, new, 1)
        return values

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.sources), [])

    def test_dialog_cannot_lose_tdesign_driver(self):
        self.assertTrue(any("TDesignDialog" in error for error in validate(self.altered("dialog", "<TDesignDialog"))))

    def test_dismissible_policy_cannot_be_bypassed(self):
        errors = validate(self.altered("drawer", ':close-on-esc-keydown="false"', ':close-on-esc-keydown="true"'))
        self.assertTrue(any("close-on-esc-keydown" in error for error in errors))

    def test_closed_overlay_cannot_claim_open_semantic_state(self):
        errors = validate(self.altered("dialog", ":data-state=\"open ? 'open' : 'closed'\"", 'data-state="open"'))
        self.assertTrue(any("data-state" in error for error in errors))

    def test_action_view_cannot_restore_private_dialog(self):
        values = self.altered("action_view", "<ScDialog", '<div class="business-category-picker-backdrop" role="dialog"')
        self.assertTrue(any("action_view" in error for error in validate(values)))

    def test_attachment_cannot_restore_private_lifecycle(self):
        values = self.altered("attachment", "<ScDialog", '<div class="attachment-viewer-backdrop">useModalLifecycle')
        self.assertTrue(any("attachment" in error for error in validate(values)))

    def test_messages_cannot_restore_private_backdrop(self):
        values = self.altered("messages", "<ScDrawer", '<aside v-if="open" class="global-message__backdrop"')
        self.assertTrue(any("messages" in error for error in validate(values)))

    def test_nested_scroll_lock_authority_is_required(self):
        values = dict(self.sources)
        values["lifecycle"] = values["lifecycle"].replace("bodyLockDepth", "legacyLock")
        self.assertTrue(any("bodyLockDepth" in error for error in validate(values)))


if __name__ == "__main__":
    unittest.main()
