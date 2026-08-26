import unittest

from scripts.verify.frontend_native_form_action_presentation_guard import OVERFLOW_MENU, RENDERER, SMART_ACTION, validate


class NativeFormActionPresentationGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RENDERER.read_text(encoding="utf-8")
        cls.smart_action = SMART_ACTION.read_text(encoding="utf-8")
        cls.overflow_menu = OVERFLOW_MENU.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.source, self.smart_action, self.overflow_menu), [])

    def test_ordinary_action_cannot_regress_to_private_button(self):
        altered = self.source.replace("<ScButton\n                v-if=\"!isSmartButtonNode(buttonNode)\"", "<button\n                v-if=\"!isSmartButtonNode(buttonNode)\"", 1)
        self.assertTrue(any("ordinary action" in error or "expected two" in error for error in validate(altered, self.smart_action, self.overflow_menu)))

    def test_private_hover_presentation_is_rejected(self):
        altered = f"{self.source}\n.native-action-btn:hover {{ background: red; }}"
        self.assertIn("native ordinary actions must not override ScButton appearance or states", validate(altered, self.smart_action, self.overflow_menu))

    def test_action_event_authority_is_preserved(self):
        altered = self.source.replace('@click.stop.prevent="emitNativeAction(node)"', '@click="legacyAction(node)"', 1)
        self.assertTrue(any("emitNativeAction(node)" in error for error in validate(altered, self.smart_action, self.overflow_menu)))

    def test_stateful_controls_are_not_mechanically_replaced(self):
        altered = self.source.replace('class="native-tab"', 'class="generic-command"', 1)
        self.assertTrue(any("stateful" in error for error in validate(altered, self.smart_action, self.overflow_menu)))

    def test_smart_action_cannot_return_to_renderer_private_css(self):
        altered = f"{self.source}\n.native-action-btn--smart {{ color: red; }}"
        self.assertIn("native renderer must not retain parallel smart-action appearance", validate(altered, self.smart_action, self.overflow_menu))

    def test_smart_action_semantic_identity_is_required(self):
        altered = self.smart_action.replace('data-semantic-role="smart-action"', 'data-role="button"')
        self.assertTrue(any("smart action" in error for error in validate(self.source, altered, self.overflow_menu)))

    def test_overflow_requires_escape_settlement(self):
        altered = self.overflow_menu.replace('@keydown.esc.stop.prevent="close(true)"', '')
        self.assertTrue(any("overflow" in error for error in validate(self.source, self.smart_action, altered)))

    def test_overflow_state_cannot_return_to_renderer(self):
        altered = f"{self.source}\nconst openMoreKeys = ref({{}});"
        self.assertTrue(any("private overflow" in error for error in validate(altered, self.smart_action, self.overflow_menu)))


if __name__ == "__main__":
    unittest.main()
