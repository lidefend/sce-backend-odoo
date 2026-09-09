# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

from ..tools.frontend_productization_fixture import (
    _bind_xmlid,
    _funding_baseline,
)


@tagged("post_install", "-at_install", "sc_gate", "acceptance_fixture_gate")
class TestFundingBaselineFixture(TransactionCase):
    def test_active_legacy_baseline_is_reconciled_by_revision(self):
        company = self.env.company
        project = self.env["project.project"].create(
            {
                "name": "Acceptance fixture revision test",
                "company_id": company.id,
                "funding_enabled": True,
            }
        )
        baseline = self.env["project.funding.baseline"].create(
            {
                "project_id": project.id,
                "total_amount": 5000.0,
                "period_start": "2025-01-01",
                "period_end": "2025-12-31",
                "line_ids": [
                    (
                        0,
                        0,
                        {"name": "FE annual plan", "planned_amount": 5000.0},
                    )
                ],
            }
        )
        baseline.action_activate()
        suffix = "REVISION_TEST"
        _bind_xmlid(self.env, "fe_funding_baseline_%s" % suffix.lower(), baseline)
        _bind_xmlid(
            self.env,
            "fe_funding_baseline_line_%s" % suffix.lower(),
            baseline.line_ids,
        )

        revised = _funding_baseline(self.env, suffix, project)

        self.assertNotEqual(revised, baseline)
        self.assertEqual(baseline.state, "superseded")
        self.assertEqual(revised.state, "active")
        self.assertEqual(str(revised.period_start), "2026-01-01")
        self.assertEqual(str(revised.period_end), "2026-12-31")
        self.assertEqual(revised.line_ids.mapped("planned_amount"), [5000.0])
