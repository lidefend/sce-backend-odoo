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
