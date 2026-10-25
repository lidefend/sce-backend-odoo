"""Transactional candidate-declaration regression, not deployed acceptance."""
import csv
from pathlib import Path
import xml.etree.ElementTree as ET

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import tagged
from .business_case import BusinessTransactionCase
from ..services.review_work_item_service import authorize_review_origin


@tagged("post_install", "-at_install", "-standard", "general_contract_finance_review")
class TestGeneralContractFinanceReview(BusinessTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        root = Path(__file__).resolve().parents[1]
        group = cls.env.ref("smart_construction_core.group_sc_cap_finance_manager")
        model = cls.env["ir.model"]._get("sc.general.contract")
        # test.safe does not upgrade modules. Load the exact new declarations
        # inside this rollback-only test transaction; never repair live data.
        with (root / "security/ir.model.access.csv").open() as stream:
            acl, = [r for r in csv.DictReader(stream) if r["id"] == "access_sc_general_contract_finance_review"]
        cls.env["ir.model.access"].create({"name": "candidate finance review", "model_id": model.id,
            "group_id": group.id, **{k: bool(int(acl[k])) for k in ("perm_read", "perm_write", "perm_create", "perm_unlink")}})
        node = ET.parse(root / "security/sc_record_rules.xml").find(".//record[@id='rule_sc_general_contract_finance_assigned_review']")
        cls.env["ir.rule"].create({"name": "candidate assigned finance review", "model_id": model.id,
            "groups": [(6, 0, group.ids)], "domain_force": node.find("field[@name='domain_force']").text,
            **{k: node.find(f"field[@name='{k}']").get("eval") == "True"
               for k in ("perm_read", "perm_write", "perm_create", "perm_unlink")}})
        cls.reviewer = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Synthetic finance review", "login": "synthetic_gc_finance_review",
            "company_id": cls.env.company.id, "company_ids": [(6, 0, cls.env.company.ids)],
            "groups_id": [(6, 0, (group | cls.env.ref("base.group_user")).ids)]})
        cls.assigned = cls.env["sc.general.contract"].create({"contract_name": "Synthetic assigned contract",
            "partner_name_text": "Synthetic vendor", "amount_total": 100, "company_id": cls.env.company.id})
        cls.unassigned = cls.assigned.copy({"contract_name": "Synthetic unassigned contract"})
        definition = cls.env["tier.definition"].create({"name": "Synthetic finance review",
            "model_id": model.id, "review_type": "individual", "reviewer_id": cls.reviewer.id,
            "company_id": cls.env.company.id, "approve_sequence": False})
        cls.review = cls.env["tier.review"].create({"model": model.model, "res_id": cls.assigned.id,
            "definition_id": definition.id, "status": "pending", "sequence": 1})

    def test_assigned_read_and_native_approval_without_contract_write(self):
        record = self.assigned.with_user(self.reviewer)
        self.assertEqual(record.read(["contract_name"])[0]["id"], self.assigned.id)
        self.assertFalse(record.check_access_rights("write", raise_exception=False))
        self.assertEqual(authorize_review_origin(record.env, {"source": "tier.review", "id": self.review.id},
            model=record._name, record_id=record.id, method_name="validate_tier"),
            {"allowed": True, "record_access_mode": "read"})
        record.validate_tier()
        self.assertEqual(self.review.status, "approved")

    def test_unassigned_read_denied(self):
        with self.assertRaises(AccessError), self.cr.savepoint():
            self.unassigned.with_user(self.reviewer).read(["contract_name"])

    def test_assigned_contract_edit_denied(self):
        self.assertFalse(self.assigned.with_user(self.reviewer).check_access_rights("write", raise_exception=False))
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.assigned.with_user(self.reviewer).write({"amount_total": 200})
        self.assertEqual(self.assigned.amount_total, 100)

    def test_cross_company_assigned_read_denied(self):
        other = self.env["res.company"].create({"name": "Synthetic other review company"})
        self.register_business_company(other)
        contract = self.unassigned.copy({"contract_name": "Synthetic cross-company assigned", "company_id": other.id})
        definition = self.review.definition_id.copy({"company_id": other.id})
        self.env["tier.review"].create({"model": "sc.general.contract", "res_id": contract.id,
            "definition_id": definition.id, "status": "pending", "sequence": 1})
        with self.assertRaises(AccessError), self.cr.savepoint():
            contract.with_user(self.reviewer).read(["contract_name"])

    def test_fresh_contract_execute_button_review(self):
        from odoo.addons.smart_core.handlers.execute_button import ExecuteButtonHandler
        acting = self.assigned.with_user(self.reviewer).env
        contract = ExecuteButtonHandler(acting)._load_current_action_contract(
            model="sc.general.contract", record_id=self.assigned.id, action_id=0, menu_id=0)
        row, = [r for r in contract["actionContract"]["actionRuleList"]
                if r.get("button", {}).get("name") == "validate_tier"]
        result = ExecuteButtonHandler(acting, payload={
            "params": {"model": "sc.general.contract", "res_id": self.assigned.id,
                "button": {**row["button"], "action_id": row["actionId"],
                    "backend_identity": row["backendIdentity"], "source_widget_id": row["sourceWidgetId"]}},
            "meta": {"work_item_origin": {"source": "tier.review", "id": self.review.id}},
        }).handle()
        result = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(result.get("ok"), result)
        self.assertEqual(self.review.status, "approved")
