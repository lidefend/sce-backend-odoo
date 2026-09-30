# -*- coding: utf-8 -*-
from odoo import models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    def _get_tier_validation_model_names(self):
        """扩展 OCA 白名单：加入业务审批执行模型。"""
        names = super()._get_tier_validation_model_names()
        if not names:
            names = []
        elif isinstance(names, (set, tuple)):
            names = list(names)
        for model_name in [
            "sc.material.inbound",
            "sc.material.acceptance",
            "sc.material.purchase.request",
            "sc.material.rfq",
            "sc.equipment.plan",
            "sc.equipment.request",
            "sc.labor.plan",
            "sc.subcontract.plan",
            "sc.subcontract.request",
            "sc.safety.plan",
            "sc.safety.disclosure",
            "sc.material.rental.plan",
            "sc.material.rental.order",
            "sc.material.rental.settlement",
            "sc.labor.request",
            "sc.attendance.checkin",
            "sc.labor.usage",
            "sc.labor.settlement",
            "sc.equipment.usage",
            "sc.equipment.settlement",
            "sc.material.settlement",
            "project.project",
            "project.task",
            "project.material.plan",
            "payment.request",
            "sc.expense.claim",
            "sc.settlement.order",
            "purchase.order",
            "construction.contract",
            "sc.general.contract",
            "sc.contract.event",
            "sc.plan",
            "sc.construction.diary",
            "sc.tax.deduction.registration",
        ]:
            if model_name not in names:
                names.append(model_name)
        return names
