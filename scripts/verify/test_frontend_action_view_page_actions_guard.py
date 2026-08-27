import unittest

from scripts.verify.frontend_action_view_page_actions_guard import ACTION_VIEW, validate


class ActionViewPageActionsGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ACTION_VIEW.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.source), [])

    def test_header_action_cannot_regress_to_legacy_button(self):
        altered = self.source.replace('<ScButton v-for="action in vm.header.actions"', '<button v-for="action in vm.header.actions"')
        self.assertIn("ActionView retains a generic legacy page action", validate(altered))

    def test_empty_primary_must_remain_primary(self):
        altered = self.source.replace('<ScButton variant="primary" size="small" type="button" @click="openFocusAction(vm.empty.primaryAction)"', '<ScButton variant="ghost" size="small" type="button" @click="openFocusAction(vm.empty.primaryAction)"')
        self.assertTrue(any("empty.primaryAction" in error for error in validate(altered)))

    def test_dialog_close_must_use_governed_action(self):
        altered = self.source.replace('@close="closeBusinessCategoryCreatePicker"', '@close="legacyClose"')
        self.assertTrue(any("closeBusinessCategoryCreatePicker" in error for error in validate(altered)))

    def test_stateful_filter_chip_cannot_be_erased(self):
        altered = self.source.replace('v-for="chip in vm.filters.quickFilters.primary"', 'v-for="item in genericActions"')
        self.assertTrue(any("stateful native control" in error for error in validate(altered)))

    def test_projection_count_rejects_parallel_action(self):
        altered = self.source.replace('</template>', '<ScButton>parallel</ScButton>\n</template>', 1)
        self.assertTrue(any("expected 11" in error for error in validate(altered)))


if __name__ == "__main__":
    unittest.main()
