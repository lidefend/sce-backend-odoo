import unittest
from scripts.verify.frontend_collection_kanban_record_card_guard import PAGE, CARD, STYLE, LANE, VISUAL, validate

class CollectionKanbanRecordCardGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = PAGE.read_text(encoding="utf-8")
        cls.card = CARD.read_text(encoding="utf-8")
        cls.style = STYLE.read_text(encoding="utf-8")
        cls.lane = LANE.read_text(encoding="utf-8")
        cls.visual = VISUAL.read_text(encoding="utf-8")

    def test_repository_contract_passes(self): self.assertEqual(validate(), [])
    def test_duplicate_adapter_fails(self): self.assertTrue(any("exactly one" in item for item in validate(self.page + "\n<CollectionKanbanRecordCard />", self.card, self.style)))
    def test_inline_card_fails(self): self.assertTrue(any("inline" in item for item in validate(self.page + '\n<article class="card" />', self.card, self.style)))
    def test_missing_semantic_owner_fails(self): self.assertTrue(validate(self.page, self.card.replace('data-semantic-component="CollectionKanbanRecordCard"', ''), self.style))
    def test_missing_keyboard_open_fails(self): self.assertTrue(validate(self.page, self.card.replace('@keydown.enter="emit(\'open\')"', ''), self.style))
    def test_missing_focus_style_fails(self): self.assertTrue(validate(self.page, self.card, self.style.replace('var(--sc-semantic-focus-ring)', 'none')))
    def test_missing_lane_semantic_owner_fails(self): self.assertTrue(validate(self.page, self.card, self.style, self.lane.replace('data-semantic-component="CollectionKanbanLane"', '')))
    def test_missing_browser_semantic_evidence_fails(self): self.assertTrue(validate(self.page, self.card, self.style, self.lane, self.visual.replace('paginationOwnerCount === 1', 'paginationOwnerCount > 0')))

if __name__ == "__main__": unittest.main()
