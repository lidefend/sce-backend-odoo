"""Three native cost forms: declared draft inputs and presence-only attachments."""
from contextlib import ExitStack
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged
from odoo.addons.smart_core.core import draft_feedback, native_advisory


@tagged('post_install', '-at_install', 'cost_processing_feedback')
class TestCostProcessingFeedback(TransactionCase):
    CASES = (
        ('sc.equipment.usage', 'view_sc_equipment_usage_form',
         '建议关联来源设备申请；建议补充供应单位；建议补充设备编号；建议补充规格型号；建议上传台班依据'),
        ('sc.subcontract.register', 'view_sc_subcontract_register_form',
         '建议关联来源分包申请；建议关联分包合同；建议补充履约期间；建议补充管理要求；建议上传分包成本依据'),
        ('sc.hr.salary.payment', 'view_sc_hr_salary_payment_form',
         '建议补充支付凭证号；建议补充发放说明；建议上传发放依据'),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = cls.env.ref('base.group_user') | cls.env.ref(
            'smart_construction_core.group_sc_cap_project_manager')
        cls.operator = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Cost feedback regression operator', 'login': 'cost_feedback_regression_operator',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, groups.ids)],
        })
        cls.denied = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Cost feedback denied operator', 'login': 'cost_feedback_denied_operator',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, cls.env.ref('base.group_user').ids)],
        })

    def parts(self, name, view_xmlid):
        model = self.env[name].with_user(self.operator).with_context(
            allowed_company_ids=self.env.company.ids, lang='en_US')
        view = self.env.ref('smart_construction_core.' + view_xmlid)
        contract, _proof = draft_feedback._assemble_contract(model, view.id)
        hosts = [node for node, _parent in native_advisory.walk(contract['layoutContract']['containerTree'])
                 if node.get('componentKey') == draft_feedback.COMPONENT_KEY]
        self.assertEqual(len(hosts), 1)
        request = {'version': draft_feedback.VERSION, 'operation': 'describe',
                   'request_id': 'cost_describe', 'view_id': view.id,
                   'container_id': hosts[0]['containerId']}
        binding = draft_feedback.evaluate(model, request)['binding']
        return model, request, binding

    def evaluate(self, model, request, binding, values):
        return draft_feedback.evaluate(model, {
            **request, 'operation': 'evaluate', 'binding_etag': binding['etag'],
            'inputs': [{'field': dep['field'], 'present': True, 'value': values[dep['field']]}
                       for dep in binding['dependencies']],
        })['result']

    def test_native_feedback_empty_complete_and_attachment_presence_without_io(self):
        for name, view, message in self.CASES:
            with self.subTest(model=name):
                model, request, binding = self.parts(name, view)
                dependencies = binding['dependencies']
                self.assertIn({'field': 'attachment_ids', 'type': 'many2many_presence'}, dependencies)
                empty = {dep['field']: False for dep in dependencies}
                complete = {dep['field']: (True if dep['type'].endswith('_presence') else
                    '2026-10-26' if dep['type'] == 'date' else '已补充') for dep in dependencies}
                before = model.search_count([])
                with ExitStack() as stack:
                    for target in (model, self.env['ir.attachment'], self.env['res.partner']):
                        for method in ('create', 'write', 'unlink'):
                            stack.enter_context(patch.object(type(target), method,
                                side_effect=AssertionError('business write during feedback')))
                    for method in ('read', 'search', 'fetch'):
                        stack.enter_context(patch.object(type(self.env['ir.attachment']), method,
                            side_effect=AssertionError('attachment read during presence evaluation')))
                    self.assertEqual(self.evaluate(model, request, binding, empty),
                                     {'content': message, 'visible': True})
                    self.assertEqual(self.evaluate(model, request, binding, complete),
                                     {'content': '', 'visible': False})
                    without_attachment = {**complete, 'attachment_ids': False}
                    self.assertEqual(self.evaluate(model, request, binding, without_attachment),
                                     {'content': message.split('；')[-1], 'visible': True})
                self.assertEqual(model.search_count([]), before)

    def test_defaults_cover_every_reviewed_input(self):
        for name, view, _message in self.CASES:
            with self.subTest(model=name):
                model, _request, binding = self.parts(name, view)
                names = [dep['field'] for dep in binding['dependencies']]
                defaults = model.default_get(names)
                self.assertEqual(set(defaults), set(names))
                self.assertEqual(defaults['attachment_ids'], [(6, 0, [])])

    def test_relation_identifiers_commands_and_wrong_scalar_types_are_rejected(self):
        for name, view, _message in self.CASES:
            with self.subTest(model=name):
                model, request, binding = self.parts(name, view)
                empty = {dep['field']: False for dep in binding['dependencies']}
                for invalid in (1, [1], [[6, 0, [1]]], {'id': 1}, 'true', None):
                    with self.subTest(value=invalid), self.assertRaisesRegex(
                            draft_feedback.DraftFeedbackError,
                            'FEEDBACK_INPUT_INVALID' if isinstance(invalid, str) else 'FEEDBACK_CONFIG_INVALID'):
                        self.evaluate(model, request, binding, {**empty, 'attachment_ids': invalid})
                scalar = next(dep['field'] for dep in binding['dependencies'] if dep['type'] in ('char', 'text'))
                with self.assertRaisesRegex(draft_feedback.DraftFeedbackError, 'FEEDBACK_CONFIG_INVALID'):
                    self.evaluate(model, request, binding, {**empty, scalar: {'untrusted': 'value'}})

    def test_unauthorized_user_cannot_describe_feedback(self):
        for name, view, _message in self.CASES:
            with self.subTest(model=name):
                model, request, _binding = self.parts(name, view)
                with self.assertRaisesRegex(draft_feedback.DraftFeedbackError, 'FEEDBACK_SOURCE_FORBIDDEN'):
                    draft_feedback.evaluate(model.with_user(self.denied), request)

    def test_subcontract_period_requires_both_dates(self):
        model, request, binding = self.parts('sc.subcontract.register', 'view_sc_subcontract_register_form')
        complete = {dep['field']: (True if dep['type'].endswith('_presence') else
            '2026-10-26' if dep['type'] == 'date' else '已补充') for dep in binding['dependencies']}
        for name in ('start_date', 'end_date'):
            with self.subTest(missing=name):
                self.assertEqual(self.evaluate(model, request, binding, {**complete, name: False}),
                                 {'content': '建议补充履约期间', 'visible': True})
