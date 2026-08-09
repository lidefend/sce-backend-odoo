from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["project.cost.plan"].search([("line_ids", "!=", False)])._rebuild_cost_tree()
