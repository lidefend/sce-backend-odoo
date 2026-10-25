"""Focused review authority boundaries; runtime ORM/API checks remain separate."""
import ast
import csv
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "addons/smart_construction_core"


class ReviewAuthorityTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((CORE / "services/review_work_item_service.py").read_text())
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "authorize_review_origin")
        self.scope = Mock(return_value=(True, {}))
        ns = {"record_in_business_scope": self.scope}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "review_authority", "exec"), ns)
        self.authorize = ns[fn.name]
        self.review = NS(id=690, model="sc.general.contract", res_id=6, status="pending", reviewer_ids=NS(ids=[13]))
        self.record = NS(_fields={"company_id": True, "review_ids": True}, company_id=1,
                         review_ids=NS(ids=[690]), can_review=True,
                         _sc_tier_review_record_access_mode="read",
                         check_access_rights=Mock(), check_access_rule=Mock())
        review_model = Mock()
        review_model.sudo.return_value.browse.return_value.exists.return_value = self.review
        record_model = Mock()
        record_model.browse.return_value.exists.return_value = self.record
        class Env(dict):
            uid = 13
            company = 1
            context = {}
        self.env = Env({"tier.review": review_model, "sc.general.contract": record_model})

    def call(self, **kw):
        return self.authorize(self.env, {"source": "tier.review", "id": 690},
                              model="sc.general.contract", record_id=6, method_name=kw.get("method", "validate_tier"))

    def test_assigned_approval_requires_read_acl_and_rule(self):
        self.assertEqual(self.call(), {"allowed": True, "record_access_mode": "read"})
        self.record.check_access_rights.assert_called_once_with("read")
        self.record.check_access_rule.assert_called_once_with("read")

    def test_rejection_uses_same_boundary(self):
        self.assertEqual(self.call(method="reject_tier")["record_access_mode"], "read")

    def test_unassigned_refused(self):
        self.review.reviewer_ids.ids = [14]
        self.assertFalse(self.call())

    def test_cross_company_refused(self):
        self.record.company_id = 2
        self.assertFalse(self.call())

    def test_out_of_business_scope_refused(self):
        self.scope.return_value = (False, {})
        self.assertFalse(self.call())

    def test_completed_review_refused(self):
        self.review.status = "approved"
        self.assertFalse(self.call())

    def test_out_of_sequence_refused(self):
        self.record.can_review = False
        self.assertFalse(self.call())

    def test_other_record_refused(self):
        self.review.res_id = 7
        self.assertFalse(self.call())

    def test_other_model_refused(self):
        self.review.model = "payment.request"
        self.assertFalse(self.call())

    def test_record_does_not_own_review_refused(self):
        self.record.review_ids.ids = [691]
        self.assertFalse(self.call())

    def test_business_methods_not_granted(self):
        self.assertFalse(self.call(method="action_signed"))

    def test_acl_denial_not_bypassed(self):
        self.record.check_access_rights.side_effect = PermissionError("denied")
        with self.assertRaises(PermissionError):
            self.call()

    def test_other_models_keep_existing_write_mode(self):
        del self.record._sc_tier_review_record_access_mode
        self.assertIs(self.call(), True)

    def test_finance_acl_cannot_edit_create_delete(self):
        with (CORE / "security/ir.model.access.csv").open() as f:
            row, = [r for r in csv.DictReader(f) if r["id"] == "access_sc_general_contract_finance_review"]
        self.assertEqual([row[x] for x in ("perm_read", "perm_write", "perm_create", "perm_unlink")], ["1", "0", "0", "0"])
        self.assertEqual(row["group_id:id"], "smart_construction_core.group_sc_cap_finance_manager")

    def test_finance_rule_is_assignment_scoped(self):
        node = ET.parse(CORE / "security/sc_record_rules.xml").find(".//record[@id='rule_sc_general_contract_finance_assigned_review']")
        self.assertEqual(node.find("field[@name='domain_force']").text, "[('review_ids.reviewer_ids', 'in', [user.id])]")
        for op in ("write", "create", "unlink"):
            self.assertEqual(node.find(f"field[@name='perm_{op}']").get("eval"), "False")

    def test_finance_step_is_standard_product_not_demo_only(self):
        tree = ast.parse((CORE / "models/support/approval_policy.py").read_text())
        values = [ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "USER_VISIBLE_APPROVAL_TEMPLATES" for t in n.targets)]
        self.assertIn("finance_manager", [scope for _, scope in values[0]["general_contract_approval"]["steps"]])


if __name__ == "__main__":
    unittest.main()
