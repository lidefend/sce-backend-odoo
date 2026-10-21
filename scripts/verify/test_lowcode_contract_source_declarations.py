import tempfile
import unittest
from pathlib import Path
from xml.sax.saxutils import quoteattr

from lowcode_config_boundary_guard import validate_source_declarations


class SourceDeclarationTest(unittest.TestCase):
    def check_payload(self, payload, *, loaded=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '__manifest__.py').write_text(repr({'data': ['seed.xml'] if loaded else []}))
            (root / 'seed.xml').write_text(
                '<odoo><record id="sample" model="ui.business.config.contract">'
                '<field name="active" eval="False"/><field name="contract_json" eval='
                + quoteattr(repr(payload)) + '/></record></odoo>')
            return validate_source_declarations(root)

    def test_explicit_statuses_in_both_carriers(self):
        for status in ('developer_draft', 'tenant_runtime', 'product_release'):
            with self.subTest(status=status):
                self.assertFalse(self.check_payload({
                    'view_orchestration': {'context': {'source_status': status}},
                    'menu_orchestration': {'source_status': status},
                }))

    def test_missing_or_invalid_status_fails_even_for_inactive_record(self):
        for payload in ({'view_orchestration': {'views': {}}},
                        {'menu_orchestration': {}},
                        {'view_orchestration': {'context': {'source_status': 'unknown'}}},
                        {'view_orchestration': {'context': []}}):
            with self.subTest(payload=payload):
                self.assertTrue(self.check_payload(payload))

    def test_unloaded_xml_is_not_install_authority(self):
        self.assertFalse(self.check_payload({'view_orchestration': {}}, loaded=False))

    def test_non_mapping_contract_is_rejected(self):
        self.assertTrue(self.check_payload([]))


if __name__ == '__main__':
    unittest.main()
