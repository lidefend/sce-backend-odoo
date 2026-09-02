# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from ..models.support import operating_metrics as opm


@tagged("post_install", "-at_install", "p1_contract_payment_allocation")
class TestContractPaymentAllocationFact(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.currency = cls.company.currency_id
        cls.partner = cls.env["res.partner"].create({"name": "Allocation Test Vendor"})
        cls.project = cls.env["project.project"].create(
            {
                "name": "Allocation Test Project",
                "company_id": cls.company.id,
                "privacy_visibility": "followers",
            }
        )
        cls.tax = cls.env["account.tax"].search(
            [("company_id", "=", cls.company.id), ("type_tax_use", "=", "purchase")],
            limit=1,
        )
        if not cls.tax:
            cls.tax = cls.env["account.tax"].create(
                {
                    "name": "Allocation Test Tax",
                    "amount": 0.0,
                    "amount_type": "percent",
                    "type_tax_use": "purchase",
                    "company_id": cls.company.id,
                }
            )
        cls.contract_a = cls._create_contract("Allocation Contract A")
        cls.contract_b = cls._create_contract("Allocation Contract B")
        cls.contract_c = cls._create_contract("Allocation Contract C")
        cls.settlement_a = cls._create_settlement("Allocation Settlement A", cls.contract_a, 100.0)
        cls.settlement_b = cls._create_settlement("Allocation Settlement B", cls.contract_b, 100.0)
        cls.settlement_c = cls._create_settlement("Allocation Settlement C", cls.contract_c, 100.0)

    @classmethod
    def _create_contract(cls, name):
        return cls.env["construction.contract"].create(
            {
                "subject": name,
                "type": "in",
                "project_id": cls.project.id,
                "partner_id": cls.partner.id,
                "company_id": cls.company.id,
                "currency_id": cls.currency.id,
                "tax_id": cls.tax.id,
            }
        )

    @classmethod
    def _create_settlement(cls, name, contract, amount):
        settlement = cls.env["sc.settlement.order"].create(
            {
                "name": name,
                "project_id": cls.project.id,
                "partner_id": cls.partner.id,
                "contract_id": contract.id,
                "company_id": cls.company.id,
                "currency_id": cls.currency.id,
                "settlement_type": "out",
                "line_ids": [(0, 0, {"name": name, "qty": 1.0, "price_unit": amount})],
            }
        )
        settlement._write_lifecycle("approve")
        return settlement

    def _request(self, name, amount, contract=None, settlement=None, line_specs=()):
        request = self.env["payment.request"].create(
            {
                "name": name,
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "currency_id": self.currency.id,
                "contract_id": contract.id if contract else False,
                "settlement_id": settlement.id if settlement else False,
                "amount": amount,
            }
        )
        for sequence, (line_settlement, line_contract, basis_amount) in enumerate(line_specs, 1):
            self.env["payment.request.line"].create(
                {
                    "request_id": request.id,
                    "sequence": sequence * 10,
                    "legacy_line_id": f"{name}-line-{sequence}",
                    "legacy_parent_id": f"{name}-parent",
                    "contract_id": line_contract.id if line_contract else False,
                    "settlement_id": line_settlement.id if line_settlement else False,
                    "settlement_line_id": line_settlement.line_ids[:1].id if line_settlement else False,
                    "amount": basis_amount,
                    "current_pay_amount": basis_amount,
                }
            )
        request.invalidate_recordset()
        self.env.cr.execute(
            "UPDATE payment_request SET state='approved', validation_status='validated' WHERE id=%s",
            (request.id,),
        )
        request.invalidate_recordset()
        return request

    def test_direct_contract_creates_complete_immutable_allocation(self):
        request = self._request(
            "Allocation Direct", 80.0, contract=self.contract_a, settlement=self.settlement_a
        )
        ledger = request.sudo()._ensure_payment_ledger(amount=80.0)
        self.assertEqual(len(ledger.contract_allocation_ids), 1)
        allocation = ledger.contract_allocation_ids
        self.assertEqual(allocation.contract_id, self.contract_a)
        self.assertEqual(allocation.allocated_amount, 80.0)
        self.assertEqual(allocation.reason_code, "direct_contract")
        self.assertEqual(ledger.contract_allocation_status, "complete")
        with self.assertRaises(AccessError):
            allocation.sudo().write({"allocated_amount": 79.0})
        with self.assertRaises(AccessError):
            ledger.sudo().write({"amount": 79.0})
        self.assertEqual(ledger.amount, 80.0)
        self.assertEqual(ledger.contract_allocated_amount, 80.0)
        self.assertEqual(ledger.contract_allocation_status, "complete")
        self.env.cr.execute(
            "UPDATE payment_ledger_allocation SET allocated_amount=81 WHERE id=%s",
            (allocation.id,),
        )
        allocation.invalidate_recordset(["allocated_amount"])
        for field_name in (
            "contract_allocated_amount",
            "contract_unallocated_amount",
            "contract_allocation_status",
        ):
            self.env.add_to_compute(ledger._fields[field_name], ledger)
        ledger._recompute_recordset(
            [
                "contract_allocated_amount",
                "contract_unallocated_amount",
                "contract_allocation_status",
            ]
        )
        self.assertEqual(ledger.contract_allocation_status, "review_required")

    def test_multi_contract_partial_payment_uses_snapshotted_line_ratio(self):
        request = self._request(
            "Allocation Multi",
            100.0,
            line_specs=(
                (self.settlement_a, self.contract_a, 60.0),
                (self.settlement_b, self.contract_b, 40.0),
            ),
        )
        ledger = request.sudo()._ensure_payment_ledger(amount=50.0)
        amounts = {
            row.contract_id.id: row.allocated_amount for row in ledger.contract_allocation_ids
        }
        self.assertEqual(amounts, {self.contract_a.id: 30.0, self.contract_b.id: 20.0})
        self.assertEqual(sum(amounts.values()), ledger.amount)

    def test_request_lines_override_conflicting_header_contract(self):
        request = self._request(
            "Allocation Line Authority",
            100.0,
            line_specs=(
                (self.settlement_b, self.contract_b, 60.0),
                (self.settlement_c, self.contract_c, 40.0),
            ),
        )
        # Simulate inconsistent imported history that normal ORM constraints reject.
        self.env.cr.execute(
            "UPDATE payment_request SET contract_id=%s WHERE id=%s",
            (self.contract_a.id, request.id),
        )
        request.invalidate_recordset(["contract_id"])
        ledger = request.sudo()._ensure_payment_ledger(amount=50.0)
        amounts = {
            row.contract_id.id: row.allocated_amount for row in ledger.contract_allocation_ids
        }
        self.assertEqual(amounts, {self.contract_b.id: 30.0, self.contract_c.id: 20.0})
        self.assertNotIn(self.contract_a.id, amounts)

    def test_currency_rounding_is_deterministic_and_exact(self):
        request = self._request(
            "Allocation Rounding",
            3.0,
            line_specs=(
                (self.settlement_a, self.contract_a, 1.0),
                (self.settlement_b, self.contract_b, 1.0),
                (self.settlement_c, self.contract_c, 1.0),
            ),
        )
        ledger = request.sudo()._ensure_payment_ledger(amount=1.0)
        rows = ledger.contract_allocation_ids.sorted("payment_request_line_id")
        self.assertEqual(sum(rows.mapped("allocated_amount")), 1.0)
        self.assertEqual(rows.mapped("allocated_amount"), [0.34, 0.33, 0.33])

    def test_basis_total_mismatch_is_explicitly_unresolved(self):
        request = self._request(
            "Allocation Mismatch",
            100.0,
            line_specs=(
                (self.settlement_a, self.contract_a, 50.0),
                (self.settlement_b, self.contract_b, 40.0),
            ),
        )
        ledger = request.sudo()._ensure_payment_ledger(amount=50.0)
        self.assertEqual(ledger.contract_allocation_status, "review_required")
        self.assertEqual(ledger.contract_allocated_amount, 0.0)
        self.assertEqual(ledger.contract_unallocated_amount, 50.0)
        self.assertEqual(
            set(ledger.contract_allocation_ids.mapped("allocation_state")),
            {"unresolved_candidate"},
        )
        self.assertEqual(
            set(ledger.contract_allocation_ids.mapped("reason_code")),
            {"basis_total_mismatch"},
        )

    def test_nonpositive_active_basis_is_never_silently_ignored(self):
        request = self._request(
            "Allocation Invalid Basis",
            100.0,
            line_specs=(
                (self.settlement_a, self.contract_a, 100.0),
                (self.settlement_b, self.contract_b, -10.0),
            ),
        )
        ledger = request.sudo()._ensure_payment_ledger(amount=50.0)
        self.assertEqual(ledger.contract_allocation_status, "review_required")
        self.assertEqual(ledger.contract_allocated_amount, 0.0)
        self.assertEqual(
            set(ledger.contract_allocation_ids.mapped("reason_code")),
            {"invalid_basis_amount"},
        )

    def test_execution_header_contract_is_not_allocation_authority(self):
        request = self._request(
            "Allocation Weak Execution", 25.0, contract=self.contract_a, settlement=self.settlement_a
        )
        self.env.cr.execute(
            """
            UPDATE payment_request
               SET payment_account_name='Allocation Test Account',
                   payment_bank_name='Allocation Test Bank',
                   payment_account_no='ACCOUNT-ALPHA'
             WHERE id=%s
            """,
            (request.id,),
        )
        request.invalidate_recordset(
            [
                "payment_account_name",
                "payment_bank_name",
                "payment_account_no",
                "payee_account_completeness",
            ]
        )
        request._compute_payee_account_completeness()
        request.flush_recordset(["payee_account_completeness"])
        execution = self.env["sc.payment.execution"].create(
            {
                "name": "Allocation Weak Execution Header",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "contract_id": self.contract_a.id,
                "payment_request_id": request.id,
                "currency_id": self.currency.id,
                "paid_amount": 25.0,
                "planned_amount": 25.0,
                "state": "paid",
            }
        )
        self.env.cr.execute(
            "UPDATE payment_request SET contract_id=NULL WHERE id=%s",
            (request.id,),
        )
        request.invalidate_recordset(["contract_id"])
        ledger = request.sudo()._ensure_payment_ledger(amount=25.0, execution=execution)
        self.assertEqual(ledger.contract_allocation_status, "review_required")
        self.assertEqual(ledger.contract_allocation_ids.allocation_state, "unresolved_global")
        self.assertFalse(ledger.contract_allocation_ids.contract_id)

    def test_missing_basis_is_global_unresolved_not_guessed(self):
        request = self._request(
            "Allocation Missing", 25.0, contract=self.contract_a, settlement=self.settlement_a
        )
        ledger = request.sudo()._ensure_payment_ledger(amount=25.0)
        values = ledger._unresolved_contract_allocation_values(
            self.env["construction.contract"], "missing_basis"
        )
        self.assertEqual(len(values), 1)
        self.assertFalse(values[0].get("contract_id"))
        self.assertEqual(values[0]["allocation_state"], "unresolved_global")
        self.assertEqual(values[0]["reason_code"], "missing_basis")

    def test_reversal_keeps_allocation_evidence_and_excludes_net_actual(self):
        request = self._request(
            "Allocation Reversal", 70.0, contract=self.contract_a, settlement=self.settlement_a
        )
        ledger = request.sudo()._ensure_payment_ledger(amount=70.0)
        allocation_ids = ledger.contract_allocation_ids.ids
        self.assertEqual(
            opm.contract_actual_paid_amount_map(self.env, [self.contract_a.id]),
            {self.contract_a.id: 70.0},
        )
        ledger.sudo().with_context(_sc_payment_ledger_internal_reversal=True).write(
            {"state": "reversed"}
        )
        self.assertEqual(ledger.contract_allocation_ids.ids, allocation_ids)
        self.assertEqual(opm.contract_actual_paid_amount_map(self.env, [self.contract_a.id]), {})

    def test_approved_request_line_allocation_basis_is_immutable(self):
        request = self._request(
            "Allocation Immutable",
            100.0,
            line_specs=((self.settlement_a, self.contract_a, 100.0),),
        )
        line = request.outflow_line_ids
        with self.assertRaises(UserError):
            line.write({"current_pay_amount": 99.0})
        with self.assertRaises(UserError):
            line.write({"contract_id": self.contract_b.id})
        draft_request = self.env["payment.request"].create(
            {
                "name": "Allocation Reparent Target",
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": self.partner.id,
                "currency_id": self.currency.id,
                "contract_id": self.contract_a.id,
                "amount": 100.0,
            }
        )
        with self.assertRaises(UserError):
            line.write({"request_id": draft_request.id})
        draft_line = self.env["payment.request.line"].create(
            {
                "request_id": draft_request.id,
                "legacy_line_id": "immutable-reverse-line",
                "legacy_parent_id": "immutable-reverse-parent",
                "contract_id": self.contract_a.id,
                "amount": 1.0,
                "current_pay_amount": 1.0,
            }
        )
        with self.assertRaises(UserError):
            draft_line.write({"request_id": request.id})
        with self.assertRaises(UserError):
            self.env["payment.request.line"].create(
                {
                    "request_id": request.id,
                    "legacy_line_id": "immutable-new-line",
                    "legacy_parent_id": "immutable-parent",
                    "contract_id": self.contract_a.id,
                    "amount": 1.0,
                    "current_pay_amount": 1.0,
                }
            )
        with self.assertRaises(UserError):
            self.env["payment.request.line"].with_context(
                default_request_id=request.id
            ).create(
                {
                    "legacy_line_id": "immutable-default-new-line",
                    "legacy_parent_id": "immutable-default-parent",
                    "contract_id": self.contract_a.id,
                    "amount": 1.0,
                    "current_pay_amount": 1.0,
                }
            )

    def test_ledger_and_allocation_builder_are_idempotent(self):
        request = self._request(
            "Allocation Idempotent", 40.0, contract=self.contract_a, settlement=self.settlement_a
        )
        first = request.sudo()._ensure_payment_ledger(amount=40.0)
        second = request.sudo()._ensure_payment_ledger(amount=40.0)
        first._ensure_contract_allocations()
        self.assertEqual(first, second)
        self.assertEqual(len(first.contract_allocation_ids), 1)

    def test_backfill_repairs_stored_scope_columns_idempotently(self):
        request = self._request(
            "Allocation Backfill Scope", 15.0, contract=self.contract_a, settlement=self.settlement_a
        )
        allocation = request.sudo()._ensure_payment_ledger(amount=15.0).contract_allocation_ids
        ledger = allocation.ledger_id
        self.env.cr.execute(
            "DELETE FROM payment_ledger_allocation WHERE id=%s",
            (allocation.id,),
        )
        self.env.cr.execute(
            """
            UPDATE payment_ledger
               SET contract_allocated_amount=NULL,
                   contract_unallocated_amount=NULL,
                   contract_allocation_status=NULL
             WHERE id=%s
            """,
            (ledger.id,),
        )
        self.env["payment.ledger.allocation"].init()
        ledger.invalidate_recordset(
            [
                "contract_allocation_ids",
                "contract_allocated_amount",
                "contract_unallocated_amount",
                "contract_allocation_status",
            ]
        )
        allocation = ledger.contract_allocation_ids
        self.assertEqual(allocation.payment_request_id, request)
        self.assertEqual(allocation.project_id, self.project)
        self.assertEqual(allocation.company_id, self.company)
        self.assertEqual(allocation.currency_id, self.currency)
        self.assertEqual(ledger.contract_allocated_amount, 15.0)
        self.assertEqual(ledger.contract_unallocated_amount, 0.0)
        self.assertEqual(ledger.contract_allocation_status, "complete")
        self.env.cr.execute(
            "SELECT ctid::text FROM payment_ledger WHERE id=%s",
            (ledger.id,),
        )
        ledger_tuple_location = self.env.cr.fetchone()[0]
        self.env["payment.ledger.allocation"].init()
        self.assertEqual(len(ledger.contract_allocation_ids), 1)
        self.env.cr.execute(
            "SELECT ctid::text FROM payment_ledger WHERE id=%s",
            (ledger.id,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], ledger_tuple_location)

    def test_backfill_never_uses_header_contract_when_active_lines_exist(self):
        request = self._request(
            "Allocation Backfill Lines Override Header",
            15.0,
            contract=self.contract_a,
            settlement=self.settlement_a,
            line_specs=((self.settlement_a, self.contract_a, 15.0),),
        )
        ledger = request.sudo()._ensure_payment_ledger(amount=15.0)
        self.env.cr.execute(
            "DELETE FROM payment_ledger_allocation WHERE ledger_id=%s",
            (ledger.id,),
        )
        self.env["payment.ledger.allocation"].init()
        ledger.invalidate_recordset(["contract_allocation_ids"])
        allocation = ledger.contract_allocation_ids
        self.assertEqual(len(allocation), 1)
        self.assertEqual(allocation.allocation_state, "unresolved_global")
        self.assertEqual(allocation.reason_code, "historical_backfill_unresolved")
        self.assertFalse(allocation.contract_id)

    def test_allocation_visibility_is_project_and_company_scoped(self):
        def create_user(login, groups, company=None):
            company = company or self.company
            return self.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": login,
                    "login": login,
                    "email": f"{login}@example.com",
                    "company_id": company.id,
                    "company_ids": [(6, 0, [company.id])],
                    "groups_id": [(6, 0, [self.env.ref(xmlid).id for xmlid in groups])],
                }
            )

        finance_read = "smart_construction_core.group_sc_cap_finance_read"
        visible_user = create_user("allocation_visible", [finance_read])
        finance_user = create_user(
            "allocation_finance_user",
            ["smart_construction_core.group_sc_cap_finance_user"],
        )
        hidden_user = create_user("allocation_hidden", [finance_read])
        finance_manager = create_user(
            "allocation_manager",
            ["smart_construction_core.group_sc_cap_finance_manager"],
        )
        no_access_user = create_user("allocation_no_access", ["base.group_user"])
        self.project.message_subscribe(
            partner_ids=[visible_user.partner_id.id, finance_user.partner_id.id]
        )

        request = self._request(
            "Allocation Visibility", 20.0, contract=self.contract_a, settlement=self.settlement_a
        )
        allocation = request.sudo()._ensure_payment_ledger(amount=20.0).contract_allocation_ids
        self.assertEqual(allocation.with_user(visible_user).read(["allocated_amount"])[0]["id"], allocation.id)
        self.assertEqual(allocation.with_user(finance_user).read(["allocated_amount"])[0]["id"], allocation.id)
        self.assertEqual(allocation.with_user(finance_manager).read(["allocated_amount"])[0]["id"], allocation.id)
        with self.assertRaises(AccessError):
            allocation.with_user(hidden_user).read(["allocated_amount"])
        with self.assertRaises(AccessError):
            allocation.with_user(no_access_user).read(["allocated_amount"])
        controlled_values = {
            "ledger_id": allocation.ledger_id.id,
            "contract_id": self.contract_a.id,
            "basis_amount": 1.0,
            "allocated_amount": 1.0,
            "allocation_state": "allocated",
            "reason_code": "direct_contract",
            "allocation_key": "forbidden-manual",
        }
        for user in (visible_user, finance_user, finance_manager, no_access_user):
            with self.assertRaises(AccessError):
                self.env["payment.ledger.allocation"].with_user(user).create(controlled_values)
            with self.assertRaises(AccessError):
                allocation.with_user(user).write({"allocated_amount": 1.0})
            with self.assertRaises(AccessError):
                allocation.with_user(user).unlink()

        other_company = self.env["res.company"].create(
            {"name": "Allocation Other Company", "currency_id": self.currency.id}
        )
        other_project = self.env["project.project"].create(
            {
                "name": "Allocation Other Project",
                "company_id": other_company.id,
                "privacy_visibility": "followers",
            }
        )
        country = (
            other_company.account_fiscal_country_id
            or other_company.partner_id.country_id
            or self.env.ref("base.cn")
        )
        other_tax_group = self.env["account.tax.group"].with_company(other_company).create(
            {
                "name": "Allocation Other Tax Group",
                "company_id": other_company.id,
                "country_id": country.id,
            }
        )
        other_tax = self.env["account.tax"].with_company(other_company).create(
            {
                "name": "Allocation Other Tax",
                "amount": 0.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "company_id": other_company.id,
                "tax_group_id": other_tax_group.id,
                "country_id": country.id,
            }
        )
        other_contract = self.env["construction.contract"].with_company(other_company).create(
            {
                "subject": "Allocation Other Contract",
                "type": "in",
                "project_id": other_project.id,
                "partner_id": self.partner.id,
                "company_id": other_company.id,
                "currency_id": self.currency.id,
                "tax_id": other_tax.id,
            }
        )
        other_settlement = self.env["sc.settlement.order"].with_company(other_company).create(
            {
                "name": "Allocation Other Settlement",
                "project_id": other_project.id,
                "partner_id": self.partner.id,
                "contract_id": other_contract.id,
                "company_id": other_company.id,
                "currency_id": self.currency.id,
                "settlement_type": "out",
                "line_ids": [(0, 0, {"name": "Other", "qty": 1.0, "price_unit": 10.0})],
            }
        )
        other_settlement._write_lifecycle("approve")
        other_request = self.env["payment.request"].with_company(other_company).create(
            {
                "name": "Allocation Other Request",
                "type": "pay",
                "project_id": other_project.id,
                "partner_id": self.partner.id,
                "company_id": other_company.id,
                "currency_id": self.currency.id,
                "contract_id": other_contract.id,
                "settlement_id": other_settlement.id,
                "amount": 10.0,
            }
        )
        self.env.cr.execute(
            "UPDATE payment_request SET state='approved', validation_status='validated' WHERE id=%s",
            (other_request.id,),
        )
        other_request.invalidate_recordset()
        other_allocation = other_request.sudo()._ensure_payment_ledger(amount=10.0).contract_allocation_ids
        with self.assertRaises(AccessError):
            other_allocation.with_user(finance_manager).read(["allocated_amount"])
