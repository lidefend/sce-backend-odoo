from __future__ import annotations

import ast
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts" / "verify" / "formal_action_runtime_drift_audit.py"
FORMAL_LISTS = ROOT / "addons" / "smart_construction_core" / "views" / "support" / "user_confirmed_formal_list_views.xml"
ALIGNMENT_LISTS = ROOT / "addons" / "smart_construction_core" / "views" / "support" / "user_confirmed_formal_list_alignment_views.xml"
USER_FEEDBACK_TESTS = ROOT / "addons" / "smart_construction_core" / "tests" / "test_user_feedback_business_views.py"


class FormalActionRuntimeDriftAuditTest(unittest.TestCase):
    @staticmethod
    def _assignments() -> dict[str, ast.AST]:
        tree = ast.parse(AUDIT.read_text(encoding="utf-8"))
        return {
            node.targets[0].id: node.value
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        }

    @staticmethod
    def _record(path: Path, record_id: str):
        root = ET.fromstring(path.read_text(encoding="utf-8"))
        record = root.find(f".//record[@id='{record_id}']")
        if record is None:
            raise AssertionError(f"missing XML record: {record_id}")
        return record

    @staticmethod
    def _field_text(record, field_name: str) -> str:
        field = record.find(f"field[@name='{field_name}']")
        if field is None:
            raise AssertionError(f"missing field: {field_name}")
        return (field.text or "").strip()

    def test_daily_source_mount_is_an_addon_root_candidate(self) -> None:
        assignments = self._assignments()
        candidates = ast.unparse(assignments["ADDON_ROOT_CANDIDATES"])
        self.assertIn("/mnt/source-addons/smart_construction_core", candidates)

    def test_formal_action_source_contracts_match_locked_runtime_expectations(self) -> None:
        contract_action = self._record(FORMAL_LISTS, "action_construction_contract_income_construction")
        self.assertEqual(
            contract_action.find("field[@name='view_id']").attrib.get("ref"),
            "smart_construction_core.view_construction_contract_income_construction_user_confirmed_tree",
        )
        self.assertIn(
            "view_construction_contract_income_construction_user_confirmed_tree",
            contract_action.find("field[@name='view_ids']").attrib.get("eval", ""),
        )

        contract_tree = self._record(FORMAL_LISTS, "view_construction_contract_income_construction_user_confirmed_tree")
        tree_node = contract_tree.find(".//tree")
        self.assertIsNotNone(tree_node)
        self.assertEqual(tree_node.attrib.get("default_order"), "date_contract desc, id desc")
        contract_fields = [field.attrib.get("name") for field in contract_tree.findall(".//tree/field")]
        self.assertEqual(contract_fields.count("name"), 1)
        number_columns = [
            (field.attrib.get("name"), field.attrib.get("string"))
            for field in contract_tree.findall(".//tree/field")
            if field.attrib.get("string") in {"单据编号", "合同编号"}
        ]
        self.assertEqual(number_columns, [("name", "单据编号")])
        self.assertNotIn("legacy_document_no", contract_fields)
        self.assertNotIn("legacy_contract_no", contract_fields)

        receipt_tree = self._record(FORMAL_LISTS, "view_sc_receipt_income_engineering_progress_formal_tree")
        receipt_fields = [field.attrib.get("name") for field in receipt_tree.findall(".//tree/field")]
        self.assertIn("legacy_contract_no", receipt_fields)

        tender_action = self._record(ALIGNMENT_LISTS, "action_tender_guarantee_formal_payment_deposit_return")
        self.assertEqual(self._field_text(tender_action, "domain"), "[]")

    def test_locked_contract_field_order_matches_installed_view_source(self) -> None:
        contracts = ast.literal_eval(self._assignments()["EXPECTED_ACTION_CONTRACTS"])
        action_views = {
            "action_construction_contract_income_construction": "view_construction_contract_income_construction_user_confirmed_tree",
            "action_sc_receipt_income_engineering_progress": "view_sc_receipt_income_engineering_progress_formal_tree",
            "action_sc_invoice_input_report_user": "view_sc_invoice_registration_input_tax_user_confirmed_tree",
        }
        for action_id, view_id in action_views.items():
            action = self._record(FORMAL_LISTS, action_id)
            view = self._record(FORMAL_LISTS, view_id)
            expected = contracts[action_id]
            actual_fields = [field.attrib.get("name") for field in view.findall(".//tree/field")]
            self.assertEqual(actual_fields, expected["field_names"], action_id)
            self.assertEqual(self._field_text(view, "name"), expected["view_name"], action_id)
            if action.find("field[@name='name']") is not None:
                self.assertEqual(self._field_text(action, "name"), expected["name"], action_id)

    def test_legacy_actions_use_source_projection_parity_instead_of_fixture_presence(self) -> None:
        assignments = self._assignments()
        non_empty = set(ast.literal_eval(assignments["EXPECTED_NON_EMPTY_ACTIONS"]))
        parity = ast.literal_eval(assignments["LEGACY_SOURCE_PARITY_ACTIONS"])
        expected = {
            "action_sc_material_inbound": "入库",
            "action_sc_material_rental_in_acceptance": "租入",
            "action_sc_material_rental_return_acceptance": "还租",
        }
        self.assertEqual(parity, expected)
        self.assertTrue(expected.keys().isdisjoint(non_empty))

        source = AUDIT.read_text(encoding="utf-8")
        self.assertIn("legacy_source_projection_count_mismatch", source)
        self.assertIn('"name": "进项税额上报"', source)
        self.assertIn("tree_fields_missing_from_registered_model", source)
        self.assertIn("tree_order_fields_missing_from_registered_model", source)

    def test_contract_feedback_regression_uses_single_formal_number_contract(self) -> None:
        source = USER_FEEDBACK_TESTS.read_text(encoding="utf-8")
        self.assertIn("def test_contract_list_exposes_single_formal_number", source)
        self.assertNotIn("def test_contract_list_exposes_legacy_contract_numbers", source)
        contract_case = source.split("def test_contract_list_exposes_single_formal_number", 1)[1].split(
            "def test_legacy_purchase_contract_is_not_business_approval_target", 1
        )[0]
        for field_name in ("legacy_contract_no", "legacy_document_no", "legacy_external_contract_no"):
            self.assertNotIn(f'"{field_name}":', contract_case)
            self.assertNotIn(f"contract.{field_name}", contract_case)
            self.assertIn(f'self.assertNotIn("{field_name}", contract._fields)', contract_case)


if __name__ == "__main__":
    unittest.main()
