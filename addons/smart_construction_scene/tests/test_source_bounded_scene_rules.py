"""Scene-owned source-bounded rule coverage on the installed native rule."""
import json
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'sc_gate', 'source_bounded_data_space_rules')
class TestSourceBoundedSceneRules(TransactionCase):
    def test_declared_scene_rules_carry_company_and_purpose_authority(self):
        declarations = Path(__file__).resolve().parents[3] / 'scripts/verify/data_scope_declarations.json'
        entries = [entry for entry in json.loads(declarations.read_text())['source_bounded']
                   if entry['file'].startswith('addons/smart_construction_scene/')]
        self.assertTrue(entries, 'Scene source-bounded declarations must be covered')
        for entry in entries:
            with self.subTest(model=entry['model'], rule=entry['rule']):
                rule = self.env.ref('smart_construction_scene.' + entry['rule'])
                self.assertEqual(rule.model_id.model, entry['model'])
                self.assertTrue(getattr(rule, 'global'))
                self.assertIn("('{0}', 'in', company_ids)".format(entry['anchor']), rule.domain_force)
                self.assertIn("('{0}', 'in', user._sc_data_company_ids())".format(entry['anchor']), rule.domain_force)
