import unittest
from scripts.verify.system_permission_role_inventory import expression, apply_commands, closure, catalog_hits, inventory, ROOT, python_write_candidates, write_inventory


class InventoryTests(unittest.TestCase):
    def test_reverse_group_membership_is_included(self):
        rows = python_write_candidates("group.sudo().write({'users': [(6, 0, ids)]})")
        self.assertEqual([row['field'] for row in rows], ['users'])

    def test_assignment_and_staged_values(self):
        rows = python_write_candidates("user.groups_id = commands\nvals['implied_ids'] = links")
        self.assertEqual([row['field'] for row in rows], ['groups_id', 'implied_ids'])

    def test_read_and_comment_not_assignment(self):
        self.assertEqual(python_write_candidates("x = user.groups_id\n# user.groups_id = []"), [])

    def test_dictionary_is_only_candidate(self):
        rows = python_write_candidates("snapshot = {'groups_id': ids}")
        self.assertEqual(rows[0]['kind'], 'dictionary_candidate')

    def test_invalid_python_not_silently_skipped(self):
        with self.assertRaises(SyntaxError):
            python_write_candidates('user.groups_id =')

    def test_xml_reverse_write_and_unrelated_model(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'addons').mkdir()
            (root / 'addons' / 'empty.xml').write_text('')
            (root / 'addons' / 'groups.xml').write_text('<odoo><record id="g" model="res.groups"><field name="users" eval="[]"/></record><record id="v" model="ir.ui.view"><field name="groups_id" eval="[]"/></record></odoo>')
            report = write_inventory(root)
            self.assertEqual(report['status'], 'candidate_inventory_complete')
            self.assertIn('addons/empty.xml', report['inputs'])
            self.assertEqual(len(report['candidates']), 1)
            self.assertEqual(report['candidates'][0]['field'], 'users')
            self.assertEqual(report['authorization_verdict'], 'not_evaluated')

    def test_no_expression_execution(self):
        with self.assertRaises(ValueError):
            expression("__import__('os').system('false')", 'x')

    def test_link_replace_unlink(self):
        commands = expression("[(4, ref('one')), (6, 0, [ref('two'), ref('external.three')]), (3, ref('two'))]", 'x')
        self.assertEqual(apply_commands({'old'}, commands), {'external.three'})

    def test_clear(self):
        self.assertEqual(apply_commands({'x'}, [[5, 0, 0]]), set())

    def test_unknown_command_fails(self):
        with self.assertRaises(ValueError):
            apply_commands({'x'}, [[0, 0, {}]])

    def test_cycle_is_bounded_and_external_is_unknown(self):
        found, unknown = closure({'a': {'implied': {'b'}}, 'b': {'implied': {'a', 'base.user'}}}, 'a')
        self.assertEqual(found, {'a', 'b', 'base.user'})
        self.assertEqual(unknown, {'base.user'})

    def test_inherited_catalog_binding_is_not_missing(self):
        groups, _ = closure({'a': {'implied': {'b'}}, 'b': {'implied': set()}}, 'a')
        result = catalog_hits({'default_roles': [{'role_code': 'reader', 'group_xmlids': ['b']}]}, groups)
        self.assertEqual(result['explicit'], ['reader'])

    def test_unknown_role_does_not_gain_owner(self):
        result = catalog_hits({'default_roles': [{'role_code': 'owner', 'group_xmlids': ['other']}]}, {'new'})
        self.assertEqual(result['explicit'], [])

    def test_repository_inventory_is_not_runtime_pass(self):
        result = inventory(ROOT)
        self.assertGreater(result['summary']['assignable_groups'], 0)
        self.assertEqual(result['authorization_verdict'], 'not_evaluated')
        self.assertFalse(result['parse_issues'])
        self.assertTrue(all(row['runtime_identity'] == 'not_run' for row in result['roles']))


if __name__ == '__main__':
    unittest.main()
