# -*- coding: utf-8 -*-
from odoo import _, fields, models, tools
from odoo.exceptions import UserError


class ScLaborSubcontractReport(models.Model):
    _name = "sc.labor.subcontract.report"
    _description = "劳务分包分析"
    _auto = False
    _rec_name = "document_name"
    _order = "fact_date desc, id desc"
    _sc_readonly_navigation_button_methods = {"action_open_source"}

    fact_type = fields.Selection(
        [("labor_usage", "劳务用工"), ("subcontract_register", "分包登记"), ("subcontract_settlement", "分包结算")],
        string="业务层级", readonly=True, index=True,
    )
    document_name = fields.Char(string="来源单据", readonly=True)
    fact_date = fields.Date(string="业务日期", readonly=True, index=True)
    company_id = fields.Many2one("res.company", string="公司", readonly=True, index=True)
    project_id = fields.Many2one("project.project", string="项目", readonly=True, index=True)
    partner_id = fields.Many2one("res.partner", string="劳务/分包单位", readonly=True, index=True)
    labor_team = fields.Char(string="班组", readonly=True, index=True)
    work_scope = fields.Char(string="工作内容/分包范围", readonly=True)
    lifecycle_state = fields.Selection(
        [("draft", "草稿"), ("in_progress", "办理中"), ("confirmed", "已确认"), ("closed", "已关闭"), ("cancelled", "已取消")],
        string="业务状态", readonly=True, index=True,
    )
    currency_id = fields.Many2one("res.currency", string="币种", readonly=True)
    labor_amount = fields.Monetary(string="劳务用工金额", currency_field="currency_id", readonly=True)
    subcontract_registered_amount = fields.Monetary(string="分包登记金额", currency_field="currency_id", readonly=True)
    subcontract_settled_amount = fields.Monetary(string="分包结算金额", currency_field="currency_id", readonly=True)
    worker_qty = fields.Float(string="用工人数", readonly=True)
    work_hours = fields.Float(string="工时", readonly=True)
    record_count = fields.Integer(string="记录数", readonly=True)
    source_model = fields.Char(string="来源模型", readonly=True)
    source_res_id = fields.Integer(string="来源记录", readonly=True)

    def action_open_source(self):
        self.ensure_one()
        allowed = {"sc.labor.usage", "sc.subcontract.register", "sc.subcontract.settlement"}
        if self.source_model not in allowed or not self.source_res_id:
            raise UserError(_("该报表行没有可打开的来源单据。"))
        record = self.env[self.source_model].browse(self.source_res_id).exists()
        if not record:
            raise UserError(_("来源单据已不存在。"))
        record.check_access_rights("read")
        record.check_access_rule("read")
        return {"type": "ir.actions.act_window", "name": self.document_name, "res_model": self.source_model, "res_id": record.id, "view_mode": "form", "target": "current"}

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT (u.id * 10 + 1)::integer AS id,
                       'labor_usage'::varchar AS fact_type,
                       u.name::varchar AS document_name,
                       u.usage_date AS fact_date,
                       p.company_id,
                       u.project_id,
                       u.contractor_id AS partner_id,
                       u.labor_team,
                       u.work_content AS work_scope,
                       CASE u.state WHEN 'submitted' THEN 'in_progress' WHEN 'confirmed' THEN 'confirmed' WHEN 'cancel' THEN 'cancelled' ELSE 'draft' END::varchar AS lifecycle_state,
                       u.currency_id,
                       COALESCE(u.amount_total, 0.0) AS labor_amount,
                       0.0::numeric AS subcontract_registered_amount,
                       0.0::numeric AS subcontract_settled_amount,
                       COALESCE(u.worker_qty, 0.0) AS worker_qty,
                       COALESCE(u.work_hours, 0.0) AS work_hours,
                       1::integer AS record_count,
                       'sc.labor.usage'::varchar AS source_model,
                       u.id AS source_res_id
                  FROM sc_labor_usage u
                  JOIN project_project p ON p.id = u.project_id
                UNION ALL
                SELECT (r.id * 10 + 2)::integer,
                       'subcontract_register'::varchar,
                       r.name::varchar,
                       r.register_date,
                       p.company_id,
                       r.project_id,
                       r.subcontractor_id,
                       NULL::varchar,
                       r.subcontract_scope,
                       CASE r.state WHEN 'active' THEN 'confirmed' WHEN 'closed' THEN 'closed' WHEN 'cancel' THEN 'cancelled' ELSE 'draft' END::varchar,
                       r.currency_id,
                       0.0::numeric,
                       COALESCE(r.registered_amount, 0.0),
                       0.0::numeric,
                       0.0::numeric,
                       0.0::numeric,
                       1::integer,
                       'sc.subcontract.register'::varchar,
                       r.id
                  FROM sc_subcontract_register r
                  JOIN project_project p ON p.id = r.project_id
                UNION ALL
                SELECT (s.id * 10 + 3)::integer,
                       'subcontract_settlement'::varchar,
                       s.name::varchar,
                       s.settlement_date,
                       p.company_id,
                       s.project_id,
                       s.subcontractor_id,
                       NULL::varchar,
                       COALESCE(r.subcontract_scope, s.name)::varchar,
                       CASE s.state WHEN 'submitted' THEN 'in_progress' WHEN 'confirmed' THEN 'confirmed' WHEN 'cancel' THEN 'cancelled' ELSE 'draft' END::varchar,
                       s.currency_id,
                       0.0::numeric,
                       0.0::numeric,
                       COALESCE(s.amount_total, 0.0),
                       0.0::numeric,
                       0.0::numeric,
                       1::integer,
                       'sc.subcontract.settlement'::varchar,
                       s.id
                  FROM sc_subcontract_settlement s
                  JOIN project_project p ON p.id = s.project_id
                  LEFT JOIN sc_subcontract_register r ON r.id = s.register_id
            )
            """
        )
