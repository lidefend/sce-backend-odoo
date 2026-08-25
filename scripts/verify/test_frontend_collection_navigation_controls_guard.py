import unittest

from scripts.verify.frontend_collection_navigation_controls_guard import COLUMN_COMPONENT, COMPONENT, GROUPING_COMPONENT, LIST_PAGE, validate


class CollectionNavigationControlsGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.component = COMPONENT.read_text(encoding="utf-8")
        cls.list_page = LIST_PAGE.read_text(encoding="utf-8")
        cls.grouping = GROUPING_COMPONENT.read_text(encoding="utf-8")
        cls.column = COLUMN_COMPONENT.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.component, self.list_page, self.grouping, self.column), [])

    def test_missing_semantic_identity_fails(self):
        altered = self.component.replace('data-semantic-component="CollectionPaginationFooter"', '')
        self.assertTrue(any("semantic-component" in item for item in validate(altered, self.list_page)))

    def test_parallel_pagination_dom_fails(self):
        altered = self.list_page + '\n<section v-else-if="showPagination" class="pagination-footer">legacy</section>\n'
        self.assertIn("list page retains parallel paged pagination DOM", validate(self.component, altered))

    def test_parallel_grouping_toolbar_fails(self):
        altered = self.list_page + '\n<header class="grouped-toolbar">legacy</header>\n'
        self.assertIn("list page retains parallel grouping toolbar DOM", validate(self.component, altered, self.grouping))

    def test_parallel_column_header_dom_fails(self):
        altered = self.list_page + '\n<th\n              v-for="col in displayedColumns">legacy</th>\n'
        self.assertIn(
            "list page retains parallel column header DOM",
            validate(self.component, altered, self.grouping, self.column),
        )

    def test_missing_column_header_semantic_identity_fails(self):
        altered = self.column.replace('data-semantic-component="CollectionColumnHeaderControl"', '')
        self.assertTrue(
            any(
                "collection column header missing" in item
                for item in validate(self.component, self.list_page, self.grouping, altered)
            )
        )


if __name__ == "__main__":
    unittest.main()
