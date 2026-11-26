import importlib.util
from copy import deepcopy
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'business_capability_authorization',
    ROOT / 'addons/smart_construction_core/services/business_capability_authorization.py',
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def capability(key='project.record.read', **changes):
    row = {
        'key': key, 'identity_kind': 'business_capability', 'business_capability': True,
        'status': 'ga', 'visible': True,
        'authorization': {
            'version': m.VERSION, 'state': 'verified', 'composable': True,
            'operations': ['read'], 'native_groups': ['fixture.group_read'],
            'native_group_edges': {'fixture.group_read': ['base.group_user']},
            'native_model_access': {'project.project': ['read']},
            'dependencies': [], 'exclusions': [], 'verification_refs': ['fixture-only'],
            'scope_policy': 'company_and_record_rules', 'sensitive': False,
        },
    }
    row['authorization'].update(changes)
    return row


class BusinessCapabilityAuthorizationTests(unittest.TestCase):
    def test_navigation_prerequisites_never_become_grants(self):
        row = capability()
        del row['authorization']
        row.update(required_groups=['fixture.group_admin'], access_action='fixture.action')
        self.assertEqual(m.composition_surface(row)['reason_code'], 'AUTHORIZATION_UNDECLARED')
        with self.assertRaises(m.CapabilityCompositionError):
            m.resolve_composition([row], [row['key']])

    def test_public_contract_hides_execution_mapping(self):
        surface = m.composition_surface(capability())
        self.assertTrue(surface['composable'])
        self.assertEqual(set(surface), {'contract_version', 'composable', 'reason_code', 'operations'})

    def test_fixed_standard_role_does_not_qualify_custom_roles(self):
        row = capability()
        row['required_roles'] = ['pm']
        self.assertEqual(m.composition_surface(row)['reason_code'], 'FIXED_ROLE_DEPENDENCY')

    def test_unverified_or_malformed_mapping_is_not_composable(self):
        for changes in ({'state': 'draft'}, {'version': 'v0'}, {'operations': []},
                        {'operations': ['execute_anything']}, {'native_groups': []},
                        {'verification_refs': []}, {'dependencies': 'project.read'},
                        {'scope_policy': 'all_companies'}, {'composable': 'true'},
                        {'sensitive': 0}):
            with self.subTest(changes=changes):
                self.assertFalse(m.composition_surface(capability(**changes))['composable'])

    def test_approval_and_sensitive_operations_require_separate_authority(self):
        for changes in ({'sensitive': True}, {'operations': ['approve']}):
            self.assertEqual(m.composition_surface(capability(**changes))['reason_code'],
                             'SEPARATE_AUTHORIZATION_REQUIRED')

    def test_native_qualification_boundary_must_be_complete_and_typed(self):
        for changes in ({'native_group_edges': {}}, {'native_group_edges': []},
                        {'native_group_edges': {'other.group': []}},
                        {'native_group_edges': {'fixture.group_read': 'base.group_user'}},
                        {'native_model_access': {}}, {'native_model_access': []},
                        {'native_model_access': {'project.project': ['approve']}},
                        {'native_model_access': {'project.project': ['read', 'read']}},
                        {'native_model_access': {'project.project': []}}):
            with self.subTest(changes=changes):
                self.assertFalse(m.composition_surface(capability(**changes))['composable'])

    def test_aliases_and_unreleased_capabilities_are_rejected(self):
        for changes in ({'identity_kind': 'entry_compatibility_alias'}, {'status': 'deprecated'},
                        {'status': 'beta'}, {'visible': False}, {'business_capability': False}):
            row = capability()
            row.update(changes)
            self.assertFalse(m.composition_surface(row)['composable'])

    def test_shared_dependency_is_resolved_once_without_mutation(self):
        a = capability('project.record.read')
        b = capability('project.record.write', dependencies=[a['key']])
        c = capability('project.record.submit', dependencies=[a['key']])
        catalog = [a, b, c]
        before = deepcopy(catalog)
        self.assertEqual(m.resolve_composition(catalog, [c['key'], b['key']]), sorted(x['key'] for x in catalog))
        self.assertEqual(catalog, before)

    def test_missing_or_unqualified_dependency_rejects_entire_selection(self):
        a = capability(dependencies=['project.other.read'])
        for catalog in ([a], [a, capability('project.other.read', state='draft')]):
            with self.assertRaises(m.CapabilityCompositionError):
                m.resolve_composition(catalog, [a['key']])

    def test_dependency_cycle_is_rejected(self):
        a = capability(dependencies=['project.other.read'])
        b = capability('project.other.read', dependencies=[a['key']])
        with self.assertRaisesRegex(m.CapabilityCompositionError, 'CYCLE'):
            m.resolve_composition([a, b], [a['key']])

    def test_exclusion_in_transitive_closure_is_rejected(self):
        a = capability(dependencies=['project.other.read'])
        b = capability('project.other.read', exclusions=[a['key']])
        with self.assertRaisesRegex(m.CapabilityCompositionError, 'CONFLICT'):
            m.resolve_composition([a, b], [a['key']])

    def test_invalid_selection_and_duplicate_catalog_rejected(self):
        a = capability()
        for selected in (None, 'project.record.read', [True], [a['key'], a['key']], ['unknown']):
            with self.subTest(selected=selected), self.assertRaises(m.CapabilityCompositionError):
                m.resolve_composition([a], selected)
        with self.assertRaisesRegex(m.CapabilityCompositionError, 'CATALOG'):
            m.resolve_composition([a, a], [a['key']])

    def test_empty_selection_grants_nothing(self):
        self.assertEqual(m.resolve_composition([capability()], []), [])
