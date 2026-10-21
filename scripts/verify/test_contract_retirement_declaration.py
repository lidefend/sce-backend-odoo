"""Retired contracts are inactive declarations, never install-time data repair."""
from pathlib import Path
import ast
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


class ContractRetirementDeclarationTest(unittest.TestCase):
    def test_retired_contract_is_inactive_draft_without_upgrade_write(self):
        for filename, identity in (
            ("view_orchestration_form_section_contract_data.xml", "business_config_contract_tender_doc_purchase_form_structure_v1"),
            ("remaining_p2_form_productization_contract.xml", "business_config_contract_tender_doc_purchase_productized_form_v1"),
        ):
            with self.subTest(identity=identity):
                root = ET.parse(ROOT / "addons/smart_construction_core/data" / filename).getroot()
                record = root.find(f".//record[@id='{identity}']")
                self.assertIsNotNone(record)
                self.assertEqual(record.find("field[@name='active']").get("eval"), "False")
                self.assertEqual(record.find("field[@name='status']").text, "draft")
                payload = ast.literal_eval(record.find("field[@name='contract_json']").get("eval"))
                self.assertEqual(payload['view_orchestration']['views'], {})
                self.assertEqual(payload['view_orchestration']['context']['source_status'], 'developer_draft')
                self.assertFalse(root.findall(".//function[@model='ui.business.config.contract'][@name='write']"))


if __name__ == "__main__":
    unittest.main()
