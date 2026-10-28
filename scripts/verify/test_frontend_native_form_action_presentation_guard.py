import unittest
import re

from scripts.verify.frontend_native_form_action_presentation_guard import OVERFLOW_MENU, RENDERER, SMART_ACTION, VISUAL_SMOKE, validate


class NativeFormActionPresentationGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RENDERER.read_text(encoding="utf-8")
        cls.smart_action = SMART_ACTION.read_text(encoding="utf-8")
        cls.overflow_menu = OVERFLOW_MENU.read_text(encoding="utf-8")
        cls.visual_smoke = VISUAL_SMOKE.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.source, self.smart_action, self.overflow_menu, self.visual_smoke), [])

    def test_declared_anchor_keeps_navigation_only_authority(self):
        anchor = next(button for button in re.findall(r"<ScButton\b[\s\S]*?</ScButton>", self.source)
                      if "node.nodeComponent?.kind === 'anchor'" in button)
        mutations = {
            "missing": "",
            "duplicate": anchor + anchor,
            "business_action": anchor.replace('navigateExplicit(node, $event)', 'emitNativeAction(node)'),
            "extra_event": anchor.replace('type="button"', 'type="button" @dblclick="writeRecord"'),
            "dynamic_event": anchor.replace('type="button"', 'type="button" @[eventName]="writeRecord"'),
            "spread": anchor.replace('type="button"', 'type="button" v-bind="untrusted"'),
            "inline_handler": anchor.replace('type="button"', 'type="button" onclick="writeRecord()"'),
            "submit": anchor.replace('type="button"', 'type="submit"'),
            "wrong_identity": anchor.replace('node.containerId', 'other.containerId'),
            "unconditional": anchor.replace('v-else-if="node.nodeComponent?.kind === \'anchor\'"', ''),
            "duplicate_click": anchor.replace('type="button"', 'type="button" @click="writeRecord"'),
        }
        for name, replacement in mutations.items():
            with self.subTest(mutation=name):
                self.assertTrue(any('anchor' in error for error in validate(
                    self.source.replace(anchor, replacement, 1), self.smart_action,
                    self.overflow_menu, self.visual_smoke,
                )))

    def test_unclassified_button_is_rejected(self):
        source = self.source.replace('<template>', '<template><ScButton @click="writeRecord">Write</ScButton>', 1)
        self.assertTrue(any('unclassified' in error for error in validate(
            source, self.smart_action, self.overflow_menu, self.visual_smoke,
        )))

    def test_container_disclosure_cannot_bypass_action_authority(self):
        button = next(button for button in re.findall(r"<ScButton\b[\s\S]*?</ScButton>", self.source)
                      if 'v-else-if="isCollapsibleContainer(node)"' in button)
        cases = (
            (button, "", "container disclosure"),
            (button, button + button, "container disclosure"),
            (button, button.replace('type="button"', 'type="button" :onDblclick="writeRecord"'), "only toggle"),
            (button, button.replace('type="button"', 'type="button" :[eventName]="writeRecord"'), "only toggle"),
            ('@click="toggleContainerCollapsed(node, index)"', '@click="emitNativeAction(node)"', "only toggle"),
            (':aria-expanded="String(!isContainerCollapsed(node, index))"', ':aria-expanded="true"', "only toggle"),
            (':disabled="nativeActionDisabled(node)"', ':disabled="false"', "disabled and event authority"),
        )
        for before, after, reason in cases:
            with self.subTest(binding=before):
                self.assertIn(before, self.source)
                altered = self.source.replace(before, after, 1)
                self.assertTrue(any(reason in error for error in validate(altered, self.smart_action, self.overflow_menu)))

    def test_ordinary_action_cannot_regress_to_private_button(self):
        altered = self.source.replace("<ScButton\n                v-if=\"!isSmartButtonNode(buttonNode)\"", "<button\n                v-if=\"!isSmartButtonNode(buttonNode)\"", 1)
        self.assertTrue(any("ordinary action" in error or "expected two" in error for error in validate(altered, self.smart_action, self.overflow_menu)))

    def test_private_hover_presentation_is_rejected(self):
        altered = f"{self.source}\n.native-action-btn:hover {{ background: red; }}"
        self.assertIn("native ordinary actions must not override ScButton appearance or states", validate(altered, self.smart_action, self.overflow_menu))

    def test_action_event_authority_is_preserved(self):
        altered = self.source.replace('@click.stop.prevent="emitNativeAction(node)"', '@click="legacyAction(node)"', 1)
        self.assertTrue(any("emitNativeAction(node)" in error for error in validate(altered, self.smart_action, self.overflow_menu)))

    def test_notebook_tab_semantic_identity_is_preserved(self):
        altered = self.source.replace("labelClass: `native-tab${", "labelClass: `generic-command${", 1)
        self.assertTrue(any("notebook tabs" in error for error in validate(altered, self.smart_action, self.overflow_menu)))

    def test_title_favorite_cannot_regress_to_private_button(self):
        altered = self.source.replace('<ScIconButton\n              v-if="titleFieldForNode(node)?.favoriteToggle"', '<button\n              v-if="titleFieldForNode(node)?.favoriteToggle"', 1)
        self.assertTrue(any("title favorite" in error for error in validate(altered, self.smart_action, self.overflow_menu)))

    def test_smart_action_cannot_return_to_renderer_private_css(self):
        altered = f"{self.source}\n.native-action-btn--smart {{ color: red; }}"
        self.assertIn("native renderer must not retain parallel smart-action appearance", validate(altered, self.smart_action, self.overflow_menu))

    def test_smart_action_semantic_identity_is_required(self):
        altered = self.smart_action.replace('data-semantic-role="smart-action"', 'data-role="button"')
        self.assertTrue(any("smart action" in error for error in validate(self.source, altered, self.overflow_menu)))

    def test_group_cannot_limit_or_fold_declared_actions(self):
        for marker in ("const SMART_BUTTON_DIRECT_LIMIT = 4;", "<NativeActionOverflowMenu />", "function overflowActionButtons() {}"):
            with self.subTest(marker=marker):
                self.assertTrue(any("undeclared folding" in error for error in validate(self.source + marker)))

    def test_group_must_consume_complete_children(self):
        altered = self.source.replace('buttonChildren(node).filter((button)', 'buttonChildren(node).slice(0, 4).filter((button)')
        self.assertTrue(any("complete ordered" in error for error in validate(altered)))

    def test_group_must_not_clip_long_actions(self):
        altered = self.source.replace('.native-actions--smart {', '.native-actions--smart { overflow: hidden;')
        self.assertTrue(any("must not clip" in error for error in validate(altered)))

    def test_smoke_requires_declared_set_comparison(self):
        altered = self.visual_smoke.replace("expectedNativeActionKeys", "oldKeys")
        self.assertTrue(any("visual smoke" in error for error in validate(self.source, visual_smoke=altered)))


if __name__ == "__main__":
    unittest.main()
