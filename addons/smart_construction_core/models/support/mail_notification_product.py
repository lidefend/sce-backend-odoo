# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class MailNotificationProduct(models.Model):
    _inherit = "mail.notification"

    sc_is_current_recipient = fields.Boolean(
        string="当前用户消息",
        compute="_compute_sc_is_current_recipient",
        search="_search_sc_is_current_recipient",
    )
    sc_subject = fields.Char(string="主题", related="mail_message_id.subject", readonly=True)
    sc_body = fields.Html(string="消息内容", related="mail_message_id.body", readonly=True)
    sc_message_date = fields.Datetime(string="发送时间", related="mail_message_id.date", readonly=True)
    sc_record_name = fields.Char(string="关联单据", related="mail_message_id.record_name", readonly=True)
    sc_source_model = fields.Char(string="来源模型", related="mail_message_id.model", readonly=True)
    sc_source_res_id = fields.Many2oneReference(
        string="来源记录",
        model_field="sc_source_model",
        related="mail_message_id.res_id",
        readonly=True,
    )

    @api.depends("res_partner_id")
    @api.depends_context("uid")
    def _compute_sc_is_current_recipient(self):
        partner = self.env.user.partner_id
        for notification in self:
            notification.sc_is_current_recipient = notification.res_partner_id == partner

    def _search_sc_is_current_recipient(self, operator, value):
        expected = bool(value)
        positive = (operator in ("=", "==") and expected) or (operator == "!=" and not expected)
        domain_operator = "=" if positive else "!="
        return [("res_partner_id", domain_operator, self.env.user.partner_id.id)]

    def _sc_check_current_recipient(self):
        if self.filtered(lambda item: item.res_partner_id != self.env.user.partner_id):
            raise AccessError(_("只能操作发送给当前用户的消息。"))

    def action_sc_mark_read(self):
        self._sc_check_current_recipient()
        self.write({"is_read": True})
        return True

    def action_sc_mark_unread(self):
        self._sc_check_current_recipient()
        self.write({"is_read": False, "read_date": False})
        return True

    def action_sc_open_source(self):
        self.ensure_one()
        self._sc_check_current_recipient()
        model_name = self.sc_source_model
        record_id = self.sc_source_res_id
        if not model_name or not record_id or model_name not in self.env:
            raise UserError(_("该消息没有可打开的关联单据。"))
        record = self.env[model_name].browse(record_id).exists()
        if not record:
            raise UserError(_("关联单据已不存在。"))
        record.check_access_rights("read")
        record.check_access_rule("read")
        self.action_sc_mark_read()
        return {
            "type": "ir.actions.act_window",
            "name": self.sc_record_name or self.sc_subject or _("关联单据"),
            "res_model": model_name,
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }
