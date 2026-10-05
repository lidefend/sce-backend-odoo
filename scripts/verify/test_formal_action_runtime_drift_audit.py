from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "scripts" / "verify" / "formal_action_runtime_drift_audit.py"
MANIFEST = ROOT / "addons" / "smart_construction_core" / "__manifest__.py"
FORMAL_LISTS = ROOT / "addons" / "smart_construction_core" / "views" / "support" / "user_confirmed_formal_list_views.xml"
ALIGNMENT_LISTS = ROOT / "addons" / "smart_construction_core" / "views" / "support" / "user_confirmed_formal_list_alignment_views.xml"
USER_FEEDBACK_TESTS = ROOT / "addons" / "smart_construction_core" / "tests" / "test_user_feedback_business_views.py"
VIEWS_ROOT = ROOT / "addons" / "smart_construction_core" / "views"


def _arch_field_names(arch_field) -> list[str]:
    if arch_field is None:
        return []
    if arch_field.text and arch_field.text.strip():
        try:
            return [node.get("name") or "" for node in ET.fromstring(arch_field.text).iter("field")]
        except ET.ParseError:
            return []
    return [node.get("name") or "" for node in arch_field.iter("field") if node is not arch_field]


def _index_repo_source() -> tuple[dict[str, list[tuple[str, str]]], dict[str, list[list[str]]]]:
    """Map locked action ids and view technical names to the repo source face."""
    actions: dict[str, list[tuple[str, str]]] = {}
    views: dict[str, list[list[str]]] = {}
    for path in sorted(VIEWS_ROOT.rglob("*.xml")):
        try:
            root = ET.fromstring(path.read_text(encoding="utf-8"))
        except ET.ParseError:
            continue
        for record in root.iter("record"):
            fields = {field.get("name") or "": field for field in record.findall("field")}
            if record.get("model") == "ir.actions.act_window":
                text = {key: (value.text or "").strip() for key, value in fields.items()}
                actions.setdefault(record.get("id") or "", []).append(
                    (text.get("name", ""), text.get("res_model", ""))
                )
            elif record.get("model") == "ir.ui.view":
                view_name = (fields["name"].text or "").strip() if "name" in fields else ""
                views.setdefault(view_name, []).append(_arch_field_names(fields.get("arch")))
    return actions, views


def _contract_source_mismatches(contracts: dict) -> list[str]:
    actions, views = _index_repo_source()
    issues = []
    for action_id, spec in sorted(contracts.items()):
        definitions = actions.get(action_id, [])
        if not definitions:
            issues.append(f"{action_id}:missing_action_definition")
            continue
        if not any(name == spec["name"] for name, _ in definitions):
            issues.append(f"{action_id}:name")
        if not any(model == spec["res_model"] for _, model in definitions):
            issues.append(f"{action_id}:res_model")
        archs = views.get(spec["view_name"], [])
        if not archs:
            issues.append(f"{action_id}:view")
        elif all(fields != spec["field_names"] for fields in archs):
            issues.append(f"{action_id}:fields")
    return issues


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

    def test_runtime_drift_audit_follows_manifest_load_order(self) -> None:
        assignments = self._assignments()
        audited_files = ast.literal_eval(assignments["HIGH_RISK_XML_FILES"])
        manifest_files = ast.literal_eval(MANIFEST.read_text(encoding="utf-8"))["data"]
        self.assertEqual(
            [item for item in manifest_files if item in audited_files],
            audited_files,
        )

    def test_high_risk_files_have_no_cross_file_forward_references(self) -> None:
        assignments = self._assignments()
        audited_files = ast.literal_eval(assignments["HIGH_RISK_XML_FILES"])
        definitions: dict[str, int] = {}
        parsed_files = []
        for file_index, relative in enumerate(audited_files):
            path = ROOT / "addons" / "smart_construction_core" / relative
            xml_root = ET.fromstring(path.read_text(encoding="utf-8"))
            parsed_files.append((file_index, relative, xml_root))
            for record in xml_root.findall(".//record[@id]"):
                definitions[record.attrib["id"]] = file_index

        forward_references = []
        for file_index, relative, xml_root in parsed_files:
            for record in xml_root.findall(".//record[@id]"):
                serialized = ET.tostring(record, encoding="unicode")
                for xmlid in re.findall(r"smart_construction_core\.([A-Za-z0-9_]+)", serialized):
                    if definitions.get(xmlid, file_index) > file_index:
                        forward_references.append(f"{relative}:{record.attrib['id']}->{xmlid}")
        self.assertEqual(forward_references, [])

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
        receipt_fields = [
            (field.attrib.get("name"), field.attrib.get("string"))
            for field in receipt_tree.findall(".//tree/field")
        ]
        self.assertIn(("legacy_contract_no", "施工管理合同"), receipt_fields)
        self.assertNotIn(("legacy_contract_no", "合同编号"), receipt_fields)

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

    def test_every_locked_contract_entry_is_bound_to_repo_source(self) -> None:
        contracts = ast.literal_eval(self._assignments()["EXPECTED_ACTION_CONTRACTS"])
        self.assertEqual(_contract_source_mismatches(contracts), [])

    def test_contract_source_binding_detects_drift(self) -> None:
        contracts = ast.literal_eval(self._assignments()["EXPECTED_ACTION_CONTRACTS"])
        key = "action_payment_request_user_payment_apply"
        mutated = dict(contracts)
        mutated[key] = dict(contracts[key], name="支付申请")
        self.assertIn(f"{key}:name", _contract_source_mismatches(mutated))
        mutated[key] = dict(contracts[key], field_names=list(contracts[key]["field_names"]) + ["bogus_field"])
        self.assertIn(f"{key}:fields", _contract_source_mismatches(mutated))

    def test_locked_contract_entries_have_no_dead_targets(self) -> None:
        contracts = ast.literal_eval(self._assignments()["EXPECTED_ACTION_CONTRACTS"])
        audited: set[str] = set()
        for relative in ast.literal_eval(self._assignments()["HIGH_RISK_XML_FILES"]):
            root = ET.fromstring(
                (ROOT / "addons" / "smart_construction_core" / relative).read_text(encoding="utf-8")
            )
            audited.update(
                record.attrib["id"]
                for record in root.findall(".//record[@model='ir.actions.act_window']")
            )
        self.assertEqual(sorted(set(contracts) - audited), [])

    def test_formal_actions_do_not_depend_on_legacy_acceptance_labels(self) -> None:
        assignments = self._assignments()
        parity = ast.literal_eval(assignments["FORMAL_ACCEPTANCE_LABEL_ACTIONS"])
        expected_domains = {
            "action_sc_material_inbound": [],
            "action_sc_material_rental_in_acceptance": [("state", "in", ["draft", "active"])],
            "action_sc_material_rental_return_acceptance": [("state", "in", ["returned", "settled"])],
        }
        self.assertEqual(parity, {})

        for action_id, expected_domain in expected_domains.items():
            action = self._record(FORMAL_LISTS, action_id)
            self.assertEqual(ast.literal_eval(self._field_text(action, "domain")), expected_domain)

        source = AUDIT.read_text(encoding="utf-8")
        self.assertIn("wrong_formal_acceptance_domain", source)
        self.assertIn("formal_acceptance_domain_count_mismatch", source)
        self.assertNotIn("missing_source_model", source)
        self.assertNotIn("online_old_legacy_direct", source)
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
