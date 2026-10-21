from unittest.mock import patch
from odoo.tests.common import tagged
from odoo.exceptions import UserError
from .business_case import BusinessTransactionCase
from ..handlers.baseline_readiness import BaselineReadinessHandler
from ..services.baseline_readiness import build_readiness


@tagged('post_install', '-at_install', 'baseline_readiness')
class TestBaselineReadiness(BusinessTransactionCase):
    def _project(self):
        return self.env['project.project'].create({'name': 'Readiness project', 'company_id': self.env.company.id})

    def _payment(self, basis=True):
        project = self._project()
        partner = self.env['res.partner'].create({'name': 'Readiness counterparty'})
        payment = self.env['payment.request'].create({
            'name': 'Readiness payment', 'type': 'pay', 'project_id': project.id,
            'partner_id': partner.id, 'amount': 100,
        })
        if basis:
            contract = self.env['construction.contract'].create({
                'subject': 'Readiness contract', 'type': 'in',
                'project_id': project.id, 'partner_id': partner.id,
            })
            self.env['payment.request.line'].create({
                'request_id': payment.id, 'legacy_line_id': 'readiness-line',
                'legacy_parent_id': 'readiness-parent', 'contract_id': contract.id,
                'amount': 100, 'current_pay_amount': 100,
            })
            payment.write({'contract_id': contract.id})
        return payment

    def test_native_display_matches_projection_and_unsaved_record(self):
        project = self._project()
        self.assertIn('办理前检查：可提交', project.submission_readiness_display)
        self.assertIn('下一步：', project.submission_readiness_display)
        new = self.env['project.project'].new({'name': 'Unsaved readiness'})
        self.assertIn('暂无记录', new.submission_readiness_display)
        payment = self._payment(basis=False)
        result = build_readiness(self.env, 'payment.request', payment.id)
        self.assertIn(result['message'], payment.submission_readiness_display)
        self.assertIn('办理前检查：待处理', payment.submission_readiness_display)

    def test_create_defaults_expose_no_data_before_record_exists(self):
        for model in ('project.project', 'payment.request'):
            with self.subTest(model=model):
                defaults = self.env[model].default_get(['submission_readiness_display'])
                self.assertIn('暂无记录', defaults['submission_readiness_display'])
                self.assertIn('请先保存或选择', defaults['submission_readiness_display'])

    def test_action_projection_shares_native_submission_checks(self):
        from ..handlers.payment_request_available_actions import PaymentRequestAvailableActionsHandler
        handler = PaymentRequestAvailableActionsHandler(self.env)
        payment = self._payment(basis=False)
        result = build_readiness(self.env, 'payment.request', payment.id)
        allowed, reason = handler._evaluate_prerequisites(payment, 'submit')
        self.assertFalse(allowed)
        self.assertEqual(reason, result['reason_code'])
        self.assertEqual(handler._submission_readiness_block['message'], result['message'])
        ready = self._payment()
        self.assertTrue(handler._evaluate_prerequisites(ready, 'submit')[0])

    def test_invalid_funding_is_blocked_in_both_projections_and_native_submit(self):
        from ..handlers.payment_request_available_actions import PaymentRequestAvailableActionsHandler
        payment = self._payment()
        payment.project_id.funding_enabled = True
        before = (payment.state, payment.write_date, payment.review_ids.ids)
        result = build_readiness(self.env, 'payment.request', payment.id)
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('资金基准', result['message'])
        action = PaymentRequestAvailableActionsHandler(self.env)._action_entry(
            payment, {'key': 'submit', 'method': 'action_submit', 'allowed_states': ['draft']})
        self.assertFalse(action['allowed'])
        self.assertEqual(action['blocked_message'], result['message'])
        self.assertIn(result['message'], payment.submission_readiness_display)
        self.assertEqual(before, (payment.state, payment.write_date, payment.review_ids.ids))
        with self.assertRaises(UserError) as error:
            payment.action_submit()
        self.assertEqual(str(error.exception), result['message'])

    def test_projection_does_not_swallow_access_or_configuration_errors(self):
        from odoo.exceptions import AccessError
        from odoo.addons.smart_core.core.form_configuration_compiler import FormConfigurationError
        from ..services.baseline_readiness import payment_advisories
        payment = self._payment()
        for error in (AccessError('denied'), FormConfigurationError('invalid', 'payment.request'), RuntimeError('unexpected')):
            with self.subTest(error=type(error).__name__), patch.object(
                    type(payment), '_collect_payment_advisories', side_effect=error):
                with self.assertRaises(type(error)):
                    payment_advisories(payment, 'submit')

    def test_missing_record_and_invalid_parameters_are_explicit(self):
        self.assertEqual(build_readiness(self.env, 'project.project')['status'], 'no_data')
        for model, record_id in [('res.users', 1), ('project.project', True), ('payment.request', -1)]:
            with self.assertRaises(ValueError):
                build_readiness(self.env, model, record_id)
        response = BaselineReadinessHandler(self.env).run({'model': 'res.users', 'record_id': 1})
        self.assertFalse(response['ok'])

    def test_project_ready_is_read_only_and_submission_uses_same_check(self):
        project = self._project()
        before = (project.write_date, project.sc_approval_state, project.review_ids.ids, project.message_ids.ids)
        response = BaselineReadinessHandler(self.env).run({'intent': 'baseline.readiness', 'params': {
            'model': 'project.project', 'record_id': project.id}})
        self.assertEqual(response['data']['status'], 'ready')
        self.assertEqual(before, (project.write_date, project.sc_approval_state, project.review_ids.ids, project.message_ids.ids))
        project.action_sc_submit()
        self.assertEqual(project.sc_approval_state, 'approved')
        blocked = build_readiness(self.env, 'project.project', project.id)
        self.assertEqual(blocked['status'], 'blocked')
        with self.assertRaisesRegex(UserError, '立项已通过'):
            project.action_sc_submit()

    def test_payment_missing_basis_matches_native_rejection(self):
        payment = self._payment(basis=False)
        result = build_readiness(self.env, 'payment.request', payment.id)
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('关联合同', result['message'])
        with self.assertRaises(UserError) as error:
            payment.action_submit()
        self.assertEqual(result['message'], str(error.exception))
        self.assertTrue(result['next_step'])

    def test_payment_soft_missing_configuration_does_not_become_hard_gate(self):
        payment = self._payment()
        before = (payment.write_date, payment.state, payment.review_ids.ids, payment.message_ids.ids,
                  payment.project_id.funding_reservation_revision)
        result = build_readiness(self.env, 'payment.request', payment.id)
        self.assertEqual(result['status'], 'ready', result)
        self.assertTrue(any(row['reason_code'] == 'PAYEE_ACCOUNT_INCOMPLETE' and row['status'] == 'warning'
                            for row in result['checks']), result)
        self.assertEqual(before, (payment.write_date, payment.state, payment.review_ids.ids, payment.message_ids.ids,
                                 payment.project_id.funding_reservation_revision))

    def test_explicit_force_block_policy_changes_readiness(self):
        payment = self._payment()
        with patch.object(type(payment), '_payment_force_block_enabled', return_value=True):
            result = build_readiness(self.env, 'payment.request', payment.id)
        self.assertEqual(result['status'], 'blocked', result)
        self.assertTrue(any(row['status'] == 'blocked' for row in result['checks']))
        self.assertEqual(result['next_step']['action'], 'review_record')

    def test_ordinary_authorized_actor_and_registered_intent(self):
        from odoo.addons.smart_core.core.intent_surface_builder import IntentSurfaceBuilder
        project = self._project()
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Readiness project manager', 'login': 'readiness_manager',
            'email': 'readiness_manager@invalid.local',
            'groups_id': [(6, 0, [self.env.ref('smart_construction_core.group_sc_cap_project_manager').id])],
            'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
        })
        project.write({'manager_id': user.id})
        actor_env = self.env(user=user, su=False)
        visible, _ = IntentSurfaceBuilder().collect(actor_env, actor_env.user)
        self.assertIn('baseline.readiness', visible)
        result = BaselineReadinessHandler(actor_env).run({'model': 'project.project', 'record_id': project.id})
        self.assertEqual(result['data']['status'], 'ready', result)
        project.with_user(user).action_sc_submit()
        self.assertEqual(project.sc_approval_state, 'approved')

    def test_denied_actor_receives_no_record_facts(self):
        project = self._project()
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Readiness unauthorized actor', 'login': 'readiness_denied',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
            'company_id': self.env.company.id, 'company_ids': [(6, 0, self.env.company.ids)],
        })
        result = build_readiness(self.env(user=user, su=False), 'project.project', project.id)
        self.assertEqual(result['status'], 'forbidden')
        self.assertEqual(result['reason_code'], 'PERMISSION_DENIED')
        self.assertEqual(result['checks'], [])
        self.assertNotIn(project.name, str(result))
