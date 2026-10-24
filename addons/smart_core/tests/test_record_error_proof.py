"""Offline native-declaration/actor-read fixtures; no production enrollment."""
import copy
from dataclasses import replace
import importlib.util
import hashlib
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.record_error_proof import (RecordErrorReview, REVIEW_PATHS, declarations,
                                    implementation_digest, validate_record_errors)
from core.form_configuration_compiler import FormConfigurationError
from core.field_presentation_usage import assert_field_body_usage


def field(kind, **kw):
    return types.SimpleNamespace(**dict(type=kind, readonly=True, compute=None,
        compute_sudo=False, inverse=None, related=None, store=True, **kw))


class Record:
    _name = 'fixture.record'

    def _compute_issue(self):
        # Reviewed fixture rule: a negative amount is a record-level error.
        return {'active': self.amount < 0, 'message': 'negative amount' if self.amount < 0 else ''}

    _compute_issue._depends = ('amount',)

    def __init__(self):
        self.id, self.amount = 7, -1
        self.env = types.SimpleNamespace(su=False, uid=39, company=types.SimpleNamespace(id=1),
                                         companies=types.SimpleNamespace(ids=[1]))
        self._fields = {
            'amount': field('float'),
            'message': field('char'),
            'active': field('boolean'),
        }
        for name in ('message', 'active'):
            self._fields[name].compute = '_compute_issue'
        self._fields['message'].sc_record_error = {
            'code': 'NEGATIVE_AMOUNT', 'active_field': 'active', 'presentation_owner': 'record_feedback'}
        self.denied, self.reads, self.forbidden_companies, self.forbidden_users = set(), [], set(), set()
        self.empty, self.bad_read_id = False, False

    def __len__(self):
        return 1

    def check_access_rights(self, mode):
        if self.env.uid in self.forbidden_users:
            raise PermissionError('secret user')

    def check_access_rule(self, mode):
        if self.env.company.id in self.forbidden_companies:
            raise PermissionError('secret company')

    def check_field_access_rights(self, mode, names):
        if set(names) & self.denied:
            raise PermissionError('secret field')
        return names

    def read(self, names):
        self.reads.append((self.id, self.env.company.id, self.env.uid, tuple(names)))
        values = self._compute_issue()
        if self.empty:
            values['message'] = ''
        return [dict(values, amount=self.amount, id=999 if self.bad_read_id else self.id)]


REVIEW = RecordErrorReview('NEGATIVE_AMOUNT', 'message', 'active',
    implementation_digest(Record._compute_issue), ('amount',), ('record_feedback',),
    tuple((channel, __file__, hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
          for channel in sorted(REVIEW_PATHS)))
Record._compute_issue._sc_record_error_review = REVIEW


def trees():
    source = dict(type='field', name='message', containerId='native-message', nativeLocator='/form/group/field[1]',
                  occurrenceIndex=0, sourceAuthority={'kind': 'native_view', 'view_id': 42})
    host = dict(type='container', containerId='error-host', componentKey='sc.feedback.message',
                componentConfig={'purpose': 'error', 'contentRef': {'containerId': 'native-message'}},
                modifiers={'invisible': {'kind': 'not', 'expr': {'kind': 'field_truthy', 'field': 'active'}}})
    return [host, copy.deepcopy(source)], [source]


class RecordProofTests(unittest.TestCase):
    def setUp(self):
        self.record = Record()
        self.nodes, self.native = trees()
        Record._compute_issue._sc_record_error_review = REVIEW
        self.actions = []

    def tearDown(self):
        Record._compute_issue._sc_record_error_review = REVIEW

    def run_proof(self):
        return validate_record_errors(self.record, self.nodes, self.native, action_rules=self.actions)

    def rejected(self, code):
        with self.assertRaises(FormConfigurationError) as caught:
            self.run_proof()
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn('secret', str(caught.exception.public_details()))

    def test_legal_source_and_no_tree_mutation(self):
        before = copy.deepcopy(self.nodes)
        self.assertEqual(self.run_proof(), ('error-host',))
        self.assertEqual(self.nodes, before)

    def test_declaration_schema(self):
        original = copy.deepcopy(self.record._fields['message'].sc_record_error)
        for patch in ({'extra': 1}, {'code': ''}, {'active_field': 'missing'}, {'presentation_owner': 'toast'}):
            with self.subTest(patch=patch):
                self.record._fields['message'].sc_record_error = {**original, **patch}
                self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_missing_declaration(self):
        del self.record._fields['message'].sc_record_error
        self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_illegal_content_types(self):
        for kind in ('html', 'many2many', 'one2many', 'integer'):
            with self.subTest(kind=kind):
                self.record._fields['message'].type = kind
                self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_invalid_activation_type(self):
        self.record._fields['active'].type = 'char'
        self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_duplicate_rule_declaration(self):
        self.record._fields['other'] = copy.deepcopy(self.record._fields['message'])
        self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_missing_and_ambiguous_references(self):
        self.nodes[0]['componentConfig']['contentRef']['containerId'] = 'message'
        self.rejected('FEEDBACK_SOURCE_INVALID')
        self.nodes, self.native = trees()
        self.nodes.append(copy.deepcopy(self.nodes[1]))
        self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_forged_provenance_and_ambiguous_native(self):
        self.nodes[1]['sourceAuthority']['view_id'] = 99
        self.rejected('FEEDBACK_SOURCE_INVALID')
        self.nodes, self.native = trees()
        self.native.append(copy.deepcopy(self.native[0]))
        self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_unreviewed_and_stale_review(self):
        Record._compute_issue._sc_record_error_review = None
        self.rejected('FEEDBACK_SOURCE_INVALID')
        Record._compute_issue._sc_record_error_review = replace(REVIEW, implementation_sha256='old')
        self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_rule_binding_mismatch(self):
        for patch in ({'code': 'OTHER'}, {'active_field': 'other'}, {'content_field': 'other'}, {'dependencies': ('other',)}):
            with self.subTest(patch=patch):
                Record._compute_issue._sc_record_error_review = replace(REVIEW, **patch)
                self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_native_compute_mismatch_or_elevation(self):
        self.record._fields['active'].compute = '_other_rule'
        self.rejected('FEEDBACK_SOURCE_INVALID')
        self.record._fields['active'].compute = '_compute_issue'
        self.record._fields['active'].compute_sudo = True
        self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_only_explicit_compiled_activation(self):
        for modifiers in (None, {}, {'invisible': False}, {'invisible': 'not active'},
                          {'invisible': {'kind': 'not', 'expr': {'kind': 'field_truthy', 'field': 'other'}}}):
            with self.subTest(modifiers=modifiers):
                self.nodes[0]['modifiers'] = modifiers
                self.rejected('FEEDBACK_CONDITION_INVALID')

    def test_active_inactive_and_resolved(self):
        self.assertEqual(self.run_proof(), ('error-host',))
        self.record.amount = 5
        self.assertEqual(self.run_proof(), ())
        self.record.amount = -5
        self.assertEqual(self.run_proof(), ('error-host',))
        self.assertEqual(len(self.record.reads), 3)

    def test_active_empty_content(self):
        self.record.empty = True
        self.rejected('FEEDBACK_CONTENT_MISSING')

    def test_content_activation_dependency_permissions(self):
        for name in ('message', 'active', 'amount'):
            with self.subTest(name=name):
                self.record.denied = {name}
                self.rejected('FEEDBACK_SOURCE_FORBIDDEN')
        self.assertEqual(self.record.reads, [])

    def test_other_channels_and_incomplete_audit(self):
        for owner in ('field_error', 'error_summary', 'operation_result', 'action_guidance'):
            with self.subTest(owner=owner):
                Record._compute_issue._sc_record_error_review = replace(REVIEW, owners=('record_feedback', owner))
                self.rejected('FEEDBACK_OWNERSHIP_CONFLICT')
        Record._compute_issue._sc_record_error_review = replace(REVIEW, evidence=())
        self.rejected('FEEDBACK_OWNERSHIP_CONFLICT')

    def test_actual_action_guidance_conflict(self):
        self.actions = [{'presentation': {'action_guidance': {'field': 'message'}}}]
        self.rejected('FEEDBACK_OWNERSHIP_CONFLICT')

    def test_stale_or_unavailable_consumer_review(self):
        for evidence in (
            tuple((channel, path, 'old') for channel, path, digest in REVIEW.evidence),
            tuple((channel, '/nonexistent-reviewed-source', digest) for channel, path, digest in REVIEW.evidence),
        ):
            Record._compute_issue._sc_record_error_review = replace(REVIEW, evidence=evidence)
            self.rejected('FEEDBACK_OWNERSHIP_CONFLICT')

    def test_duplicate_hosts(self):
        host = copy.deepcopy(self.nodes[0]); host['containerId'] = 'second'
        self.nodes.append(host)
        self.rejected('FEEDBACK_OWNERSHIP_CONFLICT')
        self.assertEqual(self.record.reads, [])

    def test_hidden_invalid_still_fails(self):
        self.record.amount = 1
        self.nodes[0]['visible'] = False
        self.nodes[0]['componentConfig']['extra'] = True
        self.rejected('FEEDBACK_SOURCE_INVALID')
        self.assertEqual(self.record.reads, [])

    def test_no_cross_record_company_or_user_authorization_cache(self):
        self.assertEqual(self.run_proof(), ('error-host',))
        self.record.id = 8; self.record.amount = 1
        self.assertEqual(self.run_proof(), ())
        self.record.env.company.id = 2; self.record.forbidden_companies.add(2)
        self.rejected('FEEDBACK_SOURCE_FORBIDDEN')
        self.record.forbidden_companies.clear(); self.record.env.uid = 40
        self.record.forbidden_users.add(40)
        self.rejected('FEEDBACK_SOURCE_FORBIDDEN')

    def test_wrong_read_record(self):
        self.record.bad_read_id = True
        self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_context_changed_during_read(self):
        read = self.record.read
        def changed(names):
            values = read(names)
            self.record.env.uid = 99
            return values
        self.record.read = changed
        self.rejected('FEEDBACK_SOURCE_FORBIDDEN')

    def test_config_cannot_supply_review(self):
        self.nodes[0]['componentConfig']['sc_record_error'] = REVIEW
        self.rejected('FEEDBACK_SOURCE_INVALID')

    def test_no_component_does_not_read_record(self):
        self.nodes = self.nodes[1:]
        self.assertEqual(self.run_proof(), ())
        self.assertEqual(self.record.reads, [])

    def test_interaction_still_forbidden(self):
        with self.assertRaisesRegex(FormConfigurationError, 'INTERACTION_FIELD_BODY_FORBIDDEN'):
            assert_field_body_usage({'sc_ui_usage': 'interaction'}, 'field')

    def test_internal_metadata_not_public(self):
        class Base:
            def _valid_field_parameter(self, field, name): return False
            def fields_get(self, **kw):
                return {'message': {'sc_record_error': {'secret': 1}, 'string': 'Message'}}
        stub = types.ModuleType('odoo')
        stub.api = types.SimpleNamespace(model=lambda f: f)
        stub.models = types.SimpleNamespace(AbstractModel=Base)
        old = sys.modules.get('odoo'); sys.modules['odoo'] = stub
        package = types.ModuleType('proof_fixture_package'); package.__path__ = [str(ROOT)]
        sys.modules['proof_fixture_package'] = package
        try:
            spec = importlib.util.spec_from_file_location('proof_fixture_package.model.base_field_presentation', ROOT / 'model/base_field_presentation.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            model = module.BaseFieldPresentation()
            self.assertTrue(model._valid_field_parameter(None, 'sc_record_error'))
            self.assertNotIn('sc_record_error', model.fields_get(attributes=['sc_record_error'])['message'])
        finally:
            for name in list(sys.modules):
                if name.startswith('proof_fixture_package'):
                    del sys.modules[name]
            if old is None: sys.modules.pop('odoo', None)
            else: sys.modules['odoo'] = old


if __name__ == '__main__':
    unittest.main()
