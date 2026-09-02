"""Promote the legacy global cost-source choice into company-owned policy."""

from odoo import SUPERUSER_ID, api


def migrate(cr, installed_version):
    del installed_version
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.company"]._migrate_legacy_cost_source_parameters()
