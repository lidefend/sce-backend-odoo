import unittest
from scripts.verify.system_permission_runtime_observation import observation_plan, validate_witness_uids


class ObservationPlanTests(unittest.TestCase):
    def test_invalid_navigation_witnesses_fail_closed(self):
        for value in ([], [1], [True], ["2"], "[2]", ["$(false)"]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_witness_uids(value)

    def test_navigation_witnesses_are_unique_sorted_integers(self):
        self.assertEqual(validate_witness_uids([7, 3, 7]), [3, 7])

    def test_missing_is_uncovered(self):
        row = observation_plan([{'id': 2, 'xmlids': []}], [])[0]
        self.assertEqual(row['status'], 'uncovered')
        self.assertIsNone(row['selected_uid'])

    def test_superuser_cannot_supply_witness(self):
        row = observation_plan([{'id': 2, 'xmlids': ['m.g']}], [{'id': 1, 'group_ids': [2]}])[0]
        self.assertEqual(row['witness_uids'], [])

    def test_deterministic_existing_witness(self):
        row = observation_plan([{'id': 2, 'xmlids': ['m.g']}], [{'id': 7, 'group_ids': [2]}, {'id': 3, 'group_ids': [2]}, {'id': 4, 'group_ids': [8]}])[0]
        self.assertEqual(row['selected_uid'], 3)
        self.assertEqual(row['witness_uids'], [3, 7])
        self.assertEqual(row['status'], 'observed_membership')

    def test_multiple_roles_remain_separate(self):
        rows = observation_plan([{'id': 2, 'xmlids': []}, {'id': 3, 'xmlids': []}], [{'id': 5, 'group_ids': [2, 3]}])
        self.assertEqual(len(rows), 2)
        self.assertEqual([row['selected_uid'] for row in rows], [5, 5])
