# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    sc_cost_from_account_move = fields.Boolean(
        string="成本台账来源：凭证",
        default=True,
    )
    sc_cost_from_purchase = fields.Boolean(
        string="成本台账来源：采购",
        default=False,
    )
    sc_cost_from_stock = fields.Boolean(
        string="成本台账来源：入库",
        default=False,
    )

    @api.constrains(
        "sc_cost_from_account_move",
        "sc_cost_from_purchase",
        "sc_cost_from_stock",
    )
    def _check_single_cost_fact_authority(self):
        for company in self:
            if sum(
                bool(value)
                for value in (
                    company.sc_cost_from_account_move,
                    company.sc_cost_from_purchase,
                    company.sc_cost_from_stock,
                )
            ) > 1:
                raise ValidationError(_("每家公司只能启用凭证、采购或入库中的一个成本事实来源。"))

    @api.model
    def _migrate_legacy_cost_source_parameters(self):
        """Promote the former database-global authority into every company."""
        key_to_field = {
            "smart_construction_core.sc_cost_from_account_move": "sc_cost_from_account_move",
            "smart_construction_core.sc_cost_from_purchase": "sc_cost_from_purchase",
            "smart_construction_core.sc_cost_from_stock": "sc_cost_from_stock",
        }
        parameters = self.env["ir.config_parameter"].sudo().search(
            [("key", "in", list(key_to_field))]
        )
        if not parameters:
            return False

        def enabled(raw):
            return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}

        selected = [parameter.key for parameter in parameters if enabled(parameter.value)]
        if len(selected) > 1:
            raise ValidationError(
                _("旧成本来源配置同时启用了多个权威来源，升级已停止；请先完成受控配置修复。")
            )
        values = {field_name: False for field_name in key_to_field.values()}
        if selected:
            values[key_to_field[selected[0]]] = True
        self.sudo().search([]).write(values)
        parameters.unlink()
        return True

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
