"""Quarantine incomplete payment identities created after earlier migrations."""


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", ("public.%s" % table_name,))
    return cr.fetchone()[0] is not None


def migrate(cr, installed_version):
    del installed_version
    if not _table_exists(cr, "payment_ledger"):
        return

    allocation_exists = _table_exists(cr, "payment_ledger_allocation")
    funding_allocation_exists = _table_exists(
        cr, "project_funding_actual_event_allocation"
    )
    # Restored tenants may predate the allocation table.  Earlier migrations
    # intentionally returned before adding ledger identity columns in that
    # case, so establish the current model columns before inspecting them.
    cr.execute(
        """
        ALTER TABLE payment_ledger
          ADD COLUMN IF NOT EXISTS project_id integer,
          ADD COLUMN IF NOT EXISTS company_id integer,
          ADD COLUMN IF NOT EXISTS partner_id integer,
          ADD COLUMN IF NOT EXISTS currency_id integer,
          ADD COLUMN IF NOT EXISTS operation_strategy varchar,
          ADD COLUMN IF NOT EXISTS normalization_state varchar
        """
    )
    # Constraint names are stable but restored databases may carry an older
    # definition.  Remove those definitions before normalization; the current
    # registry recreates both constraints from the model authority.
    cr.execute(
        "ALTER TABLE payment_ledger "
        "DROP CONSTRAINT IF EXISTS payment_ledger_canonical_identity_complete"
    )
    if allocation_exists:
        cr.execute(
            "ALTER TABLE payment_ledger_allocation "
            "DROP CONSTRAINT IF EXISTS "
            "payment_ledger_allocation_canonical_identity_complete"
        )

    locked_tables = ["payment_ledger"]
    if allocation_exists:
        locked_tables.append("payment_ledger_allocation")
    if funding_allocation_exists:
        locked_tables.append("project_funding_actual_event_allocation")
    cr.execute(
        "LOCK TABLE %s IN SHARE ROW EXCLUSIVE MODE" % ", ".join(locked_tables)
    )

    cr.execute(
        """
        UPDATE payment_ledger
           SET normalization_state = 'legacy_unresolved_identity'
         WHERE normalization_state IS DISTINCT FROM 'legacy_unresolved_identity'
           AND (
                project_id IS NULL
             OR company_id IS NULL
             OR partner_id IS NULL
             OR currency_id IS NULL
             OR operation_strategy IS NULL
           )
        """
    )

    if allocation_exists:
        cr.execute(
            """
            UPDATE payment_ledger_allocation allocation
               SET normalization_state = 'legacy_unresolved_identity',
                   allocation_state = 'unresolved_global',
                   reason_code = 'historical_backfill_unresolved'
              FROM payment_ledger ledger
             WHERE ledger.id = allocation.ledger_id
               AND (
                    ledger.normalization_state = 'legacy_unresolved_identity'
                 OR allocation.project_id IS NULL
                 OR allocation.company_id IS NULL
                 OR allocation.currency_id IS NULL
               )
               AND ROW(
                    allocation.normalization_state,
                    allocation.allocation_state,
                    allocation.reason_code
               ) IS DISTINCT FROM ROW(
                    'legacy_unresolved_identity',
                    'unresolved_global',
                    'historical_backfill_unresolved'
               )
            """
        )

    if funding_allocation_exists:
        cr.execute(
            """
            UPDATE project_funding_actual_event_allocation allocation
               SET normalization_state = 'legacy_unresolved_relation'
              FROM payment_ledger ledger
             WHERE ledger.id = allocation.actual_event_id
               AND ledger.normalization_state = 'legacy_unresolved_identity'
               AND allocation.normalization_state IS DISTINCT FROM 'legacy_unresolved_relation'
            """
        )
