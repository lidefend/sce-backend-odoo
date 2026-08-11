# -*- coding: utf-8 -*-
from __future__ import annotations

import json

from odoo import SUPERUSER_ID, api

from odoo.addons.smart_core.core.contract_lifecycle import payload_sha256


def migrate(cr, version):
    del version
    env = api.Environment(cr, SUPERUSER_ID, {"contract_lifecycle_internal": True})
    Contract = env["ui.business.config.contract"].sudo().with_context(contract_lifecycle_internal=True)
    Version = env["ui.business.config.contract.version"].sudo().with_context(contract_lifecycle_internal=True)

    for contract in Contract.with_context(active_test=False).search([]):
        contract._refresh_definition_sha256()
        base_definition = contract._definition_payload()
        for snapshot in Version.search([("contract_id", "=", contract.id)], order="version_no, id"):
            snapshot_payload = snapshot.snapshot_json if isinstance(snapshot.snapshot_json, dict) else {}
            definition = dict(base_definition, contract_json=snapshot_payload)
            cr.execute(
                """
                UPDATE ui_business_config_contract_version
                   SET definition_json = %s::jsonb,
                       payload_sha256 = %s,
                       definition_sha256 = %s,
                       source_authority_json = %s::jsonb,
                       published_at = COALESCE(published_at, create_date, NOW())
                 WHERE id = %s
                """,
                [
                    json.dumps(definition, ensure_ascii=False, sort_keys=True),
                    payload_sha256(snapshot_payload),
                    payload_sha256(definition),
                    json.dumps(contract.source_authority_contract(), ensure_ascii=False, sort_keys=True),
                    snapshot.id,
                ],
            )
        if contract.status == "published" and not Version.search_count([("contract_id", "=", contract.id)]):
            contract._append_published_version()
