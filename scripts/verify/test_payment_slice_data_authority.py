"""Caller-authority regression tests; not a substitute for ORM isolation tests."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


class UserError(Exception):
    pass


class AccessError(UserError):
    pass


def load_service():
    odoo = ModuleType('odoo')
    odoo.fields = SimpleNamespace(Date=SimpleNamespace(today=lambda: '2026-10-13'))
    exceptions = ModuleType('odoo.exceptions')
    exceptions.AccessError = AccessError
    exceptions.UserError = UserError
    path = Path(__file__).resolve().parents[2] / 'addons/smart_construction_core/services/payment_slice_entry_service.py'
    spec = importlib.util.spec_from_file_location('payment_slice_data_authority_under_test', path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {'odoo': odoo, 'odoo.exceptions': exceptions}):
        spec.loader.exec_module(module)
    return module.PaymentSliceEntryService


class Record:
    def __init__(self, identifier, **values):
        self.id = identifier
        self.denied = False
        self.checks = []
        self.__dict__.update(values)

    def check_access_rights(self, operation):
        self.checks.append(('acl', operation))
        if self.denied:
            raise AccessError('denied')

    def check_access_rule(self, operation):
        self.checks.append(('rule', operation))
        if self.denied:
            raise AccessError('denied')


class Model:
    def __init__(self, record):
        self.record = record
        self.created = []
        self.deny_create = False
        self.deny_rule = False
        self.deny_search = False

    def browse(self, identifier):
        assert identifier == self.record.id
        return self.record

    def sudo(self, *args):
        raise AssertionError('Business operation elevated its caller')

    def check_access_rights(self, operation):
        if self.deny_create:
            raise AccessError('create ACL denied')

    def search(self, *args, **kwargs):
        if self.deny_search:
            raise AccessError('search denied')
        return self.record

    def create(self, values):
        if self.deny_rule:
            raise AccessError('create rule denied')
        self.created.append(values)
        return Record(99, name='draft test', state='draft', date_request=values['date_request'])


class Environment(dict):
    pass


class PaymentSliceAuthorityTest(unittest.TestCase):
    def setUp(self):
        self.partner = Record(2, display_name='Synthetic partner')
        self.company = SimpleNamespace(currency_id=SimpleNamespace(id=1), partner_id=None)
        self.project = Record(1, partner_id=self.partner, company_id=self.company)
        self.env = Environment({'project.project': Model(self.project), 'res.partner': Model(self.partner), 'payment.request': Model(None)})
        self.env.user = SimpleNamespace(partner_id=None)
        self.env.company = self.company
        self.service = load_service()(self.env)

    def create(self, project=None):
        return self.service.create(project=project or self.project, values={'amount': 12})

    def test_authorized_creation_never_elevates(self):
        result = self.create()
        self.assertEqual(result['payment_request_id'], 99)
        self.assertEqual(self.project.checks, [('acl', 'read'), ('rule', 'read')])
        self.assertEqual(self.partner.checks, [('acl', 'read'), ('rule', 'read')])
        self.assertEqual(len(self.env['payment.request'].created), 1)

    def test_privileged_project_argument_is_rebound_to_caller(self):
        self.project.denied = True
        with self.assertRaises(AccessError):
            self.create(Record(1, partner_id=self.partner, company_id=self.company))
        self.assertEqual(self.env['payment.request'].created, [])

    def test_partner_denial_prevents_write(self):
        self.partner.denied = True
        with self.assertRaises(AccessError):
            self.create()
        self.assertEqual(self.env['payment.request'].created, [])

    def test_missing_create_acl_prevents_partner_resolution(self):
        self.env['payment.request'].deny_create = True
        with self.assertRaises(AccessError):
            self.create()
        self.assertEqual(self.partner.checks, [])
        self.assertEqual(self.env['payment.request'].created, [])

    def test_create_record_rule_denial_does_not_retry_privileged(self):
        self.env['payment.request'].deny_rule = True
        with self.assertRaises(UserError):
            self.create()
        self.assertEqual(self.env['payment.request'].created, [])

    def test_partner_search_uses_caller(self):
        self.project.partner_id = None
        self.assertEqual(self.create()['partner_name'], 'Synthetic partner')

    def test_partner_search_denial_is_not_swallowed(self):
        self.project.partner_id = None
        self.env['res.partner'].deny_search = True
        with self.assertRaises(AccessError):
            self.create()
        self.assertEqual(self.env['payment.request'].created, [])


if __name__ == '__main__':
    unittest.main()
