"""Revalidate evidence-preserving payment-ledger identity classification."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        "LOCK TABLE payment_ledger, payment_ledger_allocation, payment_request, "
        "project_project IN SHARE ROW EXCLUSIVE MODE"
    )
    cr.execute("ALTER TABLE payment_ledger ADD COLUMN IF NOT EXISTS company_id integer")
    cr.execute(
        "ALTER TABLE payment_ledger ADD COLUMN IF NOT EXISTS normalization_state varchar"
    )
    cr.execute(
        "ALTER TABLE payment_ledger_allocation "
        "ADD COLUMN IF NOT EXISTS normalization_state varchar"
    )
    cr.execute(
        """
        UPDATE payment_ledger
           SET normalization_state = 'legacy_unresolved_identity'
         WHERE normalization_state IS NULL
        """
    )
    cr.execute(
        """
        UPDATE payment_ledger_allocation
           SET normalization_state = 'legacy_unresolved_identity'
         WHERE normalization_state IS NULL
        """
    )
    cr.execute(
        """
        UPDATE payment_ledger_allocation allocation
           SET allocation_state = 'unresolved_global',
               reason_code = 'historical_backfill_unresolved'
         WHERE allocation.normalization_state = 'legacy_unresolved_identity'
           AND ROW(allocation.allocation_state, allocation.reason_code)
               IS DISTINCT FROM
               ROW('unresolved_global', 'historical_backfill_unresolved')
        """
    )
    cr.execute(
        """
        SELECT COUNT(*)
          FROM payment_ledger
         WHERE normalization_state IN ('normalized', 'legacy_observed_identity')
           AND (
                project_id IS NULL
             OR company_id IS NULL
             OR partner_id IS NULL
             OR currency_id IS NULL
             OR operation_strategy IS NULL
           )
        """
    )
    invalid_ledger_count = cr.fetchone()[0]
    if invalid_ledger_count:
        raise RuntimeError(
            "canonical payment ledger identity is incomplete: %s rows"
            % invalid_ledger_count
        )
    cr.execute(
        """
        SELECT COUNT(*)
          FROM payment_ledger ledger
          JOIN payment_request request ON request.id = ledger.payment_request_id
          JOIN project_project project ON project.id = request.project_id
         WHERE ledger.normalization_state = 'normalized'
           AND (
                ledger.project_id IS DISTINCT FROM request.project_id
             OR ledger.company_id IS DISTINCT FROM project.company_id
             OR ledger.partner_id IS DISTINCT FROM request.partner_id
             OR ledger.currency_id IS DISTINCT FROM request.currency_id
             OR ledger.operation_strategy IS DISTINCT FROM project.operation_strategy
           )
        """
    )
    normalized_conflict_count = cr.fetchone()[0]
    if normalized_conflict_count:
        raise RuntimeError(
            "normalized payment ledger conflicts with current authority: %s rows"
            % normalized_conflict_count
        )
    cr.execute(
        """
        SELECT COUNT(*)
          FROM payment_ledger_allocation allocation
          JOIN payment_ledger ledger ON ledger.id = allocation.ledger_id
         WHERE allocation.normalization_state IN ('normalized', 'legacy_observed_identity')
           AND (
                allocation.project_id IS NULL
             OR allocation.company_id IS NULL
             OR allocation.currency_id IS NULL
             OR ledger.normalization_state NOT IN ('normalized', 'legacy_observed_identity')
             OR allocation.project_id IS DISTINCT FROM ledger.project_id
             OR allocation.company_id IS DISTINCT FROM ledger.company_id
             OR allocation.currency_id IS DISTINCT FROM ledger.currency_id
           )
        """
    )
    invalid_allocation_count = cr.fetchone()[0]
    if invalid_allocation_count:
        raise RuntimeError(
            "canonical payment ledger allocation identity is invalid: %s rows"
            % invalid_allocation_count
        )
    cr.execute(
        """
        CREATE INDEX IF NOT EXISTS payment_ledger_canonical_posted_identity_idx
            ON payment_ledger
               (project_id, company_id, currency_id, partner_id, state)
         WHERE state = 'posted'
           AND normalization_state IN ('normalized', 'legacy_observed_identity')
        """
    )
