import unittest
from scripts.verify.daily_demo_contract_api_acceptance import approval_button, target_origin, validate_finance_resume, validate_sign_checkpoint, released_contract_entry, validate_sign_entry_resume


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


class SignCheckpointTests(unittest.TestCase):
    def checkpoint(self):
        prior = {"record_id": 6, "business_key": "DEMO-DELIVERY-20261025-UI01",
                 "status": "API_APPROVAL_EXECUTED_FINAL_SIGN_PENDING", "reused_reviews": [688, 689],
                 "completed_api_actions": [{"actor": "fin_mgr", "origin": {"id": 690}},
                     {"actor": "demo_role_executive", "origin": {"id": 691}}]}
        record = {"id": 6, "state": "confirmed", "validation_status": "validated"}
        reviews = [{"id": i, "status": "approved", "model": "sc.general.contract", "res_id": 6}
                   for i in (688, 689, 690, 691)]
        return prior, record, reviews

    def test_completed_exact_checkpoint(self):
        validate_sign_checkpoint(*self.checkpoint())

    def test_signed_or_unvalidated_refuses_replay(self):
        for changes in ({"state": "signed"}, {"state": "draft"}, {"validation_status": "pending"}, {"id": 7}):
            prior, record, reviews = self.checkpoint()
            record.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_sign_checkpoint(prior, record, reviews)

    def test_pending_or_uncertain_approval_refused(self):
        prior, record, reviews = self.checkpoint()
        reviews[-1]["status"] = "pending"
        with self.assertRaises(ValueError):
            validate_sign_checkpoint(prior, record, reviews)
        prior, record, reviews = self.checkpoint()
        prior["pending_mutation"] = {"actor": "fin_mgr"}
        with self.assertRaises(ValueError):
            validate_sign_checkpoint(prior, record, reviews)

    def test_wrong_or_duplicate_review_refused(self):
        for change in ({"res_id": 7}, {"model": "project.project"}, {"id": 688}):
            prior, record, reviews = self.checkpoint()
            reviews[-1].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_sign_checkpoint(prior, record, reviews)

    def test_wrong_actor_provenance_refused(self):
        prior, record, reviews = self.checkpoint()
        prior["completed_api_actions"][-1]["actor"] = "admin"
        with self.assertRaises(ValueError):
            validate_sign_checkpoint(prior, record, reviews)

    def test_sign_authority_requires_exact_native_action(self):
        contract = ApiAuthorityTests().contract()
        with self.assertRaises(ValueError):
            approval_button(contract, "action_signed")
        contract["actionContract"]["actionRuleList"][0]["button"]["name"] = "action_signed"
        self.assertEqual(approval_button(contract, "action_signed")["name"], "action_signed")
        contract["actionContract"]["actionRuleList"][0]["allowed"] = False
        with self.assertRaises(ValueError):
            approval_button(contract, "action_signed")
        with self.assertRaises(ValueError):
            approval_button(contract, "unlink")


class SignEntryTests(unittest.TestCase):
    def test_exact_released_menu_required(self):
        node = {"menu_xmlid": "smart_construction_core.menu_sc_p1_daily_contract", "action_id": 3, "menu_id": 4}
        self.assertEqual(released_contract_entry({"navigation": {"nav": [node]}}), {"action_id": 3, "menu_id": 4})
        for nodes in ([], [node, node], [{**node, "menu_id": 0}], [{**node, "menu_xmlid": "other"}]):
            with self.assertRaises(ValueError):
                released_contract_entry({"navigation": {"nav": nodes}})

    def test_only_explicit_pre_action_denial_can_resume(self):
        failed = {"status": "BLOCKED_NOT_ACCEPTED", "record_id": 6, "business_key": "DEMO-DELIVERY-20261025-UI01",
                  "pending_mutation": {"button": {"name": "action_signed"}},
                  "steps": [{"actor": "demo_full", "intent": "execute_button", "http_status": 403,
                             "response": {"error": {"message": "ACTION_CONTRACT_AUTHORITY_MISSING"}}}]}
        validate_sign_entry_resume(failed)
        for code in (200, 500, 0):
            failed["steps"][-1]["http_status"] = code
            with self.assertRaises(ValueError):
                validate_sign_entry_resume(failed)
