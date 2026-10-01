"""Pure regressions for shared field policy; no ORM or fixture."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('field_policy', ROOT / 'addons/smart_core/utils/contract_governance_form_fields.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class FieldPolicyTests(unittest.TestCase):
    def policies(self, fields, *, project=False, hidden=()):
        return MODULE.build_form_field_policies(
            {'fields': fields, 'field_groups': [{'name': 'advanced', 'fields': list(fields)}]},
            contract_required_fields=[k for k, v in fields.items() if v.get('required')],
            is_project_form=project, project_form_profile={'create_hidden_fields': list(hidden)}, to_bool=bool,
        )

    def test_optional_input_is_not_hidden_by_group(self):
        policy = self.policies({'remarks': {'type': 'text'}})['remarks']
        self.assertIn('create', policy['visible_profiles'])
        self.assertNotIn('create', policy['readonly_profiles'])
        self.assertEqual(policy['group'], 'advanced')

    def test_required_input_retains_create_and_required_authority(self):
        policy = self.policies({'relation': {'type': 'many2one', 'required': True}})['relation']
        self.assertIn('create', policy['visible_profiles'])
        self.assertIn('create', policy['required_profiles'])

    def test_readonly_fact_is_never_made_editable(self):
        policy = self.policies({'total': {'readonly': True}})['total']
        self.assertEqual(policy['readonly_profiles'], ['create', 'edit', 'readonly'])
        self.assertFalse(policy['required_profiles'])

    def test_explicit_create_hidden_policy_is_preserved(self):
        policy = self.policies({'state': {'type': 'selection'}}, project=True, hidden=['state'])['state']
        self.assertNotIn('create', policy['visible_profiles'])
        self.assertIn('create', policy['readonly_profiles'])

if __name__ == '__main__':
    unittest.main()
