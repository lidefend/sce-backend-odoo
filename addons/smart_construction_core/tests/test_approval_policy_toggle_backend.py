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

    def _one_step_handling_fixture(self, suffix):
        company = self.env.company
        project = self.env["project.project"].create({
            "name": "One step handling project %s" % suffix, "company_id": company.id,
        })
        supplier = self.env["res.partner"].create({
            "name": "One step handling supplier %s" % suffix, "supplier_rank": 1,
        })
        return company, project, supplier

    def _rental_order(self, company, project, supplier, name):
        return self.env["sc.material.rental.order"].create({
            "name": name,
            "company_id": company.id,
            "project_id": project.id,
            "supplier_id": supplier.id,
            "line_ids": [(0, 0, {
                "material_name": "钢管",
                "qty": 10.0,
                "rental_days": 5.0,
                "daily_price": 12.0,
            })],
        })

    def test_handling_gate_finishes_one_step_without_approval_rule(self):
        """Handling a document is one user action unless an approval rule exists."""
        service = self.env["sc.approval.policy"]
        company, project, supplier = self._one_step_handling_fixture("off")
        self.assertFalse(service.get_active_policy("sc.material.rental.order", company=company))
        self.assertFalse(service.is_approval_required("sc.material.rental.order", company=company))
        order = self._rental_order(company, project, supplier, "ONE-STEP-OFF")
        self.assertEqual(order.state, "draft")
        order.action_activate()
        self.assertEqual(order.state, "active")
        self.assertFalse(order.review_ids)
        # The unapproved-state refusal below is unchanged: one step is allowed,
        # a second handling of a finished document is not.
        with self.assertRaises(UserError), self.cr.savepoint():
            order.action_activate()
        self.assertEqual(order.state, "active")

    def test_handling_gate_keeps_submission_when_approval_rule_configured(self):
        """A configured approval rule keeps fail-closed submission semantics."""
        service = self.env["sc.approval.policy"]
        company, project, supplier = self._one_step_handling_fixture("on")
        service.create({
            "name": "材料租赁单审批规则",
            "code": "test.one.step.rental.order",
            "target_model": "sc.material.rental.order",
            "approval_required": True,
            "mode": "single",
            "company_id": company.id,
            "active": True,
        })
        self.assertTrue(service.is_approval_required("sc.material.rental.order", company=company))
        order = self._rental_order(company, project, supplier, "ONE-STEP-ON")
        self.assertEqual(order.state, "draft")
        with self.assertRaises(UserError), self.cr.savepoint():
            order.action_activate()
        self.assertEqual(order.state, "draft")
        self.assertFalse(order.review_ids)
