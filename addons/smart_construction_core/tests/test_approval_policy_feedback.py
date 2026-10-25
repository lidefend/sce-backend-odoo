"""Approval configuration advice must never grant payment-rule write authority."""
from unittest.mock import patch
from lxml import etree

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import file_open
from odoo.addons.smart_core.core import draft_feedback, native_advisory


@tagged('post_install', '-at_install', 'approval_policy_feedback')
class TestApprovalPolicyFeedback(TransactionCase):
    MESSAGE = '付款申请的启用审批和审批方式请在“系统参数”中发布或回滚。'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Exercise source XML before governed upgrade. This view change belongs
        # to the test transaction and is rolled back with the fixture.
        cls.view = cls.env.ref('smart_construction_core.view_sc_approval_policy_form')
        with file_open('smart_construction_core/views/support/approval_policy_views.xml', 'rb') as stream:
            tree = etree.parse(stream)
        arch = tree.xpath("//record[@id='view_sc_approval_policy_form']/field[@name='arch']/form")[0]
        cls.view.write({'arch_db': etree.tostring(arch, encoding='unicode')})
        base = cls.env.ref('base.group_user')
        admin = cls.env.ref('smart_construction_core.group_sc_cap_business_config_admin')
        cls.operator = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Approval feedback operator', 'login': 'approval_feedback_operator',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, (base | admin).ids)],
        })
        cls.denied = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Approval feedback denied', 'login': 'approval_feedback_denied',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, base.ids)],
        })

    def parts(self):
        model = self.env['sc.approval.policy'].with_user(self.operator).with_context(
            allowed_company_ids=self.env.company.ids, lang='en_US')
        contract, _ = draft_feedback._assemble_contract(model, self.view.id)
        hosts = [n for n, _ in native_advisory.walk(contract['layoutContract']['containerTree'])
                 if n.get('componentKey') == draft_feedback.COMPONENT_KEY]
        self.assertEqual(len(hosts), 1)
        request = {'version': draft_feedback.VERSION, 'operation': 'describe',
                   'request_id': 'approval_describe', 'view_id': self.view.id,
                   'container_id': hosts[0]['containerId']}
        binding = draft_feedback.evaluate(model, request)['binding']
        return model, request, binding

    def evaluate(self, parts, target):
        model, request, binding = parts
        return draft_feedback.evaluate(model, {
            **request, 'operation': 'evaluate', 'binding_etag': binding['etag'],
            'inputs': [{'field': 'target_model', 'present': True, 'value': target}],
        })['result']

    def test_native_binding_defaults_and_payment_condition_without_writes(self):
        parts = self.parts()
        model, _, binding = parts
        self.assertEqual(binding['dependencies'], [{'field': 'target_model', 'type': 'selection'}])
        self.assertEqual(model.default_get(['target_model']), {'target_model': False})
        for target, expected in [(False, ''), ('project.project', ''), ('payment.request', self.MESSAGE)]:
            with self.subTest(target=target), patch.object(
                    type(model), 'create', side_effect=AssertionError('feedback attempted create')), patch.object(
                    type(model), 'write', side_effect=AssertionError('feedback attempted write')):
                self.assertEqual(self.evaluate(parts, target), {'content': expected, 'visible': bool(expected)})

    def test_unauthorized_actor_and_unknown_target_are_rejected(self):
        model, request, binding = self.parts()
        with self.assertRaisesRegex(draft_feedback.DraftFeedbackError, 'FEEDBACK_SOURCE_FORBIDDEN'):
            draft_feedback.evaluate(model.with_user(self.denied), request)
        for value in ('invented.model', True, 42):
            with self.subTest(value=value), self.assertRaises(draft_feedback.DraftFeedbackError):
                self.evaluate((model, request, binding), value)

    def test_direct_payment_create_stays_forbidden_with_explicit_or_context_default(self):
        model, _, _ = self.parts()
        for values, context in [
            ({'target_model': 'payment.request'}, {}),
            ({}, {'default_target_model': 'payment.request'}),
        ]:
            with self.subTest(values=values), self.assertRaises(AccessError):
                model.with_context(**context).create({
                    'name': 'Must not create payment rule', 'code': 'feedback_denied_payment', **values,
                })

    def test_existing_payment_rule_mutation_stays_forbidden(self):
        # Fixture setup is rolled back; ordinary actor performs only denied writes.
        registration = self.env['sc.tenant.company.registration']._create_non_customer_space(
            tenant_key='approval-feedback-boundary-test', purpose='test',
            company_name='Approval feedback isolated company')
        company = registration.company_id
        self.operator.write({
            'company_id': company.id, 'company_ids': [(4, company.id)],
            'groups_id': [(4, self.env.ref('smart_core.group_smart_core_non_customer_data_user').id)],
        })
        policy = self.env['sc.approval.policy'].with_context(skip_tier_sync=True).create({
            'name': 'Feedback payment authority fixture', 'code': 'feedback_payment_authority',
            'target_model': 'payment.request', 'active': False, 'company_id': company.id,
        }).with_user(self.operator).with_context(allowed_company_ids=[company.id])
        before = policy.read(['target_model', 'mode', 'active'])[0]
        for values in ({'active': True}, {'mode': 'none'}, {'target_model': 'project.project'}):
            with self.subTest(values=values), self.assertRaises(AccessError):
                policy.write(values)
        with self.assertRaises(AccessError):
            policy.unlink()
        self.assertEqual(policy.read(['target_model', 'mode', 'active'])[0], before)
