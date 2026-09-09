"""Recompute stored parents after historical payment identity quarantine."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        "LOCK TABLE payment_ledger, payment_ledger_allocation, "
        "project_funding_actual_event_allocation, project_funding_baseline, "
        "project_funding_baseline_line IN SHARE ROW EXCLUSIVE MODE"
    )
    cr.execute(
        """
        WITH allocation_totals AS (
            SELECT ledger_id,
                   COALESCE(SUM(allocated_amount), 0) AS allocated_amount,
                   COUNT(*) FILTER (WHERE allocation_state != 'allocated') AS unresolved_count,
                   COUNT(*) AS allocation_count
              FROM payment_ledger_allocation
          GROUP BY ledger_id
        ), desired AS (
            SELECT ledger.id AS ledger_id,
                   COALESCE(totals.allocated_amount, 0) AS allocated_amount,
                   GREATEST(ledger.amount - COALESCE(totals.allocated_amount, 0), 0)
                       AS unallocated_amount,
                   CASE
                       WHEN COALESCE(totals.allocation_count, 0) > 0
                        AND COALESCE(totals.unresolved_count, 0) = 0
                        AND COALESCE(totals.allocated_amount, 0) = ledger.amount
                       THEN 'complete'
                       ELSE 'review_required'
                   END AS allocation_status
              FROM payment_ledger AS ledger
              LEFT JOIN allocation_totals AS totals ON totals.ledger_id = ledger.id
        )
        UPDATE payment_ledger AS ledger
           SET contract_allocated_amount = desired.allocated_amount,
               contract_unallocated_amount = desired.unallocated_amount,
               contract_allocation_status = desired.allocation_status
          FROM desired
         WHERE desired.ledger_id = ledger.id
           AND ROW(
                ledger.contract_allocated_amount,
                ledger.contract_unallocated_amount,
                ledger.contract_allocation_status
           ) IS DISTINCT FROM ROW(
                desired.allocated_amount,
                desired.unallocated_amount,
                desired.allocation_status
           )
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
              JOIN payment_ledger ledger ON ledger.id = allocation.actual_event_id
             WHERE allocation.normalization_state IN ('normalized', 'legacy_unresolved_period')
               AND ledger.normalization_state IN ('normalized', 'legacy_observed_identity')
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
