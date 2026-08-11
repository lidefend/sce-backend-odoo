# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ScMaterialSupplierReturn(models.Model):
    _name = "sc.material.supplier.return"
    _description = "材料退货单"
    _inherit = ["mail.thread", "mail.activity.mixin", "sc.material.system.default.mixin"]
    _order = "return_date desc, id desc"

    name = fields.Char("退货单号", required=True, default="新建", copy=False, tracking=True)
    project_id = fields.Many2one(
        "project.project", string="项目", required=True, index=True, tracking=True
    )
    company_id = fields.Many2one(
        related="project_id.company_id", store=True, readonly=True, string="所属公司"
    )
    source_inbound_id = fields.Many2one(
        "sc.material.inbound",
        string="来源入库单",
        index=True,
        domain="[('project_id', '=', project_id), ('state', '=', 'received')]",
        tracking=True,
    )
    supplier_id = fields.Many2one(
        "res.partner", string="退货供应商", domain=[("supplier_rank", ">", 0)], index=True
    )
    warehouse_id = fields.Many2one(
        "stock.warehouse",
        string="退货仓库",
        required=True,
        index=True,
        default=lambda self: self._sc_default_warehouse_id(),
    )
    source_location_id = fields.Many2one(
        "stock.location",
        string="退货库位",
        required=True,
        index=True,
        default=lambda self: self._sc_default_location_id(),
    )
    return_date = fields.Date("退货日期", default=fields.Date.context_today, index=True)
    reason = fields.Text("退货原因")
    responsible_id = fields.Many2one(
        "res.users", string="经办人", default=lambda self: self.env.user, index=True
    )
    currency_id = fields.Many2one(
        related="project_id.company_id.currency_id", store=True, readonly=True
    )
    amount_total = fields.Monetary(
        "退货金额", currency_field="currency_id", compute="_compute_amount_total", store=True
    )
    line_ids = fields.One2many(
        "sc.material.supplier.return.line", "return_id", string="退货明细"
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sc_material_supplier_return_attachment_rel",
        "return_id",
        "attachment_id",
        string="退货依据",
    )
    stock_picking_id = fields.Many2one(
        "stock.picking", string="库存退货单", readonly=True, copy=False, index=True
    )
    state = fields.Selection(
        [
            ("draft", "草稿"),
            ("submitted", "待确认"),
            ("returned", "已退货"),
            ("cancel", "已取消"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    processing_advisory = fields.Char("办理建议", compute="_compute_processing_advisory")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for values in vals_list:
            self._sc_apply_system_defaults(
                values,
                {
                    "project_id": "_sc_default_project_id",
                    "warehouse_id": "_sc_default_warehouse_id",
                },
            )
            if not values.get("source_location_id"):
                values["source_location_id"] = self._sc_default_location_id(
                    values.get("warehouse_id")
                )
                self._sc_mark_system_defaults(values, ["source_location_id"])
            if values.get("name", "新建") == "新建":
                values["name"] = sequence.next_by_code("sc.material.supplier.return") or _(
                    "材料退货单"
                )
        return super().create(vals_list)

    @api.depends("line_ids.amount")
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(record.line_ids.mapped("amount"))

    @api.depends(
        "source_inbound_id",
        "supplier_id",
        "return_date",
        "reason",
        "attachment_ids",
    )
    def _compute_processing_advisory(self):
        for record in self:
            suggestions = []
            if not record.source_inbound_id:
                suggestions.append("建议关联来源入库单，便于核对可退数量")
            if not record.supplier_id:
                suggestions.append("建议补充退货供应商")
            if not record.return_date:
                suggestions.append("建议补充退货日期")
            if not record.reason:
                suggestions.append("建议补充退货原因")
            if not record.attachment_ids:
                suggestions.append("建议上传退货依据")
            record.processing_advisory = (
                "；".join(suggestions) if suggestions else "当前退货资料已完善"
            )

    @api.onchange("source_inbound_id")
    def _onchange_source_inbound_id(self):
        for record in self:
            inbound = record.source_inbound_id
            if not inbound:
                continue
            record.project_id = inbound.project_id
            record.supplier_id = inbound.supplier_id
            record.warehouse_id = inbound.warehouse_id
            record.source_location_id = inbound.dest_location_id

    def action_load_inbound_lines(self):
        for record in self:
            inbound = record.source_inbound_id
            if not inbound:
                raise ValidationError(_("请先选择来源入库单。"))
            record.line_ids = [(5, 0, 0)] + [
                (
                    0,
                    0,
                    {
                        "source_inbound_line_id": line.id,
                        "product_id": line.product_id.id,
                        "material_catalog_id": line.material_catalog_id.id,
                        "material_spec": line.material_spec,
                        "product_uom_id": line.product_uom_id.id,
                        "qty": line.qty,
                        "unit_price": line.unit_price,
                        "note": line.note,
                    },
                )
                for line in inbound.line_ids
            ]
        return True

    def _check_returnable_quantities(self):
        ReturnLine = self.env["sc.material.supplier.return.line"]
        for record in self:
            for line in record.line_ids:
                if line.qty <= 0:
                    raise ValidationError(_("退货数量必须大于 0。"))
                source = line.source_inbound_line_id
                if not source:
                    continue
                if record.source_inbound_id and source.inbound_id != record.source_inbound_id:
                    raise ValidationError(_("退货明细与来源入库单不一致。"))
                already_returned = sum(
                    ReturnLine.search(
                        [
                            ("source_inbound_line_id", "=", source.id),
                            ("return_id.state", "=", "returned"),
                            ("return_id", "!=", record.id),
                        ]
                    ).mapped("qty")
                )
                if line.qty + already_returned > source.qty:
                    raise ValidationError(
                        _(
                            "材料 %(material)s 的累计退货数量不能超过来源入库数量 %(qty)s。"
                        )
                        % {
                            "material": source.material_catalog_id.display_name
                            or source.product_id.display_name,
                            "qty": source.qty,
                        }
                    )

    def action_submit(self):
        self._sc_require_material_user(_("提交材料退货"))
        self._sc_require_state({"draft"}, _("提交材料退货"))
        for record in self:
            if not record.line_ids:
                raise ValidationError(_("提交退货前必须维护退货明细。"))
        self._check_returnable_quantities()
        snapshots = {record.id: record._sc_material_audit_payload() for record in self}
        self._sc_warn_system_defaults_on_action(_("提交材料退货"))
        self.write({"state": "submitted"})
        for record in self:
            record._sc_audit_material_transition(
                "material_supplier_return_submitted",
                snapshots[record.id],
                record._sc_material_audit_payload(),
                action_name="action_submit",
            )
        return True

    def action_confirm_return(self):
        self._sc_require_material_manager(_("确认材料退货"))
        self._sc_require_state({"submitted"}, _("确认材料退货"))
        self._check_returnable_quantities()
        snapshots = {record.id: record._sc_material_audit_payload() for record in self}
        self._sc_warn_system_defaults_on_action(_("确认材料退货"))
        self.write({"state": "returned"})
        for record in self:
            record._sc_audit_material_transition(
                "material_supplier_return_confirmed",
                snapshots[record.id],
                record._sc_material_audit_payload(),
                action_name="action_confirm_return",
            )
        return True

    def action_cancel(self):
        self._sc_require_material_manager(_("取消材料退货"))
        self._sc_require_state({"draft", "submitted"}, _("取消材料退货"))
        self.write({"state": "cancel"})
        return True

    def action_reset_draft(self):
        self._sc_require_material_manager(_("退回材料退货草稿"))
        self._sc_require_state({"submitted", "cancel"}, _("退回材料退货草稿"))
        self.write({"state": "draft"})
        return True


class ScMaterialSupplierReturnLine(models.Model):
    _name = "sc.material.supplier.return.line"
    _description = "材料退货明细"
    _inherit = "sc.material.system.default.mixin"
    _order = "return_id, sequence, id"

    return_id = fields.Many2one(
        "sc.material.supplier.return",
        string="退货单",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    project_id = fields.Many2one(
        related="return_id.project_id", store=True, readonly=True, string="项目"
    )
    source_inbound_line_id = fields.Many2one(
        "sc.material.inbound.line", string="来源入库明细", index=True
    )
    product_id = fields.Many2one("product.product", string="材料", required=True, index=True)
    material_catalog_id = fields.Many2one("sc.material.catalog", string="材料档案", index=True)
    material_spec = fields.Char("规格型号")
    product_uom_id = fields.Many2one("uom.uom", string="单位")
    qty = fields.Float("退货数量", required=True)
    currency_id = fields.Many2one(related="return_id.currency_id", store=True, readonly=True)
    unit_price = fields.Monetary("退货单价", currency_field="currency_id")
    amount = fields.Monetary(
        "退货金额", currency_field="currency_id", compute="_compute_amount", store=True
    )
    note = fields.Char("备注")

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            self._sc_apply_line_defaults(values)
        return super().create(vals_list)

    @api.depends("qty", "unit_price")
    def _compute_amount(self):
        for record in self:
            record.amount = record.qty * record.unit_price

    @api.constrains("qty")
    def _check_qty(self):
        for record in self:
            if record.qty <= 0:
                raise ValidationError(_("退货数量必须大于 0。"))

    @api.onchange("source_inbound_line_id")
    def _onchange_source_inbound_line_id(self):
        for record in self:
            line = record.source_inbound_line_id
            if not line:
                continue
            record.product_id = line.product_id
            record.material_catalog_id = line.material_catalog_id
            record.material_spec = line.material_spec
            record.product_uom_id = line.product_uom_id
            record.unit_price = line.unit_price
