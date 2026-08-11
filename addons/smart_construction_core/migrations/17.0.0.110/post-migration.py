"""Remove the customer acceptance surface from the standard product baseline."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    legacy_root = env.ref(
        "smart_construction_core.menu_sc_user_acceptance_root",
        raise_if_not_found=False,
    )
    if legacy_root:
        legacy_root.with_context(active_test=False).write({"active": False})
