# -*- coding: utf-8 -*-
from odoo import fields, models


class ProjectBoqImportWizardNormCatalog(models.TransientModel):
    _inherit = "project.boq.import.wizard"

    norm_catalog_id = fields.Many2one(
        "sc.norm.catalog",
        string="匹配定额库",
        domain="[('state', '=', 'active')]",
        default=lambda self: self.env.ref(
            "sc_norm_engine.catalog_sc_2015", raise_if_not_found=False
        ),
        help="存在综合单价分析时，按所选地区、版本和专业匹配定额子目；清单仍保存独立来源快照。",
    )

    def _prepare_version_values(self, version_code):
        values = super()._prepare_version_values(version_code)
        values["norm_catalog_id"] = self.norm_catalog_id.id or False
        return values
