import unittest

from scripts.verify.frontend_collection_action_toolbar_guard import TOOLBAR, validate


class CollectionActionToolbarGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TOOLBAR.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.source), [])

    def test_missing_escape_listener_fails(self):
        altered = self.source.replace(
            "document.addEventListener('keydown', handleDocumentKeyDown)",
            "document.addEventListener('keyup', handleDocumentKeyDown)",
        )
        self.assertTrue(any("keydown" in item for item in validate(altered)))

    def test_aria_menu_without_keyboard_model_fails(self):
        altered = self.source.replace(
            'data-collection-toolbar-layer="overflow"',
            'data-collection-toolbar-layer="overflow" role="menu"',
        )
        self.assertIn(
            "collection toolbar disclosure must preserve native button semantics",
            validate(altered),
        )


if __name__ == "__main__":
    unittest.main()
