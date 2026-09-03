import unittest

from scripts.verify.frontend_collection_navigation_controls_guard import COLUMN_COMPONENT, COMPONENT, GROUPING_COMPONENT, GROUP_PAGE_COMPONENT, LIST_PAGE, validate


class CollectionNavigationControlsGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.component = COMPONENT.read_text(encoding="utf-8")
        cls.list_page = LIST_PAGE.read_text(encoding="utf-8")
        cls.grouping = GROUPING_COMPONENT.read_text(encoding="utf-8")
        cls.column = COLUMN_COMPONENT.read_text(encoding="utf-8")
        cls.group_page = GROUP_PAGE_COMPONENT.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.component, self.list_page, self.grouping, self.column, self.group_page), [])

    def test_missing_semantic_identity_fails(self):
        altered = self.component.replace('data-semantic-component="CollectionPaginationFooter"', '')
        self.assertTrue(any("semantic-component" in item for item in validate(altered, self.list_page)))

    def test_parallel_pagination_dom_fails(self):
        altered = self.list_page + '\n<section v-else-if="showPagination" class="pagination-footer">legacy</section>\n'
        self.assertIn("list page retains parallel paged pagination DOM", validate(self.component, altered))

    def test_duplicate_pagination_total_authority_fails(self):
        altered = self.component.replace(':total-content="false"', '')
        self.assertTrue(any("total-content" in item for item in validate(altered, self.list_page)))

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

    def test_nested_column_header_semantics_fail(self):
        altered = self.column.replace('<div', '<div role="columnheader" aria-sort="ascending"', 1)
        self.assertIn(
            "collection column header must not duplicate the native th semantics",
            validate(self.component, self.list_page, self.grouping, altered),
        )

    def test_missing_native_th_sort_projection_fails(self):
        altered = self.list_page.replace("{ 'aria-sort': columnAriaSort(field) }", '{}')
        self.assertTrue(
            any(
                "project sort semantics to the native th" in item
                for item in validate(self.component, altered, self.grouping, self.column)
            )
        )

    def test_parallel_group_page_controls_fail(self):
        altered = self.list_page + '\n<button class="group-page-btn">legacy</button>\n'
        self.assertIn(
            "list page retains parallel group page controls DOM",
            validate(self.component, altered, self.grouping, self.column, self.group_page),
        )

    def test_missing_group_page_semantic_identity_fails(self):
        altered = self.group_page.replace('data-semantic-component="CollectionGroupPageControls"', '')
        self.assertTrue(
            any(
                "collection group page controls missing" in item
                for item in validate(self.component, self.list_page, self.grouping, self.column, altered)
            )
        )


if __name__ == "__main__":
    unittest.main()
