# -*- coding: utf-8 -*-
from odoo import fields, models


class HrJob(models.Model):
    _inherit = "hr.job"

    sc_job_code = fields.Char(string="岗位编码", index=True, tracking=True)
    sc_responsibility = fields.Text(string="岗位职责")
    sc_qualification = fields.Text(string="任职要求")

    _sql_constraints = [("sc_job_code_company_unique", "unique(sc_job_code, company_id)", "同一公司内岗位编码不能重复。")]
