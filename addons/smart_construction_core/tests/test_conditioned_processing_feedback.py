"""Conditional native advice: selection authority and nonzero-only numeric inputs."""
from contextlib import ExitStack
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged
from odoo.addons.smart_core.core import draft_feedback, native_advisory


@tagged('post_install', '-at_install', 'conditioned_processing_feedback')
class TestConditionedProcessingFeedback(TransactionCase):
    CASES = (
        ('sc.quality.acceptance', 'view_sc_quality_acceptance_form'),
        ('sc.labor.usage', 'view_sc_labor_usage_form'),
        ('sc.hr.payroll.document', 'view_sc_hr_payroll_document_form'),
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = cls.env.ref('base.group_user') | cls.env.ref(
            'smart_construction_core.group_sc_cap_project_manager')
        cls.operator = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Conditional feedback operator', 'login': 'conditional_feedback_operator',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, groups.ids)],
        })
        cls.denied = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Conditional feedback denied', 'login': 'conditional_feedback_denied',
            'company_id': cls.env.company.id, 'company_ids': [(6, 0, cls.env.company.ids)],
            'groups_id': [(6, 0, cls.env.ref('base.group_user').ids)],
        })

    def parts(self, index):
        name, xmlid = self.CASES[index]
        model = self.env[name].with_user(self.operator).with_context(
            allowed_company_ids=self.env.company.ids, lang='en_US')
        view = self.env.ref('smart_construction_core.' + xmlid)
        contract, _ = draft_feedback._assemble_contract(model, view.id)
        hosts = [node for node, _ in native_advisory.walk(contract['layoutContract']['containerTree'])
                 if node.get('componentKey') == draft_feedback.COMPONENT_KEY]
        self.assertEqual(len(hosts), 1)
        request = {'version': draft_feedback.VERSION, 'operation': 'describe',
                   'request_id': 'conditional_describe', 'view_id': view.id,
                   'container_id': hosts[0]['containerId']}
        binding = draft_feedback.evaluate(model, request)['binding']
        return model, request, binding

    def evaluate(self, parts, values):
        model, request, binding = parts
        return draft_feedback.evaluate(model, {
            **request, 'operation': 'evaluate', 'binding_etag': binding['etag'],
            'inputs': [{'field': dep['field'], 'present': True, 'value': values[dep['field']]}
                       for dep in binding['dependencies']],
        })['result']['content']

    def values(self, parts, complete=False):
        return {dep['field']: (False if not complete else
                True if dep['type'].endswith('_presence') or dep['type'] == 'number_nonzero' else
                '2026-10-26' if dep['type'] == 'date' else
                False if dep['type'] == 'selection' else '已补充')
                for dep in parts[2]['dependencies']}

    def test_defaults_cover_all_inputs_and_authorization_stays_enforced(self):
        for index, (name, _) in enumerate(self.CASES):
            with self.subTest(model=name):
                model, request, binding = self.parts(index)
                names = [dep['field'] for dep in binding['dependencies']]
                self.assertEqual(set(model.default_get(names)), set(names))
                with self.assertRaisesRegex(draft_feedback.DraftFeedbackError, 'FEEDBACK_SOURCE_FORBIDDEN'):
                    draft_feedback.evaluate(model.with_user(self.denied), request)

    def test_quality_rectification_follows_native_result(self):
        parts = self.parts(0)
        values = {**self.values(parts, True), 'rectification_deadline': False}
        for result in (False, 'pending', 'passed', 'conditional', 'failed'):
            with self.subTest(result=result):
                expected = '建议设置整改期限' if result in ('conditional', 'failed') else ''
                self.assertEqual(self.evaluate(parts, {**values, 'result': result}), expected)
                self.assertEqual(self.evaluate(parts, {
                    **values, 'result': result, 'rectification_deadline': '2026-10-27'}), '')

    def test_labor_numeric_presence_and_attachment_are_independent(self):
        parts = self.parts(1)
        values = self.values(parts, True)
        self.assertEqual(self.evaluate(parts, values), '')
        self.assertEqual(self.evaluate(parts, {**values, 'price_unit': False}), '建议补充用工单价')
        self.assertEqual(self.evaluate(parts, {**values, 'attachment_ids': False}), '建议上传用工依据')

    def test_payroll_branch_person_alternative_and_both_period_parts(self):
        parts = self.parts(2)
        empty = self.values(parts)
        salary = '建议关联所属项目；建议补充所属部门；建议补充发放单位；建议补充核算说明；建议上传薪资核算依据'
        provident = '建议补充缴存人员；建议补充缴存期间；建议补充缴存单位；建议补充公积金账号；建议补充公积金基数'
        for kind, expected in [('salary_registration', salary),
                               ('provident_fund_registration', provident),
                               ('bonus', ''), ('social_registration', ''), (False, '')]:
            self.assertEqual(self.evaluate(parts, {**empty, 'fact_type': kind}), expected)
        complete = {**self.values(parts, True), 'fact_type': 'provident_fund_registration'}
        self.assertEqual(self.evaluate(parts, complete), '')
        for person in ({'employee_user_id': False, 'employee_name': '已补充'},
                       {'employee_user_id': True, 'employee_name': False}):
            self.assertEqual(self.evaluate(parts, {**complete, **person}), '')
        self.assertEqual(self.evaluate(parts, {
            **complete, 'employee_user_id': False, 'employee_name': False}), '建议补充缴存人员')
        for name in ('period_year', 'period_month'):
            self.assertEqual(self.evaluate(parts, {**complete, name: False}), '建议补充缴存期间')
        self.assertEqual(self.evaluate(parts, {**complete, 'provident_fund_base': False}), '建议补充公积金基数')

    def test_invalid_selection_numeric_payload_and_missing_snapshot_fail_closed(self):
        for index, field, invalid in (
                (0, 'result', ['invented', True, 1]),
                (1, 'price_unit', ['1000.50', 1000.50, None]),
                (2, 'fact_type', ['invented', True]),
                (2, 'period_year', ['2026', 2026])):
            parts = self.parts(index)
            for value in invalid:
                with self.subTest(field=field, value=value), self.assertRaises(draft_feedback.DraftFeedbackError):
                    self.evaluate(parts, {**self.values(parts), field: value})
            model, request, binding = parts
            inputs = [{'field': dep['field'], 'present': False} for dep in binding['dependencies']]
            with self.assertRaisesRegex(draft_feedback.DraftFeedbackError, 'FEEDBACK_INPUT_INVALID'):
                draft_feedback.evaluate(model, {
                    **request, 'operation': 'evaluate', 'binding_etag': binding['etag'], 'inputs': inputs})

    def test_selection_option_changes_invalidate_binding_review(self):
        parts = self.parts(0)
        model, _, _ = parts
        field = model._fields['processing_advisory']
        original = draft_feedback.reviewed_content_field(model, field)
        result_field = model._fields['result']
        # Odoo resolves translated static selections through ir.model.fields;
        # changing field.selection alone does not change the runtime option list.
        native_selection = type(result_field)._description_selection
        def changed_options(selection_field, env):
            if selection_field is result_field:
                return [('pending', 'Pending'), ('new_result', 'New')]
            return native_selection(selection_field, env)
        with patch.object(type(result_field), '_description_selection', changed_options):
            changed = draft_feedback.reviewed_content_field(model, field)
            self.assertNotEqual(original['review_sha256'], changed['review_sha256'])
            with self.assertRaisesRegex(draft_feedback.DraftFeedbackError, 'FEEDBACK_BINDING_STALE'):
                self.evaluate(parts, self.values(parts))

    def test_evaluation_never_writes_business_records_or_reads_presence_details(self):
        for index, (name, _) in enumerate(self.CASES):
            parts = self.parts(index)
            values = self.values(parts, True)
            if index == 2:
                values['fact_type'] = 'provident_fund_registration'
            model = parts[0]
            before = model.search_count([])
            with ExitStack() as stack:
                for target in (model, self.env['ir.attachment'], self.env['res.partner']):
                    for method in ('create', 'write', 'unlink'):
                        stack.enter_context(patch.object(type(target), method,
                            side_effect=AssertionError('business mutation during feedback')))
                for method in ('read', 'search', 'fetch'):
                    stack.enter_context(patch.object(type(self.env['ir.attachment']), method,
                        side_effect=AssertionError('attachment detail read during feedback')))
                self.assertEqual(self.evaluate(parts, values), '', name)
            self.assertEqual(model.search_count([]), before)
