import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_record_error_proof import Record, REVIEW, trees
from core.node_component_validation import validate_final_nodes
from core.form_configuration_compiler import FormConfigurationError
from core.unified_page_contract_v2_assembler import assemble_unified_page_contract_v2, _fingerprint
from core.field_presentation_usage import assert_field_body_usage
from unittest.mock import patch
from types import SimpleNamespace


class Env:
    def __init__(self, record):
        self.record = record
    def __getitem__(self, model):
        if model != self.record._name: raise KeyError(model)
        return self
    def browse(self, record_id):
        if record_id != self.record.id: raise AssertionError('wrong record')
        return self.record


class NodeValidationTests(unittest.TestCase):
    def setUp(self):
        self.record = Record(); self.env = Env(self.record)
        Record._compute_issue._sc_record_error_review = REVIEW
        rows, self.native = trees()
        self.contract = {'pageInfo': {'model': self.record._name, 'viewType': 'form'},
            'dataContract': {'mainData': {'id': self.record.id}},
            'layoutContract': {'containerTree': rows, 'componentRegistry': {}},
            'statusContract': {'containerStatus': []}, 'actionContract': {'actionRuleList': []}}

    @property
    def host(self): return self.contract['layoutContract']['containerTree'][0]

    def validate(self): validate_final_nodes(self.env, self.contract, self.native)

    def reject(self, code):
        with self.assertRaises(FormConfigurationError) as caught: self.validate()
        self.assertEqual(caught.exception.code, code)

    def test_four_purposes(self):
        for purpose in ('advisory', 'warning', 'error', 'explanation'):
            with self.subTest(purpose=purpose):
                self.host['componentConfig']['purpose'] = purpose
                self.validate()
                self.assertEqual(self.contract['layoutContract']['componentRegistry']['sc.feedback.message'], {'version': '1.0.0'})

    def test_unknown_and_extra_config(self):
        self.host['componentConfig']['purpose'] = 'alert'
        self.reject('FEEDBACK_CONFIG_INVALID')
        self.host['componentConfig']['purpose'] = 'advisory'
        self.host['componentConfig']['html'] = '<b>bad</b>'
        self.reject('FEEDBACK_CONFIG_INVALID')

    def test_inactive_and_empty(self):
        self.host['componentConfig']['purpose'] = 'advisory'
        self.record.empty = True
        self.validate(); self.assertFalse(self.host['visible'])
        self.host.pop('visible'); self.host['componentConfig']['purpose'] = 'warning'
        self.reject('FEEDBACK_CONTENT_MISSING')
        self.record.amount = 1
        self.validate(); self.assertFalse(self.host['visible'])

    def test_static_only_explanation(self):
        self.host['modifiers'] = {'invisible': False}
        self.host['componentConfig']['purpose'] = 'advisory'
        self.reject('FEEDBACK_CONDITION_INVALID')
        self.host['componentConfig']['purpose'] = 'explanation'
        self.validate()

    def test_undeclared_purpose_and_constant_compound(self):
        del self.host['componentConfig']['purpose']
        self.reject('FEEDBACK_LEGACY_UNDECLARED')
        self.host['componentConfig']['purpose'] = 'advisory'
        self.host['modifiers']['invisible'] = {'kind': 'any', 'exprs': [True, {'kind': 'field_truthy', 'field': 'active'}]}
        self.reject('FEEDBACK_CONDITION_INVALID')

    def test_text_explanation_and_no_action_changes(self):
        source = self.contract['layoutContract']['containerTree'][1]
        source.update(type='text', text='Native explanation')
        source.pop('name')
        self.native = [copy.deepcopy(source)]
        self.host['componentConfig']['purpose'] = 'explanation'
        self.host['modifiers'] = {'invisible': False}
        before = copy.deepcopy(self.contract['actionContract'])
        self.validate()
        self.assertEqual(self.contract['actionContract'], before)
        self.assertFalse(self.record.reads)

    def test_source_and_permissions(self):
        self.host['componentConfig']['purpose'] = 'warning'
        self.record.denied = {'amount'}
        self.reject('FEEDBACK_SOURCE_FORBIDDEN')
        self.record.denied.clear()
        self.host['componentConfig']['contentRef']['containerId'] = 'message'
        self.reject('FEEDBACK_SOURCE_INVALID')

    def test_hidden_invalid(self):
        self.host['visible'] = False
        self.host['componentConfig']['contentRef']['extra'] = 1
        self.reject('FEEDBACK_CONFIG_INVALID')

    def test_error_missing_proof(self):
        del self.record._fields['message'].sc_record_error
        self.reject('FEEDBACK_SOURCE_INVALID')

    def navigation(self):
        label = {'containerId': 'link', 'type': 'div', 'text': 'Details', 'nativeLocator': '/form/link',
                 'occurrenceIndex': 1, 'sourceAuthority': {'kind': 'native_view'},
                 'componentKey': 'sc.navigation.anchor', 'componentConfig': {'targetContainerId': 'details'}}
        target = {'containerId': 'details', 'type': 'group', 'nativeLocator': '/form/group',
                  'occurrenceIndex': 1, 'sourceAuthority': {'kind': 'native_view'}, 'modifiers': {'invisible': False}}
        self.native = copy.deepcopy([label, target]); self.contract['layoutContract']['containerTree'] = [label, target]

    def test_navigation_valid(self):
        self.navigation(); self.validate()

    def test_navigation_missing_duplicate_hidden_external(self):
        for mutation in ('missing', 'duplicate', 'hidden', 'url', 'empty'):
            with self.subTest(mutation=mutation):
                self.navigation(); rows = self.contract['layoutContract']['containerTree']
                if mutation == 'missing': rows.pop()
                if mutation == 'duplicate': rows.append(copy.deepcopy(rows[1]))
                if mutation == 'hidden': rows[1]['visible'] = False
                if mutation == 'url': rows[0]['componentConfig']['href'] = 'https://invalid.example'
                if mutation == 'empty': rows[0]['text'] = ''; self.native[0]['text'] = ''
                self.reject('NAVIGATION_TARGET_INVALID')

    def test_normalizer_mutated_source(self):
        self.contract['layoutContract']['containerTree'][1]['name'] = 'amount'
        self.reject('FEEDBACK_SOURCE_INVALID')

    def test_real_assembler_occurrence_admission_and_scope_reset(self):
        locator, occurrence = '/form/group/field[1]', 1
        field_id = 'field.message.occ.' + _fingerprint({'locator': locator, 'occurrence': occurrence})
        field = {'type': 'field', 'name': 'message', 'native_locator': locator, 'occurrence_index': occurrence,
                 'source_authority': {'kind': 'native_view'}, 'source_position': 0}
        host = {'type': 'div', 'name': 'feedback', 'componentKey': 'sc.feedback.message',
                'componentConfig': {'purpose': 'advisory', 'contentRef': {'containerId': field_id}},
                'modifiers': {'invisible': {'kind': 'not', 'expr': {'kind': 'field_truthy', 'field': 'active'}}},
                'children': [field]}
        source = {'model': self.record._name, 'view_type': 'form', 'record': {'id': 7},
            'fields': {'message': {'type': 'char', 'name': 'message', 'sc_ui_usage': 'interaction'}},
            'views': {'form': {'layout': [host]}}}
        contract = assemble_unified_page_contract_v2(source, source_type='ui.contract', node_actor_env=self.env)
        self.assertTrue(contract['layoutContract']['componentRegistry'].get('sc.feedback.message'))
        with self.assertRaisesRegex(FormConfigurationError, 'INTERACTION_FIELD_BODY_FORBIDDEN'):
            assert_field_body_usage({'name': 'message', 'sc_ui_usage': 'interaction',
                                    'native_locator': locator, 'occurrence_index': occurrence}, 'outside')
        source['views']['form']['layout'][0]['componentConfig']['extra'] = True
        with self.assertRaisesRegex(FormConfigurationError, 'FEEDBACK_CONFIG_INVALID'):
            assemble_unified_page_contract_v2(source, source_type='ui.contract', node_actor_env=self.env)

    def handler(self):
        from test_ui_contract_v2_boundaries import _load_handler
        module = _load_handler()
        import core.node_component_validation as validator
        sys.modules['odoo.addons.smart_core.core.node_component_validation'] = validator
        import core.node_component_capabilities as capabilities
        sys.modules['odoo.addons.smart_core.core.node_component_capabilities'] = capabilities
        module.FormConfigurationError = FormConfigurationError
        handler = module.UiContractV2Handler(env=self.env)
        # Existing structural tests use a capable caller; negotiation negatives
        # explicitly override/remove this in the capability-specific suite.
        original_params = handler._params
        handler._params = lambda payload: {'client_contract_capabilities': [
            'form.feedback.message.v1', 'form.navigation.anchor.v1'], **original_params(payload)}
        # Keep the real handler return paths, substituting only upstream source
        # construction and sealing transport. Assembler behavior is tested above.
        module.assemble_unified_page_contract_v2 = lambda *a, **kw: copy.deepcopy(self.contract)
        module._authority.seal_runtime_contract = lambda handler, contract, *a, **kw: contract
        handler._normalize_final_layout_contract = lambda contract: None
        handler._ensure_native_layout_widget_status_visible = lambda contract: None
        return module, handler

    def test_handler_normal_rejects_before_trim(self):
        module, handler = self.handler()
        self.host['componentConfig']['extra'] = True
        with patch.object(module, 'trim_unified_page_contract_v2', side_effect=AssertionError('trim before validation')):
            result = handler.handle(payload={'params': {'model': 'res.partner'}})
        self.assertFalse(result.ok)
        self.assertEqual(result.error['reason_code'], 'FEEDBACK_CONFIG_INVALID')

    def test_handler_scene_rejects_before_trim(self):
        module, handler = self.handler()
        self.host['componentConfig']['extra'] = True
        handler._scene_contract_source = lambda key: {}
        with patch.object(module, 'trim_unified_page_contract_v2', side_effect=AssertionError('trim before validation')):
            result = handler.handle(payload={'params': {'source_type': 'scene_contract', 'scene_key': 'fixture'}})
        self.assertFalse(result.ok)
        self.assertEqual(result.error['reason_code'], 'FEEDBACK_CONFIG_INVALID')

    def test_handler_normal_and_scene_success(self):
        for scene in (False, True):
            module, handler = self.handler()
            handler._scene_contract_source = lambda key: {}
            params = {'source_type': 'scene_contract', 'scene_key': 'fixture'} if scene else {'model': 'res.partner'}
            with patch.object(module, 'trim_unified_page_contract_v2', side_effect=lambda c, **kw: c) as trim:
                result = handler.handle(payload={'params': params})
            self.assertTrue(result.ok, result)
            self.assertEqual(trim.call_count, 1)

    def test_final_extension_is_validated(self):
        module, handler = self.handler()
        def finalizer(env, hook, *args):
            if hook != 'smart_core_finalize_unified_page_contract_v2': return None
            contract = copy.deepcopy(args[1])
            contract['layoutContract']['containerTree'][0]['componentConfig']['unknown'] = True
            return contract
        with patch.object(module, 'call_extension_hook_first', side_effect=finalizer), patch.object(
                module, 'trim_unified_page_contract_v2', side_effect=AssertionError('trim before validation')):
            result = handler.handle(payload={'params': {'model': 'res.partner'}})
        self.assertFalse(result.ok)
        self.assertEqual(result.error['reason_code'], 'FEEDBACK_CONFIG_INVALID')

    def test_final_normalizer_hidden_invalid_is_validated(self):
        module, handler = self.handler()
        def normalize(contract):
            node = contract['layoutContract']['containerTree'][0]
            node['visible'] = False
            node['componentConfig']['unknown'] = True
        handler._normalize_final_layout_contract = normalize
        with patch.object(module, 'trim_unified_page_contract_v2', side_effect=AssertionError('must validate hidden node first')):
            result = handler.handle(payload={'params': {'model': 'res.partner'}})
        self.assertFalse(result.ok)
        self.assertEqual(result.error['reason_code'], 'FEEDBACK_CONFIG_INVALID')

    def test_actual_final_normalizer_preserves_valid_proof(self):
        module, handler = self.handler()
        handler._normalize_final_layout_contract = module._projection.normalize_final_layout_contract
        with patch.object(module, 'trim_unified_page_contract_v2', side_effect=lambda c, **kw: c):
            result = handler.handle(payload={'params': {'model': 'res.partner'}})
        self.assertTrue(result.ok, result)

    def test_trim_cannot_leave_dangling_feedback_reference(self):
        module, handler = self.handler()
        def trim(contract, **kwargs):
            contract['layoutContract']['containerTree'] = contract['layoutContract']['containerTree'][:1]
            return contract
        with patch.object(module, 'trim_unified_page_contract_v2', side_effect=trim):
            result = handler.handle(payload={'params': {'model': 'res.partner'}})
        self.assertFalse(result.ok)
        self.assertEqual(result.error['reason_code'], 'FEEDBACK_SOURCE_INVALID')

    def test_error_uses_single_proof_read(self):
        self.validate()
        self.assertEqual(len(self.record.reads), 1)

    def test_cache_revalidates_pretrim_snapshot(self):
        self.env.company = self.record.env.company
        for case in ('valid', 'invalid', 'forbidden'):
            invalid = case == 'invalid'
            self.record.denied = {'amount'} if case == 'forbidden' else set()
            module, handler = self.handler()
            handler._uses_native_form_source = lambda params: False
            pretrim = copy.deepcopy(self.contract)
            if invalid: pretrim['layoutContract']['containerTree'][0]['componentConfig']['unknown'] = True
            source = {'source_type': 'ui.contract', 'ui_data': {'model': 'res.partner'}, 'ui_meta': {},
                '_assembled_v2': {'cache_version': module.ASSEMBLED_CONTRACT_CACHE_VERSION,
                  'client_type': 'wx_mini', 'delivery_profile': 'mobile_compact',
                  'limit_params': handler._trim_limit_params({})[0],
                  'contract': {'layoutContract': {'containerTree': []}},
                  'source_contract': {}, 'node_validation_contract': pretrim,
                  'node_validation_native_tree': self.native}}
            cache = SimpleNamespace(get_assembled=lambda *a, **kw: source, get=lambda *a, **kw: copy.deepcopy(source),
                                    put_generated=lambda key, token, factory: factory())
            with patch.object(module, 'build_projection_cache_key', return_value='fixture'), patch.object(
                module, 'build_projection_source_token', return_value='source'), patch.object(
                module, 'CONTRACT_PROJECTION_HOT_CACHE', cache), patch.object(
                module, 'assemble_unified_page_contract_v2', side_effect=lambda *a, **kw: copy.deepcopy(self.contract)) as assemble, patch.object(
                module, 'trim_unified_page_contract_v2', side_effect=lambda c, **kw: c) as trim:
                result = handler.handle(payload={'params': {'model': 'res.partner'}})
            self.assertEqual(result.ok, case == 'valid', result)
            self.assertEqual(trim.call_count, 1 if case == 'valid' else 0)
            self.assertEqual(assemble.call_count, 1 if case == 'valid' else 0)
            if invalid: self.assertEqual(result.error['reason_code'], 'FEEDBACK_CONFIG_INVALID')
            if case == 'forbidden': self.assertEqual(result.error['reason_code'], 'FEEDBACK_SOURCE_FORBIDDEN')


class NativeSavedFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.record = Record()
        self.record._fields['message'].compute_sudo = True
        self.record._fields['active'].compute = '_native_without_dependency_metadata'
        old_env = self.record.env
        class ActorEnv:
            def __getitem__(self, model):
                if model != 'ir.ui.view': raise AssertionError(model)
                return self
            def sudo(self): return self
            def browse(self, view_id):
                if view_id != 42: raise AssertionError(view_id)
                return SimpleNamespace(model='fixture.record', type='form')
        self.record.env = ActorEnv()
        self.record.env.__dict__.update(old_env.__dict__)
        self.arch = '<form><field name="active"/><div class="alert" invisible="not active"><field name="message"/></div></form>'
        self.record.get_view = lambda **kw: {'id': 42, 'arch': self.arch}
        self.env = Env(self.record)
        source = dict(type='field', name='message', containerId='message',
                      nativeLocator='/form[1]/div[1]/field[1]', occurrenceIndex=1,
                      sourceAuthority={'kind': 'native_view'})
        self.host = dict(type='container', containerId='host', nativeLocator='/form[1]/div[1]',
                         attributes={'invisible': 'not active'}, children=[source], componentKey='sc.feedback.message',
                         componentConfig={'purpose':'advisory', 'contentRef':{'containerId':'message'}},
                         modifiers={'invisible':{'kind':'not','expr':{'kind':'field_truthy','field':'active'}}})
        self.contract = {'pageInfo':{'model':self.record._name,'viewType':'form'},
                         'dataContract':{'mainData':{'id':7},'dataMeta':{'sourceContext':{'formViewId':42}}},
                         'layoutContract':{'containerTree':[self.host]}}
        self.native = copy.deepcopy([self.host])

    def validate(self): validate_final_nodes(self.env, self.contract, self.native)

    def test_native_orm_semantics_and_only_direct_fields(self):
        self.validate()
        self.assertEqual(self.record.reads[-1][-1], ('active', 'message'))
        self.assertNotIn('visible', self.host)
        self.record.amount = 1
        self.validate()
        self.assertFalse(self.host['visible'])

    def test_native_source_and_condition_forgery(self):
        changes = [lambda: self.host.update(nativeLocator='/form[1]/div[2]'),
                   lambda: self.host['modifiers'].update(invisible={'kind':'field_truthy','field':'active'}),
                   lambda: self.host['attributes'].update(invisible='active'),
                   lambda: self.host['children'][0].update(nativeLocator='/form[1]/field[1]'),
                   lambda: setattr(self, 'arch', self.arch.replace('name="message"','name="amount"'))]
        for change in changes:
            self.setUp(); change()
            with self.assertRaises(FormConfigurationError): self.validate()
            self.assertFalse(self.record.reads)

    def test_subview_fields_do_not_authorize_parent(self):
        self.arch = self.arch.replace('<field name="active"/>', '<field name="lines"><tree><field name="active"/></tree></field>')
        with self.assertRaises(FormConfigurationError): self.validate()
        self.assertFalse(self.record.reads)

    def test_acl_rule_field_and_context_boundaries(self):
        changes = [lambda: self.record.denied.add('message'),
                   lambda: self.record.forbidden_users.add(39),
                   lambda: self.record.forbidden_companies.add(1),
                   lambda: setattr(self.record.env, 'su', True),
                   lambda: setattr(self.record, 'bad_read_id', True)]
        for change in changes:
            self.setUp(); change()
            with self.assertRaises(FormConfigurationError) as caught: self.validate()
            self.assertEqual(caught.exception.code, 'FEEDBACK_SOURCE_FORBIDDEN')

    def test_mixed_custom_source_cannot_borrow_native_authority(self):
        custom = copy.deepcopy(self.host)
        custom.update(containerId='custom', children=[])
        custom.pop('nativeLocator')
        self.contract['layoutContract']['containerTree'].append(custom)
        with self.assertRaises(FormConfigurationError): self.validate()
        self.assertFalse(self.record.reads)

    def test_text_and_relation_condition(self):
        self.record._fields['active'].type = 'many2many'
        self.arch = self.arch.replace('<field name="message"/>', 'Native message')
        source = self.host['children'][0]
        source.update(type='text', text='Native message', nativeLocator='/form[1]/div[1]/text[1]')
        source.pop('name')
        self.native = copy.deepcopy([self.host])
        self.record.read = lambda names: [{'id':7, 'active':[]}]
        self.validate()
        self.assertFalse(self.host['visible'])
        self.host.pop('visible')
        self.record.read = lambda names: [{'id':7, 'active':[15]}]
        self.validate()
        self.assertNotIn('visible', self.host)

    def test_group_restricted_host_ancestor_and_source(self):
        for tag in ('<form', '<div', '<field name="message"'):
            self.setUp()
            self.arch = self.arch.replace(tag, tag + ' groups="fixture.restricted"', 1)
            with self.assertRaises(FormConfigurationError) as caught: self.validate()
            self.assertEqual(caught.exception.code, 'FEEDBACK_SOURCE_FORBIDDEN')
            self.assertFalse(self.record.reads)

    def test_other_native_alert_cannot_supply_content(self):
        self.arch = self.arch.replace('</form>', '<div class="alert" invisible="not active"><field name="message"/></div></form>')
        source = self.host['children'][0]
        source['nativeLocator'] = '/form[1]/div[2]/field[1]'
        self.native = copy.deepcopy([self.host])
        with self.assertRaises(FormConfigurationError): self.validate()
        self.assertFalse(self.record.reads)


if __name__ == '__main__': unittest.main()
