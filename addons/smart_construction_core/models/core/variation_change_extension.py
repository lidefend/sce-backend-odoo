# -*- coding: utf-8 -*-
from odoo import fields, models


class ScSettlementAdjustmentChangeLineage(models.Model):
    _inherit = "sc.settlement.adjustment"

    contract_change_id = fields.Many2one(
        "sc.contract.change", string="来源合同变更", index=True, readonly=True
    )
    source_site_variation_id = fields.Many2one(
        related="contract_change_id.source_site_variation_id",
        store=True,
        readonly=True,
        string="来源工程签证",
    )
