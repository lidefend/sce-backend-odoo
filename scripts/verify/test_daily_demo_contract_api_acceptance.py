import unittest
from scripts.verify.daily_demo_contract_api_acceptance import approval_button, target_origin, validate_finance_resume


class ApiAuthorityTests(unittest.TestCase):
    def checkpoint(self):
        prior = {"record_id": 6, "business_key": "DEMO-DELIVERY-20261025-UI01", "status": "BLOCKED_NOT_ACCEPTED",
                 "failure": {"actor": "fin_mgr"}, "completed_api_actions": [
                     {"actor": "ct1", "origin": {"id": 688}}, {"actor": "sc_demo_operation", "origin": {"id": 689}}]}
        rows = [{"id": i, "status": s, "model": "sc.general.contract", "res_id": 6}
                for i, s in [(688, "approved"), (689, "approved"), (690, "pending"), (691, "waiting")]]
        return prior, rows

    def test_exact_finance_checkpoint(self):
        validate_finance_resume(*self.checkpoint())

    def test_completed_finance_refuses_replay(self):
        prior, rows = self.checkpoint()
        rows[2]["status"] = "approved"
        with self.assertRaises(ValueError):
            validate_finance_resume(prior, rows)

    def test_uncertain_write_refuses_resume(self):
        prior, rows = self.checkpoint()
        prior["pending_mutation"] = {"actor": "fin_mgr"}
        with self.assertRaises(ValueError):
            validate_finance_resume(prior, rows)

    def test_wrong_document_refuses_resume(self):
        prior, rows = self.checkpoint()
        rows[0]["res_id"] = 7
        with self.assertRaises(ValueError):
            validate_finance_resume(prior, rows)

    def contract(self, **changes):
        row = dict(button={"name": "validate_tier", "type": "object"}, allowed=True, enabled=True,
                   disabled=False, entitlementEvaluated=True, actionId="a", backendIdentity="b", sourceWidgetId="c")
        row.update(changes)
        return {"actionContract": {"actionRuleList": [row]}}

    def test_native_identity_preserved(self):
        self.assertEqual(approval_button(self.contract())["backend_identity"], "b")

    def test_denied_and_incomplete_refused(self):
        for change in ({"allowed": False}, {"enabled": False}, {"disabled": True},
                       {"entitlementEvaluated": False}, {"backendIdentity": ""}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                approval_button(self.contract(**change))

    def test_ambiguous_refused(self):
        c = self.contract()
        c["actionContract"]["actionRuleList"] *= 2
        with self.assertRaises(ValueError):
            approval_button(c)

    def test_other_record_is_not_authority(self):
        with self.assertRaises(ValueError):
            target_origin({"product_workspace": {"sections": [{"key": "todo", "items": [
                {"target": {"model": "sc.general.contract", "record_id": 7}}]}]}})

    def test_actual_work_origin(self):
        origin = {"source": "tier.review", "id": 688}
        self.assertEqual(target_origin({"product_workspace": {"sections": [{"key": "todo", "items": [
            {"target": {"model": "sc.general.contract", "record_id": 6, "work_item_origin": origin}}]}]}}), origin)
