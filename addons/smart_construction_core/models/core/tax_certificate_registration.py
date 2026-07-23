# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ScTaxCertificateRegistration(models.Model):
    _name = "sc.tax.certificate.registration"
    _description = "外经证登记"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "validity_start_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(string="单据编号", required=True, default="新建", copy=False, index=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", string="公司", required=True, default=lambda self: self.env.company,
        index=True, tracking=True,
    )
    project_id = fields.Many2one(
        "project.project", string="项目", required=True, check_company=True,
        domain="[('company_id', '=', company_id)]", index=True, tracking=True,
    )
    taxpayer_name = fields.Char(string="纳税人名称", required=True, index=True, tracking=True)
    taxpayer_identifier = fields.Char(string="纳税人识别号", required=True, index=True, tracking=True)
    tax_report_management_no = fields.Char(string="报验管理编号", required=True, index=True, tracking=True)
    cross_region_business_address = fields.Char(string="跨区域经营地址", required=True, tracking=True)
    validity_start_date = fields.Date(string="有效期起", required=True, index=True, tracking=True)
    validity_end_date = fields.Date(string="有效期止", required=True, index=True, tracking=True)
    prepaid_tax_date = fields.Date(string="预缴税日期", index=True, tracking=True)
    tax_payment_certificate_no = fields.Char(string="完税凭证号", index=True, tracking=True)
    state = fields.Selection(
        [("draft", "草稿"), ("registered", "已登记"), ("completed", "已完成"), ("cancelled", "已取消")],
        string="状态", required=True, default="draft", copy=False, index=True, tracking=True,
    )
    handler_id = fields.Many2one(
        "res.users", string="经办人", required=True, default=lambda self: self.env.user,
        domain="[('company_ids', 'in', company_id)]", index=True, tracking=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", "sc_tax_certificate_registration_attachment_rel",
        "registration_id", "attachment_id", string="附件",
    )
    note = fields.Text(string="备注")

    _sql_constraints = [
        ("company_report_management_unique", "unique(company_id, tax_report_management_no)", "同一公司下的报验管理编号必须唯一。"),
    ]

    @api.constrains("validity_start_date", "validity_end_date")
    def _check_validity_dates(self):
        for record in self:
            if record.validity_start_date and record.validity_end_date and record.validity_start_date > record.validity_end_date:
                raise ValidationError(_("有效期起不能晚于有效期止。"))

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("state", "draft") != "draft":
                raise ValidationError(_("外经证登记必须从草稿状态创建。"))
            if vals.get("name", "新建") == "新建":
                vals["name"] = sequence.next_by_code("sc.tax.certificate.registration") or "新建"
        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals:
            raise ValidationError(_("请使用外经证登记的正式状态操作。"))
        return super().write(vals)

    def _require_group(self, xmlid):
        if not self.env.user.has_group(xmlid):
            raise AccessError(_("当前用户无权执行此状态操作。"))

    def action_register(self):
        self._require_group("smart_construction_core.group_sc_cap_finance_user")
        if any(record.state != "draft" for record in self):
            raise ValidationError(_("只有草稿外经证可以登记。"))
        return super(ScTaxCertificateRegistration, self).write({"state": "registered"})

    def action_complete(self):
        self._require_group("smart_construction_core.group_sc_cap_finance_manager")
        if any(record.state != "registered" for record in self):
            raise ValidationError(_("只有已登记外经证可以完成。"))
        return super(ScTaxCertificateRegistration, self).write({"state": "completed"})

    def action_cancel(self):
        self._require_group("smart_construction_core.group_sc_cap_finance_user")
        if any(record.state != "registered" for record in self):
            raise ValidationError(_("只有已登记外经证可以取消。"))
        return super(ScTaxCertificateRegistration, self).write({"state": "cancelled"})
