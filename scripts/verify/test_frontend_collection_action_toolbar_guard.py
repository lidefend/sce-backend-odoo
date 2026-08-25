import unittest

from scripts.verify.frontend_collection_action_toolbar_guard import LIST_PAGE, TOOLBAR, validate


class CollectionActionToolbarGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TOOLBAR.read_text(encoding="utf-8")
        cls.list_source = LIST_PAGE.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.source, self.list_source), [])

    def test_missing_escape_listener_fails(self):
        altered = self.source.replace(
            "document.addEventListener('keydown', handleDocumentKeyDown)",
            "document.addEventListener('keyup', handleDocumentKeyDown)",
        )
        self.assertTrue(any("keydown" in item for item in validate(altered, self.list_source)))

    def test_aria_menu_without_keyboard_model_fails(self):
        altered = self.source.replace(
            'data-collection-toolbar-layer="overflow"',
            'data-collection-toolbar-layer="overflow" role="menu"',
        )
        self.assertIn(
            "collection toolbar disclosure must preserve native button semantics",
            validate(altered, self.list_source),
        )

    def test_parallel_direct_and_overflow_projection_fails(self):
        altered = self.list_source.replace(
            'v-for="action in selectionDirectActions"',
            'v-for="(action, actionIndex) in selectionActions"',
        )
        self.assertIn(
            "collection batch actions must not duplicate overflow actions in the direct row",
            validate(self.source, altered),
        )


if __name__ == "__main__":
    unittest.main()
