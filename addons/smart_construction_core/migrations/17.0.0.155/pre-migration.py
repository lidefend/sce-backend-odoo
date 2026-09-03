"""Quarantine ledgers upgraded before explicit snapshot provenance existed."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        "LOCK TABLE payment_ledger, payment_ledger_allocation, payment_request, "
        "project_project, project_funding_actual_event_allocation, "
        "project_funding_baseline, project_funding_baseline_line "
        "IN SHARE ROW EXCLUSIVE MODE"
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
    _quarantine_funding_children_and_recompute(cr)


def _quarantine_funding_children_and_recompute(cr):
    cr.execute(
        """
        UPDATE project_funding_actual_event_allocation allocation
           SET normalization_state = 'legacy_unresolved_relation'
          FROM payment_ledger ledger
         WHERE ledger.id = allocation.actual_event_id
           AND ledger.normalization_state NOT IN ('normalized', 'legacy_observed_identity')
           AND allocation.normalization_state IS DISTINCT FROM 'legacy_unresolved_relation'
        """
    )
    cr.execute(
        """
        WITH totals AS (
            SELECT allocation.baseline_id, SUM(allocation.effective_amount) AS amount
              FROM project_funding_actual_event_allocation allocation
              JOIN payment_ledger ledger ON ledger.id = allocation.actual_event_id
             WHERE allocation.normalization_state IN ('normalized', 'legacy_unresolved_period')
               AND ledger.normalization_state IN ('normalized', 'legacy_observed_identity')
             GROUP BY allocation.baseline_id
        )
        UPDATE project_funding_baseline baseline
           SET allocated_amount = COALESCE(totals.amount, 0),
               remaining_amount = baseline.total_amount - COALESCE(totals.amount, 0)
          FROM (SELECT id FROM project_funding_baseline) target
          LEFT JOIN totals ON totals.baseline_id = target.id
         WHERE baseline.id = target.id
           AND ROW(baseline.allocated_amount, baseline.remaining_amount)
               IS DISTINCT FROM
               ROW(COALESCE(totals.amount, 0), baseline.total_amount - COALESCE(totals.amount, 0))
        """
    )
    cr.execute(
        """
        WITH totals AS (
            SELECT allocation.plan_line_id, SUM(allocation.effective_amount) AS amount
              FROM project_funding_actual_event_allocation allocation
              JOIN payment_ledger ledger ON ledger.id = allocation.actual_event_id
             WHERE allocation.normalization_state IN ('normalized', 'legacy_unresolved_period')
               AND ledger.normalization_state IN ('normalized', 'legacy_observed_identity')
             GROUP BY allocation.plan_line_id
        )
        UPDATE project_funding_baseline_line line
           SET allocated_amount = COALESCE(totals.amount, 0),
               remaining_amount = line.planned_amount - COALESCE(totals.amount, 0)
          FROM (SELECT id FROM project_funding_baseline_line) target
          LEFT JOIN totals ON totals.plan_line_id = target.id
         WHERE line.id = target.id
           AND ROW(line.allocated_amount, line.remaining_amount)
               IS DISTINCT FROM
               ROW(COALESCE(totals.amount, 0), line.planned_amount - COALESCE(totals.amount, 0))
        """
    )
    cr.execute(
        """
        WITH totals AS (
            SELECT allocation.actual_event_id, SUM(allocation.effective_amount) AS amount
              FROM project_funding_actual_event_allocation allocation
              JOIN payment_ledger parent ON parent.id = allocation.actual_event_id
             WHERE allocation.normalization_state IN ('normalized', 'legacy_unresolved_period')
               AND parent.normalization_state IN ('normalized', 'legacy_observed_identity')
             GROUP BY allocation.actual_event_id
        )
        UPDATE payment_ledger ledger
           SET fund_plan_allocated_amount = COALESCE(totals.amount, 0),
               fund_plan_unallocated_amount = ledger.amount - COALESCE(totals.amount, 0)
          FROM (SELECT id FROM payment_ledger) target
          LEFT JOIN totals ON totals.actual_event_id = target.id
         WHERE ledger.id = target.id
           AND ROW(ledger.fund_plan_allocated_amount, ledger.fund_plan_unallocated_amount)
               IS DISTINCT FROM
               ROW(COALESCE(totals.amount, 0), ledger.amount - COALESCE(totals.amount, 0))
        """
    )
