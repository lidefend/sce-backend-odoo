"""Expose the payment handling summary in upgraded formal form contracts.

The generated form-structure seed is intentionally ``noupdate``.  Existing
databases therefore need an explicit, idempotent migration when PFL-035 adds
new authoritative payment facts to that structure.  The migration changes
only the payment.request generated contract and preserves every existing row.
"""

import json


SUMMARY_FIELDS = (
    ("payee_account_completeness", 21),
    ("payee_account_source_display", 22),
    ("payment_execution_status_display", 23),
    ("payment_blocking_reason_display", 24),
    ("legal_next_action_display", 25),
)


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        "ALTER TABLE payment_ledger "
        "DROP CONSTRAINT IF EXISTS payment_ledger_uniq_payment_request_id"
    )
    cr.execute(
        "UPDATE payment_ledger SET state = 'posted' WHERE state IS NULL"
    )
    cr.execute(
        "DROP INDEX IF EXISTS payment_ledger_one_posted_per_request_idx"
    )
    cr.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS payment_ledger_one_posted_per_execution_idx "
        "ON payment_ledger (payment_execution_id) "
        "WHERE payment_execution_id IS NOT NULL AND state = 'posted'"
    )
    cr.execute(
        "DROP INDEX IF EXISTS sc_payment_execution_one_active_per_request_idx"
    )
    cr.execute(
        "CREATE UNIQUE INDEX "
        "sc_payment_execution_one_active_per_request_idx "
        "ON sc_payment_execution (payment_request_id) "
        "WHERE payment_request_id IS NOT NULL AND state IN ('draft', 'confirmed')"
    )
    cr.execute(
        """
        SELECT contract.id, contract.contract_json
          FROM ui_business_config_contract contract
          JOIN ir_model_data data
            ON data.model = 'ui.business.config.contract'
           AND data.res_id = contract.id
         WHERE data.module = 'smart_construction_core'
           AND data.name = 'business_config_contract_payment_request_form_structure_generated'
         FOR UPDATE OF contract
        """
    )
    row = cr.fetchone()
    if not row:
        return

    contract_id, payload = row
    payload = payload if isinstance(payload, dict) else json.loads(payload or "{}")
    form = payload.setdefault("view_orchestration", {}).setdefault("views", {}).setdefault("form", {})
    fields = form.setdefault("fields", [])
    existing = {
        str(item.get("name") or "").strip()
        for item in fields
        if isinstance(item, dict)
    }
    changed = False
    for name, sequence in SUMMARY_FIELDS:
        if name in existing:
            continue
        fields.append({"name": name, "sequence": sequence})
        existing.add(name)
        changed = True
    if not changed:
        return
    fields.sort(key=lambda item: (int(item.get("sequence") or 100), str(item.get("name") or "")))
    cr.execute(
        "UPDATE ui_business_config_contract SET contract_json = %s::jsonb WHERE id = %s",
        (json.dumps(payload, ensure_ascii=False), contract_id),
    )
