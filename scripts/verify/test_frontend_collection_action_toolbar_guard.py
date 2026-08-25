import unittest

from scripts.verify.frontend_collection_action_toolbar_guard import BATCH_BAR, LIST_PAGE, OVERFLOW_CONTROLLER, TOOLBAR, validate


class CollectionActionToolbarGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TOOLBAR.read_text(encoding="utf-8")
        cls.list_source = LIST_PAGE.read_text(encoding="utf-8")
        cls.overflow_source = OVERFLOW_CONTROLLER.read_text(encoding="utf-8")
        cls.batch_source = BATCH_BAR.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.source, self.list_source, self.overflow_source, self.batch_source), [])

    def test_missing_escape_listener_fails(self):
        altered = self.source.replace(
            "document.addEventListener('keydown', handleDocumentKeyDown)",
            "document.addEventListener('keyup', handleDocumentKeyDown)",
        )
        self.assertTrue(any("keydown" in item for item in validate(altered, self.list_source)))

    def test_missing_batch_escape_listener_fails(self):
        altered = self.overflow_source.replace(
            "document.addEventListener('keydown', closeOnEscape)",
            "document.addEventListener('keyup', closeOnEscape)",
        )
        self.assertTrue(any("overflow controller" in item for item in validate(self.source, self.list_source, altered)))

    def test_missing_primitive_focus_resolution_fails(self):
        altered = self.overflow_source.replace("root?.matches('button')", "false")
        self.assertTrue(any("overflow controller" in item for item in validate(self.source, self.list_source, altered)))

    def test_aria_menu_without_keyboard_model_fails(self):
        altered = self.source.replace(
            'data-collection-toolbar-layer="overflow"',
            'data-collection-toolbar-layer="overflow" role="menu"',
        )
        self.assertIn(
            "collection toolbar disclosure must preserve native button semantics",
            validate(altered, self.list_source, self.overflow_source, self.batch_source),
        )

    def test_parallel_direct_and_overflow_projection_fails(self):
        altered = self.batch_source.replace(
            'v-for="action in actionLayout.direct"',
            'v-for="(action, actionIndex) in actions"',
        )
        self.assertIn(
            "collection batch actions must not duplicate overflow actions in the direct row",
            validate(self.source, self.list_source, self.overflow_source, altered),
        )

    def test_parallel_batch_bar_dom_fails(self):
        altered = self.list_source + '\n<section data-semantic-component="CollectionBatchActionBar">legacy</section>\n'
        self.assertIn(
            "list page retains parallel batch action bar DOM",
            validate(self.source, altered, self.overflow_source, self.batch_source),
        )


if __name__ == "__main__":
    unittest.main()
