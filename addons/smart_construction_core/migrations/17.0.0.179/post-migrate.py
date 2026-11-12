from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    del version
    env = api.Environment(cr, SUPERUSER_ID, {})
    entry_model = env["sc.product.scenario.entry"].sudo()
    from odoo.addons.smart_construction_core.services.scenario_surface_projection import (
        legacy_native_center_seed,
    )

    for entry in entry_model.search([("center_key", "=", False)]):
        entry.write(legacy_native_center_seed(env, entry.menu_id))
