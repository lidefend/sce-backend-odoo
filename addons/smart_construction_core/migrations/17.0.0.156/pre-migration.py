"""Forward-fix funding children already linked to quarantined payment history."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        "LOCK TABLE payment_ledger, project_funding_actual_event_allocation, "
        "project_funding_baseline, project_funding_baseline_line "
        "IN SHARE ROW EXCLUSIVE MODE"
    )
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
