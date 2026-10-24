"""Offline native parser -> model declaration -> real assembler. No database IDs."""
import ast
import copy
import json
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from test_native_view_parser_surfaces import _TreeFormParserProbe, _parse_test_xml
from test_record_error_proof import Record, field
from core.native_advisory import project
from core.unified_page_contract_v2_assembler import assemble_unified_page_contract_v2
from core.node_component_validation import validate_final_nodes, walk
from core.node_component_capabilities import validate_component_capabilities
from core.field_presentation_usage import assert_field_body_usage, field_presentation_usage
from core.form_configuration_compiler import FormConfigurationError

NAME = 'processing_advisory'
LOCATOR = '/form[1]/sheet[1]/div[1]/field[1]'
BINDING = {'purpose': 'advisory', 'occurrences': [{'view_xmlid': 'fixture.team_form',
    'native_locator': LOCATOR, 'occurrence_index': 1}]}
# Synthetic offline identities only, never presented as existing Odoo records.
VIEW = 101
RECORD = 201


class AdvisoryRecord(Record):
    _name = 'sc.team.loan.deduction.workspace'

    def __init__(self):
        super().__init__()
        self.id = RECORD
        self.business_date, self.note = False, False
        self._fields = {NAME: field('char', sc_ui_usage='interaction', sc_feedback_usage=copy.deepcopy(BINDING)),
                        'business_date': field('date'), 'note': field('text')}
        self._fields[NAME].compute = '_compute_advisory'

    def _compute_advisory(self):
        # Execute the actual source compute body against in-memory values only.
        path = ROOT.parent / 'smart_construction_core/models/support/team_loan_deduction_workspace.py'
        tree = ast.parse(path.read_text())
        method = next(n for c in tree.body if isinstance(c, ast.ClassDef) for n in c.body
                      if isinstance(n, ast.FunctionDef) and n.name == '_compute_processing_advisory')
        method.decorator_list = []
        scope = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(path), 'exec'), scope)
        scope[method.name]([self])
        return getattr(self, NAME)
    _compute_advisory._depends = ('business_date', 'note')

    def read(self, names):
        self.reads.append(tuple(names))
        self._compute_advisory()
        return [dict(id=self.id, **{n: getattr(self, n) for n in names})]


class Env:
    def __init__(self, record): self.record = record
    def __getitem__(self, model):
        if model != self.record._name: raise KeyError(model)
        return self.record
    def ref(self, xmlid, raise_if_not_found=False):
        if xmlid != 'fixture.team_form': return None
        return types.SimpleNamespace(_name='ir.ui.view', model=self.record._name, type='form', id=VIEW)


AdvisoryRecord.browse = lambda self, rid: self if rid == self.id else None


class NativeAdvisoryTests(unittest.TestCase):
    def setUp(self):
        self.record = AdvisoryRecord(); self.env = Env(self.record)
        path = ROOT.parent / 'smart_construction_core/views/support/team_loan_deduction_workspace_views.xml'
        self.arch = ET.tostring(ET.parse(path).find('.//form'), encoding='unicode')
        self.meta = {NAME: {'type': 'char', 'string': '办理提示', 'sc_ui_usage': 'interaction'},
                     'business_date': {'type': 'date'}, 'note': {'type': 'text'},
                     'project_id': {'type': 'many2one', 'relation': 'project.project'},
                     'partner_id': {'type': 'many2one', 'relation': 'res.partner'}}
        self.layout = _TreeFormParserProbe()._extract_form_layout_dom(_parse_test_xml(self.arch), self.meta)
        self.source = {'model': self.record._name, 'view_type': 'form', 'view_id': VIEW,
                       'record': {'id': RECORD}, 'fields': self.meta,
                       'nativeFormProjection': {'layout': self.layout, 'fieldDescriptors': self.meta},
                       'views': {'form': {'layout': self.layout}}}

    @property
    def host(self): return self.layout[1]['children'][2]
    @property
    def binding(self): return self.record._fields[NAME].sc_feedback_usage
    def assemble(self):
        return assemble_unified_page_contract_v2(self.source, source_type='ui.contract', node_actor_env=self.env)
    def rejects(self, code):
        with self.assertRaisesRegex(FormConfigurationError, code): self.assemble()

    def test_parser_to_final_four_cases(self):
        before = copy.deepcopy(self.source)
        for date, note in [(False, False), ('2026-10-23', False), (False, '说明'), ('2026-10-23', '说明')]:
            self.record.business_date, self.record.note = date, note
            result = self.assemble()
            rows = list(walk(result['layoutContract']['containerTree']))
            hosts = [n for n, _ in rows if n.get('componentKey') == 'sc.feedback.message']
            self.assertEqual(len(hosts), 1)
            host = hosts[0]
            self.assertEqual(host['componentConfig']['purpose'], 'advisory')
            self.assertEqual(host['modifiers'], self.host['modifiers'])
            self.assertNotIn('componentKey', host['attributes'])
            ref = host['componentConfig']['contentRef']['containerId']
            sources = [n for n, _ in rows if n.get('containerId') == ref]
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0]['nativeLocator'], LOCATOR)
            self.assertEqual(host['children'], sources)
            native = copy.deepcopy(result['layoutContract']['containerTree'])
            validate_final_nodes(self.env, result, native)
            # The validator only tightens visibility; visible nodes retain the
            # native default rather than acquiring a new `visible=True` flag.
            if date and note:
                self.assertIs(host['visible'], False)
            else:
                self.assertNotEqual(host.get('visible'), False)
            with self.assertRaisesRegex(FormConfigurationError, 'COMPONENT_CAPABILITY_REQUIRED'):
                validate_component_capabilities(result, {})
            validate_component_capabilities(result, {'client_contract_capabilities': ['form.feedback.message.v1']})
            self.assertNotIn('sc_feedback_usage', json.dumps(result))
        self.assertEqual(self.source, before)

    def test_reviewed_compute_declares_independent_draft_capability(self):
        review = {
            'purpose': 'advisory',
            'inputs': [
                {'field': 'business_date', 'type': 'date'},
                {'field': 'note', 'type': 'text'},
            ],
        }
        function = AdvisoryRecord._compute_advisory
        function._sc_feedback_evaluation_review = review
        self.addCleanup(lambda: delattr(function, '_sc_feedback_evaluation_review'))
        result = self.assemble()
        host = next(
            node for node, _path in walk(result['layoutContract']['containerTree'])
            if node.get('componentKey') == 'sc.feedback.message'
        )
        self.assertEqual(host['componentConfig']['evaluation'], {
            'capability': 'form.feedback.draft.v1',
            'visibilityOwner': 'feedback_evaluation',
        })
        with self.assertRaisesRegex(FormConfigurationError, 'COMPONENT_CAPABILITY_REQUIRED'):
            validate_component_capabilities(result, {
                'client_contract_capabilities': ['form.feedback.message.v1'],
            })
        validate_component_capabilities(result, {
            'client_contract_capabilities': [
                'form.feedback.message.v1',
                'form.feedback.draft.v1',
            ],
        })

    def test_unknown_purpose_properties_and_empty(self):
        for value in ({**BINDING, 'purpose': 'warning'}, {**BINDING, 'extra': True},
                      {**BINDING, 'occurrences': []}, {}, 'advisory'):
            with self.subTest(value=value):
                self.record._fields[NAME].sc_feedback_usage = value
                self.rejects('FEEDBACK_CONFIG_INVALID')

    def test_duplicate_and_bad_bindings(self):
        for changes in ({'native_locator': '//field'}, {'occurrence_index': True},
                        {'occurrence_index': 0}, {'view_xmlid': ''}, {'extra': 1}):
            with self.subTest(changes=changes):
                self.record._fields[NAME].sc_feedback_usage = copy.deepcopy(BINDING)
                self.binding['occurrences'][0].update(changes)
                self.rejects('FEEDBACK_CONFIG_INVALID')
        self.record._fields[NAME].sc_feedback_usage = copy.deepcopy(BINDING)
        self.binding['occurrences'] *= 2
        self.rejects('FEEDBACK_CONFIG_INVALID')

    def test_wrong_view_locator_occurrence(self):
        self.source['view_id'] = VIEW + 1
        self.rejects('INTERACTION_FIELD_BODY_FORBIDDEN')
        self.source['view_id'] = VIEW
        for change in ({'native_locator': LOCATOR.replace('field[1]', 'field[2]')}, {'occurrence_index': 2}, {'view_xmlid': 'fixture.missing'}):
            self.record._fields[NAME].sc_feedback_usage = copy.deepcopy(BINDING)
            self.binding['occurrences'][0].update(change)
            self.rejects('FEEDBACK_SOURCE_INVALID')

    def test_same_name_different_occurrence_not_admitted(self):
        other = copy.deepcopy(self.host['children'][0])
        other['native_locator'] = '/form[1]/sheet[1]/field[1]'
        other['occurrence_index'] = 2
        self.layout[1]['children'].append(other)
        self.rejects('INTERACTION_FIELD_BODY_FORBIDDEN')

    def test_ambiguous_source(self):
        self.layout[1]['children'].append(copy.deepcopy(self.host))
        self.rejects('FEEDBACK_SOURCE_INVALID')

    def test_raw_mismatch_missing_illegal_and_hidden(self):
        original = copy.deepcopy(self.host)
        for mutation in ('raw', 'expr', 'missing', 'string', 'hidden', 'attributes_type', 'modifiers_type'):
            self.layout[1]['children'][2] = copy.deepcopy(original)
            if mutation == 'raw': self.host['modifiers']['invisible']['raw'] = 'not note'
            if mutation == 'expr': self.host['modifiers']['invisible']['expr']['field'] = 'note'
            if mutation == 'missing': self.host.pop('modifiers')
            if mutation == 'string': self.host['modifiers']['invisible'] = 'not processing_advisory'
            if mutation == 'attributes_type': self.host['attributes'] = 'invalid'
            if mutation == 'modifiers_type': self.host['modifiers'] = ['invalid']
            if mutation == 'hidden':
                self.host['visible'] = False
                self.host['modifiers']['invisible']['extra'] = True
            with self.subTest(mutation=mutation): self.rejects('FEEDBACK_CONDITION_INVALID')

    def test_permission_and_missing_record(self):
        for name in (NAME, 'note'):
            self.record.denied = {name}
            self.rejects('FEEDBACK_SOURCE_FORBIDDEN')
        self.record.denied.clear()
        self.source.pop('record')
        self.rejects('FEEDBACK_SOURCE_INVALID')

    def test_unauthorized_and_scope_restoration(self):
        self.assemble()
        with self.assertRaisesRegex(FormConfigurationError, 'INTERACTION_FIELD_BODY_FORBIDDEN'):
            assert_field_body_usage({'name': NAME, 'sc_ui_usage': 'interaction', 'native_locator': LOCATOR, 'occurrence_index': 1}, 'outside')
        del self.record._fields[NAME].sc_feedback_usage
        self.rejects('INTERACTION_FIELD_BODY_FORBIDDEN')

    def test_failure_also_restores_scope(self):
        self.record.denied = {NAME}
        self.rejects('FEEDBACK_SOURCE_FORBIDDEN')
        with self.assertRaisesRegex(FormConfigurationError, 'INTERACTION_FIELD_BODY_FORBIDDEN'):
            assert_field_body_usage({'name': NAME, 'sc_ui_usage': 'interaction', 'native_locator': LOCATOR, 'occurrence_index': 1}, 'outside')

    def test_nonform_and_page_metadata_cannot_authorize(self):
        other = {'model': self.record._name, 'view_type': 'tree'}
        self.assertIs(project(other, self.env), other)
        del self.record._fields[NAME].sc_feedback_usage
        self.meta[NAME]['sc_feedback_usage'] = copy.deepcopy(BINDING)
        self.rejects('INTERACTION_FIELD_BODY_FORBIDDEN')

    def test_source_provenance_and_ownership_conflict(self):
        self.host['children'][0]['source_authority'] = {'model': 'other.model'}
        self.rejects('FEEDBACK_SOURCE_INVALID')
        self.host['children'][0].pop('source_authority')
        self.host['componentKey'] = 'sc.feedback.message'
        self.rejects('FEEDBACK_OWNERSHIP_CONFLICT')

    def test_final_validation_rechecks_binding_and_condition(self):
        result = self.assemble()
        originals = copy.deepcopy(result['layoutContract']['containerTree'])
        host = next(n for n, _ in walk(result['layoutContract']['containerTree']) if n.get('componentKey') == 'sc.feedback.message')
        host['modifiers']['invisible']['raw'] = 'not note'
        with self.assertRaisesRegex(FormConfigurationError, 'FEEDBACK_CONDITION_INVALID'):
            validate_final_nodes(self.env, result, originals)
        result = self.assemble()
        self.binding['occurrences'][0]['occurrence_index'] = 2
        with self.assertRaisesRegex(FormConfigurationError, 'FEEDBACK_SOURCE_INVALID'):
            validate_final_nodes(self.env, result, originals)

    def test_old_xml_without_declaration_is_identical(self):
        del self.record._fields[NAME].sc_feedback_usage
        self.meta[NAME]['sc_ui_usage'] = 'fact'
        self.assertEqual(self.assemble(), assemble_unified_page_contract_v2(self.source, source_type='ui.contract'))

    def test_fields_get_does_not_leak(self):
        path = ROOT / 'model/base_field_presentation.py'
        cls = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef))
        class Base:
            _fields = {NAME: self.record._fields[NAME]}
            def fields_get(self, **kwargs): return {NAME: {'sc_feedback_usage': copy.deepcopy(BINDING)}}
            def _valid_field_parameter(self, field, name): return False
        scope = {'models': types.SimpleNamespace(AbstractModel=Base), 'api': types.SimpleNamespace(model=lambda f: f), 'field_presentation_usage': field_presentation_usage}
        exec(compile(ast.Module(body=[cls], type_ignores=[]), str(path), 'exec'), scope)
        obj = scope[cls.name]()
        self.assertTrue(obj._valid_field_parameter(None, 'sc_feedback_usage'))
        self.assertNotIn('sc_feedback_usage', json.dumps(obj.fields_get()))
        self.assertNotIn('sc_feedback_usage', json.dumps(obj.fields_get(attributes=['sc_feedback_usage'])))


if __name__ == '__main__': unittest.main()
