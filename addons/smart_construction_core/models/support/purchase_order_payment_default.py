# -*- coding: utf-8 -*-
from odoo import api, models

from ...services.default_payment_terms import resolve_default_payment_term


class PurchaseOrderPaymentDefault(models.Model):
    _inherit = "purchase.order"

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if "payment_term_id" in fields_list and not values.get("payment_term_id"):
            term = resolve_default_payment_term(self.env)
            if term:
                values["payment_term_id"] = term.id
        return values
