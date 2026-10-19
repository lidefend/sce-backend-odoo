import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[2] / 'addons/smart_core/security/group_assignment.py'
spec = importlib.util.spec_from_file_location('group_assignment', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class GroupAssignmentTests(unittest.TestCase):
    def test_last_role_removes_exclusive_root(self):
        self.assertEqual(m.replace_roles({1, 20}, {20}, set()), {1})

    def test_other_role_and_explicit_capability_remain(self):
        self.assertEqual(m.replace_roles({1, 20, 21, 90}, {20, 21}, {21}), {1, 21, 90})

    def test_unknown_origin_is_not_inferred(self):
        with self.assertRaises(m.GroupAuthorityGap):
            m.verified_roots(None, {1, 20, 90}, {1, 20, 90})

    def test_membership_drift_is_rejected(self):
        state = {'version': 1, 'status': 'tracked', 'roots': [1], 'observed': [1]}
        with self.assertRaises(m.GroupAuthorityGap):
            m.verified_roots(state, {1, 90}, {1})

    def test_definition_drift_is_rejected(self):
        state = {'version': 1, 'status': 'tracked', 'roots': [1], 'observed': [1]}
        with self.assertRaises(m.GroupAuthorityGap):
            m.verified_roots(state, {1}, {1, 90})

    def test_native_explicit_replace_can_establish_origin(self):
        self.assertEqual(m.apply_commands(None, [(6, 0, [1, 90])]), {1, 90})

    def test_incremental_unknown_cannot_establish_origin(self):
        with self.assertRaises(m.GroupAuthorityGap):
            m.apply_commands(None, [(4, 90)])

    def test_incremental_roles_preserve_unmentioned_roots(self):
        self.assertEqual(m.apply_commands({20, 21}, [(3, 20), (4, 22)]), {21, 22})

    def test_undeclared_role_rejected(self):
        with self.assertRaises(m.GroupAuthorityGap):
            m.replace_roles({1, 20}, {20}, {99})

    def test_unsupported_commands_never_look_like_empty_selection(self):
        for commands in (None, False, "invalid", [(0, 0, {})], [(6, 0, [True])], [(6, 0, [-1])], [7]):
            with self.subTest(commands=commands), self.assertRaises(m.GroupAuthorityGap):
                m.apply_commands(set(), commands)
