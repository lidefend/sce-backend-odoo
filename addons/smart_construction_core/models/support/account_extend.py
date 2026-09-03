# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"
    _check_company_auto = True

    project_id = fields.Many2one(
        "project.project",
        string="关联项目",
        check_company=True,
        help="用于将发票/凭证成本写入项目台账。",
    )

    def action_post(self):
        res = super().action_post()
        for company in self.mapped("company_id"):
            company_moves = self.filtered(lambda move: move.company_id == company)
            if company_moves._is_cost_enabled(
                "smart_construction_core.sc_cost_from_account_move", company=company
            ):
                company_moves._create_cost_ledger_entries()
        return res

    def button_draft(self):
        res = super().button_draft()
        self.env["project.cost.ledger"]._withdraw_generated_cost_rows(
            "account.move.line", self.ids
        )
        return res

    def _is_cost_enabled(self, param_key, company=None):
        return self.env["project.cost.ledger"]._automatic_source_enabled(
            param_key, company=company
        )

    def _create_cost_ledger_entries(self):
        ledger_obj = self.env["project.cost.ledger"]
        values = []
        for move in self.filtered(lambda m: m.move_type in ("in_invoice", "in_refund", "entry")):
            for line in move.line_ids.filtered(
                lambda line: line.display_type not in ("line_section", "line_note")
            ):
                vals = line._prepare_cost_ledger_vals()
                if not vals:
                    continue
                values.append(vals)
        return ledger_obj._upsert_generated_cost_rows(values)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    project_id = fields.Many2one(
        "project.project",
        string="项目",
        related="move_id.project_id",
        store=True,
        readonly=False,
    )
    wbs_id = fields.Many2one(
        "construction.work.breakdown",
        string="工程结构",
        domain="[('project_id', '=', project_id)]",
    )
    cost_code_id = fields.Many2one(
        "project.cost.code",
        string="成本科目",
    )

    def _prepare_cost_ledger_vals(self):
        self.ensure_one()
        project = self.project_id
        if not project or not self.cost_code_id:
            return False
        internal_group = self.account_id.internal_group
        if internal_group not in ("expense", "asset"):
            return False
        company_amount = self.balance
        if not company_amount:
            return False
        source_currency = self.currency_id or self.company_currency_id
        source_amount = (
            self.amount_currency
            if self.currency_id and self.currency_id != self.company_currency_id
            else company_amount
        )
        return {
            "project_id": project.id,
            "wbs_id": self.wbs_id.id,
            "cost_code_id": self.cost_code_id.id,
            "date": self.date or fields.Date.context_today(self),
            "qty": self.quantity,
            "uom_id": self.product_uom_id.id,
            "source_amount": source_amount,
            "source_currency_id": source_currency.id,
            "company_amount": company_amount,
            "partner_id": self.partner_id.id,
            "source_model": "account.move.line",
            "source_id": self.move_id.id,
            "source_line_id": self.id,
            "note": f"{self.move_id.name or self.move_id.ref} - {self.name}",
        }
