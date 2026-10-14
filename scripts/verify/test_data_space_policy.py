"""Pure decision tests. Real ORM tests own persisted scope enforcement."""
import ast
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = load('addons/smart_core/security/data_space.py', 'data_space_policy_under_test')
capability = load('addons/smart_core/utils/tenant_payload_capability.py', 'data_space_capability_under_test')


class DataSpacePolicyTest(unittest.TestCase):
    def test_customer_default_and_explicit(self):
        for values in ({}, {'data_purpose': 'customer'}):
            policy.validate_customer_registration(values)

    def test_customer_import_rejects_all_other_purposes(self):
        for purpose in ('demo', 'test', '', None, 'unknown'):
            with self.subTest(purpose=purpose), self.assertRaises(ValueError):
                policy.validate_customer_registration({'data_purpose': purpose})

    def test_sudo_of_product_administrator_is_not_maintenance(self):
        for su in (False, True):
            with self.subTest(su=su), self.assertRaises(PermissionError):
                policy.validate_non_customer_creation(uid=51, superuser_id=1, su=su, purpose='demo', tenant_key='demo-a')

    def test_maintenance_requires_superuser_mode(self):
        with self.assertRaises(PermissionError):
            policy.validate_non_customer_creation(uid=1, superuser_id=1, su=False, purpose='test', tenant_key='test-a')

    def test_maintenance_cannot_register_customer_or_unknown(self):
        for purpose in ('customer', '', None, 'unknown'):
            with self.subTest(purpose=purpose), self.assertRaises(ValueError):
                policy.validate_non_customer_creation(uid=1, superuser_id=1, su=True, purpose=purpose, tenant_key='a')

    def test_valid_maintenance_purposes(self):
        for purpose in ('demo', 'test'):
            policy.validate_non_customer_creation(uid=1, superuser_id=1, su=True, purpose=purpose, tenant_key='space-a')

    def test_blank_identity_rejected(self):
        for key in ('', ' ', None):
            with self.subTest(key=key), self.assertRaises(ValueError):
                policy.validate_non_customer_creation(uid=1, superuser_id=1, su=True, purpose='demo', tenant_key=key)

    def test_empty_company_scope_does_not_fall_back(self):
        domain = policy.registration_scope_domain([], ('demo', 'test'))
        self.assertIn(('company_id', 'in', []), domain)
        self.assertIn(('active', '=', True), domain)
        self.assertIn(('data_purpose', 'in', ['demo', 'test']), domain)
        self.assertIn(('company_id.is_platform_bootstrap_company', '=', False), domain)

    def test_company_domain_preserves_exact_authority(self):
        self.assertIn(('company_id', 'in', [4, 8]), policy.registration_scope_domain([4, 8], ('demo', 'test')))

    def test_customer_identity_does_not_receive_demo_or_test(self):
        self.assertEqual(policy.principal_data_purposes(platform_admin=False, non_customer_user=False), ('customer',))

    def test_non_customer_ceiling_is_not_union_with_customer(self):
        for administrator, test_user in ((True, False), (False, True), (True, True)):
            self.assertEqual(policy.principal_data_purposes(platform_admin=administrator, non_customer_user=test_user), ('demo', 'test'))

    def test_production_import_signature_boundary(self):
        # Execute the actual function without importing an Odoo registry. In
        # particular, do not take its registry.in_test_mode() shortcut.
        path = ROOT / 'addons/smart_core/models/tenant_payload_import_batch.py'
        node = next(n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == '_assert_signed_import_boundary')
        namespace = {'os': os, 'AccessError': PermissionError, 'UserError': ValueError,
                     'IMPORTER_GROUP': 'importer', 'maintenance_capability_matches': capability.maintenance_capability_matches}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
        check = namespace['_assert_signed_import_boundary']
        secret = 'a' * 64
        with patch.dict(os.environ, {'SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY': secret}):
            for member, context, denied in [
                (False, {}, True),
                (True, {}, True),
                (True, {'sc_tenant_payload_import': True}, True),
                (True, {'sc_tenant_payload_import': True, 'sc_tenant_payload_maintenance_capability': 'wrong'}, True),
                (True, {'sc_tenant_payload_import': True, 'sc_tenant_payload_maintenance_capability': secret}, False),
            ]:
                env = SimpleNamespace(user=SimpleNamespace(has_group=lambda group: member), context=context,
                                      registry=SimpleNamespace(in_test_mode=lambda: False))
                with self.subTest(member=member, context_keys=list(context), denied=denied):
                    if denied:
                        with self.assertRaises((PermissionError, ValueError)):
                            check(env)
                    else:
                        check(env)


if __name__ == '__main__':
    unittest.main()
