import unittest

from scripts.verify.frontend_native_form_action_presentation_guard import RENDERER, validate


class NativeFormActionPresentationGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RENDERER.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.source), [])

    def test_ordinary_action_cannot_regress_to_private_button(self):
        altered = self.source.replace("<ScButton\n                v-if=\"!isSmartButtonNode(buttonNode)\"", "<button\n                v-if=\"!isSmartButtonNode(buttonNode)\"", 1)
        self.assertTrue(any("ordinary action" in error or "expected two" in error for error in validate(altered)))

    def test_private_hover_presentation_is_rejected(self):
        altered = f"{self.source}\n.native-action-btn:hover {{ background: red; }}"
        self.assertIn("native ordinary actions must not override ScButton appearance or states", validate(altered))

    def test_action_event_authority_is_preserved(self):
        altered = self.source.replace('@click.stop.prevent="emitNativeAction(node)"', '@click="legacyAction(node)"', 1)
        self.assertTrue(any("emitNativeAction(node)" in error for error in validate(altered)))

    def test_stateful_controls_are_not_mechanically_replaced(self):
        altered = self.source.replace('class="native-tab"', 'class="generic-command"', 1)
        self.assertTrue(any("stateful" in error for error in validate(altered)))


if __name__ == "__main__":
    unittest.main()
