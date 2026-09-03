# -*- coding: utf-8 -*-
import os
import runpy
import threading
import uuid
from unittest.mock import patch

from psycopg2.errors import SerializationFailure

from odoo import SUPERUSER_ID, api
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules.module import get_module_path
from odoo.modules.registry import Registry
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "sc_gate", "p1_funding_authority")
class TestP1FundingAuthority(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({
            "name": "P1 资金权威项目",
            "code": "P1-FUND-AUTH",
            "funding_enabled": True,
            "company_id": cls.env.company.id,
        })

    def _draft(self, total=100.0, start="2026-01-01", end="2026-12-31"):
        return self.env["project.funding.baseline"].create({
            "project_id": self.project.id,
            "total_amount": total,
            "period_start": start,
            "period_end": end,
            "line_ids": [
                (0, 0, {"name": "人工费", "planned_amount": total * 0.6}),
                (0, 0, {"name": "材料费", "planned_amount": total * 0.4}),
            ],
        })

    def _commercial_basis(self, label):
        partner = self.env["res.partner"].create({"name": f"{label}供应商"})
        tax = self.env["account.tax"].search([
            ("company_id", "=", self.env.company.id),
            ("type_tax_use", "=", "purchase"),
        ], limit=1)
        if not tax:
            tax = self.env["account.tax"].create({
                "name": f"{label}测试税率", "amount": 0.0,
                "amount_type": "percent", "type_tax_use": "purchase",
                "company_id": self.env.company.id,
            })
        contract = self.env["construction.contract"].create({
            "subject": f"{label}合同", "type": "in",
            "project_id": self.project.id, "partner_id": partner.id,
            "company_id": self.env.company.id,
            "currency_id": self.env.company.currency_id.id, "tax_id": tax.id,
        })
        return partner, contract

    def _finance_user(self, login, group_xmlid):
        user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": login,
            "login": login,
            "company_id": self.env.company.id,
            "company_ids": [(6, 0, [self.env.company.id])],
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref(group_xmlid).id,
            ])],
        })
        self.project.message_subscribe(partner_ids=[user.partner_id.id])
        return user

    def _cleanup_committed_concurrency_project(self, project_id):
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cursor:
            cleanup_env = api.Environment(cursor, SUPERUSER_ID, {})
            baselines = cleanup_env["project.funding.baseline"].sudo().search([
                ("project_id", "=", project_id),
            ])
            if baselines:
                cleanup_env["mail.activity"].sudo().search([
                    ("res_model", "=", "project.funding.baseline"),
                    ("res_id", "in", baselines.ids),
                ]).unlink()
                cleanup_env["mail.followers"].sudo().search([
                    ("res_model", "=", "project.funding.baseline"),
                    ("res_id", "in", baselines.ids),
                ]).unlink()
                cleanup_env["mail.message"].sudo().search([
                    ("model", "=", "project.funding.baseline"),
                    ("res_id", "in", baselines.ids),
                ]).unlink()
            cursor.execute(
                "DELETE FROM project_funding_baseline WHERE project_id = %s",
                [project_id],
            )
            cleanup_env["project.project"].browse(project_id).exists().unlink()
            cursor.execute(
                """
                SELECT
                    EXISTS(SELECT 1 FROM project_project WHERE id = %s),
                    EXISTS(
                        SELECT 1 FROM project_funding_baseline
                         WHERE project_id = %s
                    )
                """,
                [project_id, project_id],
            )
            if any(cursor.fetchone()):
                raise AssertionError(
                    f"concurrency fixture cleanup failed for project {project_id}"
                )
            cursor.commit()

    def _cleanup_committed_submit_fixture(
        self, project_id, partner_id, contract_id, request_ids, created_tax_id,
        previous_funding_cap_block,
    ):
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as cursor:
            cleanup_env = api.Environment(
                cursor, SUPERUSER_ID, {"tracking_disable": True}
            )
            cleanup_env["sc.audit.log"].sudo().search([
                ("model", "=", "payment.request"),
                ("res_id", "in", request_ids),
            ]).unlink()
            cursor.execute(
                "UPDATE payment_request SET state = 'cancel' WHERE id = ANY(%s)",
                [request_ids],
            )
            requests = cleanup_env["payment.request"].sudo().browse(request_ids)
            requests.invalidate_recordset()
            requests.exists().unlink()
            cleanup_env["construction.contract"].sudo().browse(
                contract_id
            ).exists().unlink()
            if created_tax_id:
                cleanup_env["account.tax"].sudo().browse(
                    created_tax_id
                ).exists().unlink()
            baselines = cleanup_env["project.funding.baseline"].sudo().search([
                ("project_id", "=", project_id),
            ])
            if baselines:
                cleanup_env["mail.activity"].sudo().search([
                    ("res_model", "=", "project.funding.baseline"),
                    ("res_id", "in", baselines.ids),
                ]).unlink()
                cleanup_env["mail.followers"].sudo().search([
                    ("res_model", "=", "project.funding.baseline"),
                    ("res_id", "in", baselines.ids),
                ]).unlink()
                cleanup_env["mail.message"].sudo().search([
                    ("model", "=", "project.funding.baseline"),
                    ("res_id", "in", baselines.ids),
                ]).unlink()
            cursor.execute(
                "DELETE FROM project_funding_baseline WHERE project_id = %s",
                [project_id],
            )
            cleanup_env["project.project"].sudo().browse(
                project_id
            ).exists().unlink()
            cleanup_env["res.partner"].sudo().browse(partner_id).exists().unlink()
            cleanup_env["ir.config_parameter"].sudo().set_param(
                "sc.payment.force_block.p0_payment_funding_cap_exceeded",
                previous_funding_cap_block,
            )
            cursor.commit()

    def test_controlled_activation_and_immutable_authority(self):
        baseline = self._draft()
        self.assertEqual(baseline.version_no, 1)
        self.assertTrue(baseline.version_key)
        self.assertEqual(len(set(baseline.line_ids.mapped("line_key"))), 2)
        with self.assertRaises(AccessError):
            baseline.write({"state": "active"})
        with self.assertRaises(AccessError):
            baseline.with_context(_sc_funding_baseline_token=True).write({
                "state": "active",
            })
        with self.assertRaises(AccessError):
            baseline.write({"project_id": self.project.id})
        baseline.action_activate()
        self.assertEqual(baseline.state, "active")
        self.assertTrue(baseline.activated_at)
        with self.assertRaises(UserError):
            baseline.write({"total_amount": 101.0})
        with self.assertRaises(UserError):
            baseline.line_ids[:1].write({"planned_amount": 61.0})
        with self.assertRaises(UserError):
            baseline.unlink()

    def test_plan_conservation_and_version_successor(self):
        invalid = self._draft(total=101.0)
        invalid.line_ids[:1].write({"planned_amount": 50.0})
        with self.assertRaises(ValidationError):
            invalid.action_activate()
        invalid.action_cancel()

        first = self._draft()
        first.action_activate()
        revision = first.action_create_revision("年度滚动修订")
        self.assertEqual(revision.supersedes_id, first)
        self.assertEqual(revision.version_no, first.version_no + 1)
        self.assertEqual(
            revision.line_ids.mapped("line_key"), first.line_ids.mapped("line_key")
        )
        revision.action_activate()
        self.assertEqual(first.state, "superseded")
        self.assertEqual(first.superseded_by_id, revision)
        self.assertEqual(revision.state, "active")
        close_action = revision.with_context(
            funding_baseline_operation="close"
        ).action_open_transition_wizard()
        self.assertEqual(
            close_action["res_model"], "project.funding.baseline.transition.wizard"
        )
        close_wizard = self.env[close_action["res_model"]].with_context(
            **close_action["context"]
        ).create({"reason": "本控制期已完成"})
        close_wizard.action_apply()
        self.assertEqual(revision.state, "closed")
        self.assertEqual(revision.end_reason, "本控制期已完成")

        cancelled = revision.action_create_revision("取消的候选修订")
        cancelled.action_cancel()
        replacement = revision.action_create_revision("重新建立候选修订")
        self.assertNotEqual(cancelled, replacement)
        self.assertEqual(replacement.supersedes_id, revision)
        replacement.action_activate()
        self.assertEqual(revision.state, "closed")
        self.assertEqual(revision.superseded_by_id, replacement)
        self.assertEqual(replacement.state, "active")

    def test_normalized_period_and_direct_journal_crud_fail_closed(self):
        with self.assertRaises(ValidationError):
            self.env["project.funding.baseline"].create({
                "project_id": self.project.id,
                "total_amount": 100.0,
            })
        with self.assertRaises(UserError):
            self.env["project.funding.baseline"].create({
                "project_id": self.project.id,
                "total_amount": 100.0,
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
                "state": "active",
            })
        with self.assertRaises(AccessError):
            self.env["project.funding.actual.event.allocation"].sudo().create({})

    def test_line_parent_and_lineage_identity_are_service_owned(self):
        active = self._draft()
        active.action_activate()
        draft = active.action_create_revision("明细身份验证")
        foreign_key = active.line_ids[:1].line_key
        injected = self.env["project.funding.baseline.line"].create({
            "baseline_id": draft.id,
            "name": "外部新增科目",
            "planned_amount": 1.0,
            "line_key": foreign_key,
        })
        self.assertNotEqual(injected.line_key, foreign_key)
        with self.assertRaises(AccessError):
            injected.write({"baseline_id": active.id})
        with self.assertRaises(UserError):
            active.write({"line_ids": [(4, injected.id)]})

    def test_batch_submit_conserves_the_shared_baseline_cap(self):
        baseline = self._draft()
        baseline.action_activate()
        partner, contract = self._commercial_basis("批量提交")
        requests = self.env["payment.request"]
        for index in range(2):
            requests |= self.env["payment.request"].create({
                "name": f"P1-FUND-BATCH-{index}",
                "type": "pay",
                "project_id": self.project.id,
                "partner_id": partner.id,
                "contract_id": contract.id,
                "currency_id": self.env.company.currency_id.id,
                "amount": 60.0,
                "date_request": "2026-06-01",
                "payment_account_name": "批量提交供应商",
                "payment_bank_name": "测试银行",
                "payment_account_no": f"TEST-BATCH-{index}",
            })
        self.env["ir.config_parameter"].sudo().set_param(
            "sc.payment.force_block_all", "1"
        )
        with self.env.cr.savepoint(), self.assertRaises(UserError):
            requests.action_submit()
        requests.invalidate_recordset(["state", "funding_baseline_id"])
        self.assertEqual(set(requests.mapped("state")), {"draft"})
        self.assertFalse(requests.mapped("funding_baseline_id"))

    def test_native_finance_roles_menu_views_and_lifecycle_authority(self):
        reader = self._finance_user(
            "p1-funding-native-reader",
            "smart_construction_core.group_sc_cap_finance_read",
        )
        operator = self._finance_user(
            "p1-funding-native-operator",
            "smart_construction_core.group_sc_cap_finance_user",
        )
        manager = self._finance_user(
            "p1-funding-native-manager",
            "smart_construction_core.group_sc_cap_finance_manager",
        )
        baseline = self._draft()
        menus = self.env["ir.ui.menu"].browse([
            self.env.ref("smart_construction_core.menu_sc_funding_plan_summary").id,
            self.env.ref("smart_construction_core.menu_payment_ledger").id,
            self.env.ref(
                "smart_construction_core.menu_project_funding_actual_event_allocation"
            ).id,
        ])
        for user in (reader, operator, manager):
            visible_menu_ids = self.env["ir.ui.menu"].with_user(user)._visible_menu_ids()
            loaded_menus = self.env["ir.ui.menu"].with_user(user).load_menus(False)
            for menu in menus:
                current = menu
                while current:
                    self.assertTrue(
                        current.active,
                        f"inactive native menu ancestor: {current.get_external_id().get(current.id)}",
                    )
                    self.assertIn(current.id, visible_menu_ids)
                    current = current.parent_id
                self.assertTrue(
                    menu.id in loaded_menus or str(menu.id) in loaded_menus
                )
        for model_name in (
            "project.funding.baseline",
            "payment.ledger",
            "project.funding.actual.event.allocation",
        ):
            model = self.env[model_name]
            for user in (reader, operator, manager):
                self.assertTrue(model.with_user(user).get_view(view_type="tree")["arch"])
                self.assertTrue(model.with_user(user).get_view(view_type="form")["arch"])
        with self.assertRaises(AccessError):
            self.env["payment.ledger.funding.allocation.wizard"].with_user(
                reader
            ).check_access_rights("create")
        self.assertTrue(
            self.env["payment.ledger.funding.allocation.wizard"].with_user(
                operator
            ).check_access_rights("create")
        )
        with self.assertRaises(AccessError):
            self.env["project.funding.baseline.transition.wizard"].with_user(
                operator
            ).check_access_rights("create")
        self.assertTrue(
            self.env["project.funding.baseline.transition.wizard"].with_user(
                manager
            ).check_access_rights("create")
        )
        with self.assertRaises(AccessError):
            baseline.with_user(reader).action_activate()
        with self.assertRaises(AccessError):
            baseline.with_user(operator).action_activate()
        baseline.with_user(manager).action_activate()
        transition = baseline.with_user(manager).with_context(
            funding_baseline_operation="revision"
        ).action_open_transition_wizard()
        self.assertEqual(
            transition["res_model"], "project.funding.baseline.transition.wizard"
        )

    def test_request_binding_is_an_immutable_period_snapshot(self):
        baseline = self._draft()
        baseline.action_activate()
        partner, contract = self._commercial_basis("资金权威")
        request = self.env["payment.request"].create({
            "name": "P1-FUND-REQUEST",
            "type": "pay",
            "project_id": self.project.id,
            "partner_id": partner.id,
            "contract_id": contract.id,
            "currency_id": self.env.company.currency_id.id,
            "amount": 20.0,
            "date_request": "2026-06-01",
            "payment_account_name": "资金权威供应商",
            "payment_bank_name": "测试银行",
            "payment_account_no": "TEST-BINDING-001",
        })
        self.assertEqual(request._resolve_funding_baseline_binding(), baseline)
        with self.assertRaises(AccessError):
            request.with_context(_sc_funding_baseline_binding_token=True).write({
                "funding_baseline_id": baseline.id,
            })
        request.action_submit()
        self.assertEqual(request.state, "submit")
        self.assertEqual(request.funding_baseline_id, baseline)

    def test_company_and_currency_are_immutable_economic_snapshots(self):
        baseline = self._draft()
        baseline.action_activate()
        partner, contract = self._commercial_basis("经济身份快照")
        request = self.env["payment.request"].create({
            "name": "P1-FUND-IDENTITY", "type": "pay",
            "project_id": self.project.id, "partner_id": partner.id,
            "contract_id": contract.id, "currency_id": self.env.company.currency_id.id,
            "amount": 20.0, "date_request": "2026-06-01",
            "payment_account_name": "经济身份快照供应商",
            "payment_bank_name": "测试银行",
            "payment_account_no": "TEST-IDENTITY-001",
        })
        request.action_submit()
        self.env.cr.execute(
            "UPDATE payment_request SET state='approved', validation_status='validated' WHERE id=%s",
            [request.id],
        )
        request.invalidate_recordset()
        ledger = request.sudo()._ensure_payment_ledger(amount=20.0)
        allocation = ledger.action_allocate_funding([
            {"plan_line_id": baseline.line_ids[0].id, "amount": 20.0},
        ], "p1-economic-identity")
        execution = self.env["sc.payment.execution"].create({
            "name": "P1-FUND-IDENTITY-REV", "project_id": self.project.id,
            "partner_id": partner.id, "contract_id": contract.id,
            "payment_request_id": request.id, "planned_amount": 20.0,
            "paid_amount": 20.0, "currency_id": self.env.company.currency_id.id,
            "state": "paid", "reversal_reason": "跨公司历史冲销验证",
        })
        original_company = baseline.company_id
        original_currency = baseline.currency_id
        other_company = self.env["res.company"].create({
            "name": "P1 资金快照异币种公司",
            "currency_id": self.env.ref("base.USD").id,
        })

        self.project.write({"company_id": other_company.id})
        baseline.invalidate_recordset()
        baseline.line_ids.invalidate_recordset()
        allocation.invalidate_recordset()
        self.assertEqual(baseline.state, "active")
        self.assertEqual(baseline.company_id, original_company)
        self.assertEqual(baseline.currency_id, original_currency)
        self.assertEqual(set(baseline.line_ids.mapped("company_id")), {original_company})
        self.assertEqual(set(baseline.line_ids.mapped("currency_id")), {original_currency})
        self.assertEqual(allocation.company_id, original_company)
        self.assertEqual(allocation.currency_id, original_currency)
        self.assertEqual(allocation.allocated_amount, 20.0)
        self.assertEqual(allocation.effective_amount, 20.0)
        with self.assertRaises(UserError):
            baseline.action_create_revision("不得跨币种复制")
        with self.assertRaises(AccessError):
            baseline.write({"company_id": other_company.id})
        execution.sudo().action_reverse_payment()
        journal = self.env["project.funding.actual.event.allocation"].sudo().search([
            ("actual_event_id", "=", ledger.id),
        ])
        self.assertEqual(sum(journal.mapped("effective_amount")), 0.0)
        self.assertEqual(set(journal.mapped("company_id")), {original_company})
        self.assertEqual(set(journal.mapped("currency_id")), {original_currency})

        self.project.write({"company_id": original_company.id})
        baseline.action_close("完成原公司资金控制期")
        self.project.write({"company_id": other_company.id})
        baseline.invalidate_recordset()
        baseline.line_ids.invalidate_recordset()
        allocation.invalidate_recordset()
        self.assertEqual(baseline.state, "closed")
        self.assertEqual(baseline.company_id, original_company)
        self.assertEqual(baseline.currency_id, original_currency)
        self.assertEqual(allocation.company_id, original_company)
        self.assertEqual(allocation.currency_id, original_currency)
        self.assertEqual(allocation.effective_amount, 20.0)
        with self.assertRaises(AccessError):
            request.write({"funding_baseline_id": False})
        with self.assertRaises(UserError):
            baseline.action_create_revision("异币种项目不得复制历史金额")
        self.project.write({"company_id": original_company.id})
        revision = baseline.action_create_revision("切换下一权威版本")
        revision.action_activate()
        self.assertEqual(request.funding_baseline_id, baseline)

    def test_allocation_journal_is_idempotent_conserved_and_reversed_by_append(self):
        baseline = self._draft()
        baseline.action_activate()
        partner, contract = self._commercial_basis("资金分配")
        request = self.env["payment.request"].create({
            "name": "P1-FUND-ALLOC", "type": "pay",
            "project_id": self.project.id, "partner_id": partner.id,
            "contract_id": contract.id, "currency_id": self.env.company.currency_id.id,
            "amount": 80.0, "date_request": "2026-06-01",
            "payment_account_name": "资金分配供应商",
            "payment_bank_name": "测试银行",
            "payment_account_no": "TEST-ACCOUNT-001",
        })
        request.action_submit()
        self.env.cr.execute(
            "UPDATE payment_request SET state='approved', validation_status='validated' WHERE id=%s",
            [request.id],
        )
        request.invalidate_recordset()
        ledger = request.sudo()._ensure_payment_ledger(amount=80.0)
        reader = self._finance_user(
            "p1-funding-allocation-reader",
            "smart_construction_core.group_sc_cap_finance_read",
        )
        operator = self._finance_user(
            "p1-funding-allocation-operator",
            "smart_construction_core.group_sc_cap_finance_user",
        )
        manager = self._finance_user(
            "p1-funding-allocation-manager",
            "smart_construction_core.group_sc_cap_finance_manager",
        )
        with self.assertRaises(AccessError):
            ledger.with_user(reader).action_open_funding_allocation_wizard()
        first_line = baseline.line_ids[:1]
        rows = ledger.with_user(operator).action_allocate_funding(
            [{"plan_line_id": first_line.id, "amount": 40.0}], "p1-op-001"
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.effective_amount, 40.0)
        replay = ledger.action_allocate_funding(
            [{"plan_line_id": first_line.id, "amount": 40.0}], "p1-op-001"
        )
        self.assertEqual(replay, rows)
        rounded_replay = ledger.action_allocate_funding(
            [{"plan_line_id": first_line.id, "amount": 40.001}], "p1-op-001"
        )
        self.assertEqual(rounded_replay, rows)
        with self.assertRaises(UserError):
            ledger.action_allocate_funding([
                {"plan_line_id": first_line.id, "amount": 40.0},
                {"plan_line_id": baseline.line_ids[1].id, "amount": 1.0},
            ], "p1-op-001")
        with self.assertRaises(ValidationError):
            ledger.action_allocate_funding(
                [{"plan_line_id": first_line.id, "amount": 30.0}], "p1-op-over"
            )
        with self.assertRaises(AccessError):
            rows.write({"allocated_amount": 39.0})
        with self.assertRaises(AccessError):
            ledger.with_user(operator).with_context(
                funding_allocation_mode="correct"
            ).action_open_funding_allocation_wizard()
        wizard_action = ledger.with_user(operator).action_open_funding_allocation_wizard()
        wizard = self.env[wizard_action["res_model"]].with_user(operator).with_context(
            **wizard_action["context"]
        ).create({
            "line_ids": [(0, 0, {
                "plan_line_id": baseline.line_ids[1].id,
                "available_amount": baseline.line_ids[1].remaining_amount,
                "amount": 20.0,
            })],
        })
        wizard.action_confirm()
        self.assertEqual(ledger.fund_plan_allocated_amount, 60.0)
        correction = ledger.with_user(manager).with_context(
            funding_allocation_mode="correct"
        ).action_open_funding_allocation_wizard()
        correction_wizard = self.env[correction["res_model"]].with_user(manager).with_context(
            **correction["context"]
        ).create({
            "original_allocation_ids": [(6, 0, rows.ids)],
            "reason": "科目归属纠正",
            "line_ids": [
                (0, 0, {
                    "plan_line_id": baseline.line_ids[0].id,
                    "available_amount": baseline.line_ids[0].remaining_amount,
                    "amount": 20.0,
                }),
                (0, 0, {
                    "plan_line_id": baseline.line_ids[1].id,
                    "available_amount": baseline.line_ids[1].remaining_amount,
                    "amount": 20.0,
                }),
            ],
        })
        correction_key = correction_wizard.operation_key
        correction_specs = [
            {"plan_line_id": baseline.line_ids[0].id, "amount": 20.0},
            {"plan_line_id": baseline.line_ids[1].id, "amount": 20.0},
        ]
        correction_wizard.action_confirm()
        self.assertTrue(rows.reversed_by_id)
        self.assertEqual(ledger.fund_plan_allocated_amount, 60.0)
        correction_replay = ledger.action_reallocate_funding(
            rows.ids, correction_specs, correction_key, "科目归属纠正"
        )
        self.assertEqual(len(correction_replay), 3)
        with self.assertRaises(UserError):
            ledger.action_reallocate_funding(
                rows.ids, correction_specs, correction_key, "更换纠正原因"
            )
        with self.assertRaises(UserError):
            ledger.action_reallocate_funding(
                rows.ids,
                [{"plan_line_id": baseline.line_ids[0].id, "amount": 40.0}],
                correction_key,
                "科目归属纠正",
            )
        execution = self.env["sc.payment.execution"].create({
            "name": "P1-FUND-REV", "project_id": self.project.id,
            "partner_id": partner.id, "contract_id": contract.id,
            "payment_request_id": request.id, "planned_amount": 80.0,
            "paid_amount": 80.0, "currency_id": self.env.company.currency_id.id,
            "state": "paid", "reversal_reason": "付款撤销测试",
        })
        def broken_message_post(record, *args, **kwargs):
            record.env.cr.execute("SELECT * FROM sc_p1_missing_chatter_relation")

        with patch.object(type(execution), "message_post", broken_message_post):
            execution.with_user(manager).action_reverse_payment()
        self.env.cr.execute("SELECT 1")
        self.assertEqual(self.env.cr.fetchone()[0], 1)
        self.assertEqual(execution.state, "cancel")
        journal = self.env["project.funding.actual.event.allocation"].sudo().search([
            ("actual_event_id", "=", ledger.id),
        ])
        self.assertEqual(len(journal), 8)
        self.assertEqual(sum(journal.mapped("effective_amount")), 0.0)
        self.assertEqual(ledger.state, "reversed")

    def test_correction_wizard_keeps_full_plan_lines_available(self):
        baseline = self._draft()
        baseline.action_activate()
        partner, contract = self._commercial_basis("满额纠正")
        request = self.env["payment.request"].create({
            "name": "P1-FUND-FULL-CORRECTION", "type": "pay",
            "project_id": self.project.id, "partner_id": partner.id,
            "contract_id": contract.id, "currency_id": self.env.company.currency_id.id,
            "amount": 100.0, "date_request": "2026-06-01",
            "payment_account_name": "满额纠正供应商",
            "payment_bank_name": "测试银行",
            "payment_account_no": "TEST-FULL-CORRECTION-001",
        })
        request.action_submit()
        self.env.cr.execute(
            "UPDATE payment_request SET state='approved', validation_status='validated' WHERE id=%s",
            [request.id],
        )
        request.invalidate_recordset()
        ledger = request.sudo()._ensure_payment_ledger(amount=100.0)
        originals = ledger.action_allocate_funding([
            {"plan_line_id": baseline.line_ids[0].id, "amount": 60.0},
            {"plan_line_id": baseline.line_ids[1].id, "amount": 40.0},
        ], "p1-full-allocation")
        self.assertFalse(any(baseline.line_ids.mapped("remaining_amount")))
        action = ledger.with_context(
            funding_allocation_mode="correct"
        ).action_open_funding_allocation_wizard()
        wizard = self.env[action["res_model"]].with_context(
            **action["context"]
        ).create({
            "original_allocation_ids": [(6, 0, originals.ids)],
            "reason": "满额计划内审计纠正",
        })
        self.assertEqual(set(wizard.line_ids.mapped("plan_line_id")), set(baseline.line_ids))
        for line in wizard.line_ids:
            line.amount = line.plan_line_id.planned_amount
        wizard.action_confirm()
        self.assertTrue(all(originals.mapped("reversed_by_id")))
        self.assertEqual(ledger.fund_plan_allocated_amount, 100.0)

    def test_batch_funding_gate_has_fixed_baseline_query_growth(self):
        baseline = self._draft(total=1000.0)
        baseline.action_activate()
        partner, contract = self._commercial_basis("查询预算")
        requests = self.env["payment.request"].create([{
            "name": f"P1-FUND-QUERY-{index}", "type": "pay",
            "project_id": self.project.id, "partner_id": partner.id,
            "contract_id": contract.id, "currency_id": self.env.company.currency_id.id,
            "amount": 1.0, "date_request": "2026-06-01",
            "payment_account_name": "查询预算供应商",
            "payment_bank_name": "测试银行",
            "payment_account_no": f"TEST-QUERY-{index}",
        } for index in range(50)])
        self.env["ir.config_parameter"].sudo().set_param(
            "sc.payment.force_block_all", "1"
        )

        def query_count(records):
            start = self.env.cr.sql_log_count
            records._enforce_batch_funding_submit_gate(evaluation_cache={})
            return self.env.cr.sql_log_count - start

        one_count = query_count(requests[:1])
        ten_count = query_count(requests[:10])
        fifty_count = query_count(requests)
        self.assertLessEqual(ten_count, one_count + 3)
        self.assertLessEqual(fifty_count, one_count + 3)

    def test_concurrent_activation_serializes_project_authority(self):
        registry = Registry(self.env.cr.dbname)
        setup_cursor = registry.cursor()
        try:
            setup_env = api.Environment(setup_cursor, SUPERUSER_ID, {})
            project = setup_env["project.project"].create({
                "name": "P1 并发资金权威 " + uuid.uuid4().hex[:8],
                "code": "P1-FUND-CONCURRENT-" + uuid.uuid4().hex[:8],
                "funding_enabled": True,
                "company_id": setup_env.company.id,
            })
            baselines = setup_env["project.funding.baseline"]
            for index in range(2):
                baselines |= setup_env["project.funding.baseline"].create({
                    "project_id": project.id,
                    "total_amount": 100.0,
                    "period_start": "2026-01-01",
                    "period_end": "2026-12-31",
                    "line_ids": [(0, 0, {
                        "name": f"并发计划 {index}", "planned_amount": 100.0,
                    })],
                })
            project_id = project.id
            baseline_ids = baselines.ids
            setup_cursor.commit()
            self.addCleanup(
                self._cleanup_committed_concurrency_project,
                project_id,
            )
        finally:
            setup_cursor.close()

        started = threading.Event()
        finished = threading.Event()
        result = []
        serialization_failures = []

        def activate_competing_baseline():
            cursor = registry.cursor()
            try:
                started.set()
                for attempt in range(2):
                    env = api.Environment(cursor, SUPERUSER_ID, {})
                    try:
                        env["project.funding.baseline"].browse(
                            baseline_ids[1]
                        ).action_activate()
                        cursor.commit()
                        result.append("activated")
                        break
                    except SerializationFailure:
                        serialization_failures.append(attempt)
                        cursor.rollback()
                        if attempt:
                            result.append("serialization_failed")
                    except UserError:
                        cursor.rollback()
                        result.append("rejected")
                        break
            finally:
                cursor.close()
                finished.set()

        first_cursor = registry.cursor()
        try:
            first_env = api.Environment(first_cursor, SUPERUSER_ID, {})
            first = first_env["project.funding.baseline"].browse(baseline_ids[0])
            first._lock_project_baselines([project_id])
            competing = threading.Thread(target=activate_competing_baseline)
            competing.start()
            self.assertTrue(started.wait(5))
            self.assertFalse(
                finished.wait(0.2),
                "competing activation must wait on the shared project authority lock",
            )
            first.action_activate()
            first_cursor.commit()
            competing.join(10)
            self.assertFalse(competing.is_alive())
            self.assertEqual(result, ["rejected"])
            self.assertGreaterEqual(len(serialization_failures), 1)
        finally:
            first_cursor.close()

        verify_cursor = registry.cursor()
        try:
            verify_env = api.Environment(verify_cursor, SUPERUSER_ID, {})
            verified = verify_env["project.funding.baseline"].browse(baseline_ids)
            self.assertEqual(len(verified.filtered(lambda row: row.state == "active")), 1)
            self.assertEqual(len(verified.filtered(lambda row: row.state == "draft")), 1)
        finally:
            verify_cursor.close()

    def test_concurrent_submit_serializes_shared_baseline_reservation(self):
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as setup_cursor:
            setup_env = api.Environment(setup_cursor, SUPERUSER_ID, {})
            project = setup_env["project.project"].create({
                "name": "P1 并发资金占用 " + uuid.uuid4().hex[:8],
                "code": "P1-FUND-SUBMIT-" + uuid.uuid4().hex[:8],
                "funding_enabled": True,
                "company_id": setup_env.company.id,
            })
            baseline = setup_env["project.funding.baseline"].create({
                "project_id": project.id,
                "total_amount": 100.0,
                "period_start": "2026-01-01",
                "period_end": "2026-12-31",
                "line_ids": [(0, 0, {
                    "name": "并发资金占用", "planned_amount": 100.0,
                })],
            })
            baseline.action_activate()
            partner = setup_env["res.partner"].create({
                "name": "P1 并发资金占用供应商 " + uuid.uuid4().hex[:8],
            })
            tax = setup_env["account.tax"].search([
                ("company_id", "=", setup_env.company.id),
                ("type_tax_use", "=", "purchase"),
            ], limit=1)
            created_tax_id = False
            if not tax:
                tax = setup_env["account.tax"].create({
                    "name": "P1 并发资金占用测试税率",
                    "amount": 0.0,
                    "amount_type": "percent",
                    "type_tax_use": "purchase",
                    "company_id": setup_env.company.id,
                })
                created_tax_id = tax.id
            contract = setup_env["construction.contract"].create({
                "subject": "P1 并发资金占用合同",
                "type": "in",
                "project_id": project.id,
                "partner_id": partner.id,
                "company_id": setup_env.company.id,
                "currency_id": setup_env.company.currency_id.id,
                "tax_id": tax.id,
            })
            requests = setup_env["payment.request"].create([{
                "name": f"P1-FUND-CONCURRENT-SUBMIT-{index}",
                "type": "pay",
                "project_id": project.id,
                "partner_id": partner.id,
                "contract_id": contract.id,
                "currency_id": setup_env.company.currency_id.id,
                "amount": 60.0,
                "date_request": "2026-06-01",
                "payment_account_name": "并发资金占用供应商",
                "payment_bank_name": "测试银行",
                "payment_account_no": f"TEST-CONCURRENT-SUBMIT-{index}",
            } for index in range(2)])
            config = setup_env["ir.config_parameter"].sudo()
            previous_funding_cap_block = config.get_param(
                "sc.payment.force_block.p0_payment_funding_cap_exceeded", False
            )
            config.set_param(
                "sc.payment.force_block.p0_payment_funding_cap_exceeded", "1"
            )
            project_id = project.id
            partner_id = partner.id
            contract_id = contract.id
            request_ids = requests.ids
            setup_cursor.commit()
            self.addCleanup(
                self._cleanup_committed_submit_fixture,
                project_id,
                partner_id,
                contract_id,
                request_ids,
                created_tax_id,
                previous_funding_cap_block,
            )

        barrier = threading.Barrier(2)
        result_lock = threading.Lock()
        outcomes = []
        serialization_failures = []

        def submit_request(request_id):
            outcome = "unexpected"
            with registry.cursor() as cursor:
                for attempt in range(2):
                    env = api.Environment(cursor, SUPERUSER_ID, {})
                    try:
                        cursor.execute(
                            "SELECT id FROM payment_request WHERE id = %s",
                            [request_id],
                        )
                        if attempt == 0:
                            barrier.wait(timeout=15)
                        env["payment.request"].browse(request_id).action_submit()
                        cursor.commit()
                        outcome = "submitted"
                        break
                    except SerializationFailure:
                        cursor.rollback()
                        with result_lock:
                            serialization_failures.append(request_id)
                    except UserError:
                        cursor.rollback()
                        outcome = "rejected"
                        break
                    except Exception as error:  # pragma: no cover - evidence surface
                        cursor.rollback()
                        outcome = ("unexpected", repr(error))
                        break
            with result_lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=submit_request, args=(request_id,))
            for request_id in request_ids
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(30)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(sorted(outcomes), ["rejected", "submitted"], outcomes)
        self.assertGreaterEqual(len(serialization_failures), 1)

        with registry.cursor() as verify_cursor:
            verify_env = api.Environment(verify_cursor, SUPERUSER_ID, {})
            verified = verify_env["payment.request"].browse(request_ids)
            self.assertEqual(sorted(verified.mapped("state")), ["draft", "submit"])
            reserved = sum(
                verified.filtered(
                    lambda request: request.state in ("submit", "approve", "approved")
                ).mapped("amount")
            )
            self.assertEqual(reserved, 60.0)
            self.assertLessEqual(reserved, 100.0)

    def test_authority_switch_serializes_with_submit_and_rebinds_current_version(self):
        registry = Registry(self.env.cr.dbname)
        with registry.cursor() as setup_cursor:
            setup_env = api.Environment(setup_cursor, SUPERUSER_ID, {})
            project = setup_env["project.project"].create({
                "name": "P1 权威切换提交 " + uuid.uuid4().hex[:8],
                "code": "P1-FUND-SWITCH-" + uuid.uuid4().hex[:8],
                "funding_enabled": True, "company_id": setup_env.company.id,
            })
            baseline = setup_env["project.funding.baseline"].create({
                "project_id": project.id, "total_amount": 100.0,
                "period_start": "2026-01-01", "period_end": "2026-12-31",
                "line_ids": [(0, 0, {"name": "原权威", "planned_amount": 100.0})],
            })
            baseline.action_activate()
            revision = baseline.action_create_revision("并发切换权威")
            partner = setup_env["res.partner"].create({"name": "P1 权威切换供应商"})
            tax = setup_env["account.tax"].search([
                ("company_id", "=", setup_env.company.id),
                ("type_tax_use", "=", "purchase"),
            ], limit=1)
            contract = setup_env["construction.contract"].create({
                "subject": "P1 权威切换合同", "type": "in",
                "project_id": project.id, "partner_id": partner.id,
                "company_id": setup_env.company.id,
                "currency_id": setup_env.company.currency_id.id, "tax_id": tax.id,
            })
            request = setup_env["payment.request"].create({
                "name": "P1-FUND-SWITCH-SUBMIT", "type": "pay",
                "project_id": project.id, "partner_id": partner.id,
                "contract_id": contract.id, "currency_id": setup_env.company.currency_id.id,
                "amount": 20.0, "date_request": "2026-06-01",
                "payment_account_name": "P1 权威切换供应商",
                "payment_bank_name": "测试银行", "payment_account_no": "TEST-SWITCH",
            })
            config = setup_env["ir.config_parameter"].sudo()
            previous = config.get_param(
                "sc.payment.force_block.p0_payment_funding_cap_exceeded", False
            )
            ids = (project.id, partner.id, contract.id, request.id, revision.id)
            setup_cursor.commit()
            self.addCleanup(
                self._cleanup_committed_submit_fixture,
                ids[0], ids[1], ids[2], [ids[3]], False, previous,
            )

        started = threading.Event()
        finished = threading.Event()
        result = []
        serialization_failures = []

        def submit_during_switch():
            with registry.cursor() as cursor:
                for attempt in range(2):
                    env = api.Environment(cursor, SUPERUSER_ID, {})
                    try:
                        cursor.execute("SELECT id FROM payment_request WHERE id=%s", [ids[3]])
                        if attempt == 0:
                            started.set()
                        env["payment.request"].browse(ids[3]).action_submit()
                        cursor.commit()
                        result.append("submitted")
                        break
                    except SerializationFailure:
                        serialization_failures.append(attempt)
                        cursor.rollback()
                    except Exception as error:  # pragma: no cover - evidence surface
                        cursor.rollback()
                        result.append(repr(error))
                        break
            finished.set()

        with registry.cursor() as lifecycle_cursor:
            lifecycle_env = api.Environment(lifecycle_cursor, SUPERUSER_ID, {})
            current_revision = lifecycle_env["project.funding.baseline"].browse(ids[4])
            current_revision._lock_project_baselines([ids[0]])
            thread = threading.Thread(target=submit_during_switch)
            thread.start()
            self.assertTrue(started.wait(5))
            self.assertFalse(finished.wait(0.2))
            current_revision.action_activate()
            lifecycle_cursor.commit()
            thread.join(10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(result, ["submitted"])
        self.assertTrue(serialization_failures)
        with registry.cursor() as verify_cursor:
            verify_env = api.Environment(verify_cursor, SUPERUSER_ID, {})
            verified = verify_env["payment.request"].browse(ids[3])
            self.assertEqual(verified.funding_baseline_id.id, ids[4])

    def test_legacy_migration_never_invents_period_or_version_and_replays_cleanly(self):
        baseline = self._draft()
        self.env.cr.execute(
            "ALTER TABLE project_funding_baseline "
            "ALTER COLUMN normalization_state DROP NOT NULL"
        )
        self.env.cr.execute(
            """
            UPDATE project_funding_baseline
               SET state='active', version_key=NULL, normalization_state=NULL
             WHERE id=%s
            """,
            [baseline.id],
        )
        baseline.invalidate_recordset()
        migration = runpy.run_path(os.path.join(
            get_module_path("smart_construction_core"),
            "migrations/17.0.0.143/pre-migration.py",
        ))["migrate"]
        migration(self.env.cr, "17.0.0.142")
        baseline.invalidate_recordset()
        self.assertFalse(baseline.version_no)
        self.assertEqual(baseline.version_key, f"legacy:{baseline.id}")
        self.assertEqual(baseline.normalization_state, "legacy_unresolved_period")
        self.env.cr.execute(
            "SELECT ctid::text FROM project_funding_baseline WHERE id=%s", [baseline.id]
        )
        first_ctid = self.env.cr.fetchone()[0]
        migration(self.env.cr, "17.0.0.143")
        self.env.cr.execute(
            "SELECT ctid::text FROM project_funding_baseline WHERE id=%s", [baseline.id]
        )
        self.assertEqual(self.env.cr.fetchone()[0], first_ctid)

    def test_legacy_active_revision_requires_explicit_period_and_normalized_row_is_untouched(self):
        normalized = self._draft(total=20.0)
        self.env.cr.execute(
            "SELECT ctid::text FROM project_funding_baseline WHERE id=%s",
            [normalized.id],
        )
        normalized_ctid = self.env.cr.fetchone()[0]
        legacy = self._draft(total=30.0)
        self.env.cr.execute(
            """
            UPDATE project_funding_baseline
               SET state='active', version_no=NULL, period_start=NULL, period_end=NULL,
                   normalization_state='legacy_unresolved_period'
             WHERE id=%s
            """,
            [legacy.id],
        )
        legacy.invalidate_recordset()
        with self.assertRaises(ValidationError):
            legacy.action_create_revision("补齐历史权威")
        revision = legacy.action_create_revision(
            "补齐历史权威", "2027-01-01", "2027-12-31"
        )
        self.assertEqual(revision.normalization_state, "normalized")
        migration = runpy.run_path(os.path.join(
            get_module_path("smart_construction_core"),
            "migrations/17.0.0.143/pre-migration.py",
        ))["migrate"]
        migration(self.env.cr, "17.0.0.142")
        self.env.cr.execute(
            "SELECT ctid::text FROM project_funding_baseline WHERE id=%s",
            [normalized.id],
        )
        self.assertEqual(self.env.cr.fetchone()[0], normalized_ctid)

    def test_0144_migration_replay_preserves_constraint_and_index_identity(self):
        migration_root = os.path.join(
            get_module_path("smart_construction_core"), "migrations/17.0.0.144"
        )
        pre_migrate = runpy.run_path(os.path.join(
            migration_root, "pre-migration.py"
        ))["migrate"]
        post_migrate = runpy.run_path(os.path.join(
            migration_root, "post-migration.py"
        ))["migrate"]
        self.env.cr.execute(
            """
            SELECT constraint_meta.oid, pg_get_constraintdef(constraint_meta.oid)
              FROM pg_constraint AS constraint_meta
              JOIN pg_class AS table_meta
                ON table_meta.oid = constraint_meta.conrelid
             WHERE table_meta.relname = 'project_funding_baseline'
               AND constraint_meta.conname =
                   'project_funding_baseline_total_amount_positive'
            """
        )
        constraint_before = self.env.cr.fetchone()
        self.assertIn("normalization_state", constraint_before[1])
        pre_migrate(self.env.cr, "17.0.0.144")
        self.env.cr.execute(
            """
            SELECT constraint_meta.oid, pg_get_constraintdef(constraint_meta.oid)
              FROM pg_constraint AS constraint_meta
              JOIN pg_class AS table_meta
                ON table_meta.oid = constraint_meta.conrelid
             WHERE table_meta.relname = 'project_funding_baseline'
               AND constraint_meta.conname =
                   'project_funding_baseline_total_amount_positive'
            """
        )
        self.assertEqual(self.env.cr.fetchone(), constraint_before)
        post_migrate(self.env.cr, "17.0.0.144")
        self.env.cr.execute(
            "SELECT oid FROM pg_class WHERE relname=%s",
            ["project_funding_baseline_one_live_successor_uidx"],
        )
        index_oid = self.env.cr.fetchone()[0]
        post_migrate(self.env.cr, "17.0.0.144")
        self.env.cr.execute(
            "SELECT oid FROM pg_class WHERE relname=%s",
            ["project_funding_baseline_one_live_successor_uidx"],
        )
        self.assertEqual(self.env.cr.fetchone()[0], index_oid)

    def test_0145_migration_quarantines_identity_without_invention_and_replays(self):
        missing_identity = self._draft(total=25.0)
        valid = self._draft(total=30.0)
        valid.action_activate()
        partner, contract = self._commercial_basis("迁移身份隔离")
        request = self.env["payment.request"].create({
            "name": "P1-FUND-MIGRATION-IDENTITY", "type": "pay",
            "project_id": self.project.id, "partner_id": partner.id,
            "contract_id": contract.id, "currency_id": self.env.company.currency_id.id,
            "amount": 10.0, "date_request": "2026-06-01",
            "payment_account_name": "迁移身份隔离供应商",
            "payment_bank_name": "测试银行", "payment_account_no": "TEST-MIG-145",
        })
        request.action_submit()
        self.env.cr.execute(
            "UPDATE payment_request SET state='approved', validation_status='validated' WHERE id=%s",
            [request.id],
        )
        request.invalidate_recordset()
        ledger = request.sudo()._ensure_payment_ledger(amount=10.0)
        allocation = ledger.action_allocate_funding([{
            "plan_line_id": valid.line_ids[0].id, "amount": 10.0,
        }], "p1-migration-145")
        other_company = self.env["res.company"].create({
            "name": "P1 迁移异常身份公司", "currency_id": self.env.ref("base.USD").id,
        })
        self.env.cr.execute(
            "ALTER TABLE project_funding_baseline DROP CONSTRAINT IF EXISTS "
            "project_funding_baseline_normalized_identity_present"
        )
        self.env.cr.execute(
            "UPDATE project_funding_baseline SET company_id=NULL, currency_id=NULL WHERE id=%s",
            [missing_identity.id],
        )
        self.env.cr.execute(
            "UPDATE project_funding_actual_event_allocation SET company_id=%s WHERE id=%s",
            [other_company.id, allocation.id],
        )
        migration = runpy.run_path(os.path.join(
            get_module_path("smart_construction_core"),
            "migrations/17.0.0.145/pre-migration.py",
        ))["migrate"]
        migration(self.env.cr, "17.0.0.144")
        self.env.cr.execute(
            "SELECT normalization_state, company_id, currency_id, ctid::text "
            "FROM project_funding_baseline WHERE id=%s", [missing_identity.id],
        )
        baseline_after = self.env.cr.fetchone()
        self.assertEqual(baseline_after[:3], ("legacy_unresolved_identity", None, None))
        self.env.cr.execute(
            "SELECT normalization_state, company_id, ctid::text "
            "FROM project_funding_actual_event_allocation WHERE id=%s", [allocation.id],
        )
        allocation_after = self.env.cr.fetchone()
        self.assertEqual(allocation_after[0], "legacy_unresolved_relation")
        self.assertEqual(allocation_after[1], other_company.id)
        manager = self._finance_user(
            "p1-funding-quarantine-manager",
            "smart_construction_core.group_sc_cap_finance_manager",
        )
        manager.write({"company_ids": [(6, 0, [self.env.company.id, other_company.id])]})
        scoped = dict(allowed_company_ids=[self.env.company.id, other_company.id])
        self.assertFalse(
            self.env["project.funding.baseline"].with_user(manager).with_context(
                **scoped
            ).search([("id", "=", missing_identity.id)])
        )
        self.assertFalse(
            self.env["project.funding.baseline.line"].with_user(manager).with_context(
                **scoped
            ).search([("baseline_id", "=", missing_identity.id)])
        )
        self.assertFalse(
            self.env["project.funding.actual.event.allocation"].with_user(
                manager
            ).with_context(**scoped).search([("id", "=", allocation.id)])
        )
        migration(self.env.cr, "17.0.0.145")
        self.env.cr.execute(
            "SELECT normalization_state, company_id, currency_id, ctid::text "
            "FROM project_funding_baseline WHERE id=%s", [missing_identity.id],
        )
        self.assertEqual(self.env.cr.fetchone(), baseline_after)
        self.env.cr.execute(
            "SELECT normalization_state, company_id, ctid::text "
            "FROM project_funding_actual_event_allocation WHERE id=%s", [allocation.id],
        )
        self.assertEqual(self.env.cr.fetchone(), allocation_after)
