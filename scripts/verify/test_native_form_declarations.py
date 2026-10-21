"""Current native form and interaction declarations."""
import ast
import importlib
import json
import runpy
from pathlib import Path
import sys
import types
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


class NativeFormDeclarationTest(unittest.TestCase):
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

    def test_payment_list_declarations_respect_native_field_usage(self):
        product = ROOT / 'addons/smart_construction_core'
        interaction = set()
        for node in ast.walk(ast.parse((product / 'models/core/payment_request.py').read_text())):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                if any(k.arg == 'sc_ui_usage' and isinstance(k.value, ast.Constant)
                       and k.value.value == 'interaction' for k in node.value.keywords):
                    interaction.update(t.id for t in node.targets if isinstance(t, ast.Name))
        self.assertIn('legal_next_action_display', interaction)
        policy = runpy.run_path(str(product / 'core_extension_policy_maps.py'))['BUSINESS_LIST_DEFAULT_VISIBILITY_BY_MODEL']['payment.request']
        profiles = []
        for node in ast.walk(ast.parse((product / 'core_extension.py').read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'register_legacy_standard_list_profile':
                profile = ast.literal_eval(node.args[0])
                if profile.get('model_name') == 'payment.request':
                    profiles.append(profile)
        self.assertEqual(len(profiles), 1)
        for columns in (policy['visible'], policy['critical'], policy['roles'],
                        profiles[0]['columns_order'], profiles[0]['column_labels']):
            self.assertFalse(interaction.intersection(columns), interaction.intersection(columns))
        root = ET.parse(product / 'views/support/user_confirmed_formal_list_views.xml').getroot()
        tree = root.find("record[@id='view_payment_request_formal_payment_apply_tree']/field[@name='arch']/tree")
        fields = {field.get('name') for field in tree.iter('field')}
        self.assertFalse(set(policy['critical']) - fields)
        self.assertFalse(fields.intersection(interaction))

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
                        parents = {child: parent for parent in carrier.iter() for child in parent}
                        for field in carrier.iter('field'):
                            if field.get('name') in fields:
                                parent = parents.get(field)
                                if parent is not None and parent.tag == 'div' and parent.get('role') == 'status':
                                    self.assertEqual(field.get('name'), 'processing_advisory')
                                    self.assertEqual(parent.get('invisible'), 'not processing_advisory')
                                    self.assertIn('alert-info', parent.get('class', '').split())
                                    self.assertEqual(field.get('readonly'), '1')
                                    self.assertEqual(field.get('nolabel'), '1')
                                    continue
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
