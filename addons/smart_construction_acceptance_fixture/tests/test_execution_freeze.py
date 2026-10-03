# -*- coding: utf-8 -*-
import os
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..tools.frontend_productization_fixture import (
    _company,
    _contract,
    _execution,
    _funding_baseline,
    _partner,
    _project,
    _request,
    _settlement,
    _tax,
    _user,
)


@tagged(
    "post_install",
    "-at_install",
    "sc_gate",
    "acceptance_fixture_gate",
    "acceptance_fixture_execution_freeze",
)
class TestAcceptanceFixtureExecutionFreeze(TransactionCase):
    """Lock the fixture payment-execution contract against real behaviour.

    ``sc.payment.execution.create`` only admits drafts, so the fixture reconciles
    the editable facts through the ORM and then freezes the workflow state and
    paid amount on its own disposable row.  This test drives the fixture helper
    on a real chain and asserts both the frozen result - including the stored
    list projection the browser reads - and that the model guard is still intact.
    """

    def setUp(self):
        super().setUp()
        credentials = patch.dict(
            os.environ, {"SC_ACCEPTANCE_FIXTURE_PASSWORD": "scdevpass"}
        )
        credentials.start()
        self.addCleanup(credentials.stop)

    def test_execution_is_frozen_and_the_model_guard_stays_intact(self):
        env = self.env
        company = _company(env, "FREEZE")
        pm = _user(
            env,
            "fixture_role_freeze_pm",
            "Acceptance Fixture Freeze PM",
            company,
            [company],
            ["smart_construction_core.group_sc_role_project_manager"],
        )
        finance = _user(
            env,
            "fixture_role_freeze_finance",
            "Acceptance Fixture Freeze Finance",
            company,
            [company],
            ["smart_construction_core.group_sc_role_finance_manager"],
        )
        partner = _partner(env, "FREEZE", company)
        tax = _tax(env, "FREEZE", company)
        project = _project(env, "FREEZE", company, pm, partner)
        _funding_baseline(env, "FREEZE", project)
        contract, _line = _contract(env, "FREEZE", project, partner, tax, "confirmed", 1000.0)
        settlement = _settlement(env, "FREEZE", project, contract, partner, "approve", 1000.0)
        request = _request(
            env, "FREEZE", 1, project, contract, settlement, partner, "approved", 1000.0
        )

        record = _execution(
            env, "FREEZE", project, contract, request, partner, finance, "paid", 1000.0
        )

        self.assertEqual(record.state, "paid")
        self.assertAlmostEqual(record.paid_amount, 1000.0, 2)
        self.assertEqual(record.partner_payment_status_display, "已付款")
        self.assertEqual(record.partner_payment_amount_display, "1000.0")

        with self.assertRaisesRegex(UserError, "草稿"):
            env["sc.payment.execution"].sudo().create(
                {
                    "name": "FE-FREEZE-GUARD-PE-001",
                    "project_id": project.id,
                    "payment_request_id": request.id,
                    "partner_id": partner.id,
                    "state": "paid",
                }
            )
