import ast
import importlib
import json
import runpy
from pathlib import Path
import sys
import types
import unittest
import tempfile
import xml.etree.ElementTree as ET

from form_structure_contract_seed_generate import (
    ROOT, DEFAULT_OUTPUT, RETIREMENT_DECLARATION,
    apply_declared_retirements, retired_seed_ids,
    main,
)


class NativeGuidanceSeedRetirementTest(unittest.TestCase):
    def test_tender_native_form_retains_unique_fields_without_body_state_or_hint(self):
        root = ET.parse(ROOT / 'addons/smart_construction_core/views/support/tender_views.xml').getroot()
        form = root.find("record[@id='view_tender_doc_purchase_form']/field[@name='arch']/form")
        trace = form.find(".//group[@name='tender_purchase_source_trace']")
        for name in ('legacy_visible_applicant_name', 'legacy_visible_document_state', 'legacy_record_id', 'legacy_source_table', 'legacy_attachment_ref'):
            self.assertEqual(trace.find(f".//field[@name='{name}']").get('readonly'), '1', name)
        self.assertIsNone(trace.find(".//field[@name='active']").get('readonly'))
        attachment = form.find("sheet//field[@name='attachment_ids']")
        self.assertEqual(attachment.get('widget'), 'many2many_binary')
        self.assertIsNone(attachment.get('invisible'))
        self.assertEqual(len(form.findall("header/field[@name='state']")), 1)
        self.assertEqual(form.findall("sheet//field[@name='state']"), [])
        self.assertEqual(form.findall(".//group[@string='办理提示']"), [])

    def test_tender_projection_retirement_applies_on_install_and_upgrade(self):
        pairs = (
            ('view_orchestration_form_section_contract_data.xml', 'business_config_contract_tender_doc_purchase_form_structure_v1'),
            ('remaining_p2_form_productization_contract.xml', 'business_config_contract_tender_doc_purchase_productized_form_v1'),
        )
        for filename, identity in pairs:
            root = ET.parse(ROOT / 'addons/smart_construction_core/data' / filename).getroot()
            record = root.find(f".//record[@id='{identity}']")
            self.assertIs(ast.literal_eval(record.find("field[@name='active']").get('eval')), False)
            self.assertEqual(record.findtext("field[@name='status']"), 'draft')
            self.assertEqual(ast.literal_eval(record.find("field[@name='contract_json']").get('eval')), {'view_orchestration': {'views': {}}})
            retirement = root.find("function[@model='ui.business.config.contract'][@name='write']")
            self.assertIn(identity, retirement.find('value').get('eval'))
            self.assertEqual(ast.literal_eval(retirement.findall('value')[1].get('eval')), {'active': False, 'status': 'draft'})

    def test_new_form_mirror_generation_is_forbidden_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'seeds.xml'
            output.write_text('existing native authority')
            self.assertEqual(main(['--output', str(output)]), 2)
            self.assertEqual(output.read_text(), 'existing native authority')

    def setUp(self):
        self.declaration = RETIREMENT_DECLARATION.read_text()
        self.xml = DEFAULT_OUTPUT.read_text()

    def test_exact_install_and_upgrade_authority(self):
        identities = retired_seed_ids(self.declaration)
        native_form_ids = {row.get("id") for row in ET.fromstring(self.xml).findall("record") if row.findtext("field[@name='view_type']") == "form"}
        self.assertEqual(identities, native_form_ids)
        self.assertGreater(len(identities), 0)
        result = apply_declared_retirements(self.xml, self.declaration)
        before = {row.get('id'): row for row in ET.fromstring(self.xml).findall('record')}
        after = {row.get('id'): row for row in ET.fromstring(result).findall('record')}
        self.assertEqual(set(before), set(after))
        for identity, record in after.items():
            if identity in identities:
                self.assertIs(ast.literal_eval(record.find("field[@name='active']").get('eval')), False)
                self.assertEqual(record.find("field[@name='status']").text, 'draft')
                self.assertEqual(ast.literal_eval(record.find("field[@name='contract_json']").get('eval')), {"view_orchestration": {"views": {}}})
            else:
                self.assertEqual(ET.tostring(before[identity]), ET.tostring(record))
        manifest = ast.literal_eval((ROOT / 'addons/smart_construction_core/__manifest__.py').read_text())
        self.assertLess(manifest['data'].index('data/view_orchestration_contract_generated_data.xml'),
                        manifest['data'].index('data/native_guidance_form_retirement.xml'))
        self.assertEqual(apply_declared_retirements(result, self.declaration), result)

    def test_missing_target_fails_before_output(self):
        with self.assertRaisesRegex(ValueError, 'Missing generated retirement targets'):
            apply_declared_retirements('<odoo/>', self.declaration)

    def test_executable_or_foreign_reference_rejected(self):
        for invalid in (
            self.declaration.replace("ref('smart_construction_core.", "run('smart_construction_core.", 1),
            self.declaration.replace('smart_construction_core.', 'another_module.', 1),
            self.declaration.replace("'active': False", "'active': True"),
        ):
            with self.assertRaises(ValueError):
                retired_seed_ids(invalid)

    def test_unrelated_record_bytes_preserved(self):
        unrelated = '<record id="untouched" model="ui.business.config.contract"><field name="name"> kept </field></record>'
        result = apply_declared_retirements(self.xml.replace('</odoo>', unrelated + '</odoo>'), self.declaration)
        self.assertIn(unrelated, result)

    def test_native_interaction_declaration_descendants(self):
        package = types.ModuleType('guidance_source_core')
        package.__path__ = [str(ROOT / 'addons/smart_core')]
        sys.modules[package.__name__] = package
        usage = importlib.import_module('guidance_source_core.core.field_presentation_usage')
        product = ROOT / 'addons/smart_construction_core'
        fields = {}
        for path in (product / 'models').rglob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
                    continue
                if any(keyword.arg == 'sc_ui_usage' and isinstance(keyword.value, ast.Constant)
                       and keyword.value.value == 'interaction' for keyword in node.value.keywords):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            fields[target.id] = {'sc_ui_usage': 'interaction'}
        self.assertIn('company_contractor_responsibility_notice', fields)
        templates = runpy.run_path(str(product / 'models/support/business_form_policy_templates.py'))
        for policy in templates['get_business_category_form_policy_templates']().values():
            usage.assert_configuration_field_usage(policy, fields)
        checked = 0
        for directory in ('views', 'data'):
            for path in (product / directory).rglob('*.xml'):
                root = ET.parse(path).getroot()
                for carrier in root.iter('field'):
                    if carrier.get('name') == 'arch':
                        for field in carrier.iter('field'):
                            if field.get('name') in fields:
                                usage.assert_field_body_usage(fields[field.get('name')], str(path),
                                                              hidden=usage.statically_hidden(field.attrib))
                        checked += 1
                    elif carrier.get('name') == 'contract_json' and carrier.get('eval'):
                        payload = ast.literal_eval(carrier.get('eval'))
                        usage.assert_configuration_field_usage(payload.get('view_orchestration', {}), fields)
                        checked += 1
                    elif carrier.get('name') == 'form_policy_json' and (carrier.text or '').strip():
                        usage.assert_configuration_field_usage(json.loads(carrier.text), fields)
                        checked += 1
        self.assertGreater(checked, 0)


if __name__ == '__main__':
    unittest.main()
