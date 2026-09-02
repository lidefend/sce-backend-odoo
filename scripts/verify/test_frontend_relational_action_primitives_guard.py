import unittest

from scripts.verify.frontend_relational_action_primitives_guard import X2MANY, VIEW_RELATION, validate


class RelationalActionPrimitivesGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x2many = X2MANY.read_text(encoding="utf-8")
        cls.view_relation = VIEW_RELATION.read_text(encoding="utf-8")

    def test_repository_contract_passes(self):
        self.assertEqual(validate(self.x2many, self.view_relation), [])

    def test_one2many_create_cannot_regress_to_legacy_button(self):
        altered = self.x2many.replace('<ScButton\n          v-if="adapter.one2manyCanCreate(field.name)"', '<button\n          v-if="adapter.one2manyCanCreate(field.name)"')
        self.assertIn("relational surface retains a generic legacy command", validate(altered, self.view_relation))

    def test_destructive_commands_keep_danger_variant(self):
        altered = self.view_relation.replace('class="relational-delete" type="button" variant="danger"', 'class="relational-delete" type="button" variant="ghost"')
        self.assertTrue(any("relational-delete" in error for error in validate(self.x2many, altered)))

    def test_editor_uses_governed_input(self):
        altered = self.view_relation.replace('<ScInput v-model="draftName"', '<input v-model="draftName"')
        self.assertTrue(any("draftName" in error for error in validate(self.x2many, altered)))

    def test_legacy_css_cannot_override_button_variant(self):
        altered = f"{self.x2many}\n.chip-btn {{ background: red; }}"
        self.assertIn("relational surface overrides governed ScButton variant presentation", validate(altered, self.view_relation))

    def test_cancel_keeps_existing_settlement_behavior(self):
        altered = self.view_relation.replace('variant="ghost" @click="cancelEdit"', 'variant="ghost" :disabled="saving" @click="cancelEdit"')
        self.assertIn("relational cancel changed the existing transaction settlement boundary", validate(self.x2many, altered))

    def test_stateful_tag_choice_remains_governed(self):
        altered = self.x2many.replace('ProfessionalManyToManySelect', 'GenericManyToManySelect')
        self.assertTrue(any("stateful governed" in error for error in validate(altered, self.view_relation)))

    def test_raw_relation_control_is_rejected(self):
        altered = self.x2many.replace('<ScCheckbox', '<input', 1)
        self.assertTrue(any("raw interactive control" in error for error in validate(altered, self.view_relation)))

    def test_business_specific_collection_action_is_rejected(self):
        altered = self.x2many.replace(
            '<slot name="collection-actions" />',
            '<SettlementIntroduceDialog v-if="isSettlementIntroduceField(field)" />',
        )
        self.assertIn(
            "shared X2Many surface retains a business-specific collection action",
            validate(altered, self.view_relation),
        )

    def test_readonly_attachment_cannot_restore_upload_control(self):
        altered = self.x2many.replace('v-if="!field.readonly"\n        :key="uploadTick"', ':key="uploadTick"', 1)
        self.assertTrue(any("readonly attachment authority" in error for error in validate(altered, self.view_relation)))

    def test_readonly_attachment_cannot_restore_remove_control(self):
        altered = self.x2many.replace('v-if="!field.readonly"\n            variant="ghost"', 'variant="ghost"', 1)
        self.assertTrue(any("readonly attachment authority" in error for error in validate(altered, self.view_relation)))

    def test_readonly_attachment_upload_handler_fails_closed(self):
        altered = self.x2many.replace('if (field.readonly) return;', '', 1)
        self.assertTrue(any("readonly attachment authority" in error for error in validate(altered, self.view_relation)))

    def test_parallel_command_is_rejected(self):
        altered = self.view_relation.replace('</template>', '<ScButton>parallel</ScButton>\n</template>', 1)
        self.assertTrue(any("expected 6" in error for error in validate(self.x2many, altered)))


if __name__ == "__main__":
    unittest.main()
