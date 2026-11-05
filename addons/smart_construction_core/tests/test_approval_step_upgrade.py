"""Default initialization and maintenance authority; real upgrades use local.test rehearsal."""
from odoo.tests.common import tagged, Form
from unittest.mock import patch
from .business_case import BusinessTransactionCase


@tagged('post_install', '-at_install', 'sc_smoke', 'approval_step_upgrade')
class TestApprovalStepUpgrade(BusinessTransactionCase):
    def setUp(self):
        super().setUp()
        self.policy = self.env.ref('smart_construction_core.approval_policy_payment_request')
        self.policy.write({'company_id': self.env.company.id})

    def test_clean_install_has_complete_initial_template(self):
        expected = [key for _, key in self.policy.USER_VISIBLE_APPROVAL_TEMPLATES[self.policy.code]['steps']]
        self.assertEqual(self.policy.step_ids.sorted(lambda s: (s.sequence, s.id)).mapped('approval_scope_key'), expected)
        self.assertEqual(self.policy.mode, 'linear')
        self.assertIn(self.policy.USER_VISIBLE_TEMPLATE_MARKER, self.policy.note)

    def test_native_form_order_survives_repeated_initializer_calls(self):
        actor = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Step maintenance test', 'login': 'step.maintenance.test',
            'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id,
                self.env.ref('smart_construction_core.group_sc_cap_business_config_admin').id])],
        })
        record = self.policy.with_user(actor)
        self.assertFalse(record.env.su)
        with Form(record, view='smart_construction_core.view_sc_approval_policy_form') as form:
            with form.step_ids.edit(0) as step:
                step.sequence = 25
        before = self.policy.step_ids.read(['sequence', 'approve_group_id', 'amount_min', 'amount_max'])
        self.policy.apply_user_visible_approval_templates()
        self.policy.apply_user_visible_approval_templates()
        self.assertEqual(before, self.policy.step_ids.read(['sequence', 'approve_group_id', 'amount_min', 'amount_max']))

    def test_deleted_step_and_future_template_addition_are_not_reseeded(self):
        step = self.policy.step_ids[-1:]
        step.write({'active': False})
        step.unlink()
        before = self.policy.step_ids.ids
        self.policy.apply_user_visible_approval_templates()
        self.assertEqual(self.policy.step_ids.ids, before)

    def test_new_template_step_is_not_implicitly_added_on_existing_install(self):
        template = self.policy.USER_VISIBLE_APPROVAL_TEMPLATES[self.policy.code]
        before = self.policy.step_ids.ids
        with patch.dict(self.policy.USER_VISIBLE_APPROVAL_TEMPLATES, {
            self.policy.code: {**template, 'steps': template['steps'] + [('New optional step', 'executive')]},
        }):
            self.policy.apply_user_visible_approval_templates()
        self.assertEqual(self.policy.step_ids.ids, before)

    def test_unmarked_existing_policy_is_not_assumed_to_be_seed(self):
        self.policy.write({'note': 'Administrator maintained policy'})
        self.policy.step_ids[:1].write({'sequence': 99})
        before = self.policy.step_ids.read(['sequence', 'approve_group_id'])
        self.policy.apply_user_visible_approval_templates()
        self.assertEqual(before, self.policy.step_ids.read(['sequence', 'approve_group_id']))
        self.assertEqual(self.policy.note, 'Administrator maintained policy')
