"""Carry the retired 项目信息编辑 composition into the unified 项目台账.

The unified ledger surface must render the composition declared by its
authoritative native form (including the fields carried over from the retired
duplicate entry).  A stale user-level legacy ``ui.form.field.policy`` overlay
left over from the split-surface era suppressed fields declared by that form,
so the runtime contract dropped them even though the ledger form declares
them.  Retire only those stale rows; ACL, record rules and field permissions
are untouched.
"""

from odoo import api

from odoo.addons.smart_construction_core.services.project_ledger_field_overlay_repair import (
    retire_stale_ledger_field_overlay,
)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, 1, {})
    report = retire_stale_ledger_field_overlay(env, dry_run=False)
    if report.get("status") == "applied":
        cr.commit()
