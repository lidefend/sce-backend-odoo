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


class MultiSourceAuthorityTests(unittest.TestCase):
    def test_v1_migrates_without_inventing_sources(self):
        self.assertEqual(m.verified_sources({'version': 1, 'status': 'tracked', 'roots': [1, 20]}), {'native': {1, 20}})

    def test_revoke_one_role_preserves_native_and_other_role_overlap(self):
        sources = {'native': {1, 20}, 'role:1': {20, 30}, 'role:2': {30, 40}}
        result = m.replace_source(sources, 'role:1', [])
        self.assertEqual(m.source_union(result), {1, 20, 30, 40})
        result = m.replace_source(result, 'role:2', [])
        self.assertEqual(m.source_union(result), {1, 20})
        self.assertIn('role:1', sources)

    def test_native_noop_replace_does_not_adopt_managed_roots(self):
        sources = {'native': {1}, 'role:1': {20}}
        result = m.apply_native_source_commands(sources, [(6, 0, [1, 20, 30])])
        self.assertEqual(result['native'], {1, 30})
        self.assertEqual(m.source_union(m.replace_source(result, 'role:1', [])), {1, 30})

    def test_explicit_native_add_can_preserve_shared_root(self):
        result = m.apply_native_source_commands({'native': {1}, 'role:1': {20}}, [(4, 20)])
        self.assertEqual(m.source_union(m.replace_source(result, 'role:1', [])), {1, 20})

    def test_native_write_cannot_remove_managed_root(self):
        for commands in ([(6, 0, [1])], [(3, 20)], [(5,)]):
            with self.subTest(commands=commands), self.assertRaises(m.GroupAuthorityGap):
                m.apply_native_source_commands({'native': {1}, 'role:1': {20}}, commands)

    def test_source_drift_is_rejected(self):
        state = {'version': 2, 'status': 'tracked', 'roots': [1, 20], 'observed': [1, 20], 'sources': {'native': [1]}}
        with self.assertRaises(m.GroupAuthorityGap):
            m.verified_roots(state, [1, 20], [1, 20])

    def test_unknown_origin_and_forged_source_values_are_rejected(self):
        for state in ({}, {'version': 2, 'status': 'tracked', 'sources': {'native': [True]}}):
            with self.assertRaises(m.GroupAuthorityGap):
                m.verified_sources(state)
