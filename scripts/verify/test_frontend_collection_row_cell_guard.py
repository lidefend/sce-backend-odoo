import unittest

from scripts.verify.frontend_collection_row_cell_guard import LIST_PAGE, ROW_CELL, ROW_CELL_CSS, validate


class CollectionRowCellGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.list_source = LIST_PAGE.read_text(encoding="utf-8")
        cls.cell_source = ROW_CELL.read_text(encoding="utf-8")
        cls.css_source = ROW_CELL_CSS.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.list_source, self.cell_source, self.css_source), [])

    def test_parallel_cell_dom_fails(self):
        altered = self.list_source + '\n<button class="favorite-toggle">legacy</button>\n'
        self.assertTrue(any("parallel row-cell DOM" in item for item in validate(altered, self.cell_source, self.css_source)))

    def test_missing_group_adapter_fails(self):
        altered = self.list_source.replace(':columns="collectionTableColumns(group.key)"', ':columns="legacyGroupColumns"')
        self.assertTrue(any("TDesign column" in item for item in validate(altered, self.cell_source, self.css_source)))

    def test_missing_event_contract_fails(self):
        altered = self.list_source.replace("onOpenRecord: () => handleRow(row)", "onOpenRecord: noop", 1)
        self.assertTrue(any("shared event contract" in item for item in validate(altered, self.cell_source, self.css_source)))

    def test_missing_semantic_identity_fails(self):
        altered = self.cell_source.replace('data-semantic-component="CollectionRowCell"', '')
        self.assertTrue(any("semantic-component" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_relation_tag_semantics_fails(self):
        altered = self.cell_source.replace('data-semantic-cell-kind="relation-tags"', '')
        self.assertTrue(any("relation-tags" in item for item in validate(self.list_source, altered, self.css_source)))

    def test_missing_style_owner_fails(self):
        altered = self.css_source.replace(".status-badge", ".legacy-status-badge")
        self.assertTrue(any("style ownership" in item for item in validate(self.list_source, self.cell_source, altered)))

    def test_missing_primary_truncation_fails(self):
        altered = self.css_source.replace("text-overflow: ellipsis", "text-overflow: clip")
        self.assertTrue(any("truncation contract" in item for item in validate(self.list_source, self.cell_source, altered)))


if __name__ == "__main__":
    unittest.main()
