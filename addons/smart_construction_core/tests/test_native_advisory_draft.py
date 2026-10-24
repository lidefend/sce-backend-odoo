"""Native Odoo integration tests, selected only by native_advisory_draft."""
import copy
import logging
from contextlib import contextmanager
from unittest.mock import patch

from lxml import etree
from odoo import release
from odoo.exceptions import AccessError
from odoo.models import BaseModel
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.smart_core.core.form_configuration_compiler import FormConfigurationError
from odoo.addons.smart_core.core.native_advisory import walk
from odoo.addons.smart_core.core import draft_feedback
from odoo.addons.smart_core.handlers.api_onchange import ApiOnchangeHandler
from .advisory_draft_prototype import (
    CONTENT, LOCATOR, MODEL, VIEW, DraftRejected, context_identity, evaluate,
)

_logger = logging.getLogger(__name__)
BINDING = {'purpose': 'advisory', 'occurrences': [
    {'view_xmlid': VIEW, 'native_locator': LOCATOR, 'occurrence_index': 1},
]}
FEEDBACK_REVIEW = {
    'purpose': 'advisory',
    'inputs': [
        {'field': 'business_date', 'type': 'date'},
        {'field': 'note', 'type': 'text'},
    ],
}


@tagged('post_install', '-at_install', 'native_advisory_draft')
class TestNativeAdvisoryDraft(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env['res.company'].create({'name': 'R6.1 synthetic company'})
        groups = [cls.env.ref('base.group_user').id,
                  cls.env.ref('smart_construction_core.group_sc_cap_project_user').id]
        cls.users = cls.env['res.users'].with_context(no_reset_password=True).create([
            {'name': 'R6.1 synthetic operator %s' % n, 'login': 'r6_1_synthetic_%s' % n,
             'groups_id': [(6, 0, groups)], 'company_id': cls.company.id,
             'company_ids': [(6, 0, [cls.company.id, cls.other_company.id])]}
            for n in (1, 2)
        ])
        _logger.info('R6.1 native ORM identity: Odoo=%s database=%s', release.version, cls.env.cr.dbname)

    def setUp(self):
        super().setUp()
        self.model = self.env[MODEL].with_user(self.users[0]).with_context(
            allowed_company_ids=[self.company.id], lang='en_US')
        self.view = self.model.env.ref(VIEW)
        # Actual current-user get_view and actual registered parser, no fake ORM.
        arch = self.model.get_view(view_id=self.view.id, view_type='form')['arch']
        metadata = self.model.fields_get()
        self.layout = self.model.env['app.view.parser']._extract_form_layout_dom(
            etree.fromstring(arch.encode()), metadata)
        self.field = self.model._fields[CONTENT]
        self.declaration_patch = patch.object(self.field, 'sc_feedback_usage', copy.deepcopy(BINDING), create=True)
        self.declaration_patch.start()
        self.addCleanup(self.declaration_patch.stop)

    def call(self, pairs=None, **kw):
        model = kw.pop('model', self.model)
        return evaluate(model, [('business_date', False), ('note', False)] if pairs is None else pairs,
                        view_id=kw.pop('view_id', self.view.id), layout=kw.pop('layout', self.layout),
                        expected_context=kw.pop('expected_context', context_identity(model)), **kw)

    @contextmanager
    def reviewed_feedback(self):
        method = type(self.model)._compute_processing_advisory
        with patch.object(method, '_sc_feedback_evaluation_review', FEEDBACK_REVIEW, create=True):
            yield

    def feedback_request(self, operation, **values):
        contract, _proof = draft_feedback._assemble_contract(self.model, self.view.id)
        host = next(
            node for node, _path in walk(contract['layoutContract']['containerTree'])
            if node.get('componentKey') == draft_feedback.COMPONENT_KEY
        )
        source_id = host['componentConfig']['contentRef']['containerId']
        source = next(
            node for node, _path in walk(contract['layoutContract']['containerTree'])
            if node.get('containerId') == source_id
        )
        self.assertEqual(host['componentConfig']['evaluation'], {
            'capability': draft_feedback.CAPABILITY,
            'visibilityOwner': draft_feedback.VISIBILITY_OWNER,
        })
        self.assertEqual(source['sourceAuthority']['view_id'], self.view.id)
        block = {
            'version': draft_feedback.VERSION,
            'operation': operation,
            'request_id': 'r6_3_' + operation,
            'view_id': self.view.id,
            'container_id': host['containerId'],
        }
        if operation == 'evaluate':
            block.update(binding_etag=values.pop('binding_etag'), inputs=values.pop('inputs'))
        return block

    def test_controlled_describe_and_evaluate_use_native_draft_no_writes(self):
        with self.reviewed_feedback():
            with self.no_writes():
                described = draft_feedback.evaluate(self.model, self.feedback_request('describe'))
                self.assertEqual(described['status'], 'described')
                binding = described['binding']
                self.assertEqual(binding['native_locator'], LOCATOR)
                self.assertEqual(binding['dependencies'], FEEDBACK_REVIEW['inputs'])
                request = self.feedback_request(
                    'evaluate',
                    binding_etag=binding['etag'],
                    inputs=[
                        {'field': 'business_date', 'present': True, 'value': '2026-10-23'},
                        {'field': 'note', 'present': True, 'value': ''},
                    ],
                )
                result = draft_feedback.evaluate(self.model, request)
                self.assertEqual(result['status'], 'ready')
                self.assertEqual(result['result'], {
                    'content': '建议补充办理说明',
                    'visible': True,
                })

    def test_controlled_evaluate_rejects_stale_missing_and_extra_inputs(self):
        with self.reviewed_feedback(), self.no_writes():
            binding = draft_feedback.evaluate(
                self.model, self.feedback_request('describe'),
            )['binding']
            valid_inputs = [
                {'field': 'business_date', 'present': True, 'value': False},
                {'field': 'note', 'present': True, 'value': False},
            ]
            cases = [
                ('FEEDBACK_BINDING_STALE', {'binding_etag': '0' * 64, 'inputs': valid_inputs}),
                ('FEEDBACK_INPUT_INVALID', {
                    'binding_etag': binding['etag'],
                    'inputs': [{'field': 'business_date', 'present': False}, valid_inputs[1]],
                }),
                ('FEEDBACK_INPUT_INVALID', {
                    'binding_etag': binding['etag'],
                    'inputs': [*valid_inputs, {'field': CONTENT, 'present': True, 'value': 'x'}],
                }),
            ]
            for code, values in cases:
                with self.subTest(code=code, values=values), self.assertRaisesRegex(
                        draft_feedback.DraftFeedbackError, code):
                    draft_feedback.evaluate(
                        self.model,
                        self.feedback_request('evaluate', **copy.deepcopy(values)),
                    )

    def test_onchange_handler_exposes_only_strict_feedback_result(self):
        with self.reviewed_feedback(), self.no_writes():
            params = {
                'model': MODEL,
                'values': {},
                'changed_fields': [],
                'client_contract_capabilities': [
                    'form.feedback.message.v1',
                    draft_feedback.CAPABILITY,
                ],
                'feedback_evaluation': self.feedback_request('describe'),
            }
            result = ApiOnchangeHandler(
                env=self.model.env,
                payload={'params': params},
            ).handle()
            self.assertTrue(result['ok'], result)
            data = result['data']
            self.assertEqual(data['feedback_evaluation']['status'], 'described')
            self.assertEqual(data['patch'], {})
            self.assertEqual(data['modifiers_patch'], {})
            self.assertEqual(data['line_patches'], [])
            self.assertNotIn('unified_page_patch_v2', result)
            self.assertNotIn('lite_preview', result)
            params['client_contract_capabilities'] = []
            denied = ApiOnchangeHandler(
                env=self.model.env,
                payload={'params': params},
            ).handle()
            self.assertFalse(denied['ok'])
            self.assertEqual(denied['code'], 409)
            self.assertEqual(
                denied['error']['reason_code'],
                'COMPONENT_CAPABILITY_REQUIRED',
            )

    @contextmanager
    def no_writes(self):
        # Flush fixture setup first. During evaluation every SQL operation must
        # be a SELECT; reject mutations before execution, including ORM writes.
        self.env.flush_all()
        cursor_type = type(self.env.cr)
        original = cursor_type.execute
        queries = []

        def readonly(cursor, query, *args, **kwargs):
            text = query.code if hasattr(query, 'code') else query
            if isinstance(text, bytes):
                text = text.decode()
            self.assertTrue(isinstance(text, str) and text.lstrip().upper().startswith('SELECT'),
                            'Non-SELECT SQL during draft evaluation')
            queries.append(text)
            return original(cursor, query, *args, **kwargs)

        cls = type(self.model)
        with patch.object(cursor_type, 'execute', readonly), \
                patch.object(cls, 'create', side_effect=AssertionError('create called')), \
                patch.object(cls, 'write', side_effect=AssertionError('write called')), \
                patch.object(cls, 'unlink', side_effect=AssertionError('unlink called')):
            yield queries

    def test_four_native_cases_no_writes(self):
        self.assertIs(self.model.new.__func__, BaseModel.new)
        self.assertFalse(self.model.env.su)
        _logger.info('R6.1 source: type=%s store=%s compute_sudo=%s deps=%s native_new=True su=False',
                     self.field.type, self.field.store, self.field.compute_sudo,
                     self.field.get_depends(self.model))
        before = self.model.search_count([])
        cases = [
            (False, False, '建议补充办理日期；建议补充办理说明', False),
            ('2026-10-23', False, '建议补充办理说明', False),
            (False, '办理说明', '建议补充办理日期', False),
            ('2026-10-23', '办理说明', '', True),
        ]
        ids = []
        old = copy.deepcopy(self.layout)
        for day, note, text, invisible in cases:
            with self.subTest(date=day, note=note), self.no_writes():
                result = self.call([('business_date', day), ('note', note)])
                self.assertEqual(result.content, text)
                self.assertIs(result.invisible, invisible)
                self.assertIs(result.visible, not invisible)
                self.assertNotIn(result.native_id, ids)
                ids.append(result.native_id)
                _logger.info('R6.1 case complete=True date=%r note=%r content=%r invisible=%s visible=%s',
                             day, note, result.content, result.invisible, result.visible)
        self.assertEqual(self.model.search_count([]), before)
        self.assertEqual(self.layout, old)

    def test_missing_is_not_clear(self):
        for pairs in ([], [('business_date', False)], [('note', '')]):
            with self.subTest(pairs=pairs), self.assertRaisesRegex(DraftRejected, 'INPUT_MISSING'):
                self.call(pairs)
        self.assertTrue(self.call([('business_date', False), ('note', '')]).visible)

    def test_unknown_duplicate_types(self):
        bad = [
            [('business_date', False), ('note', ''), ('note', '')],
            [('business_date', False), ('note', ''), (CONTENT, 'injected')],
            [('business_date', None), ('note', '')],
            [('business_date', '2026-02-31'), ('note', '')],
            [('business_date', True), ('note', '')],
            [('business_date', False), ('note', [])],
        ]
        for pairs in bad:
            with self.subTest(pairs=pairs), self.assertRaisesRegex(DraftRejected, 'INPUT_INVALID'):
                self.call(pairs)

    def test_declaration_missing_or_invalid(self):
        for value, error in ((None, DraftRejected), ({**BINDING, 'purpose': 'error'}, FormConfigurationError),
                             ({**BINDING, 'extra': True}, FormConfigurationError)):
            with patch.object(self.field, 'sc_feedback_usage', value), self.assertRaises(error):
                self.call()

    def test_wrong_view_locator_occurrence(self):
        with self.assertRaisesRegex(DraftRejected, 'SOURCE_INVALID'):
            self.call(view_id=self.model.env.ref('project.edit_project').id)
        for key, value in [('native_locator', '/form[1]/sheet[1]/div[2]/field[1]'), ('occurrence_index', 2)]:
            binding = copy.deepcopy(BINDING)
            binding['occurrences'][0][key] = value
            with patch.object(self.field, 'sc_feedback_usage', binding), self.assertRaisesRegex(DraftRejected, 'SOURCE_INVALID'):
                self.call()

    def test_ambiguous_or_wrong_native_source(self):
        layout = copy.deepcopy(self.layout)
        node = next(n for n, p in walk(layout) if n.get('name') == CONTENT)
        layout.append(copy.deepcopy(node))
        with self.assertRaisesRegex(DraftRejected, 'SOURCE_INVALID'):
            self.call(layout=layout)
        node['name'] = 'note'
        with self.assertRaisesRegex(DraftRejected, 'SOURCE_INVALID'):
            self.call(layout=layout)

    def test_condition_raw_mismatch_and_missing(self):
        for value in ({'kind': 'static', 'value': True}, None):
            layout = copy.deepcopy(self.layout)
            host = next(p for n, p in walk(layout) if n.get('name') == CONTENT)
            host['modifiers']['invisible'] = value
            with self.assertRaisesRegex(FormConfigurationError, 'FEEDBACK_CONDITION_INVALID'):
                self.call(layout=layout)

    def test_content_and_each_dependency_read_denied(self):
        original = type(self.model).check_field_access_rights
        for denied in (CONTENT, 'business_date', 'note'):
            def check(record, operation, fields, denied=denied):
                if denied in fields:
                    raise AccessError('synthetic denial')
                return original(record, operation, fields)
            with self.subTest(denied=denied), patch.object(type(self.model), 'check_field_access_rights', check), \
                    self.assertRaisesRegex(DraftRejected, 'SOURCE_FORBIDDEN'):
                self.call()

    def test_model_acl_denied(self):
        with patch.object(type(self.model), 'check_access_rights', side_effect=AccessError('synthetic denial')), \
                self.assertRaisesRegex(DraftRejected, 'SOURCE_FORBIDDEN'):
            self.call()

    def test_native_field_group_permissions(self):
        self.assertFalse(self.model.env.user.has_group('base.group_system'))
        for name in (CONTENT, 'business_date', 'note'):
            with self.subTest(field=name), patch.object(self.model._fields[name], 'groups', 'base.group_system'), \
                    self.assertRaisesRegex(DraftRejected, 'SOURCE_FORBIDDEN'):
                self.call()

    def test_hidden_invalid_source_is_still_rejected(self):
        layout = copy.deepcopy(self.layout)
        source, host = next((n, p) for n, p in walk(layout) if n.get('name') == CONTENT)
        host['visible'] = False
        source['name'] = 'note'
        with self.assertRaisesRegex(DraftRejected, 'SOURCE_INVALID'):
            self.call(layout=layout)

    def test_sudo_related_and_compute_dependencies_rejected(self):
        with self.assertRaisesRegex(DraftRejected, 'CONTEXT_INVALID'):
            self.call(model=self.model.sudo())
        for key, value in [('compute_sudo', True), ('related', ('note',)), ('_depends', ('project_id.name',))]:
            with patch.object(self.field, key, value), self.assertRaisesRegex(DraftRejected, 'SOURCE_INVALID'):
                self.call()
        with patch.object(self.model._fields['note'], 'compute', '_unreviewed'), \
                self.assertRaisesRegex(DraftRejected, 'SOURCE_INVALID'):
            self.call()

    def test_unreviewed_compute_rejected(self):
        with patch.object(self.field, 'compute', '_sc_readable_context_name'), \
                self.assertRaisesRegex(DraftRejected, 'SOURCE_INVALID'):
            self.call()

    def test_compute_exception_is_not_empty_feedback(self):
        # Fail the native descriptor itself after proof checks. Never substitute
        # another implementation and pretend it is the reviewed business rule.
        field_type = type(self.field)
        original = field_type.__get__
        def raising(field, record, owner=None):
            if field is self.field and record:
                raise RuntimeError('synthetic native compute failure')
            return original(field, record, owner)
        with patch.object(field_type, '__get__', raising), self.assertRaisesRegex(RuntimeError, 'native compute failure'):
            self.call()

    def test_user_company_context_isolation(self):
        first = self.call()
        for model in (self.model.with_user(self.users[1]),
                      self.model.with_context(allowed_company_ids=[self.other_company.id])):
            with self.assertRaisesRegex(DraftRejected, 'CONTEXT_INVALID'):
                self.call(model=model, expected_context=first.context)
            current = self.call(model=model, pairs=[('business_date', '2026-10-23'), ('note', '完整')])
            self.assertNotEqual(current.context, first.context)
            self.assertFalse(current.visible)
        self.assertTrue(self.call().visible)

    def test_existing_record_rules_and_draft_override(self):
        # Fixture setup is explicitly outside evaluation and rolled back by Odoo.
        project = self.env['project.project'].create({'name': 'R6.1 synthetic project'})
        partner = self.env['res.partner'].create({'name': 'R6.1 synthetic partner'})
        saved = self.model.create({'project_id': project.id, 'partner_id': partner.id,
                                   'business_date': '2026-10-23', 'note': '已保存'})
        with self.no_writes():
            self.assertTrue(self.call(origin=saved).visible)
        self.assertEqual(saved.note, '已保存')
        second = self.model.create({'project_id': project.id, 'partner_id': partner.id,
                                    'business_date': False, 'note': False})
        with self.no_writes():
            self.assertFalse(self.call(pairs=[('business_date', '2026-10-23'), ('note', '当前草稿')], origin=second).visible)
            self.assertTrue(self.call(origin=saved).visible)
        self.assertFalse(second.note)
        with self.assertRaisesRegex(DraftRejected, 'INPUT_MISSING'):
            self.call(pairs=[], origin=saved)
        # Exercise a real ir.rule denial, not an assumed creator-only policy.
        # This fixture rule is transactionally rolled back, never production ACL.
        self.env['ir.rule'].create({
            'name': 'R6.1 synthetic source ownership boundary',
            'model_id': self.env['ir.model']._get(MODEL).id,
            'domain_force': "[('create_uid', '=', user.id)]",
        })
        other = self.model.with_user(self.users[1])
        with self.assertRaisesRegex(DraftRejected, 'SOURCE_FORBIDDEN'):
            self.call(model=other, origin=saved.with_env(other.env))

    def test_internal_declaration_not_exposed(self):
        self.assertNotIn('sc_feedback_usage', self.model.fields_get([CONTENT])[CONTENT])
        self.assertNotIn('sc_feedback_usage', self.model.fields_get([CONTENT], attributes=['sc_feedback_usage'])[CONTENT])
