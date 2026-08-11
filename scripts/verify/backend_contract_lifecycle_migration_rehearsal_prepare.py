# Executed only in an isolated rehearsal database through odoo_shell_exec.sh.
from __future__ import annotations

import os


if os.getenv("ISOLATED_REHEARSAL_DATABASE") != "1":
    raise RuntimeError("migration rehearsal requires ISOLATED_REHEARSAL_DATABASE=1")
if env.cr.dbname != "sc_contract_lifecycle":
    raise RuntimeError("migration rehearsal is restricted to sc_contract_lifecycle")

Contract = env["ui.business.config.contract"].sudo().with_context(active_test=False)
contract = Contract.search([("status", "=", "published")], order="id", limit=1)
if not contract:
    raise RuntimeError("migration rehearsal requires one published product contract")

env.cr.execute(
    """
    UPDATE ui_business_config_contract
       SET payload_sha256 = 'legacy-unsealed',
           definition_sha256 = 'legacy-unsealed',
           source_authority_json = '{}'::jsonb
     WHERE id = %s
    """,
    [contract.id],
)
env.cr.execute(
    """
    UPDATE ui_business_config_contract_version
       SET payload_sha256 = 'legacy-unsealed',
           definition_sha256 = 'legacy-unsealed',
           source_authority_json = '{}'::jsonb
     WHERE contract_id = %s
    """,
    [contract.id],
)
env.cr.execute(
    "UPDATE ir_module_module SET latest_version = '17.0.1.1.8' WHERE name = 'smart_core'"
)
env.cr.commit()
print("prepared legacy contract lifecycle row contract_id=%s database=%s" % (contract.id, env.cr.dbname))
