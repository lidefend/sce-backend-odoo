# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ScLaborUsageProductAdvisory(models.Model):
    _inherit = "sc.labor.usage"

    processing_advisory = fields.Char("办理建议", compute="_compute_processing_advisory", sc_ui_usage="interaction")

    @api.depends(
        "contractor_id",
        "work_type",
        "construction_part",
        "foreman_name",
        "price_unit",
        "attachment_ids",
    )
    def _compute_processing_advisory(self):
        for usage in self:
            suggestions = []
            if not usage.contractor_id:
                suggestions.append("建议补充劳务单位")
            if not usage.work_type:
                suggestions.append("建议补充工种")
            if not usage.construction_part:
                suggestions.append("建议补充施工部位")
            if not usage.foreman_name:
                suggestions.append("建议补充带班人")
            if not usage.price_unit:
                suggestions.append("建议补充用工单价")
            if not usage.attachment_ids:
                suggestions.append("建议上传用工依据")
            usage.processing_advisory = (
                "；".join(suggestions) if suggestions else ""
            )
