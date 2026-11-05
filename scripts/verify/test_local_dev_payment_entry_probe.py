import unittest
from scripts.verify.local_dev_payment_entry_probe import missing_layers


class PaymentEntryProbeTests(unittest.TestCase):
    def row(self):
        return dict(published=True, scope={'scenario_key': 'payment.capital', 'scenario_active': True},
                    enabled=True, menu_group_allowed=True, action_group_allowed=True, read_acl=True, route_allowed=True)

    def test_each_layer_reported_independently(self):
        for key, layer in [('published', 'native_publication'), ('enabled', 'company_enablement'),
                           ('read_acl', 'role_authorization'), ('route_allowed', 'runtime_route_authority')]:
            with self.subTest(key=key):
                self.assertEqual(missing_layers({**self.row(), key: False}), [layer])

    def test_missing_binding_never_means_exempt(self):
        self.assertEqual(missing_layers({**self.row(), 'scope': {'location': 'missing'}}), ['scenario_binding'])
        self.assertEqual(missing_layers(self.row()), [])


if __name__ == '__main__':
    unittest.main()
