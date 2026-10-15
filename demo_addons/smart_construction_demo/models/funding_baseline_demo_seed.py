# -*- coding: utf-8 -*-
"""Demo-side funding baseline seeding hooks.

Scenario XML can call these through <function> tags so a baseline becomes
active mid-file (payment-request funding gates require exactly one active
baseline at payment-request creation time, which happens inside the same
XML document).
"""

from odoo import models


class ProjectFundingBaselineDemoSeed(models.Model):
    _inherit = "project.funding.baseline"

    def sc_demo_activate(self):
        """Activate draft baselines through the controlled lifecycle.

        Idempotent: non-draft records are skipped, so repeated loads and
        upgrades never re-trigger the activation chain.
        """
        from ..hooks import assert_demo_seed_principal, guard_demo_scope
        from ..tools.scenario_loader import _demo_action_record

        assert_demo_seed_principal(self.env)
        guard_demo_scope(self.env)
        for record in self:
            if record.state == "draft":
                _demo_action_record(self.env, record, "action_activate").action_activate()
