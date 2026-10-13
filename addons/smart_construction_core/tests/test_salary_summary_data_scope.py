# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError, UserError, ValidationError


@tagged("post_install", "-at_install", "salary_summary_data_scope")
class TestSalarySummaryDataScope(TransactionCase):
    """Exercise the actual SQL view; these tests do not certify record rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.companies = cls.env["res.company"].create([
            {"name": "Salary scope synthetic A"},
            {"name": "Salary scope synthetic B"},
        ])
        cls.projects = cls.env["project.project"].create([
            {"name": "Salary scope A1", "company_id": cls.companies[0].id,
             "operation_strategy": "direct"},
            {"name": "Salary scope A2", "company_id": cls.companies[0].id,
             "operation_strategy": "direct"},
            {"name": "Salary scope B1", "company_id": cls.companies[1].id,
             "operation_strategy": "direct"},
        ])
        cls.Payroll = cls.env["sc.hr.payroll.document"].sudo()
        cls.Summary = cls.env["sc.salary.summary"].sudo()
        # Transactional DDL exercises the candidate definition and rolls back
        # with this test class. It is not an installed-runtime upgrade receipt.
        cls.Summary.init()

    def _salary(self, project, amount, *, done=True, currency=None):
        record = self.Payroll.create({
            "fact_type": "salary_registration",
            "project_id": project.id,
            "employee_name": "Synthetic scope employee",
            "period_year": 2026,
            "period_month": 10,
            "payer_unit": "Synthetic same payer",
            "currency_id": (currency or project.company_id.currency_id).id,
            "gross_amount": amount,
            "net_salary": amount,
        })
        if done:
            record.action_submit()
            record.action_done()
        self.env.flush_all()
        return record

    def _summaries(self):
        self.Summary.invalidate_model()
        return self.Summary.search([("project_id", "in", self.projects.ids)])

    def test_same_labels_do_not_combine_companies_or_projects(self):
        for project, amount in zip(self.projects, (11, 101, 1001)):
            self._salary(project, amount)
        summaries = self._summaries()
        self.assertEqual(len(summaries), 3)
        actual = {
            (row.company_id.id, row.project_id.id):
                (row.net_salary, row.document_count)
            for row in summaries
        }
        self.assertEqual(actual, {
            (project.company_id.id, project.id): (amount, 1)
            for project, amount in zip(self.projects, (11, 101, 1001))
        })

    def test_drilldown_matches_source_partition_and_done_state(self):
        included = self._salary(self.projects[0], 11)
        self._salary(self.projects[0], 17, done=False)
        self._salary(self.projects[1], 101)
        self._salary(self.projects[2], 1001)
        row = self._summaries().filtered(lambda item: item.project_id == self.projects[0])
        self.assertEqual(self.Payroll.search(row._salary_document_domain()), included)
        self.assertEqual(row.net_salary, included.net_salary)

    def test_currency_partitions_and_drilldown_remain_separate(self):
        currency = self.env["res.currency"].with_context(active_test=False).search([
            ("id", "!=", self.projects[0].company_id.currency_id.id),
        ], limit=1)
        self.assertTrue(currency, "A distinct native currency is required")
        first = self._salary(self.projects[0], 11)
        second = self._salary(self.projects[0], 101, currency=currency)
        rows = self._summaries()
        self.assertEqual(len(rows), 2)
        for row in rows:
            expected = first if row.currency_id == first.currency_id else second
            self.assertEqual(self.Payroll.search(row._salary_document_domain()), expected)
            self.assertEqual(row.net_salary, expected.net_salary)

    def test_same_partition_still_aggregates(self):
        self._salary(self.projects[0], 11)
        self._salary(self.projects[0], 101)
        row = self._summaries()
        self.assertEqual(len(row), 1)
        self.assertEqual(row.net_salary, 112)
        self.assertEqual(row.document_count, 2)
        self.assertEqual(len(self.Payroll.search(row._salary_document_domain())), 2)

    def test_unknown_ownership_is_not_a_shared_aggregate(self):
        unowned = self.Payroll.create({
            "fact_type": "salary_registration",
            "employee_name": "Synthetic unknown owner",
            "period_year": 2026, "period_month": 10,
            "payer_unit": "Synthetic unowned salary scope",
            "gross_amount": 999, "net_salary": 999,
        })
        unowned.action_submit()
        unowned.action_done()
        self.env.flush_all()
        # Legacy unresolved ownership is retained, never backfilled from the
        # executing administrator's company. New creates now have an owner.
        self.env.cr.execute(
            "UPDATE sc_hr_payroll_document SET company_id = NULL WHERE id = %s",
            [unowned.id],
        )
        unowned.invalidate_recordset()
        self.assertFalse(unowned.company_id)
        self.assertFalse(self.Summary.search([
            ("payer_unit", "=", "Synthetic unowned salary scope"),
        ]))

    def test_empty_payer_values_share_one_exact_partition(self):
        first = self._salary(self.projects[0], 11)
        second = self._salary(self.projects[0], 101)
        literal = self._salary(self.projects[0], 1001)
        # Reproduce the two legacy storage forms and an actual label-equal
        # company name, without changing the native completion workflow.
        self.env.cr.execute(
            "UPDATE sc_hr_payroll_document SET payer_unit = NULL WHERE id = %s",
            [first.id],
        )
        self.env.cr.execute(
            "UPDATE sc_hr_payroll_document SET payer_unit = '' WHERE id = %s",
            [second.id],
        )
        self.env.cr.execute(
            "UPDATE sc_hr_payroll_document SET payer_unit = %s WHERE id = %s",
            ["未填写发放单位", literal.id],
        )
        self.Payroll.invalidate_model()
        rows = self._summaries()
        self.assertEqual(len(rows), 2)
        empty = rows.filtered(lambda row: not row.payer_unit_key)
        named = rows - empty
        self.assertEqual(empty.net_salary, 112)
        self.assertEqual(self.Payroll.search(empty._salary_document_domain()), first | second)
        self.assertEqual(named.net_salary, 1001)
        self.assertEqual(self.Payroll.search(named._salary_document_domain()), literal)

    def test_company_level_salary_has_ownership_without_project(self):
        records = self.Payroll.create([
            {"fact_type": "salary_registration", "company_id": company.id,
             "employee_name": "Synthetic company payroll", "period_year": 2026,
             "period_month": 10, "payer_unit": "Synthetic company payer",
             "gross_amount": amount, "net_salary": amount}
            for company, amount in zip(self.companies, (11, 101))
        ])
        records.action_submit()
        records.action_done()
        self.env.flush_all()
        self.assertFalse(records.project_id)
        rows = self.Summary.search([("payer_unit", "=", "Synthetic company payer")])
        self.assertEqual(len(rows), 2)
        for row in rows:
            expected = records.filtered(lambda record: record.company_id == row.company_id)
            self.assertEqual(self.Payroll.search(row._salary_document_domain()), expected)
            self.assertEqual(row.net_salary, expected.net_salary)

    def test_source_rejects_project_company_mismatch(self):
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.Payroll.create({
                "fact_type": "salary_registration", "project_id": self.projects[0].id,
                "company_id": self.companies[1].id,
            })

    def test_source_ownership_cannot_be_relabelled_or_rebound(self):
        record = self._salary(self.projects[0], 11, done=False)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            record.write({"company_id": self.companies[1].id})
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            record.write({"project_id": self.projects[2].id})
        self.assertEqual(record.company_id, self.companies[0])
        self.assertEqual(record.project_id, self.projects[0])

    def test_source_cannot_have_explicit_empty_company(self):
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.Payroll.create({"fact_type": "salary_registration", "company_id": False})

    def test_copy_preserves_owner_and_rejects_cross_company_project(self):
        record = self._salary(self.projects[0], 11, done=False)
        copied = record.copy()
        self.assertEqual(copied.company_id, record.company_id)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            record.copy({"project_id": self.projects[2].id})

    def _company_salary(self):
        return self.Payroll.create({
            "fact_type": "salary_registration", "company_id": self.companies[0].id,
            "employee_name": "Synthetic company employee", "period_year": 2026,
            "period_month": 10, "gross_amount": 100, "net_salary": 100,
        })

    def test_company_salary_cannot_bypass_lifecycle(self):
        for vals in ({"state": "done"}, {"paid_amount": 50}):
            with self.subTest(vals=vals), self.assertRaises(UserError), self.env.cr.savepoint():
                self.Payroll.create({"fact_type": "salary_registration", **vals})
        record = self._company_salary()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            record.write({"state": "done"})
        record.action_submit()
        record.action_done()
        for vals in ({"net_salary": 200}, {"paid_amount": 50}, {"fact_type": "bonus"}):
            with self.subTest(vals=vals), self.assertRaises(UserError), self.env.cr.savepoint():
                record.write(vals)

    def test_context_defaults_cannot_bypass_source_lifecycle(self):
        for defaults in ({"default_state": "done"}, {"default_paid_amount": 50}):
            with self.subTest(defaults=defaults), self.assertRaises(UserError), self.env.cr.savepoint():
                self.Payroll.with_context(
                    default_project_id=self.projects[0].id,
                    default_fact_type="salary_registration", **defaults,
                ).create({})

    def test_department_and_parent_company_changes_are_guarded(self):
        department = self.env["hr.department"].create({
            "name": "Synthetic payroll department", "company_id": self.companies[0].id,
        })
        other = self.env["hr.department"].create({
            "name": "Synthetic other department", "company_id": self.companies[1].id,
        })
        record = self._salary(self.projects[0], 11, done=False)
        record.department_id = department
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            record.department_id = other
        record.active = False
        for parent in (self.projects[0], department):
            with self.subTest(parent=parent._name), self.assertRaises(ValidationError), self.env.cr.savepoint():
                parent.write({"company_id": self.companies[1].id})

    def test_non_sudo_company_and_context_spoof_are_denied(self):
        actor = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Synthetic payroll scope actor", "login": "synthetic_payroll_scope_actor",
            "company_id": self.companies[0].id,
            "company_ids": [(6, 0, self.companies[0].ids)],
            "groups_id": [(6, 0, [self.env.ref("smart_construction_core.group_sc_cap_project_user").id])],
        })
        Payroll = self.Payroll.with_user(actor)
        for context, values in (
            ({}, {"company_id": self.companies[1].id}),
            ({"default_company_id": self.companies[1].id}, {}),
            ({"allowed_company_ids": self.companies[1].ids}, {}),
        ):
            with self.subTest(context=context), self.assertRaises(AccessError), self.env.cr.savepoint():
                Payroll.with_context(**context).create({"fact_type": "salary_registration", **values})

    def test_company_payment_inherits_parent_and_cannot_change_realm(self):
        payroll = self._company_salary()
        payroll.action_submit()
        payroll.action_done()
        payment = self.env["sc.hr.salary.payment"].sudo().create({
            "payroll_document_id": payroll.id, "payment_amount": 10,
        })
        self.assertEqual(payment.company_id, payroll.company_id)
        self.assertFalse(payment.project_id)
        other = self._salary(self.projects[2], 101)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            payment.write({"payroll_document_id": other.id})
        payment.action_submit()
        payment.action_confirm()
        self.assertEqual(payroll.paid_amount, 10)

    def test_legacy_unknown_owner_cannot_be_repaired_by_ordinary_write(self):
        payroll = self._company_salary()
        self.env.flush_all()
        self.env.cr.execute("UPDATE sc_hr_payroll_document SET company_id = NULL WHERE id = %s", [payroll.id])
        payroll.invalidate_recordset()
        for vals in ({"description": "attempt"}, {"company_id": self.companies[0].id}):
            with self.subTest(vals=vals), self.assertRaises(ValidationError), self.env.cr.savepoint():
                payroll.write(vals)

    def test_rpc_context_flags_do_not_authorize_salary_writes(self):
        payroll = self._company_salary()
        for key, values in (
            ("sc_payroll_state_transition", {"state": "done"}),
            ("sc_salary_payment_summary_sync", {"paid_amount": 99}),
        ):
            with self.subTest(key=key), self.assertRaises(UserError), self.env.cr.savepoint():
                payroll.with_context(**{key: True}).write(values)
        payment = self.env["sc.hr.salary.payment"].sudo().create({
            "payroll_document_id": payroll.id, "payment_amount": 10,
        })
        with self.assertRaises(UserError), self.env.cr.savepoint():
            payment.with_context(sc_salary_payment_state_transition=True).write({"state": "confirmed"})

    def test_opening_balances_are_not_an_alternative_payment_write(self):
        payroll = self._company_salary()
        for values in ({"payment_opening_amount": 99}, {"payment_detail_initialized": True}):
            with self.subTest(values=values):
                with self.assertRaises(UserError), self.env.cr.savepoint():
                    payroll.write(values)
                with self.assertRaises(UserError), self.env.cr.savepoint():
                    self.Payroll.create({"fact_type": "salary_registration", **values})
                with self.assertRaises(UserError), self.env.cr.savepoint():
                    self.Payroll.with_context(**{
                        "default_" + key: value for key, value in values.items()
                    }).create({"fact_type": "salary_registration"})

    def test_payment_context_cannot_create_a_confirmed_payment(self):
        payroll = self._company_salary()
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self.env["sc.hr.salary.payment"].with_context(default_state="confirmed").create({
                "payroll_document_id": payroll.id, "payment_amount": 10,
            })
        payment = self.env["sc.hr.salary.payment"].with_context(default_state="confirmed").create({
            "payroll_document_id": payroll.id, "payment_amount": 10, "state": "draft",
        })
        self.assertEqual(payment.state, "draft")

    def test_type_conversion_cannot_import_payment_or_completed_state(self):
        for carried in ({"paid_amount": 10}, {"payment_opening_amount": 10},
                        {"payment_detail_initialized": True}, {"state": "done"}):
            with self.subTest(carried=carried):
                record = self.Payroll.create({"fact_type": "bonus", **carried})
                with self.assertRaises(UserError), self.env.cr.savepoint():
                    record.write({"fact_type": "salary_registration"})
        clean = self.Payroll.create({"fact_type": "bonus"})
        clean.write({"fact_type": "salary_registration"})
        self.assertEqual(clean.fact_type, "salary_registration")
