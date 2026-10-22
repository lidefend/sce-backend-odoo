# -*- coding: utf-8 -*-
"""Read-only F4 approval/numbering/permission readiness probe."""
from __future__ import annotations

import json

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "-standard", "demo_usage_foundation_approval")
class TestDemoUsageFoundationApproval(TransactionCase):
    def test_approval_readiness_and_zero_reviewer_groups(self):
        report = {
            "policies": 0,
            "steps": 0,
            "zero_reviewer_steps": [],
            "numbering_active": 0,
            "errors": [],
        }
        try:
            policies = self.env["sc.approval.policy"].search([])
            report["policies"] = len(policies)
            steps = self.env["sc.approval.step"].search([])
            report["steps"] = len(steps)
            for step in steps:
                group = step.approve_group_id or step.policy_id.manager_group_id
                users = 0
                if group:
                    users = self.env["res.users"].search_count(
                        [("groups_id", "in", group.id), ("share", "=", False), ("active", "=", True)]
                    )
                if users == 0:
                    report["zero_reviewer_steps"].append(
                        {
                            "id": step.id,
                            "policy": step.policy_id.id if step.policy_id else None,
                            "group": group.id if group else None,
                            "group_xmlid": group.get_external_id().get(group.id) if group else None,
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            report["errors"].append(f"{type(exc).__name__}: {exc}")

        try:
            report["numbering_active"] = self.env["ir.sequence"].search_count(
                [("active", "=", True)]
            )
        except Exception as exc:  # noqa: BLE001
            report.setdefault("errors", []).append(f"ir.sequence {type(exc).__name__}: {exc}")

        print("DEMO_APPROVAL_REPORT " + json.dumps(report, ensure_ascii=False))
        self.assertEqual(report["errors"], [])
        self.assertGreater(report["policies"], 0)
        self.assertGreater(report["steps"], 0)
        self.assertEqual(report["zero_reviewer_steps"], [])
        self.assertGreater(report["numbering_active"], 0)
