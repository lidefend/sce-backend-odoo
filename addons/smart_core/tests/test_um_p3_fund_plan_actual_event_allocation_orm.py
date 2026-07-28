# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "admin_vis_p3_project_record_rule_orm")
class TestUmP3FundPlanActualEventAllocationOrm(TransactionCase):
    """Real-ORM proof for explicit amount-bearing budget/event allocation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create(
            {"name": "UM-P3 S02 company B"}
        )
        base_user = cls.env.ref("base.group_user")
        finance_user = cls.env.ref(
            "smart_construction_core.group_sc_cap_finance_user"
        )
        project_read = cls.env.ref(
            "smart_construction_core.group_sc_cap_project_read"
        )
        cls.caller = cls.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "UM-P3 S02 allocation caller",
                "login": "um_p3_s02_allocation_caller",
                "email": "um_p3_s02@example.invalid",
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, [cls.company_a.id])],
                "groups_id": [
                    (6, 0, [base_user.id, finance_user.id, project_read.id])
                ],
            }
        )
        cls.setup_context = {
            **cls.env.context,
            "allowed_company_ids": [cls.company_a.id, cls.company_b.id],
            "tracking_disable": True,
        }
        Project = cls.env["project.project"].with_context(cls.setup_context)

        def project(label, company, owner):
            return Project.create(
                {
                    "name": f"UM-P3 S02 {label}",
                    "code": f"UM-P3-S02-{label}",
                    "company_id": company.id,
                    "privacy_visibility": "followers",
                    "user_id": owner.id,
                    "funding_enabled": True,
                }
            )

        cls.project_a = project("project-a", cls.company_a, cls.caller)
        cls.project_a_other = project(
            "project-a-other",
            cls.company_a,
            cls.caller,
        )
        cls.hidden_project = project(
            "project-hidden",
            cls.company_a,
            cls.env.user,
        )
        cls.project_b = project("project-b", cls.company_b, cls.env.user)
        cls.partner = cls.env["res.partner"].create(
            {"name": "UM-P3 S02 supplier"}
        )
        cls.other_partner = cls.env["res.partner"].create(
            {"name": "UM-P3 S02 other supplier"}
        )
        cls.tax = cls.env["account.tax"].search(
            [("type_tax_use", "in", ("purchase", "none"))],
            limit=1,
        )

        def baseline(label, project_record, state, line_amounts):
            return cls.env["project.funding.baseline"].with_context(
                cls.setup_context
            ).create(
                {
                    "project_id": project_record.id,
                    "total_amount": sum(line_amounts),
                    "state": state,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": f"{label} bucket {index}",
                                "planned_amount": amount,
                            },
                        )
                        for index, amount in enumerate(line_amounts, start=1)
                    ],
                }
            )

        cls.baseline_a = baseline(
            "baseline-a",
            cls.project_a,
            "active",
            [500.0, 500.0],
        )
        cls.baseline_a_next = baseline(
            "baseline-a-next",
            cls.project_a,
            "draft",
            [1000.0],
        )
        cls.baseline_a_other = baseline(
            "baseline-a-other-project",
            cls.project_a_other,
            "active",
            [500.0],
        )
        cls.hidden_baseline = baseline(
            "baseline-hidden",
            cls.hidden_project,
            "active",
            [500.0],
        )
        cls.baseline_b = baseline(
            "baseline-b",
            cls.project_b,
            "active",
            [500.0],
        )

        def actual_event(label, project_record, partner, amount):
            Contract = cls.env["construction.contract"].with_context(
                cls.setup_context
            )
            contract = Contract.create(
                {
                    "subject": f"UM-P3 S02 {label} contract",
                    "type": "in",
                    "project_id": project_record.id,
                    "company_id": project_record.company_id.id,
                    "partner_id": partner.id,
                    "tax_id": cls.tax.id,
                }
            )
            settlement = cls.env["sc.settlement.order"].with_context(
                cls.setup_context
            ).create(
                {
                    "project_id": project_record.id,
                    "company_id": project_record.company_id.id,
                    "partner_id": partner.id,
                    "settlement_type": "out",
                    "title": f"UM-P3 S02 {label} settlement",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": f"{label} line",
                                "contract_id": contract.id,
                                "qty": 1.0,
                                "price_unit": amount,
                            },
                        )
                    ],
                }
            )
            settlement.write({"state": "approve"})
            request = cls.env["payment.request"].with_context(
                cls.setup_context
            ).create(
                {
                    "project_id": project_record.id,
                    "partner_id": partner.id,
                    "contract_id": contract.id,
                    "settlement_id": settlement.id,
                    "amount": amount,
                    "type": "pay",
                }
            )
            cls.env.cr.execute(
                """
                UPDATE payment_request
                   SET state = 'approved',
                       validation_status = 'validated'
                 WHERE id = %s
                """,
                [request.id],
            )
            cls.env.invalidate_all()
            request = cls.env["payment.request"].browse(request.id)
            event = request.with_context(
                payment_soft_gate=True
            )._ensure_payment_ledger(amount=amount)
            return request, event

        cls.request_a1, cls.event_a1 = actual_event(
            "event-a1",
            cls.project_a,
            cls.partner,
            100.0,
        )
        cls.request_a2, cls.event_a2 = actual_event(
            "event-a2",
            cls.project_a,
            cls.other_partner,
            80.0,
        )
        cls.request_a_other, cls.event_a_other = actual_event(
            "event-a-other",
            cls.project_a_other,
            cls.partner,
            70.0,
        )
        cls.hidden_request, cls.hidden_event = actual_event(
            "event-hidden",
            cls.hidden_project,
            cls.partner,
            60.0,
        )
        cls.request_b, cls.event_b = actual_event(
            "event-b",
            cls.project_b,
            cls.partner,
            50.0,
        )
        cls.caller_env = cls.env(
            user=cls.caller,
            context={
                **cls.env.context,
                "allowed_company_ids": [cls.company_a.id],
                "tracking_disable": True,
            },
        )

    def _allocation(self, line, event, amount, env=None):
        env = env or self.caller_env
        return env["project.funding.actual.event.allocation"].create(
            {
                "plan_line_id": line.id,
                "actual_event_id": event.id,
                "allocated_amount": amount,
            }
        )

    def test_single_plan_line_allocates_single_actual_event(self):
        allocation = self._allocation(
            self.baseline_a.line_ids[0],
            self.event_a1,
            100.0,
        )
        self.assertEqual(allocation.project_id, self.project_a)
        self.assertEqual(allocation.company_id, self.company_a)
        self.assertEqual(allocation.currency_id, self.event_a1.currency_id)
        self.assertEqual(self.event_a1.fund_plan_allocated_amount, 100.0)
        self.assertEqual(self.event_a1.fund_plan_unallocated_amount, 0.0)

    def test_multiple_plan_lines_allocate_one_actual_event(self):
        self._allocation(self.baseline_a.line_ids[0], self.event_a1, 40.0)
        self._allocation(self.baseline_a.line_ids[1], self.event_a1, 60.0)
        self.assertEqual(len(self.event_a1.fund_plan_allocation_ids), 2)
        self.assertEqual(self.event_a1.fund_plan_allocated_amount, 100.0)

    def test_one_plan_line_allocates_multiple_actual_events(self):
        line = self.baseline_a.line_ids[0]
        self._allocation(line, self.event_a1, 40.0)
        self._allocation(line, self.event_a2, 30.0)
        self.assertEqual(set(line.allocation_ids.mapped("actual_event_id").ids), {
            self.event_a1.id,
            self.event_a2.id,
        })
        self.assertEqual(line.allocated_amount, 70.0)

    def test_partial_exact_and_unallocated_events_are_valid(self):
        self.assertFalse(self.event_a1.fund_plan_allocation_ids)
        partial = self._allocation(
            self.baseline_a.line_ids[0],
            self.event_a1,
            25.0,
        )
        self.assertEqual(self.event_a1.fund_plan_unallocated_amount, 75.0)
        partial.write({"allocated_amount": 100.0})
        self.assertEqual(self.event_a1.fund_plan_unallocated_amount, 0.0)

    def test_overallocation_and_nonpositive_amounts_are_rejected(self):
        self._allocation(self.baseline_a.line_ids[0], self.event_a1, 70.0)
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self._allocation(
                self.baseline_a.line_ids[1],
                self.event_a1,
                31.0,
            )
        for amount in (0.0, -1.0):
            with self.env.cr.savepoint(), self.assertRaises(ValidationError):
                self._allocation(
                    self.baseline_a.line_ids[1],
                    self.event_a2,
                    amount,
                )

    def test_cross_company_and_cross_project_pairs_are_rejected(self):
        Allocation = self.env["project.funding.actual.event.allocation"]
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self._allocation(
                self.baseline_a.line_ids[0],
                self.event_b,
                10.0,
                env=self.env,
            )
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self._allocation(
                self.baseline_a.line_ids[0],
                self.event_a_other,
                10.0,
                env=self.env,
            )
        self.assertFalse(Allocation.search([]))

    def test_counterparty_and_contract_are_not_invented_plan_dimensions(self):
        line = self.baseline_a.line_ids[0]
        self.assertNotIn("partner_id", line._fields)
        self.assertNotIn("contract_id", line._fields)
        allocation = self._allocation(line, self.event_a2, 20.0)
        self.assertEqual(
            allocation.actual_event_id.partner_id,
            self.other_partner,
        )

    def test_no_active_plan_project_or_request_auto_binding(self):
        self.assertEqual(self.baseline_a.state, "active")
        self.assertEqual(self.event_a1.project_id, self.baseline_a.project_id)
        self.assertTrue(self.event_a1.payment_request_id)
        self.assertFalse(self.event_a1.fund_plan_allocation_ids)
        self.assertFalse(self.request_a1._fields.get("fund_plan_allocation_ids"))

    def test_plan_version_switch_preserves_existing_allocation(self):
        allocation = self._allocation(
            self.baseline_a.line_ids[0],
            self.event_a1,
            50.0,
        )
        self.baseline_a.write({"state": "closed"})
        self.baseline_a_next.write({"state": "active"})
        self.assertEqual(allocation.plan_line_id.baseline_id, self.baseline_a)
        self.assertEqual(allocation.allocated_amount, 50.0)

    def test_create_write_unlink_and_event_write_revalidate(self):
        allocation = self._allocation(
            self.baseline_a.line_ids[0],
            self.event_a1,
            40.0,
            env=self.env,
        )
        allocation.write(
            {
                "plan_line_id": self.baseline_a.line_ids[1].id,
                "allocated_amount": 60.0,
            }
        )
        self.assertEqual(
            allocation.plan_line_id,
            self.baseline_a.line_ids[1],
        )
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self.event_a1.write({"amount": 59.0})
        allocation.unlink()
        self.assertFalse(self.event_a1.fund_plan_allocation_ids)

    def test_one2many_and_import_context_cannot_bypass_validation(self):
        self.event_a1.write(
            {
                "fund_plan_allocation_ids": [
                    (
                        0,
                        0,
                        {
                            "plan_line_id": self.baseline_a.line_ids[0].id,
                            "allocated_amount": 50.0,
                        },
                    )
                ]
            }
        )
        with self.env.cr.savepoint(), self.assertRaises(ValidationError):
            self.caller_env[
                "project.funding.actual.event.allocation"
            ].with_context(import_file=True).create(
                {
                    "plan_line_id": self.baseline_a.line_ids[1].id,
                    "actual_event_id": self.event_a1.id,
                    "allocated_amount": 51.0,
                }
            )

    def test_unauthorized_and_nonexistent_identifiers_are_equivalent(self):
        observations = []
        for event_id in (
            self.hidden_event.id,
            self.hidden_event.id + 1000000,
        ):
            with self.env.cr.savepoint(), self.assertRaises(AccessError) as raised:
                self._allocation(
                    self.baseline_a.line_ids[0],
                    self.env["payment.ledger"].browse(event_id),
                    10.0,
                )
            observations.append((type(raised.exception), str(raised.exception)))
        self.assertEqual(observations[0], observations[1])

    def test_allowed_company_and_administrator_contracts_hold(self):
        self.assertFalse(
            self.caller_env[
                "project.funding.actual.event.allocation"
            ].search([("company_id", "=", self.company_b.id)])
        )
        allocation = self._allocation(
            self.baseline_b.line_ids[0],
            self.event_b,
            20.0,
            env=self.env,
        )
        self.assertEqual(allocation.company_id, self.company_b)
        allocation.unlink()

    def test_allocated_plan_line_and_event_deletion_are_blocked(self):
        allocation = self._allocation(
            self.baseline_a.line_ids[0],
            self.event_a1,
            10.0,
            env=self.env,
        )
        with self.env.cr.savepoint(), self.assertRaises(UserError):
            allocation.plan_line_id.unlink()
        with self.env.cr.savepoint(), self.assertRaises(UserError):
            allocation.actual_event_id.unlink()

    def test_funding_baseline_search_obeys_project_and_company_scope(self):
        Baseline = self.caller_env["project.funding.baseline"]
        visible_ids = set(Baseline.search([]).ids)
        self.assertIn(self.baseline_a.id, visible_ids)
        self.assertIn(self.baseline_a_next.id, visible_ids)
        self.assertNotIn(self.hidden_baseline.id, visible_ids)
        self.assertNotIn(self.baseline_b.id, visible_ids)

    def test_funding_baseline_create_hides_unauthorized_and_missing_projects(self):
        observations = []
        for project_id in (
            self.hidden_project.id,
            self.hidden_project.id + 1000000,
        ):
            with self.env.cr.savepoint(), self.assertRaises(AccessError) as raised:
                self.caller_env["project.funding.baseline"].create(
                    {
                        "project_id": project_id,
                        "total_amount": 10.0,
                    }
                )
            observations.append((type(raised.exception), str(raised.exception)))
        self.assertEqual(observations[0], observations[1])

    def test_funding_baseline_write_revalidates_target_project(self):
        baseline = self.caller_env["project.funding.baseline"].create(
            {
                "project_id": self.project_a.id,
                "total_amount": 10.0,
            }
        )
        observations = []
        for project_id in (
            self.hidden_project.id,
            self.hidden_project.id + 1000000,
        ):
            with self.env.cr.savepoint(), self.assertRaises(AccessError) as raised:
                baseline.write({"project_id": project_id})
            observations.append((type(raised.exception), str(raised.exception)))
        self.assertEqual(observations[0], observations[1])
        self.assertEqual(baseline.project_id, self.project_a)

    def test_funding_baseline_follower_visibility_is_dynamic(self):
        Baseline = self.caller_env["project.funding.baseline"]
        self.assertFalse(Baseline.search([("id", "=", self.hidden_baseline.id)]))
        self.hidden_project.message_subscribe(
            partner_ids=[self.caller.partner_id.id]
        )
        self.assertEqual(
            Baseline.search([("id", "=", self.hidden_baseline.id)]),
            self.hidden_baseline,
        )
        self.hidden_project.message_unsubscribe(
            partner_ids=[self.caller.partner_id.id]
        )
        self.assertFalse(Baseline.search([("id", "=", self.hidden_baseline.id)]))

    def test_funding_baseline_admin_contract_and_cross_company_boundary(self):
        with self.env.cr.savepoint(), self.assertRaises(AccessError):
            self.caller_env["project.funding.baseline"].create(
                {
                    "project_id": self.project_b.id,
                    "total_amount": 10.0,
                }
            )
        self.assertEqual(
            self.env["project.funding.baseline"].with_context(
                allowed_company_ids=[self.company_a.id, self.company_b.id]
            ).search_count([]),
            5,
        )
