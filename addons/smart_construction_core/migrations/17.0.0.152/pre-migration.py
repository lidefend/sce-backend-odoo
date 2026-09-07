"""Quarantine partial historical allocation identity without inventing dimensions."""


def migrate(cr, installed_version):
    del installed_version
    # This table may not exist in older tenant backups.  The ORM creates it
    # during the registry update; there is no historical allocation data to
    # quarantine in that case.
    cr.execute("SELECT to_regclass('public.payment_ledger_allocation')")
    if cr.fetchone()[0] is None:
        return
    cr.execute(
        "LOCK TABLE payment_ledger_allocation, payment_ledger, payment_request "
        "IN SHARE ROW EXCLUSIVE MODE"
    )
    cr.execute(
        """
        UPDATE payment_ledger_allocation allocation
           SET allocation_state = 'unresolved_global',
               reason_code = 'historical_backfill_unresolved'
         WHERE (
                allocation.payment_request_id IS NULL
             OR allocation.project_id IS NULL
             OR allocation.company_id IS NULL
             OR allocation.currency_id IS NULL
         )
           AND ROW(allocation.allocation_state, allocation.reason_code)
               IS DISTINCT FROM
               ROW('unresolved_global', 'historical_backfill_unresolved')
        """
    )
