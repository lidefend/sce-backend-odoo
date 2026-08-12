# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..support.state_guard import raise_guard


class ScSettlementOrder(models.Model):
    _inherit = "sc.settlement.order"

    contract_source_kind = fields.Selection(
        [
            ("construction_contract", "项目合同"),
            ("general_contract", "日常合同"),
        ],
        string="合同来源",
        default=lambda self: self.env.context.get("default_contract_source_kind") or "construction_contract",
        index=True,
        tracking=True,
    )
    general_contract_id = fields.Many2one(
        "sc.general.contract",
        string="日常合同",
        index=True,
        ondelete="restrict",
        tracking=True,
        domain="[('company_id', '=', company_id), '|', ('project_id', '=', False), ('project_id', '=', project_id)]",
    )
    source_contract_model = fields.Char(
        string="来源合同模型",
        compute="_compute_contract_source_projection",
        store=True,
        index=True,
    )
    source_contract_res_id = fields.Integer(
        string="来源合同记录ID",
        compute="_compute_contract_source_projection",
        store=True,
        index=True,
    )
    source_contract_name = fields.Char(
        string="来源合同名称",
        compute="_compute_contract_source_projection",
        store=True,
        index=True,
    )
    source_contract_no = fields.Char(
        string="来源合同编号",
        compute="_compute_contract_source_projection",
        store=True,
        index=True,
    )

    def init(self):
        super().init()
        self.env.cr.execute(
            """
            UPDATE sc_settlement_order
               SET contract_source_kind = 'construction_contract'
             WHERE contract_id IS NOT NULL
               AND general_contract_id IS NULL
               AND contract_source_kind IS NULL
            """
        )

    @api.depends(
        "contract_id",
        "contract_id.subject",
        "contract_id.name",
        "general_contract_id",
        "general_contract_id.contract_name",
        "general_contract_id.contract_no",
        "general_contract_id.name",
    )
    def _compute_contract_source_projection(self):
        for order in self:
            if order.general_contract_id:
                contract = order.general_contract_id
                order.source_contract_model = "sc.general.contract"
                order.source_contract_res_id = contract.id
                order.source_contract_name = contract.contract_name or contract.display_name
                order.source_contract_no = contract.contract_no or contract.name
            elif order.contract_id:
                contract = order.contract_id
                order.source_contract_model = "construction.contract"
                order.source_contract_res_id = contract.id
                order.source_contract_name = contract.subject or contract.display_name
                order.source_contract_no = contract.name
            else:
                order.source_contract_model = False
                order.source_contract_res_id = 0
                order.source_contract_name = False
                order.source_contract_no = False

    @api.constrains("contract_id", "general_contract_id", "contract_source_kind")
    def _check_exclusive_contract_source(self):
        for order in self:
            if order.contract_id and order.general_contract_id:
                raise ValidationError(_("一张结算单只能关联项目合同或日常合同，不能同时关联两类合同。"))
            if order.contract_id and order.contract_source_kind == "general_contract":
                raise ValidationError(_("日常合同结算不能关联项目合同。"))
            if order.general_contract_id and order.contract_source_kind != "general_contract":
                raise ValidationError(_("日常合同来源必须使用“日常合同”合同来源类型。"))

    @api.constrains(
        "general_contract_id",
        "project_id",
        "company_id",
        "partner_id",
        "currency_id",
        "settlement_type",
    )
    def _check_general_contract_consistency(self):
        for order in self.filtered("general_contract_id"):
            contract = order.general_contract_id
            if contract.company_id != order.company_id:
                raise ValidationError(_("日常合同公司与结算单公司不一致。"))
            if contract.project_id and contract.project_id != order.project_id:
                raise ValidationError(_("日常合同项目与结算单项目不一致。"))
            if contract.partner_id and order.partner_id and contract.partner_id != order.partner_id:
                raise ValidationError(_("日常合同往来单位与结算单往来单位不一致。"))
            if contract.currency_id and order.currency_id and contract.currency_id != order.currency_id:
                raise ValidationError(_("日常合同币种与结算单币种不一致。"))
            expected = order._settlement_type_from_general_contract(contract)
            if expected and order.settlement_type != expected:
                raise ValidationError(_("日常合同方向与结算收支类型不一致。"))

    @api.model
    def _settlement_type_from_general_contract(self, contract):
        if contract.contract_direction == "income":
            return "in"
        if contract.contract_direction == "expense":
            return "out"
        return False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("general_contract_id"):
                vals["contract_source_kind"] = "general_contract"
                vals["contract_id"] = False
                self._apply_general_contract_values(vals)
        return super().create(vals_list)

    def write(self, vals):
        source_fields = {"contract_id", "general_contract_id", "contract_source_kind"}
        if source_fields & set(vals):
            locked = self.filtered(lambda order: order.state != "draft")
            if locked:
                raise UserError(_("结算单提交后不能更换合同来源；请退回草稿后处理。"))
        values = dict(vals)
        if values.get("general_contract_id"):
            values["contract_source_kind"] = "general_contract"
            values["contract_id"] = False
            self._apply_general_contract_values(values)
        elif values.get("contract_id"):
            values["contract_source_kind"] = "construction_contract"
            values["general_contract_id"] = False
        result = super().write(values)
        if "general_contract_id" in values and not self.env.context.get("skip_settlement_contract_projection"):
            self._synchronize_detail_contract_projection(explicit_header_contract=bool(values.get("general_contract_id")))
        return result

    @api.model
    def _apply_general_contract_values(self, vals):
        contract = self.env["sc.general.contract"].browse(vals.get("general_contract_id")).exists()
        if not contract:
            return vals
        if contract.project_id:
            vals.setdefault("project_id", contract.project_id.id)
        vals.setdefault("company_id", contract.company_id.id)
        if contract.currency_id:
            vals.setdefault("currency_id", contract.currency_id.id)
        if contract.partner_id:
            vals.setdefault("partner_id", contract.partner_id.id)
            vals.setdefault("settlement_unit_id", contract.partner_id.id)
        settlement_type = self._settlement_type_from_general_contract(contract)
        if settlement_type:
            vals["settlement_type"] = settlement_type
        return vals

    @api.onchange("general_contract_id")
    def _onchange_general_contract_id(self):
        for order in self:
            contract = order.general_contract_id
            if not contract:
                continue
            order.contract_source_kind = "general_contract"
            order.contract_id = False
            if contract.project_id:
                order.project_id = contract.project_id
            order.company_id = contract.company_id
            order.currency_id = contract.currency_id
            if contract.partner_id:
                order.partner_id = contract.partner_id
                order.settlement_unit_id = contract.partner_id
            settlement_type = order._settlement_type_from_general_contract(contract)
            if settlement_type:
                order.settlement_type = settlement_type

    def _synchronize_detail_contract_projection(self, *, explicit_header_contract=False):
        general_orders = self.filtered(lambda order: order.contract_source_kind == "general_contract" or order.general_contract_id)
        standard_orders = self - general_orders
        if standard_orders:
            super(ScSettlementOrder, standard_orders)._synchronize_detail_contract_projection(
                explicit_header_contract=explicit_header_contract
            )
        for order in general_orders:
            if order.contract_id:
                raise UserError(_("日常合同结算不能保留项目合同来源。"))
            if not order.line_ids:
                continue
            wrong = order.line_ids.filtered(
                lambda line: line.contract_id
                or not line.general_contract_id
                or line.general_contract_id != order.general_contract_id
            )
            if wrong:
                raise UserError(_("日常合同结算的全部明细必须绑定表头同一份日常合同。"))

    def _check_line_contracts_or_raise(self):
        general_orders = self.filtered(lambda order: order.contract_source_kind == "general_contract" or order.general_contract_id)
        standard_orders = self - general_orders
        if standard_orders:
            super(ScSettlementOrder, standard_orders)._check_line_contracts_or_raise()
        for order in general_orders:
            if not order.general_contract_id:
                raise_guard(
                    "SETTLEMENT_GENERAL_CONTRACT_REQUIRED",
                    "结算单[%s]" % order.display_name,
                    _("校验日常合同结算"),
                    reasons=[_("日常合同结算必须选择日常合同")],
                )
            contract = order.general_contract_id
            if contract.contract_direction not in ("income", "expense"):
                raise_guard(
                    "SETTLEMENT_GENERAL_CONTRACT_DIRECTION_REQUIRED",
                    "结算单[%s]" % order.display_name,
                    _("校验日常合同结算"),
                    reasons=[_("日常合同必须明确为收入合同或支出合同")],
                )
            if contract.state not in ("confirmed", "signed", "legacy_confirmed"):
                raise_guard(
                    "SETTLEMENT_GENERAL_CONTRACT_STATE_INVALID",
                    "结算单[%s]" % order.display_name,
                    _("校验日常合同结算"),
                    reasons=[_("日常合同必须已确认或已签署")],
                )
            order._synchronize_detail_contract_projection(explicit_header_contract=True)

    @api.depends(
        "contract_id.amount_final",
        "contract_id.amount_total",
        "contract_id.engineering_address",
        "general_contract_id.amount_total",
        "general_contract_id.engineering_address",
        "project_id",
    )
    def _compute_contract_snapshot(self):
        general_orders = self.filtered("general_contract_id")
        standard_orders = self - general_orders
        if standard_orders:
            super(ScSettlementOrder, standard_orders)._compute_contract_snapshot()
        for order in general_orders:
            contract = order.general_contract_id
            order.contract_total_amount = contract.amount_total or 0.0
            order.engineering_address = (
                contract.engineering_address
                or getattr(order.project_id, "sc_address", False)
                or getattr(order.project_id, "location", False)
                or ""
            )


class ScSettlementOrderLine(models.Model):
    _inherit = "sc.settlement.order.line"

    general_contract_id = fields.Many2one(
        "sc.general.contract",
        string="日常合同",
        index=True,
        ondelete="restrict",
    )

    @api.constrains("contract_id", "general_contract_id")
    def _check_exclusive_contract_source(self):
        for line in self:
            if line.contract_id and line.general_contract_id:
                raise ValidationError(_("结算明细只能关联项目合同或日常合同。"))

    @api.model_create_multi
    def create(self, vals_list):
        has_general_rows = False
        for vals in vals_list:
            settlement = self.env["sc.settlement.order"].browse(vals.get("settlement_id")).exists()
            if settlement and (settlement.contract_source_kind == "general_contract" or settlement.general_contract_id):
                has_general_rows = True
                vals["contract_id"] = False
                vals.setdefault("general_contract_id", settlement.general_contract_id.id)
        records = super(
            ScSettlementOrderLine,
            self.with_context(legacy_migration_allow_missing_contract=has_general_rows),
        ).create(vals_list)
        records._check_general_contract_match()
        if not self.env.context.get("legacy_migration_allow_missing_contract"):
            invalid_standard = records.filtered(
                lambda item: item.settlement_id.contract_source_kind != "general_contract" and not item.contract_id
            )
            if invalid_standard:
                raise ValidationError(_("项目合同结算明细必须关联项目合同。"))
        return records

    def write(self, vals):
        result = super().write(vals)
        self._check_general_contract_match()
        if "general_contract_id" in vals:
            self.mapped("settlement_id")._synchronize_detail_contract_projection()
        return result

    def _check_general_contract_match(self):
        for line in self.filtered(lambda item: item.settlement_id.contract_source_kind == "general_contract"):
            if line.contract_id or line.general_contract_id != line.settlement_id.general_contract_id:
                raise ValidationError(_("结算明细日常合同必须与结算单表头一致。"))


class PaymentRequest(models.Model):
    _inherit = "payment.request"

    settlement_contract_source_model = fields.Char(
        related="settlement_id.source_contract_model",
        string="结算来源合同模型",
        store=True,
        readonly=True,
        index=True,
    )
    settlement_contract_source_res_id = fields.Integer(
        related="settlement_id.source_contract_res_id",
        string="结算来源合同记录ID",
        store=True,
        readonly=True,
        index=True,
    )


class ScInvoiceRegistration(models.Model):
    _inherit = "sc.invoice.registration"

    settlement_contract_source_model = fields.Char(
        related="settlement_id.source_contract_model",
        string="结算来源合同模型",
        store=True,
        readonly=True,
        index=True,
    )
    settlement_contract_source_res_id = fields.Integer(
        related="settlement_id.source_contract_res_id",
        string="结算来源合同记录ID",
        store=True,
        readonly=True,
        index=True,
    )
