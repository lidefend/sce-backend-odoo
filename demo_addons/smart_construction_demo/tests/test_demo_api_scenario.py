# -*- coding: utf-8 -*-
"""Read-only API scenario-driver surface readback.

The full role-driven four-tier approval journey is owned by the product layer's
action-surface tests. This demo-layer check pins the preconditions the demo
scenario driver relies on: the floorplan payment fixture is drivable and the
multi-tier approval chain is wired for ``payment.request``.
"""
from __future__ import annotations

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "-standard", "demo_api_scenario")
class TestDemoApiScenarioSurface(TransactionCase):
    def test_payment_approval_chain_surface_wired(self):
        fixture = self.env.ref(
            "smart_construction_demo.payment_request_floorplan_demo_record"
        )
        self.assertEqual(fixture.state, "draft")
        self.assertTrue(fixture.amount > 0)
        self.assertTrue(fixture.contract_id)
        self.assertTrue(hasattr(type(fixture), "action_submit"))
        self.assertTrue(hasattr(type(fixture), "action_approval_decision"))

        tiers = (
            self.env["tier.definition"]
            .sudo()
            .search_count([("model_id.model", "=", "payment.request")])
        )
        self.assertGreaterEqual(tiers, 2)
        policies = (
            self.env["sc.approval.policy"]
            .sudo()
            .search_count([("target_model", "=", "payment.request")])
        )
        self.assertGreaterEqual(policies, 1)

    def test_four_tier_approval_role_driven(self):
        from odoo.exceptions import AccessError, UserError, ValidationError

        from ..seed.steps.step_payment_request_floorplan_demo import _guidance_fixture

        result = _guidance_fixture(self.env)
        payment = self.env["payment.request"].browse(result["payment_request_id"])
        self.assertEqual(payment.state, "draft")
        self.assertFalse(result["guidance"]["blocking"])

        submitter = self.env.ref("smart_construction_demo.user_demo_role_project_a_member")
        material = self.env.ref("smart_construction_demo.user_sc_material_01")

        submitted = payment.with_user(submitter).sudo(False)
        submitted.action_submit()
        self.assertIn(payment.state, ("submit", "approve", "approved", "done"))
        self.assertTrue(payment.review_ids)

        with self.assertRaises(UserError):
            submitted.action_submit()

        with self.assertRaises(ValidationError):
            payment.with_user(material).sudo(False).action_approval_decision()

        approvals = 0
        for _ in range(12):
            payment = payment.sudo()
            waiting = payment.review_ids.filtered(
                lambda review: review.status in ("pending", "waiting")
            )
            if not waiting:
                break
            review = waiting[0]
            candidates = review.reviewer_ids.filtered(
                lambda user: (
                    user.has_group("smart_construction_core.group_sc_cap_finance_manager")
                    or user.has_group("smart_construction_core.group_sc_role_executive")
                    or user.has_group("smart_core.group_smart_core_finance_approver")
                )
            )
            if not candidates:
                candidates = review.reviewer_ids
            if not candidates:
                raise AssertionError("no reviewer for approval tier %s" % review.sequence)
            actor = candidates[0]
            before = len(payment.review_ids)
            payment.with_user(actor).sudo(False).action_approval_decision()
            approvals += 1
            self.assertEqual(len(payment.review_ids), before)

        self.assertGreaterEqual(approvals, 1)
        self.assertIn(payment.state, ("approved", "done"))
