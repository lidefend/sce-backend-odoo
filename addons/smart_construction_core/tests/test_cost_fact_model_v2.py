# -*- coding: utf-8 -*-
import json
import os
import runpy

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules.module import get_module_path
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval


@tagged("post_install", "-at_install", "sc_gate", "cost_fact_v2")
class TestCostFactModelV2(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project = self.env["project.project"].create(
            {"name": "成本事实 V2 项目", "company_id": self.env.company.id}
        )
        self.other_project = self.env["project.project"].create(
            {"name": "其他成本项目", "company_id": self.env.company.id}
        )
        self.wbs = self.env["construction.work.breakdown"].create(
            {"name": "主体结构", "code": "CFV2-WBS", "project_id": self.project.id}
        )
        self.other_wbs = self.env["construction.work.breakdown"].create(
            {"name": "其他结构", "code": "CFV2-OTHER", "project_id": self.other_project.id}
        )
        self.cost_code = self.env["project.cost.code"].create(
            {"name": "成本事实测试科目", "code": "CFV2", "type": "other"}
        )
        self.Ledger = self.env["project.cost.ledger"]

    def _generated_values(self, source_model="account.move.line", source_id=101, source_line_id=201):
        return {
            "project_id": self.project.id,
            "wbs_id": self.wbs.id,
            "cost_code_id": self.cost_code.id,
            "date": "2026-09-02",
            "source_amount": 125.0,
            "source_currency_id": self.project.company_id.currency_id.id,
            "source_model": source_model,
            "source_id": source_id,
            "source_line_id": source_line_id,
            "note": "受控生成成本事实",
        }

    def test_stage_policy_and_idempotent_service(self):
        mappings = (
            ("purchase.order.line", "commitment", "memorandum"),
            ("stock.move", "receipt_accrual", "memorandum"),
            ("sc.material.outbound", "consumption", "operational_actual"),
            ("sc.equipment.usage", "consumption", "operational_actual"),
            ("sc.material.settlement", "settlement", "memorandum"),
            ("account.move.line", "accounting_actual", "financial_actual"),
        )
        values = [
            self._generated_values(model, 1000 + index, 2000 + index)
            for index, (model, _stage, _treatment) in enumerate(mappings)
        ]
        rows = self.Ledger._upsert_generated_cost_rows(values)
        self.assertEqual(len(rows), len(mappings))
        for model, stage, treatment in mappings:
            row = rows.filtered(lambda item: item.source_model == model)
            self.assertEqual(row.recognition_stage, stage)
            self.assertEqual(row.reporting_treatment, treatment)
            self.assertEqual(row.currency_id, self.project.company_id.currency_id)
            self.assertEqual(row.source_amount, 125.0)
            self.assertEqual(row.amount, 125.0)

        replay = self.Ledger._upsert_generated_cost_rows(values)
        self.assertEqual(set(replay.ids), set(rows.ids))
        self.assertEqual(
            self.Ledger.search_count([("source_id", "in", [value["source_id"] for value in values])]),
            len(mappings),
        )

    def test_generated_identity_and_payload_are_guarded(self):
        values = self._generated_values()
        with self.assertRaises(AccessError):
            self.Ledger.create(values)
        with self.assertRaises(ValidationError):
            self.Ledger.create(
                {
                    "project_id": self.project.id,
                    "cost_code_id": self.cost_code.id,
                    "source_model": "account.move.line",
                }
            )

        row = self.Ledger._upsert_generated_cost_rows([values])
        with self.assertRaises(AccessError):
            row.write({"amount": 999})
        with self.assertRaises(AccessError):
            row.unlink()
        with self.assertRaises(AccessError):
            row.with_context(sc_cost_generated_service=True).write({"amount": 999})
        with self.assertRaises(AccessError):
            self.Ledger.with_context(sc_cost_generated_service=True).create(values)
        with self.assertRaises(AccessError):
            self.Ledger.with_user(self.env.ref("base.user_admin")).with_context(
                install_mode=True
            ).create(values)

        manual = self.Ledger.create(
            {
                "project_id": self.project.id,
                "cost_code_id": self.cost_code.id,
                "date": "2026-09-02",
                "amount": 10,
            }
        )
        with self.assertRaises(AccessError):
            manual.write(
                {
                    "source_model": "account.move.line",
                    "source_id": 101,
                    "source_line_id": 201,
                }
            )
        with self.assertRaises(AccessError):
            manual.write({"normalization_state": "legacy_unresolved_currency"})
        with self.assertRaises(AccessError):
            self.Ledger.create({
                "project_id": self.project.id,
                "cost_code_id": self.cost_code.id,
                "date": "2026-09-02",
                "amount": 10,
                "normalization_state": "legacy_unresolved_currency",
            })

    def test_legacy_foreign_currency_migration_preserves_source_and_quarantines(self):
        module_path = get_module_path("smart_construction_core")
        self.assertFalse(
            os.path.exists(os.path.join(module_path, "migrations/17.0.0.140/pre-migration.py"))
        )
        migration = runpy.run_path(
            os.path.join(module_path, "migrations/17.0.0.141/post-migration.py")
        )["migrate"]
        foreign_currency = self.env.ref("base.USD")
        self.assertNotEqual(foreign_currency, self.project.company_id.currency_id)
        row = self.Ledger.create({
            "project_id": self.project.id,
            "cost_code_id": self.cost_code.id,
            "date": "2026-09-02",
            "amount": 123.45,
        })
        self.env.cr.execute(
            """
            UPDATE project_cost_ledger
               SET currency_id = %s,
                   source_currency_id = NULL,
                   source_amount = NULL,
                   normalization_state = 'normalized'
             WHERE id = %s
            """,
            [foreign_currency.id, row.id],
        )
        row.invalidate_recordset()

        migration(self.env.cr, "17.0.0.136")
        row.invalidate_recordset()
        self.assertEqual(row.source_currency_id, foreign_currency)
        self.assertEqual(row.source_amount, 123.45)
        self.assertEqual(row.currency_id, self.project.company_id.currency_id)
        self.assertEqual(row.amount, 0)
        self.assertEqual(row.normalization_state, "legacy_unresolved_currency")

        migration(self.env.cr, "17.0.0.140")
        row.invalidate_recordset()
        self.assertEqual(row.source_currency_id, foreign_currency)
        self.assertEqual(row.source_amount, 123.45)
        self.assertEqual(row.amount, 0)
        self.assertEqual(row.normalization_state, "legacy_unresolved_currency")

    def test_legacy_unresolved_owner_preserves_unknown_currency_without_guessing(self):
        module_path = get_module_path("smart_construction_core")
        normalize_history = runpy.run_path(
            os.path.join(module_path, "migrations/17.0.0.141/post-migration.py")
        )["migrate"]
        isolate_owner_scope = runpy.run_path(
            os.path.join(module_path, "migrations/17.0.0.142/post-migration.py")
        )["migrate"]
        isolated_project = self.env["project.project"].create({
            "name": "历史归属与币种均未知的项目",
            "company_id": self.env.company.id,
        })
        row = self.Ledger.create({
            "project_id": isolated_project.id,
            "cost_code_id": self.cost_code.id,
            "date": "2026-09-02",
            "amount": 88.0,
        })
        self.env.cr.execute(
            "UPDATE project_project SET company_id = NULL WHERE id = %s",
            [isolated_project.id],
        )
        self.env.cr.execute(
            """
            UPDATE project_cost_ledger
               SET currency_id = NULL,
                   source_currency_id = NULL,
                   source_amount = NULL,
                   normalization_state = 'normalized'
             WHERE id = %s
            """,
            [row.id],
        )
        isolated_project.invalidate_recordset(["company_id"])
        row.invalidate_recordset()

        normalize_history(self.env.cr, "17.0.0.136")
        isolate_owner_scope(self.env.cr, "17.0.0.141")
        row.invalidate_recordset()
        self.assertFalse(row.company_id)
        self.assertFalse(row.currency_id)
        self.assertFalse(row.source_currency_id)
        self.assertEqual(row.source_amount, 88.0)
        self.assertEqual(row.amount, 88.0)
        self.assertEqual(row.normalization_state, "legacy_unresolved_owner")
        self.assertEqual(row.recognition_stage, "legacy_unresolved")
        self.assertEqual(row.reporting_treatment, "memorandum")
        self.env.cr.execute(
            "SELECT ctid::text FROM project_cost_ledger WHERE id = %s", [row.id]
        )
        first_ctid = self.env.cr.fetchone()[0]

        normalize_history(self.env.cr, "17.0.0.141")
        isolate_owner_scope(self.env.cr, "17.0.0.142")
        row.invalidate_recordset()
        self.assertFalse(row.company_id)
        self.assertFalse(row.currency_id)
        self.assertFalse(row.source_currency_id)
        self.assertEqual(row.source_amount, 88.0)
        self.assertEqual(row.amount, 88.0)
        self.assertEqual(row.normalization_state, "legacy_unresolved_owner")
        self.assertEqual(row.recognition_stage, "legacy_unresolved")
        self.assertEqual(row.reporting_treatment, "memorandum")
        self.env.cr.execute(
            "SELECT ctid::text FROM project_cost_ledger WHERE id = %s", [row.id]
        )
        self.assertEqual(self.env.cr.fetchone()[0], first_ctid)

    def test_legacy_known_owner_unknown_currency_replay_never_guesses_source_currency(self):
        module_path = get_module_path("smart_construction_core")
        migration = runpy.run_path(
            os.path.join(module_path, "migrations/17.0.0.141/post-migration.py")
        )["migrate"]
        row = self.Ledger.create({
            "project_id": self.project.id,
            "cost_code_id": self.cost_code.id,
            "date": "2026-09-02",
            "amount": 55.0,
        })
        self.env.cr.execute(
            """
            UPDATE project_cost_ledger
               SET currency_id = NULL,
                   source_currency_id = NULL,
                   source_amount = NULL,
                   normalization_state = 'normalized'
             WHERE id = %s
            """,
            [row.id],
        )
        row.invalidate_recordset()

        migration(self.env.cr, "17.0.0.136")
        row.invalidate_recordset()
        self.assertEqual(row.company_id, self.project.company_id)
        self.assertEqual(row.currency_id, self.project.company_id.currency_id)
        self.assertFalse(row.source_currency_id)
        self.assertEqual(row.source_amount, 55.0)
        self.assertEqual(row.amount, 0)
        self.assertEqual(row.normalization_state, "legacy_unresolved_currency")
        self.env.cr.execute(
            "SELECT ctid::text FROM project_cost_ledger WHERE id = %s", [row.id]
        )
        first_ctid = self.env.cr.fetchone()[0]

        migration(self.env.cr, "17.0.0.141")
        row.invalidate_recordset()
        self.assertEqual(row.currency_id, self.project.company_id.currency_id)
        self.assertFalse(row.source_currency_id)
        self.assertEqual(row.source_amount, 55.0)
        self.assertEqual(row.amount, 0)
        self.assertEqual(row.normalization_state, "legacy_unresolved_currency")
        self.env.cr.execute(
            "SELECT ctid::text FROM project_cost_ledger WHERE id = %s", [row.id]
        )
        self.assertEqual(self.env.cr.fetchone()[0], first_ctid)

    def test_project_period_wbs_and_currency_containment(self):
        with self.assertRaises(ValidationError):
            self.Ledger.create(
                {
                    "project_id": self.project.id,
                    "wbs_id": self.other_wbs.id,
                    "cost_code_id": self.cost_code.id,
                    "date": "2026-09-02",
                    "amount": 10,
                }
            )

        other_company = self.env["res.company"].create(
            {"name": "成本事实其他公司", "currency_id": self.env.company.currency_id.id}
        )
        other_company_project = self.env["project.project"].with_context(
            allowed_company_ids=[self.env.company.id, other_company.id]
        ).create({"name": "其他公司项目", "company_id": other_company.id})
        partner = self.env["res.partner"].create({"name": "跨公司供应商"})
        with self.assertRaises(UserError):
            self.env["purchase.order"].with_context(
                allowed_company_ids=[self.env.company.id, other_company.id]
            ).create(
                {
                    "partner_id": partner.id,
                    "company_id": self.env.company.id,
                    "project_id": other_company_project.id,
                }
            )
        period = self.env["project.cost.period"].create(
            {"project_id": self.project.id, "period": "2026-08"}
        )
        with self.assertRaises(ValidationError):
            self.Ledger.create(
                {
                    "project_id": self.project.id,
                    "period_id": period.id,
                    "cost_code_id": self.cost_code.id,
                    "date": "2026-09-02",
                    "amount": 10,
                }
            )
        other_period = self.env["project.cost.period"].create(
            {"project_id": self.other_project.id, "period": "2026-09"}
        )
        with self.assertRaises(ValidationError):
            self.Ledger.create(
                {
                    "project_id": self.project.id,
                    "period_id": other_period.id,
                    "cost_code_id": self.cost_code.id,
                    "date": "2026-09-02",
                    "amount": 10,
                }
            )

    def test_withdraw_preserves_source_identity_and_repost_reactivates(self):
        values = self._generated_values()
        row = self.Ledger._upsert_generated_cost_rows([values])
        self.Ledger._withdraw_generated_cost_rows(values["source_model"], [values["source_id"]])
        self.assertEqual(row.recognition_state, "withdrawn")
        replay = self.Ledger._upsert_generated_cost_rows([values])
        self.assertEqual(replay, row)
        self.assertEqual(replay.recognition_state, "active")

    def test_manual_adjustment_remains_explicit_actual(self):
        row = self.Ledger.create(
            {
                "project_id": self.project.id,
                "cost_code_id": self.cost_code.id,
                "date": "2026-09-02",
                "amount": 88,
            }
        )
        self.assertFalse(row.is_generated)
        self.assertEqual(row.recognition_stage, "manual_adjustment")
        self.assertEqual(row.reporting_treatment, "manual_actual")

    def test_cost_operator_can_edit_manual_but_never_generated_fact(self):
        user = self.env["res.users"].create(
            {
                "name": "成本事实经办",
                "login": "cost-fact-operator-v2",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [(6, 0, [
                    self.env.ref("base.group_user").id,
                    self.env.ref("smart_construction_core.group_sc_cap_cost_user").id,
                ])],
            }
        )
        self.project.user_id = user
        operator_ledger = self.Ledger.with_user(user)
        manual = operator_ledger.create(
            {
                "project_id": self.project.id,
                "cost_code_id": self.cost_code.id,
                "date": "2026-09-02",
                "amount": 20,
            }
        )
        manual.write({"amount": 25})
        self.assertEqual(manual.amount, 25)
        with self.assertRaises(AccessError):
            manual.with_context(sc_cost_generated_service=True).write(
                {
                    "source_model": "account.move.line",
                    "source_id": 301,
                    "source_line_id": 401,
                }
            )
        generated = self.Ledger._upsert_generated_cost_rows(
            [self._generated_values(source_id=302, source_line_id=402)]
        )
        with self.assertRaises(AccessError):
            generated.with_user(user).with_context(sc_cost_generated_service=True).write(
                {"amount": 1}
            )
        with self.assertRaises(AccessError):
            generated.with_user(user).with_context(sc_cost_generated_service=True).unlink()

    def test_cost_role_matrix_and_source_navigation_acl(self):
        base_group = self.env.ref("base.group_user")
        reader = self.env["res.users"].create({
            "name": "成本事实只读",
            "login": "cost-fact-reader-v2",
            "company_id": self.env.company.id,
            "company_ids": [(6, 0, [self.env.company.id])],
            "groups_id": [(6, 0, [
                base_group.id,
                self.env.ref("smart_construction_core.group_sc_cap_cost_read").id,
            ])],
        })
        manager = self.env["res.users"].create({
            "name": "成本事实经理",
            "login": "cost-fact-manager-v2",
            "company_id": self.env.company.id,
            "company_ids": [(6, 0, [self.env.company.id])],
            "groups_id": [(6, 0, [
                base_group.id,
                self.env.ref("smart_construction_core.group_sc_cap_cost_manager").id,
                self.env.ref("purchase.group_purchase_user").id,
            ])],
        })
        self.project.user_id = manager
        self.project.message_subscribe(partner_ids=[reader.partner_id.id])
        manual = self.Ledger.create({
            "project_id": self.project.id,
            "cost_code_id": self.cost_code.id,
            "date": "2026-09-02",
            "amount": 10,
        })
        self.assertEqual(manual.with_user(reader).amount, 10)
        self.assertEqual(self.Ledger.with_user(reader).search([("id", "=", manual.id)]), manual)
        menu = self.env.ref("smart_construction_core.menu_sc_project_cost_ledger")
        data_center = self.env.ref("smart_construction_core.menu_sc_data_center")
        action = self.env.ref("smart_construction_core.action_project_cost_ledger")
        self.assertIn(
            self.env.ref("smart_construction_core.group_sc_cap_cost_read"),
            menu.groups_id,
        )
        self.assertEqual(menu.parent_id, data_center)
        visible_menu_ids = self.env["ir.ui.menu"].with_user(reader)._visible_menu_ids()
        current_menu = menu
        while current_menu:
            self.assertTrue(current_menu.active)
            self.assertIn(current_menu.id, visible_menu_ids)
            current_menu = current_menu.parent_id
        loaded_menus = self.env["ir.ui.menu"].with_user(reader).load_menus(False)
        self.assertTrue(
            menu.id in loaded_menus or str(menu.id) in loaded_menus,
            "the cost ledger must survive the real native web menu loader",
        )
        self.assertIn(
            self.env.ref("smart_construction_core.group_sc_cap_cost_read"),
            action.groups_id,
        )
        self.assertIn("tree", action.view_mode.split(","))
        self.assertIn("form", action.view_mode.split(","))
        self.assertTrue(self.Ledger.with_user(reader).get_view(view_type="tree")["arch"])
        self.assertTrue(self.Ledger.with_user(reader).get_view(view_type="form")["arch"])
        with self.assertRaises(AccessError):
            self.Ledger.with_user(reader).create({
                "project_id": self.project.id,
                "cost_code_id": self.cost_code.id,
                "date": "2026-09-02",
                "amount": 1,
            })
        manager_manual = self.Ledger.with_user(manager).create({
            "project_id": self.project.id,
            "cost_code_id": self.cost_code.id,
            "date": "2026-09-02",
            "amount": 20,
        })
        manager_manual.write({"amount": 21})
        manager_manual.unlink()

        partner = self.env["res.partner"].create({"name": "导航权限供应商"})
        product = self.env["product.product"].create({
            "name": "导航权限材料", "type": "consu", "purchase_line_warn": "no-message"
        })
        order = self.env["purchase.order"].create({
            "partner_id": partner.id,
            "project_id": self.project.id,
            "order_line": [(0, 0, {
                "name": "导航权限采购行",
                "product_id": product.id,
                "product_qty": 1,
                "product_uom": self.env.ref("uom.product_uom_unit").id,
                "price_unit": 10,
                "project_id": self.project.id,
                "cost_code_id": self.cost_code.id,
            })],
        })
        fact = order._create_cost_ledger_entries()
        with self.assertRaises(AccessError):
            fact.with_user(reader).action_open_source()
        self.assertEqual(
            fact.with_user(manager).action_open_source()["res_id"], order.order_line.id
        )

    def test_conflicting_automatic_sources_fail_closed(self):
        company = self.env.company
        previous = {
            field_name: company[field_name]
            for field_name in (
                "sc_cost_from_account_move",
                "sc_cost_from_purchase",
                "sc_cost_from_stock",
            )
        }
        try:
            with self.assertRaises(ValidationError):
                company.write(
                    {"sc_cost_from_account_move": True, "sc_cost_from_purchase": True}
                )
        finally:
            company.write(previous)

    def test_purchase_writer_creates_commitment_once(self):
        partner = self.env["res.partner"].create({"name": "成本采购供应商"})
        product = self.env["product.product"].create(
            {
                "name": "成本采购材料",
                "type": "consu",
                "purchase_line_warn": "no-message",
            }
        )
        order = self.env["purchase.order"].create(
            {
                "partner_id": partner.id,
                "project_id": self.project.id,
                "company_id": self.env.company.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": "成本采购材料",
                            "product_id": product.id,
                            "product_qty": 2,
                            "product_uom": product.uom_po_id.id,
                            "price_unit": 50,
                            "project_id": self.project.id,
                            "wbs_id": self.wbs.id,
                            "cost_code_id": self.cost_code.id,
                        },
                    )
                ],
            }
        )
        order._create_cost_ledger_entries()
        order._create_cost_ledger_entries()
        row = self.Ledger.search(
            [("source_model", "=", "purchase.order.line"), ("source_line_id", "=", order.order_line.id)]
        )
        self.assertEqual(len(row), 1)
        self.assertEqual(row.recognition_stage, "commitment")
        self.assertEqual(row.reporting_treatment, "memorandum")
        self.assertEqual(row.source_amount, 100)
        source_action = row.action_open_source()
        self.assertEqual(source_action["res_model"], "purchase.order.line")
        self.assertEqual(source_action["res_id"], order.order_line.id)
        order.button_cancel()
        self.assertEqual(row.recognition_state, "withdrawn")

    def test_purchase_writer_uses_each_order_company_authority(self):
        company_a = self.env.company
        company_b = self.env["res.company"].create(
            {"name": "成本来源业务公司", "currency_id": company_a.currency_id.id}
        )
        company_a.write({
            "sc_cost_from_account_move": True,
            "sc_cost_from_purchase": False,
            "sc_cost_from_stock": False,
        })
        company_b.write({
            "sc_cost_from_account_move": False,
            "sc_cost_from_purchase": True,
            "sc_cost_from_stock": False,
        })
        env = self.env(context={
            **self.env.context,
            "allowed_company_ids": [company_a.id, company_b.id],
        })
        project_b = env["project.project"].create(
            {"name": "成本来源公司 B 项目", "company_id": company_b.id}
        )
        partner = env["res.partner"].create({"name": "多公司成本供应商"})
        product = env["product.product"].create(
            {"name": "多公司成本材料", "type": "consu", "purchase_line_warn": "no-message"}
        )

        def make_order(project, company, suffix):
            return env["purchase.order"].create({
                "partner_id": partner.id,
                "project_id": project.id,
                "company_id": company.id,
                "order_line": [(0, 0, {
                    "name": "多公司成本材料 " + suffix,
                    "product_id": product.id,
                    "product_qty": 1,
                    "product_uom": product.uom_po_id.id,
                    "price_unit": 10,
                    "project_id": project.id,
                    "cost_code_id": self.cost_code.id,
                })],
            })

        order_a = make_order(self.project, company_a, "A")
        order_b = make_order(project_b, company_b, "B")
        rows = (order_a | order_b)._create_enabled_cost_ledger_entries()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.source_line_id, order_b.order_line.id)

    def test_project_material_return_creates_negative_operational_fact(self):
        product = self.env["product.product"].create(
            {
                "name": "成本事实退库材料",
                "type": "consu",
                "purchase_line_warn": "no-message",
            }
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        issue = self.env["sc.material.outbound"].create(
            {
                "name": "CFV2-ISSUE",
                "outbound_type": "issue",
                "project_id": self.project.id,
                "warehouse_id": warehouse.id,
                "source_location_id": warehouse.lot_stock_id.id,
                "currency_id": self.env.company.currency_id.id,
                "line_ids": [(0, 0, {
                    "product_id": product.id,
                    "product_uom_id": product.uom_id.id,
                    "qty": 5,
                    "unit_price": 15,
                })],
            }
        )
        issue.action_submit()
        issue.action_issue()
        outbound = self.env["sc.material.outbound"].create(
            {
                "name": "CFV2-RETURN",
                "outbound_type": "return",
                "project_id": self.project.id,
                "warehouse_id": warehouse.id,
                "source_location_id": warehouse.lot_stock_id.id,
                "currency_id": self.env.company.currency_id.id,
                "line_ids": [(0, 0, {
                    "product_id": product.id,
                    "product_uom_id": product.uom_id.id,
                    "qty": 3,
                    "unit_price": 999,
                    "origin_issue_line_id": issue.line_ids.id,
                })],
            }
        )
        native_return_line = self.env["sc.material.outbound.line"].new({
            "outbound_id": outbound.id,
            "origin_issue_line_id": issue.line_ids.id,
        })
        native_return_line._onchange_origin_issue_line_id()
        self.assertEqual(native_return_line.product_id, product)
        self.assertFalse(native_return_line.material_catalog_id)
        native_arch = self.env.ref(
            "smart_construction_core.view_sc_material_outbound_form"
        ).arch_db
        self.assertIn(
            'name="material_catalog_id" required="parent.outbound_type != \'return\'"',
            native_arch,
        )
        outbound.action_submit()
        outbound.action_issue()
        rows = self.Ledger.search([
            ("source_model", "=", "sc.material.outbound"),
            ("source_id", "=", outbound.id),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.qty, -3)
        self.assertEqual(rows.source_amount, -45)
        self.assertEqual(rows.reporting_treatment, "operational_actual")
        category = self.env["sc.business.category"].search(
            [("code", "=", "material.return")], limit=1
        )
        self.assertTrue(category)
        policy = json.loads(category.ledger_policy_json)
        self.assertTrue(
            policy["cost_triggers"]["issue_project_cost_ledger"]
        )
        self.assertEqual(issue.line_ids.returned_qty, 3)
        with self.assertRaises(UserError):
            issue.line_ids.write({"qty": 6})
        with self.assertRaises(UserError):
            outbound.line_ids.write({"origin_issue_line_id": False})
        with self.assertRaises(UserError):
            issue.write({"outbound_date": "2026-09-03"})
        with self.assertRaises(UserError):
            outbound.write({"state": "draft"})

        excessive = self.env["sc.material.outbound"].create(
            {
                "name": "CFV2-RETURN-EXCESS",
                "outbound_type": "return",
                "project_id": self.project.id,
                "warehouse_id": warehouse.id,
                "source_location_id": warehouse.lot_stock_id.id,
                "currency_id": self.env.company.currency_id.id,
                "line_ids": [
                    (0, 0, {
                        "product_id": product.id,
                        "product_uom_id": product.uom_id.id,
                        "qty": 1.5,
                        "unit_price": 15,
                        "origin_issue_line_id": issue.line_ids.id,
                    }),
                    (0, 0, {
                        "product_id": product.id,
                        "product_uom_id": product.uom_id.id,
                        "qty": 1.5,
                        "unit_price": 15,
                        "origin_issue_line_id": issue.line_ids.id,
                    }),
                ],
            }
        )
        with self.assertRaises(ValidationError):
            excessive.action_submit()

    def test_confirmed_custom_cost_sources_are_immutable(self):
        product = self.env["product.product"].create(
            {"name": "终态事实材料", "type": "consu", "purchase_line_warn": "no-message"}
        )
        supplier = self.env["res.partner"].create({"name": "终态事实供应商"})
        settlement = self.env["sc.material.settlement"].create({
            "name": "CFV2-SETTLEMENT-LOCK",
            "project_id": self.project.id,
            "supplier_id": supplier.id,
            "currency_id": self.env.company.currency_id.id,
            "line_ids": [(0, 0, {
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "qty": 2,
                "unit_price": 30,
            })],
        })
        with self.assertRaises(UserError):
            settlement.write({"state": "confirmed"})
        settlement.action_submit()
        settlement.action_confirm()
        with self.assertRaises(UserError):
            settlement.write({"settlement_date": "2026-09-03"})
        with self.assertRaises(UserError):
            settlement.line_ids.write({"unit_price": 31})
        with self.assertRaises(UserError):
            settlement.write({"state": "draft"})

        usage_values = {
            "name": "CFV2-USAGE-LOCK",
            "project_id": self.project.id,
            "usage_date": "2026-09-02",
            "equipment_name": "塔吊",
            "usage_location": "一号楼",
            "operator_name": "测试操作员",
            "usage_qty": 1,
            "usage_hours": 2,
            "currency_id": self.env.company.currency_id.id,
            "price_unit": 50,
        }
        with self.assertRaises(UserError):
            self.env["sc.equipment.usage"].create({**usage_values, "state": "confirmed"})
        usage = self.env["sc.equipment.usage"].create(usage_values)
        usage.action_submit()
        usage.action_confirm()
        with self.assertRaises(UserError):
            usage.write({"usage_hours": 3})
        with self.assertRaises(UserError):
            usage.write({"state": "draft"})
        with self.assertRaises(UserError):
            usage.unlink()

    def test_generated_batch_has_bounded_query_growth(self):
        def values(count, offset):
            return [
                self._generated_values(
                    source_id=offset + index,
                    source_line_id=offset + 1000 + index,
                )
                for index in range(count)
            ]

        self.Ledger._upsert_generated_cost_rows(values(1, 10000))
        start = self.env.cr.sql_log_count
        self.Ledger._upsert_generated_cost_rows(values(10, 20000))
        ten_count = self.env.cr.sql_log_count - start
        start = self.env.cr.sql_log_count
        self.Ledger._upsert_generated_cost_rows(values(100, 30000))
        hundred_count = self.env.cr.sql_log_count - start
        self.assertLessEqual(hundred_count, ten_count + 8)

        ten = values(10, 40000)
        hundred = values(100, 50000)
        self.Ledger._upsert_generated_cost_rows(ten)
        self.Ledger._upsert_generated_cost_rows(hundred)
        corrected_ten = [{**item, "source_amount": 250.0} for item in ten]
        corrected_hundred = [{**item, "source_amount": 250.0} for item in hundred]
        start = self.env.cr.sql_log_count
        self.Ledger._upsert_generated_cost_rows(corrected_ten)
        ten_update_count = self.env.cr.sql_log_count - start
        start = self.env.cr.sql_log_count
        self.Ledger._upsert_generated_cost_rows(corrected_hundred)
        hundred_update_count = self.env.cr.sql_log_count - start
        self.assertLessEqual(hundred_update_count, ten_update_count + 12)

        start = self.env.cr.sql_log_count
        self.Ledger._withdraw_generated_cost_rows(
            "account.move.line", [item["source_id"] for item in ten]
        )
        ten_withdraw_count = self.env.cr.sql_log_count - start
        start = self.env.cr.sql_log_count
        self.Ledger._withdraw_generated_cost_rows(
            "account.move.line", [item["source_id"] for item in hundred]
        )
        hundred_withdraw_count = self.env.cr.sql_log_count - start
        self.assertLessEqual(hundred_withdraw_count, ten_withdraw_count + 8)
        start = self.env.cr.sql_log_count
        self.Ledger._upsert_generated_cost_rows(corrected_hundred)
        reactivate_count = self.env.cr.sql_log_count - start
        self.assertLessEqual(reactivate_count, hundred_update_count + 8)

    def test_account_writer_uses_signed_company_balance_and_draft_withdraws(self):
        expense = self.env["account.account"].create(
            {"name": "成本事实费用", "code": "CFV2EXP", "account_type": "expense"}
        )
        payable = self.env["account.account"].create(
            {"name": "成本事实应付", "code": "CFV2PAY", "account_type": "liability_current"}
        )
        journal = self.env["account.journal"].create(
            {"name": "成本事实日记账", "code": "CFV2J", "type": "general", "company_id": self.env.company.id}
        )
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2026-09-02",
                "project_id": self.project.id,
                "journal_id": journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "成本确认",
                            "account_id": expense.id,
                            "debit": 300,
                            "credit": 0,
                            "wbs_id": self.wbs.id,
                            "cost_code_id": self.cost_code.id,
                        },
                    ),
                    (0, 0, {"name": "应付", "account_id": payable.id, "debit": 0, "credit": 300}),
                ],
            }
        )
        company = self.env.company
        previous = {
            field_name: company[field_name]
            for field_name in (
                "sc_cost_from_account_move",
                "sc_cost_from_purchase",
                "sc_cost_from_stock",
            )
        }
        try:
            company.write(
                {
                    "sc_cost_from_account_move": True,
                    "sc_cost_from_purchase": False,
                    "sc_cost_from_stock": False,
                }
            )
            move.action_post()
            row = self.Ledger.search(
                [("source_model", "=", "account.move.line"), ("source_id", "=", move.id)]
            )
            self.assertEqual(len(row), 1)
            self.assertEqual(row.amount, 300)
            self.assertEqual(row.recognition_stage, "accounting_actual")
            self.assertEqual(row.reporting_treatment, "financial_actual")
            move.button_draft()
            self.assertEqual(row.recognition_state, "withdrawn")

            usd = self.env.ref("base.USD")
            usd.active = True
            source_amount = 40.0
            company_amount = 123.45
            foreign_move = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "date": "2026-09-02",
                    "project_id": self.project.id,
                    "journal_id": journal.id,
                    "line_ids": [
                        (0, 0, {
                            "name": "外币成本确认",
                            "account_id": expense.id,
                            "debit": company_amount,
                            "currency_id": usd.id,
                            "amount_currency": source_amount,
                            "wbs_id": self.wbs.id,
                            "cost_code_id": self.cost_code.id,
                        }),
                        (0, 0, {
                            "name": "外币应付",
                            "account_id": payable.id,
                            "credit": company_amount,
                            "currency_id": usd.id,
                            "amount_currency": -source_amount,
                        }),
                    ],
                }
            )
            foreign_move.action_post()
            foreign_row = self.Ledger.search([
                ("source_model", "=", "account.move.line"),
                ("source_id", "=", foreign_move.id),
            ])
            self.assertEqual(foreign_row.source_currency_id, usd)
            self.assertEqual(foreign_row.source_amount, source_amount)
            self.assertAlmostEqual(foreign_row.amount, company_amount, places=2)

            action = self.env.ref("smart_construction_core.action_project_cost_ledger")
            self.assertNotIn(("recognition_state", "=", "active"), safe_eval(action.domain or "[]"))
            self.assertEqual(safe_eval(action.context)["search_default_filter_active"], 1)
        finally:
            company.write(previous)
