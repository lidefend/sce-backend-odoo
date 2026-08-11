"""Archive P2 customer-confirmation form surfaces left by older P1 versions."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    metadata = env["ir.model.data"].sudo().search(
        [
            ("module", "=", "smart_construction_core"),
            ("model", "=", "ir.ui.view"),
            ("name", "ilike", "user_confirmed_form"),
        ]
    )
    views = env["ir.ui.view"].sudo().with_context(active_test=False).browse(metadata.mapped("res_id")).exists()
    if views:
        views.write({"active": False})
