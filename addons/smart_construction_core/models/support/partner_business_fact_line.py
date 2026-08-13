# -*- coding: utf-8 -*-
from odoo import fields, models, tools
from odoo.exceptions import UserError


class ScPartnerBusinessFactLine(models.Model):
    _name = "sc.partner.business.fact.line"
    _inherit = "sc.optional.product.projection"
    _description = "客户供应商关联业务明细"
    _auto = False
    _rec_name = "display_name"
    _order = "document_date desc, id desc"

    display_name = fields.Char(string="业务摘要", readonly=True)
    partner_id = fields.Many2one("res.partner", string="往来单位", readonly=True, index=True)
    company_id = fields.Many2one("res.company", string="公司", readonly=True, index=True)
    business_role = fields.Selection(
        [("customer", "客户"), ("supplier", "供应商")],
        string="业务方向",
        readonly=True,
        index=True,
    )
    source_label = fields.Char(string="业务类型", readonly=True, index=True)
    project_id = fields.Many2one("project.project", string="项目", readonly=True, index=True)
    project_name = fields.Char(string="项目名称", readonly=True, index=True)
    document_no = fields.Char(string="单据编号", readonly=True, index=True)
    document_date = fields.Date(string="单据日期", readonly=True, index=True)
    amount = fields.Monetary(string="金额", currency_field="currency_id", readonly=True)
    currency_id = fields.Many2one("res.currency", string="币种", readonly=True)
    document_state = fields.Char(string="单据状态", readonly=True, index=True)
    creator_name = fields.Char(string="录入人", readonly=True, index=True)
    created_time = fields.Datetime(string="录入时间", readonly=True, index=True)
    source_model = fields.Char(string="来源模型", readonly=True, index=True)
    source_res_id = fields.Integer(string="来源记录", readonly=True, index=True)
    source_note = fields.Text(string="说明", readonly=True)

    def init(self):
        self.env.cr.execute(
            """
            SELECT to_regclass('construction_contract'),
                   to_regclass('sc_receipt_income'),
                   to_regclass('payment_request'),
                   to_regclass('sc_settlement_order'),
                   to_regclass('sc_invoice_registration')
            """
        )
        if not all(self.env.cr.fetchone()):
            self._create_empty_projection_view()
            return
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE VIEW {self._table} AS (
                SELECT contract.id * 10 + 1 AS id,
                       contract.partner_id AS partner_id,
                       contract.company_id AS company_id,
                       CASE WHEN contract.type = 'out' THEN 'customer' ELSE 'supplier' END AS business_role,
                       CASE WHEN contract.type = 'out' THEN '收入合同' ELSE '支出合同' END AS source_label,
                       contract.project_id AS project_id,
                       NULL::varchar AS project_name,
                       COALESCE(contract.name, contract.subject) AS document_no,
                       contract.date_contract AS document_date,
                       contract.amount_total AS amount,
                       contract.currency_id AS currency_id,
                       contract.state AS document_state,
                       creator.name AS creator_name,
                       contract.create_date AS created_time,
                       'construction.contract'::varchar AS source_model,
                       contract.id AS source_res_id,
                       contract.subject AS source_note,
                       CONCAT(
                           CASE WHEN contract.type = 'out' THEN '收入合同' ELSE '支出合同' END,
                           ' · ', COALESCE(contract.name, contract.subject)
                       ) AS display_name
                  FROM construction_contract contract
             LEFT JOIN res_users create_user ON create_user.id = contract.create_uid
             LEFT JOIN res_partner creator ON creator.id = create_user.partner_id
                 WHERE contract.partner_id IS NOT NULL

                UNION ALL

                SELECT receipt.id * 10 + 2 AS id,
                       receipt.partner_id AS partner_id,
                       receipt.company_id AS company_id,
                       'customer'::varchar AS business_role,
                       '收款登记'::varchar AS source_label,
                       receipt.project_id AS project_id,
                       NULL::varchar AS project_name,
                       COALESCE(receipt.name, receipt.document_no) AS document_no,
                       receipt.date_receipt AS document_date,
                       receipt.amount AS amount,
                       receipt.currency_id AS currency_id,
                       receipt.state AS document_state,
                       COALESCE(receipt.creator_name, creator.name) AS creator_name,
                       COALESCE(receipt.created_time, receipt.create_date) AS created_time,
                       'sc.receipt.income'::varchar AS source_model,
                       receipt.id AS source_res_id,
                       receipt.note AS source_note,
                       CONCAT('收款登记 · ', COALESCE(receipt.name, receipt.document_no)) AS display_name
                  FROM sc_receipt_income receipt
             LEFT JOIN res_users create_user ON create_user.id = receipt.create_uid
             LEFT JOIN res_partner creator ON creator.id = create_user.partner_id
                 WHERE receipt.partner_id IS NOT NULL

                UNION ALL

                SELECT request.id * 10 + 3 AS id,
                       request.partner_id AS partner_id,
                       request.company_id AS company_id,
                       CASE WHEN request.type = 'receive' THEN 'customer' ELSE 'supplier' END AS business_role,
                       CASE WHEN request.type = 'receive' THEN '收款申请' ELSE '付款申请' END AS source_label,
                       request.project_id AS project_id,
                       NULL::varchar AS project_name,
                       request.name AS document_no,
                       request.date_request AS document_date,
                       request.amount AS amount,
                       request.currency_id AS currency_id,
                       request.state AS document_state,
                       COALESCE(request.creator_name, creator.name) AS creator_name,
                       COALESCE(request.created_time, request.create_date) AS created_time,
                       'payment.request'::varchar AS source_model,
                       request.id AS source_res_id,
                       request.note AS source_note,
                       CONCAT(
                           CASE WHEN request.type = 'receive' THEN '收款申请' ELSE '付款申请' END,
                           ' · ', request.name
                       ) AS display_name
                  FROM payment_request request
             LEFT JOIN res_users create_user ON create_user.id = request.create_uid
             LEFT JOIN res_partner creator ON creator.id = create_user.partner_id
                 WHERE request.partner_id IS NOT NULL

                UNION ALL

                SELECT settlement.id * 10 + 4 AS id,
                       settlement.partner_id AS partner_id,
                       settlement.company_id AS company_id,
                       CASE WHEN settlement.settlement_type = 'in' THEN 'customer' ELSE 'supplier' END AS business_role,
                       CASE WHEN settlement.settlement_type = 'in' THEN '收入结算' ELSE '支出结算' END AS source_label,
                       settlement.project_id AS project_id,
                       NULL::varchar AS project_name,
                       COALESCE(settlement.name, settlement.title) AS document_no,
                       COALESCE(settlement.date_settlement, settlement.document_date) AS document_date,
                       settlement.amount_total AS amount,
                       settlement.currency_id AS currency_id,
                       settlement.state AS document_state,
                       creator.name AS creator_name,
                       settlement.create_date AS created_time,
                       'sc.settlement.order'::varchar AS source_model,
                       settlement.id AS source_res_id,
                       COALESCE(settlement.settlement_description, settlement.note) AS source_note,
                       CONCAT(
                           CASE WHEN settlement.settlement_type = 'in' THEN '收入结算' ELSE '支出结算' END,
                           ' · ', COALESCE(settlement.name, settlement.title)
                       ) AS display_name
                  FROM sc_settlement_order settlement
             LEFT JOIN res_users create_user ON create_user.id = settlement.create_uid
             LEFT JOIN res_partner creator ON creator.id = create_user.partner_id
                 WHERE settlement.partner_id IS NOT NULL

                UNION ALL

                SELECT invoice.id * 10 + 5 AS id,
                       invoice.partner_id AS partner_id,
                       invoice.company_id AS company_id,
                       CASE WHEN invoice.direction = 'output' THEN 'customer' ELSE 'supplier' END AS business_role,
                       CASE
                           WHEN invoice.direction = 'output' THEN '销项发票'
                           WHEN invoice.direction = 'input' THEN '进项发票'
                           WHEN invoice.direction = 'prepaid' THEN '预缴税'
                           ELSE '发票登记'
                       END AS source_label,
                       invoice.project_id AS project_id,
                       NULL::varchar AS project_name,
                       COALESCE(invoice.invoice_no, invoice.name) AS document_no,
                       COALESCE(invoice.invoice_date, invoice.document_date) AS document_date,
                       invoice.amount_total AS amount,
                       invoice.currency_id AS currency_id,
                       invoice.state AS document_state,
                       COALESCE(invoice.creator_name, creator.name) AS creator_name,
                       COALESCE(invoice.created_time, invoice.create_date) AS created_time,
                       'sc.invoice.registration'::varchar AS source_model,
                       invoice.id AS source_res_id,
                       invoice.note AS source_note,
                       CONCAT(
                           CASE
                               WHEN invoice.direction = 'output' THEN '销项发票'
                               WHEN invoice.direction = 'input' THEN '进项发票'
                               WHEN invoice.direction = 'prepaid' THEN '预缴税'
                               ELSE '发票登记'
                           END,
                           ' · ', COALESCE(invoice.invoice_no, invoice.name)
                       ) AS display_name
                  FROM sc_invoice_registration invoice
             LEFT JOIN res_users create_user ON create_user.id = invoice.create_uid
             LEFT JOIN res_partner creator ON creator.id = create_user.partner_id
                 WHERE invoice.partner_id IS NOT NULL
            )
            """
        )

    def action_open_source_record(self):
        self.ensure_one()
        if not self.source_model or not self.source_res_id or self.source_model not in self.env:
            raise UserError("没有可打开的来源业务单据。")
        source = self.env[self.source_model].browse(self.source_res_id).exists()
        if not source:
            raise UserError("来源业务单据不存在或已被归档清理。")
        return {
            "type": "ir.actions.act_window",
            "name": self.source_label or source.display_name,
            "res_model": self.source_model,
            "res_id": source.id,
            "view_mode": "form",
            "target": "current",
        }
