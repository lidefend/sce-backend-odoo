from odoo import SUPERUSER_ID, api

from odoo.addons.smart_core.utils.backend_contract_boundaries import (
    ensure_lowcode_contract_source_status,
)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    industry_contract_ids = env["ir.model.data"].search([
        ("module", "=", "smart_construction_core"),
        ("model", "=", "ui.business.config.contract"),
    ]).mapped("res_id")
    contracts = env["ui.business.config.contract"].search(
        [
            ("id", "in", industry_contract_ids),
            ("active", "=", True),
            ("status", "=", "published"),
        ]
    )
    for contract in contracts:
        payload = contract.contract_json if isinstance(contract.contract_json, dict) else {}
        normalized_payload = ensure_lowcode_contract_source_status(payload)
        if normalized_payload != payload:
            contract.with_context(tracking_disable=True).write(
                {"contract_json": normalized_payload}
            )
