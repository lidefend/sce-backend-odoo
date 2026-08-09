# -*- coding: utf-8 -*-
import logging

from odoo import api, models


_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _sc_ensure_cny_currency(self):
        """Keep the product RMB-only for business users on install and upgrade."""
        currency = self.env.ref("base.CNY", raise_if_not_found=False)
        if not currency:
            return False
        currency.sudo().active = True
        for company in self.sudo().search([]):
            if company.currency_id == currency:
                continue
            # Odoo forbids changing a company's currency after journal items
            # exist.  Product upgrades must preserve those accounting facts
            # instead of making the whole module migration fail.
            has_journal_items = bool(
                self.env["account.move.line"].sudo().search_count(
                    [("company_id", "=", company.id)], limit=1
                )
            )
            if has_journal_items:
                _logger.warning(
                    "Keep company %s currency %s: journal items already exist; "
                    "automatic CNY migration is unsafe.",
                    company.display_name,
                    company.currency_id.display_name,
                )
                continue
            _logger.info("Set company %s currency to CNY.", company.display_name)
            company.currency_id = currency
        return True
