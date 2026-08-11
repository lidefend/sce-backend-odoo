# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class ScOfficeAsset(models.Model):
    _name = "sc.office.asset"
    _description = "办公资产"
    _inherit = ["mail.thread", "mail.activity.mixin", "sc.delete.guard.mixin"]
    _order = "asset_code, id"

    asset_code = fields.Char(string="资产编号", required=True, index=True, tracking=True)
    name = fields.Char(string="资产名称", required=True, index=True, tracking=True)
    category = fields.Selection([("computer", "电脑设备"), ("office_equipment", "办公设备"), ("furniture", "办公家具"), ("vehicle", "行政车辆"), ("other", "其他")], string="资产类别", required=True, default="office_equipment", index=True)
    specification = fields.Char(string="规格型号")
    serial_no = fields.Char(string="序列号", index=True)
    company_id = fields.Many2one("res.company", string="所属公司", required=True, default=lambda self: self.env.company, index=True)
    department_id = fields.Many2one("hr.department", string="使用部门", index=True)
    custodian_id = fields.Many2one("hr.employee", string="保管人", index=True, tracking=True)
    location = fields.Char(string="存放地点")
    purchase_date = fields.Date(string="购置日期")
    purchase_value = fields.Monetary(string="购置原值", currency_field="currency_id")
    currency_id = fields.Many2one("res.currency", string="币种", required=True, default=lambda self: self.env.company.currency_id.id)
    status = fields.Selection([("available", "闲置可用"), ("in_use", "领用中"), ("maintenance", "维修中"), ("retired", "已报废")], string="资产状态", required=True, default="available", tracking=True, index=True)
    active = fields.Boolean(default=True, index=True)
    note = fields.Text(string="备注")
    attachment_ids = fields.Many2many("ir.attachment", "sc_office_asset_attachment_rel", "asset_id", "attachment_id", string="附件")

    _sql_constraints = [("office_asset_code_company_unique", "unique(asset_code, company_id)", "同一公司内资产编号不能重复。")]

    def action_assign(self):
        for record in self:
            if record.status == "retired":
                raise UserError(_("已报废资产不能领用。"))
            if not record.custodian_id:
                raise UserError(_("领用前必须指定保管人。"))
        self.write({"status": "in_use"})
        return True

    def action_return(self):
        self.write({"status": "available", "custodian_id": False})
        return True

    def action_maintenance(self):
        if self.filtered(lambda record: record.status == "retired"):
            raise UserError(_("已报废资产不能转入维修。"))
        self.write({"status": "maintenance"})
        return True

    def action_retire(self):
        self.write({"status": "retired", "active": False, "custodian_id": False})
        return True

    def unlink(self):
        if self.filtered(lambda record: record.status != "available"):
            raise UserError(_("仅闲置可用的办公资产允许删除。"))
        self._sc_raise_delete_blockers(action_label="删除办公资产")
        return super().unlink()
