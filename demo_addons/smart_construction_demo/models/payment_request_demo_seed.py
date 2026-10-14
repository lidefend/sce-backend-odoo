# -*- coding: utf-8 -*-
"""Demo-side payment-request seeding hooks.

Scenario XML can call these through ``<function>`` tags to carry a seeded draft
request to its approved state mid-file: a downstream record in the same
document (for example the payment execution) may only be created once its
payment request is approved. The driver reuses the demo seat map in
``tools/scenario_loader.py`` and calls the product's own submission and
per-tier approval actions, so no document state is written directly.
"""

from odoo import models


class PaymentRequestDemoSeed(models.Model):
    _inherit = "payment.request"

    def sc_demo_drive_approval(self):
        """Carry seeded draft requests to approved through the real tier chain.

        Idempotent: a request already approved (or beyond) is left untouched, so
        repeated loads and upgrades never replay approvals.
        """
        from odoo.addons.smart_construction_demo.tools.scenario_loader import (
            _demo_drive_approval,
        )

        for record in self:
            _demo_drive_approval(record.env, record)
