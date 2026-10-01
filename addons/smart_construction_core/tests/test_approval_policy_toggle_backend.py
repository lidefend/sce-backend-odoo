# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


@tagged("post_install", "-at_install", "sc_approval_policy")
class TestApprovalPolicyToggleBackend(TransactionCase):
    def test_approval_required_toggle_normalizes_mode_and_runtime(self):
        policy = self.env.ref("smart_construction_core.approval_policy_receipt_income").sudo()

        policy.write({"active": True, "approval_required": False, "mode": "none"})
        self.assertFalse(
            self.env["sc.approval.policy"].is_approval_required(policy.target_model, company=policy.company_id)
        )

        policy.write({"approval_required": True})
        self.assertTrue(policy.approval_required)
        self.assertEqual(policy.mode, "single")
        self.assertTrue(
            self.env["sc.approval.policy"].is_approval_required(policy.target_model, company=policy.company_id)
        )

        policy.write({"approval_required": False})
        self.assertFalse(policy.approval_required)
        self.assertEqual(policy.mode, "none")
        self.assertFalse(
            self.env["sc.approval.policy"].is_approval_required(policy.target_model, company=policy.company_id)
        )

    def test_mode_change_keeps_approval_required_consistent(self):
        policy = self.env.ref("smart_construction_core.approval_policy_settlement_adjustment").sudo()

        policy.write({"active": True, "mode": "linear"})
        self.assertTrue(policy.approval_required)

        policy.write({"mode": "none"})
        self.assertFalse(policy.approval_required)

    def test_native_create_context_state_guard(self):
        """Real ORM defaults; transactional setup, ordinary PM creates only."""
        company = self.env.company
        actor = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Native create guard PM", "login": "native.create.guard.pm",
            "company_id": company.id, "company_ids": [(6, 0, [company.id])],
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id,
                self.env.ref("smart_construction_core.group_sc_role_project_manager").id])],
        })
        project = self.env["project.project"].create({
            "name": "Native state guard project", "company_id": company.id,
            "user_id": actor.id, "manager_id": actor.id,
        })
        supplier = self.env["res.partner"].create({"name": "Native state guard supplier", "supplier_rank": 1})
        for model_name in ("sc.labor.plan", "sc.material.rental.order"):
            with self.subTest(model=model_name):
                model = self.env[model_name].with_user(actor).with_context(allowed_company_ids=[company.id])
                self.assertFalse(model.env.su)
                self.assertTrue(model.check_access_rights("create", raise_exception=False))
                vals = {"name": "NATIVE-STATE-GUARD", "project_id": project.id}
                if model_name == "sc.material.rental.order": vals["supplier_id"] = supplier.id
                domain = [("project_id", "=", project.id)]
                before = model.search_count(domain)
                effective = model.with_context(default_state="approved")
                self.assertEqual(effective.default_get(["state"])["state"], "approved")
                for batch in ([dict(vals)], [dict(vals, state="draft"), dict(vals)]):
                    with self.assertRaises(UserError), self.cr.savepoint():
                        effective.create(batch)
                    self.assertEqual(model.search_count(domain), before)
                explicit = effective.create(dict(vals, state="draft"))
                ordinary = model.create(dict(vals))
                self.assertEqual(explicit.state, "draft")
                self.assertEqual(ordinary.state, "draft")
                self.assertEqual(explicit.create_uid, actor)
                self.assertEqual(ordinary.create_uid, actor)
                self.assertEqual(model.search_count(domain), before + 2)
