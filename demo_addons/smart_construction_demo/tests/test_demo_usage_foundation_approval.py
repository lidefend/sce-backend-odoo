# -*- coding: utf-8 -*-
"""Read-only F4 approval/numbering/permission readiness probe."""
from __future__ import annotations

import json

from odoo.tests.common import TransactionCase, tagged
from ..tools.scenario_loader import _DEMO_APPROVAL_ACTORS


@tagged("post_install", "-at_install", "-standard", "demo_usage_foundation_approval")
class TestDemoUsageFoundationApproval(TransactionCase):
    def test_approval_readiness_and_zero_reviewer_groups(self):
        report = {
            "policies": 0,
            "steps": 0,
            "zero_reviewer_steps": [],
            "declared_actor_access_gaps": [],
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
                # A populated group does not prove the declared demo seat can
                # use the document. Keep API execution as a separate gate.
                group_xmlid = group.get_external_id().get(group.id) if group else None
                actor_xmlid = _DEMO_APPROVAL_ACTORS.get(group_xmlid)
                if actor_xmlid:
                    actor = self.env.ref(actor_xmlid, raise_if_not_found=False)
                    model_name = step.policy_id.target_model
                    reason = None
                    if not actor or not actor.active or actor not in group.users:
                        reason = "declared_actor_missing_inactive_or_not_in_group"
                    elif model_name not in self.env or not self.env[model_name].with_user(actor).check_access_rights("read", raise_exception=False):
                        reason = "declared_actor_lacks_model_read"
                    if reason:
                        report["declared_actor_access_gaps"].append({
                            "step": step.id, "model": model_name,
                            "actor_xmlid": actor_xmlid, "reason": reason,
                        })
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
        self.assertEqual(report["declared_actor_access_gaps"], [])
        self.assertGreater(report["numbering_active"], 0)
