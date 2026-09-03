# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    """Extend stock moves with project/cost metadata for cost ledger writes."""

    _inherit = "stock.move"
    _check_company_auto = True

    project_id = fields.Many2one(
        "project.project",
        string="项目",
        check_company=True,
        compute="_compute_project_fields",
        store=True,
        recursive=True,
        readonly=False,
    )
    wbs_id = fields.Many2one(
        "construction.work.breakdown",
        string="工程结构",
        domain="[('project_id', '=', project_id)]",
        compute="_compute_project_fields",
        store=True,
        recursive=True,
        readonly=False,
    )
    cost_code_id = fields.Many2one(
        "project.cost.code",
        string="成本科目",
        compute="_compute_cost_code",
        store=True,
        recursive=True,
        readonly=False,
    )

    @api.depends(
        "picking_id",
        "picking_id.project_id",
        "product_id",
        "origin_returned_move_id",
        "origin_returned_move_id.project_id",
        "origin_returned_move_id.wbs_id",
    )
    def _compute_project_fields(self):
        """Propagate项目/WBS信息:优先取采购行，其次取入库单抬头。"""
        for move in self:
            project = False
            wbs = False
            purchase_line = getattr(move, "purchase_line_id", False)
            if purchase_line:
                project = purchase_line.project_id or purchase_line.order_id.project_id
                wbs = getattr(purchase_line, "wbs_id", False)
            elif move.origin_returned_move_id:
                project = move.origin_returned_move_id.project_id
                wbs = move.origin_returned_move_id.wbs_id
            elif move.picking_id and move.picking_id.project_id:
                project = move.picking_id.project_id
            move.project_id = project.id if project else False
            move.wbs_id = wbs.id if wbs else False

    @api.depends("product_id", "origin_returned_move_id", "origin_returned_move_id.cost_code_id")
    def _compute_cost_code(self):
        """Derive成本科目：采购行优先，其次读取产品默认值。"""
        for move in self:
            cost_code = False
            purchase_line = getattr(move, "purchase_line_id", False)
            if purchase_line and purchase_line.cost_code_id:
                cost_code = purchase_line.cost_code_id
            elif move.origin_returned_move_id:
                cost_code = move.origin_returned_move_id.cost_code_id
            elif move.product_id.default_cost_code_id:
                cost_code = move.product_id.default_cost_code_id
            move.cost_code_id = cost_code.id if cost_code else False


class StockPicking(models.Model):
    """Hook incoming receipts to create project cost ledger entries."""

    _inherit = "stock.picking"
    _check_company_auto = True

    project_id = fields.Many2one(
        "project.project",
        string="项目",
        check_company=True,
        help="用于将入库成本写入项目台账。",
    )

    def button_validate(self):
        """After standard validation, push成本信息至台账。"""
        for picking in self:
            if picking.project_id:
                picking.project_id._ensure_operation_allowed(
                    operation_label="确认出入库",
                    blocked_states=("paused", "closed"),
                )
        res = super().button_validate()
        for company in self.mapped("company_id"):
            company_pickings = self.filtered(lambda picking: picking.company_id == company)
            if company_pickings._is_cost_enabled(
                "smart_construction_core.sc_cost_from_stock", company=company
            ):
                company_pickings._create_cost_ledger_from_moves()
        return res

    def _is_cost_enabled(self, param_key, company=None):
        return self.env["project.cost.ledger"]._automatic_source_enabled(
            param_key, company=company
        )

    def _create_cost_ledger_from_moves(self):
        """Create ledger entries for each incoming move (材料成本自动落账)。"""
        ledger_obj = self.env["project.cost.ledger"]
        values = []
        moves = self.mapped("move_ids").filtered(
            lambda move: (
                move.project_id
                and move.cost_code_id
                and move.quantity > 0
                and (
                    move.location_id.usage == "supplier"
                    or (
                        move.origin_returned_move_id
                        and move.location_dest_id.usage == "supplier"
                    )
                )
            )
        )
        return_origin_ids = moves.mapped("origin_returned_move_id").ids
        ledger_obj._lock_generated_source_headers(
            [("stock.move", source_id) for source_id in return_origin_ids]
            + [("stock.move", move_id) for move_id in moves.ids]
        )
        scope_values = []
        for move in moves:
            ledger_date = (
                move.picking_id.date_done.date()
                if move.picking_id.date_done
                else fields.Date.context_today(self)
            )
            scope_values.append({
                "project_id": move.project_id.id,
                "period": ledger_obj._compute_period_value(ledger_date),
            })
        ledger_obj._resolve_periods(scope_values)
        scope_periods = self.env["project.cost.period"].browse(
            sorted({vals["period_id"] for vals in scope_values})
        )
        ledger_obj._lock_cost_periods(scope_periods)
        for period in scope_periods:
            ledger_obj._ensure_period_unlocked(period, "Write")
        ledger_obj._lock_existing_generated_source_rows(
            [("stock.move", source_id) for source_id in return_origin_ids]
        )
        ledger_obj.invalidate_model()
        origin_facts = ledger_obj.sudo().search([
            ("source_model", "=", "stock.move"),
            ("source_id", "in", return_origin_ids),
            ("recognition_state", "=", "active"),
        ]) if return_origin_ids else ledger_obj.browse()
        origin_fact_by_move = {fact.source_id: fact for fact in origin_facts}
        for picking in self:
            for move in picking.move_ids & moves:
                is_supplier_return = bool(
                    move.origin_returned_move_id and move.location_dest_id.usage == "supplier"
                )
                source_move = move.origin_returned_move_id if is_supplier_return else move
                purchase_line = getattr(source_move, "purchase_line_id", False)
                origin_fact = origin_fact_by_move.get(source_move.id)
                if is_supplier_return and (not origin_fact or not origin_fact.qty):
                    raise ValidationError(
                        _("供应商退货必须锚定有效的原收货成本事实，禁止按采购价或标准价猜测冲销。")
                    )
                if origin_fact and origin_fact.qty:
                    base_price = abs(origin_fact.source_amount / origin_fact.qty)
                    source_currency = origin_fact.source_currency_id
                else:
                    base_price = purchase_line.price_unit if purchase_line else move.product_id.standard_price
                    source_currency = (
                        purchase_line.order_id.currency_id
                        if purchase_line
                        else move.company_id.currency_id
                    )
                ledger_date = move.picking_id.date_done.date() if move.picking_id.date_done else fields.Date.context_today(self)
                signed_qty = -move.quantity if is_supplier_return else move.quantity
                amount = base_price * signed_qty
                vals = {
                    "project_id": move.project_id.id,
                    "wbs_id": move.wbs_id.id,
                    "cost_code_id": move.cost_code_id.id,
                    "date": ledger_date,
                    "qty": signed_qty,
                    "uom_id": move.product_uom.id,
                    "source_amount": amount,
                    "source_currency_id": source_currency.id,
                    "partner_id": picking.partner_id.id,
                    "source_model": "stock.move",
                    "source_id": move.id,
                    "source_line_id": move.id,
                    "note": (
                        f"{picking.name} - {move.product_id.display_name}"
                        + ("（供应商退货）" if is_supplier_return else "")
                    ),
                }
                values.append(vals)
        return ledger_obj._upsert_generated_cost_rows(values)
