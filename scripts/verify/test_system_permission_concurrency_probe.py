"""Probe safety prerequisites, not evidence that database races passed."""
import unittest
from scripts.verify.system_permission_concurrency_probe import FILES, CONFIRMATION, validate_identity, validate_mode


class TestConcurrencyProbeIdentity(unittest.TestCase):
    def test_only_declared_incremental_modes_allowed(self):
        self.assertEqual(validate_mode('baseline'), 'baseline')
        self.assertEqual(validate_mode('editor_only'), 'editor_only')
        for mode in ('', 'all', 'full', None):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                validate_mode(mode)

    def args(self):
        hashes = {name: 'a' * 64 for name in FILES}
        return ['sc_contract_lifecycle', '^sc_contract_lifecycle$', CONFIRMATION, False, hashes, dict(hashes)]

    def test_exact_isolated_identity_allowed(self):
        validate_identity(*self.args())

    def test_persistent_demo_and_other_databases_rejected(self):
        for database in ('sc_dev_demo', 'sc_demo', 'sc_contract_snapshot', '', 'sc_contract_lifecycle_other'):
            with self.subTest(database=database), self.assertRaises(ValueError):
                args = self.args()
                args[0] = database
                validate_identity(*args)

    def test_unbound_filter_rejected(self):
        for dbfilter in ('.*', 'sc_contract_lifecycle', '^sc_.*$', ''):
            with self.subTest(dbfilter=dbfilter), self.assertRaises(ValueError):
                args = self.args()
                args[1] = dbfilter
                validate_identity(*args)

    def test_confirmation_cannot_be_omitted_or_boolean(self):
        for confirmation in (None, '', True, 'true', 'RUN'):
            with self.subTest(confirmation=confirmation), self.assertRaises(ValueError):
                args = self.args()
                args[2] = confirmation
                validate_identity(*args)

    def test_shared_test_cursor_rejected(self):
        args = self.args()
        args[3] = True
        with self.assertRaises(ValueError):
            validate_identity(*args)

    def test_changed_or_missing_source_rejected(self):
        for actual in ({}, {**self.args()[5], FILES[0]: 'b' * 64}):
            with self.subTest(actual=actual), self.assertRaises(ValueError):
                args = self.args()
                args[5] = actual
                validate_identity(*args)

    def test_empty_or_malformed_expected_hashes_rejected(self):
        for hashes in ({}, [], {name: 'not-a-hash' for name in FILES}):
            with self.subTest(hashes=hashes), self.assertRaises(ValueError):
                args = self.args()
                args[4] = args[5] = hashes
                validate_identity(*args)


if __name__ == '__main__':
    unittest.main()
