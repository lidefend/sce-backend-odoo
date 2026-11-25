"""Offline protocol and real handler boundary tests; no browser/database."""
import copy
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import test_node_component_validation as fixtures
from core.node_component_capabilities import (
    validate_component_capabilities,
    NODE_CAPABILITIES,
    OPTIONAL_NODE_CAPABILITIES,
)
from core.form_configuration_compiler import FormConfigurationError

CAPS = list(NODE_CAPABILITIES.values())


def contract(keys):
    return {'pageInfo': {'contractVersion': '2.2.0'}, 'layoutContract': {
        'containerTree': [
            {
                'containerId': str(i),
                'type': 'field' if k == 'readable_value' else 'div',
                **({'fieldCode': 'field_%s' % i} if k == 'readable_value' else {}),
                'semanticType': k,
            }
            for i, k in enumerate(keys)
        ]}}


class CapabilityTests(unittest.TestCase):
    def test_matrix(self):
        for keys in ([], ['feedback_message'], ['navigation_anchor'], list(NODE_CAPABILITIES)):
            for supplied in (None, [], CAPS[:1], CAPS[1:], CAPS, True, CAPS[0], {'x': True}, [None]):
                with self.subTest(keys=keys, supplied=supplied):
                    p = {'accepted_contract_versions': ['2.7.x']}
                    if supplied is not None: p['client_contract_capabilities'] = supplied
                    expected = isinstance(supplied, list) and all(NODE_CAPABILITIES[k] in supplied for k in keys)
                    if not keys or expected:
                        validate_component_capabilities(contract(keys), p)
                    else:
                        with self.assertRaises(FormConfigurationError) as exc:
                            validate_component_capabilities(contract(keys), p)
                        self.assertEqual(exc.exception.code, 'COMPONENT_CAPABILITY_REQUIRED')

    def test_empty_tree_does_not_require_unused_capability(self):
        c = contract([])
        validate_component_capabilities(c, {})

    def test_registered_field_behavior_unchanged(self):
        validate_component_capabilities(contract(['readable_value']), {})

    def test_unknown_or_mispositioned_semantic_is_a_contract_defect(self):
        with self.assertRaises(FormConfigurationError) as unknown:
            validate_component_capabilities(contract(['feedback_messsage']), {})
        self.assertEqual(unknown.exception.code, 'NODE_SEMANTIC_UNKNOWN')

        misplaced = contract([])
        misplaced['layoutContract']['containerTree'] = [{
            'containerId': 'node',
            'type': 'div',
            'semanticType': 'readable_value',
        }]
        with self.assertRaises(FormConfigurationError) as context:
            validate_component_capabilities(misplaced, {})
        self.assertEqual(context.exception.code, 'NODE_SEMANTIC_CONTEXT_INVALID')

    def test_ribbon_requires_capability_but_unsupported_node_is_published_for_client_rejection(self):
        with self.assertRaises(FormConfigurationError) as exc:
            validate_component_capabilities(
                contract(['display_ribbon']),
                {'client_contract_capabilities': []},
            )
        self.assertEqual(exc.exception.code, 'COMPONENT_CAPABILITY_REQUIRED')
        validate_component_capabilities(
            contract(['display_ribbon']),
            {'client_contract_capabilities': ['form.display.ribbon.v1']},
        )
        validate_component_capabilities(
            contract(['unsupported_native_node']),
            {'client_contract_capabilities': []},
        )

    def test_draft_feedback_requires_independent_capability(self):
        c = contract(['feedback_message'])
        c['layoutContract']['containerTree'][0]['componentConfig'] = {
            'purpose': 'advisory',
            'contentRef': {'containerId': 'source'},
            'evaluation': {
                'capability': 'form.feedback.draft.v1',
                'visibilityOwner': 'feedback_evaluation',
            },
        }
        with self.assertRaisesRegex(FormConfigurationError, 'COMPONENT_CAPABILITY_REQUIRED'):
            validate_component_capabilities(c, {
                'client_contract_capabilities': ['form.feedback.message.v1'],
            })
        validate_component_capabilities(c, {
            'client_contract_capabilities': [
                'form.feedback.message.v1',
                'form.feedback.draft.v1',
            ],
        })

    def test_unsupported_optional_nodes_do_not_fail_the_page(self):
        c = contract([
            'feedback_message',
            'insight_summary',
            'action_list',
        ])
        c['layoutContract']['containerTree'][1]['children'] = [{
            'containerId': 'nested-optional',
            'semanticType': 'action_list',
        }]
        c['statusContract'] = {'containerStatus': [
            {'containerId': '0'},
            {'containerId': '1'},
            {'containerId': 'nested-optional'},
        ]}
        validate_component_capabilities(c, {
            'client_contract_capabilities': ['form.feedback.message.v1'],
        })
        self.assertEqual(
            [node['semanticType'] for node in c['layoutContract']['containerTree']],
            ['feedback_message'],
        )
        self.assertEqual(c['statusContract']['containerStatus'], [{'containerId': '0'}])

    def test_supported_optional_nodes_remain_when_the_client_declares_them(self):
        c = contract(['insight_summary', 'action_list'])
        validate_component_capabilities(c, {
            'client_contract_capabilities': list(OPTIONAL_NODE_CAPABILITIES.values()),
        })
        self.assertEqual(
            [node['semanticType'] for node in c['layoutContract']['containerTree']],
            ['insight_summary', 'action_list'],
        )


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.NodeValidationTests()
        self.fixture.setUp()

    def handler(self):
        module, handler = self.fixture.handler()
        # Remove capable defaults used only by existing structural regression fixtures.
        handler._params = lambda payload: module._adapters.params_from_payload(payload, handler.params)
        return module, handler

    def test_normal_scene_request_capabilities(self):
        for scene in (False, True):
            module, handler = self.handler()
            handler._scene_contract_source = lambda key: {}
            for caps in ([], CAPS, [], CAPS):
                params = {
                    'client_type': 'web_pc',
                    'client_contract_capabilities': caps,
                    'accepted_contract_versions': ['2.7.x'],
                }
                params.update({'source_type': 'scene_contract', 'scene_key': 'fixture'} if scene else {'model': 'res.partner'})
                with patch.object(module, 'trim_unified_page_contract_v2', side_effect=lambda c, **kw: c) as trim:
                    result = handler.handle(payload={'params': params})
                self.assertEqual(result.ok, bool(caps), result)
                self.assertEqual(trim.call_count, int(bool(caps)))
                if not caps:
                    self.assertEqual(result.code, 409)
                    self.assertEqual(result.error['reason_code'], 'COMPONENT_CAPABILITY_REQUIRED')

    def test_navigation_and_combined_real_paths(self):
        for combined in (False, True):
            self.fixture.setUp()
            feedback = copy.deepcopy(self.fixture.contract['layoutContract']['containerTree'])
            self.fixture.navigation()
            if combined:
                self.fixture.contract['layoutContract']['containerTree'].extend(feedback)
                self.fixture.native.extend(copy.deepcopy(feedback))
            for scene in (False, True):
                module, handler = self.handler()
                handler._scene_contract_source = lambda key: {}
                for caps in ([], CAPS[1:], CAPS):
                    params = {
                        'model': 'res.partner',
                        'client_type': 'web_pc',
                        'client_contract_capabilities': caps,
                        'accepted_contract_versions': ['2.7.x'],
                    }
                    if scene: params.update(source_type='scene_contract', scene_key='fixture')
                    with patch.object(module, 'trim_unified_page_contract_v2', side_effect=lambda c, **kw: c):
                        result = handler.handle({'params': params})
                    self.assertEqual(result.ok, bool(caps) and (not combined or caps == CAPS), result)

    def test_post_seal_injection_is_checked(self):
        module, handler = self.handler()
        self.fixture.contract['layoutContract']['containerTree'] = []
        module._authority.seal_runtime_contract = lambda *a, **kw: contract(['feedback_message'])
        with patch.object(module, 'trim_unified_page_contract_v2', side_effect=lambda c, **kw: c):
            result = handler.handle({'params': {
                'model': 'res.partner',
                'client_type': 'web_pc',
                'accepted_contract_versions': ['2.7.x'],
            }})
        self.assertFalse(result.ok)
        self.assertEqual(result.error['reason_code'], 'COMPONENT_CAPABILITY_REQUIRED')

    def test_legacy_hot_cache_no_reassembly_or_trim(self):
        f = self.fixture
        f.env.company = f.record.env.company
        module, handler = self.handler()
        handler._uses_native_form_source = lambda params: False
        source = {'source_type': 'ui.contract', 'ui_data': {'model': 'res.partner'}, 'ui_meta': {},
            '_assembled_v2': {'cache_version': module.ASSEMBLED_CONTRACT_CACHE_VERSION,
              'client_type': 'wx_mini', 'delivery_profile': 'mobile_compact',
              'limit_params': handler._trim_limit_params({})[0], 'contract': contract([]),
              'source_contract': {}, 'node_validation_contract': contract([]),
              'node_validation_native_tree': []}}
        cache = SimpleNamespace(get_assembled=lambda *a, **kw: source, get=lambda *a, **kw: copy.deepcopy(source))
        with patch.object(module, 'build_projection_cache_key', return_value='fixture'), patch.object(
                module, 'build_projection_source_token', return_value='source'), patch.object(
                module, 'CONTRACT_PROJECTION_HOT_CACHE', cache), patch.object(
                module, 'assemble_unified_page_contract_v2', side_effect=AssertionError('hot reassembly')), patch.object(
                module, 'trim_unified_page_contract_v2', side_effect=AssertionError('hot trim')):
            result = handler.handle({'params': {
                'model': 'res.partner',
                'client_type': 'web_pc',
                'accepted_contract_versions': ['2.7.x'],
            }})
        self.assertTrue(result.ok, result)

    def test_final_boundary_covers_any_success_and_mutated_seal(self):
        module, handler = self.handler()
        for keys in ([], ['feedback_message'], ['navigation_anchor'], list(NODE_CAPABILITIES)):
            handler._handle_contract = lambda *args: module.IntentExecutionResult(ok=True, data=contract(keys))
            result = handler.handle({'params': {
                'client_type': 'web_pc',
                'client_contract_capabilities': [],
                'accepted_contract_versions': ['2.7.x'],
            }})
            self.assertEqual(result.ok, not keys)
            if keys: self.assertEqual(result.error['reason_code'], 'COMPONENT_CAPABILITY_REQUIRED')

    def test_config_failure_precedes_capability_failure(self):
        module, handler = self.handler()
        self.fixture.host['componentConfig']['extra'] = True
        with patch.object(module, 'trim_unified_page_contract_v2', side_effect=AssertionError('must reject before trim')):
            result = handler.handle({'params': {
                'model': 'res.partner',
                'client_type': 'web_pc',
                'accepted_contract_versions': ['2.7.x'],
            }})
        self.assertEqual(result.error['reason_code'], 'FEEDBACK_CONFIG_INVALID')

    def test_trim_cannot_hide_unsupported_component(self):
        module, handler = self.handler()
        with patch.object(module, 'trim_unified_page_contract_v2', side_effect=lambda c, **kw: contract([])) as trim:
            result = handler.handle({'params': {
                'model': 'res.partner',
                'client_type': 'web_pc',
                'accepted_contract_versions': ['2.7.x'],
            }})
        self.assertFalse(result.ok)
        self.assertEqual(trim.call_count, 0)

    def test_cached_pretrim_component_checked_per_request(self):
        f = self.fixture
        f.env.company = f.record.env.company
        module, handler = self.handler()
        handler._uses_native_form_source = lambda params: False
        pretrim = copy.deepcopy(f.contract)
        fixtures.validate_final_nodes(f.env, pretrim, f.native)
        source = {'source_type': 'ui.contract', 'ui_data': {'model': 'res.partner'}, 'ui_meta': {},
            '_assembled_v2': {'cache_version': getattr(self, 'cache_version', module.ASSEMBLED_CONTRACT_CACHE_VERSION),
              'client_type': 'wx_mini', 'delivery_profile': 'mobile_compact',
              'limit_params': handler._trim_limit_params({})[0], 'contract': contract([]),
              'source_contract': {}, 'node_validation_contract': pretrim,
              'node_validation_native_tree': f.native}}
        cache = SimpleNamespace(get_assembled=lambda *a, **kw: source, get=lambda *a, **kw: copy.deepcopy(source),
                                put_generated=lambda k, t, factory: factory())
        for uid, caps in ((39, []), (40, CAPS), (39, [])):
            f.record.env.uid = uid
            with patch.object(module, 'build_projection_cache_key', return_value='fixture'), patch.object(
                    module, 'build_projection_source_token', return_value='source'), patch.object(
                    module, 'CONTRACT_PROJECTION_HOT_CACHE', cache), patch.object(
                    module, 'trim_unified_page_contract_v2', side_effect=lambda c, **kw: c):
                result = handler.handle({'params': {
                    'model': 'res.partner',
                    'client_type': 'web_pc',
                    'client_contract_capabilities': caps,
                    'accepted_contract_versions': ['2.7.x'],
                }})
            self.assertEqual(result.ok, bool(caps), result)
            if not caps: self.assertEqual(result.error['reason_code'], 'COMPONENT_CAPABILITY_REQUIRED')

    def test_old_snapshot_reassembly_still_requires_capabilities(self):
        self.cache_version = 'ui-contract-v2-node-validation-pretrim-v1'
        self.test_cached_pretrim_component_checked_per_request()


if __name__ == '__main__': unittest.main()
