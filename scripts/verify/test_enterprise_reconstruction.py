import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from scripts.dev.enterprise_reconstruction import bootstrap, reference, compare_configuration


class EnterpriseReconstructionTests(unittest.TestCase):
    def test_bootstrap_rejects_persistent_database_before_model_access(self):
        for name in ('sc_dev_demo', 'sc_clean', 'sc_prod', 'sc_test'):
            with self.subTest(name=name), self.assertRaises(AssertionError):
                bootstrap(SimpleNamespace(cr=SimpleNamespace(dbname=name)))

    def test_reference_preserves_relations_without_executing_eval(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            demo = root / 'demo_addons/smart_construction_demo'
            demo.mkdir(parents=True)
            (demo / '__manifest__.py').write_text(repr({'data': ['first.xml', 'second.xml']}))
            (demo / 'first.xml').write_text('''<odoo>
              <record id="d" model="hr.department"><field name="name">Department</field></record>
              <record id="u" model="res.users"><field name="groups_id" eval="must_not_execute()"/></record>
              <record id="p" model="project.project"><field name="name">Not configuration</field></record>
            </odoo>''')
            (demo / 'second.xml').write_text('''<odoo><record id="d" model="hr.department">
              <field name="parent_id" ref="smart_construction_demo.parent"/>
            </record></odoo>''')
            result = reference(root)
            self.assertEqual(len(result['records']), 2)
            department, user = result['records']
            self.assertEqual(department['fields']['name']['text'], 'Department')
            self.assertEqual(department['fields']['parent_id']['ref'], 'smart_construction_demo.parent')
            self.assertEqual(user['fields']['groups_id']['eval'], 'must_not_execute()')
            self.assertEqual(len(result['sources']), 2)

    def test_parity_rejects_wrong_parent_despite_matching_creation_count(self):
        reference_data = {'records': [{'xmlid': 'demo.child', 'model': 'hr.department', 'fields': {
            'name': {'text': 'Child'}, 'parent_id': {'ref': 'demo.parent'}}}]}
        facts = {'hr.department': {'rows': [{'id': 4, 'name': 'Child', 'parent_id': [9, 'Wrong']}],
                                  'external_ids': {'3': 'demo.parent'}},
                 'res.groups': {'rows': [], 'external_ids': {}}}
        progress = {'stages': {'departments': {'records': [{'xmlid': 'demo.child', 'id': 4}]}}}
        result = compare_configuration(reference_data, facts, progress)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['differences'][0]['field'], 'parent_id')

    def test_parity_rejects_extra_inherited_business_authority(self):
        reference_data = {'records': [{'xmlid': 'demo.u', 'model': 'res.users', 'fields': {
            'name': {'text': 'User'}, 'groups_id': {'eval': "[(6, 0, [ref('x.group_sc_role_reader')])]"}}}]}
        facts = {'res.company': {'rows': [], 'external_ids': {'1': 'base.main_company'}},
                 'res.users': {'rows': [{'id': 7, 'name': 'User', 'active': True, 'company_ids': [1], 'groups_id': [2, 3]}]},
                 'res.groups': {'rows': [{'id': 2, 'implied_ids': []}, {'id': 3, 'implied_ids': [4]}],
                                'external_ids': {'2': 'x.group_sc_role_reader'}}}
        progress = {'stages': {'users': {'records': [{'xmlid': 'demo.u', 'id': 7}]}}}
        result = compare_configuration(reference_data, facts, progress)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['differences'], [{'record': 'demo.u', 'field': 'permission_closure',
                                                'expected': [2], 'actual': [2, 3, 4]}])
        facts['res.users']['rows'][0]['groups_id'] = [2]
        result = compare_configuration(reference_data, facts, progress)
        self.assertEqual(result['status'], 'passed')
        self.assertGreater(result['assertions'], 0)

    def test_reference_fingerprint_changes_when_source_changes(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            demo = root / 'demo_addons/smart_construction_demo'
            demo.mkdir(parents=True)
            (demo / '__manifest__.py').write_text(repr({'data': ['source.xml']}))
            source = demo / 'source.xml'
            source.write_text('<odoo><record id="job" model="hr.job"><field name="name">A</field></record></odoo>')
            before = reference(root)
            source.write_text(source.read_text().replace('>A<', '>B<'))
            after = reference(root)
            self.assertNotEqual(before['sources'], after['sources'])
            self.assertEqual(json.loads(json.dumps(after))['records'][0]['fields']['name']['text'], 'B')


if __name__ == '__main__':
    unittest.main()
