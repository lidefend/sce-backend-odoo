"""Keep native company-rule evaluation inside the platform licensing bound."""
from odoo import models
from odoo.exceptions import AccessError


class IrRule(models.Model):
    _inherit = 'ir.rule'

    def _compute_domain_context_values(self):
        yield from super()._compute_domain_context_values()
        # Native domains may cache the result of user._sc_data_company_ids().
        # A license expiry need not write any row or trigger cache invalidation.
        # Resolve the current upper bound as part of the native cache identity.
        # Native sudo bypasses record rules. Resolving licensing in its cache
        # key would recurse while fetching the very metadata licensing needs.
        yield () if self.env.su else tuple(self.env.user._sc_authorized_company_ids())

    def _eval_context(self):
        context = super()._eval_context()
        if self.env.su:
            return context
        allowed = set(self.env.user._sc_authorized_company_ids())
        if context['company_id'] not in allowed:
            raise AccessError('PLATFORM_COMPANY_NOT_AUTHORIZED')
        context['company_ids'] = sorted(set(context['company_ids']) & allowed)
        return context
