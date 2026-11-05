import unittest
from unittest.mock import Mock
from scripts.ops.local_dev_payment_entry_configuration import unchanged_boundaries, publish_frozen_snapshot, assert_entry_ready, MENU


class ConfigurationBoundariesTests(unittest.TestCase):
    def test_effective_target_publication_and_non_sudo_route_are_required(self):
        gate = dict(applied=True, reason='OK', platform_db='sc_dev_demo', snapshot_id=12,
                    menu_release_states={MENU: 'released'})
        route = dict(ok=True, data=dict(allowed=True, menu_id=339, action_id=908, model='sc.payment.execution'))
        assert_entry_ready(gate, route, [12], 339, 908)
        for invalid in ({**gate, 'menu_release_states': {}}, {**gate, 'snapshot_id': 11},
                        {**gate, 'applied': False}, {**gate, 'platform_db': 'another_database'},
                        {**gate, 'reason': 'MISSING'}):
            with self.subTest(gate=invalid), self.assertRaises(RuntimeError):
                assert_entry_ready(invalid, route, [12], 339, 908)
        for invalid in ({**route, 'ok': False}, {**route, 'data': {}},
                        {**route, 'data': {**route['data'], 'allowed': False}},
                        {**route, 'data': {**route['data'], 'action_id': 999}}):
            with self.subTest(route=invalid), self.assertRaises(RuntimeError):
                assert_entry_ready(gate, invalid, [12], 339, 908)

    def test_existing_approval_is_not_replayed(self):
        snapshot = Mock(state='approved')
        publish_frozen_snapshot(snapshot)
        snapshot.action_approve.assert_not_called()
        snapshot.action_release.assert_called_once()

    def test_candidate_uses_formal_approval_before_release(self):
        snapshot = Mock(state='candidate')
        snapshot.action_approve.side_effect = lambda: setattr(snapshot, 'state', 'approved')
        publish_frozen_snapshot(snapshot)
        snapshot.action_approve.assert_called_once()
        snapshot.action_release.assert_called_once()

    def test_invalid_state_cannot_publish(self):
        snapshot = Mock(state='superseded')
        with self.assertRaises(RuntimeError):
            publish_frozen_snapshot(snapshot)
        snapshot.action_release.assert_not_called()

    def test_only_publication_and_enablement_may_change(self):
        before = dict(groups=[1], menu_groups=[2], action_groups=[3], exempt=False, bindings=[(4, 'payment.capital')], acl=[5], enabled=False)
        self.assertTrue(unchanged_boundaries(before, {**before, 'enabled': True, 'active_snapshot_ids': [6]}))
        for field in ('groups', 'menu_groups', 'action_groups', 'exempt', 'bindings', 'acl'):
            self.assertFalse(unchanged_boundaries(before, {**before, field: None}), field)


if __name__ == '__main__':
    unittest.main()
