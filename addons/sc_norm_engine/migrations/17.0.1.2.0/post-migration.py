from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Remove the legacy client-action workbench after menus move to act_window."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    model_data = env["ir.model.data"].search(
        [
            ("module", "=", "sc_norm_engine"),
            ("name", "=", "action_sc_norm_catalog"),
            ("model", "=", "ir.actions.client"),
        ],
        limit=1,
    )
    if not model_data:
        return
    legacy_action = env["ir.actions.client"].browse(model_data.res_id).exists()
    if legacy_action:
        bound_menu = env["ir.ui.menu"].search(
            [("action", "=", "ir.actions.client,%s" % legacy_action.id)],
            limit=1,
        )
        if bound_menu:
            return
        legacy_action.unlink()
    model_data.unlink()
