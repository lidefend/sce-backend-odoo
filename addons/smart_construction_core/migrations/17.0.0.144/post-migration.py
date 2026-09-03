"""Install the exact live-successor uniqueness backstop."""


def _predicate_shape(value):
    normalized = (value or "").lower().replace("::text", "").replace("!=", "<>")
    return "".join(char for char in normalized if char not in " ()")


def _has_exact_index(cr):
    cr.execute(
        """
        SELECT index_meta.indisunique,
               ARRAY(
                   SELECT attribute.attname
                     FROM unnest(index_meta.indkey::smallint[])
                          WITH ORDINALITY AS key(attnum, position)
                     JOIN pg_attribute AS attribute
                       ON attribute.attrelid = table_meta.oid
                      AND attribute.attnum = key.attnum
                    WHERE key.position <= index_meta.indnkeyatts
                    ORDER BY key.position
               ),
               ARRAY(
                   SELECT attribute.attname
                     FROM unnest(index_meta.indkey::smallint[])
                          WITH ORDINALITY AS key(attnum, position)
                     JOIN pg_attribute AS attribute
                       ON attribute.attrelid = table_meta.oid
                      AND attribute.attnum = key.attnum
                    WHERE key.position > index_meta.indnkeyatts
                    ORDER BY key.position
               ),
               pg_get_expr(index_meta.indpred, index_meta.indrelid)
          FROM pg_class AS index_class
          JOIN pg_index AS index_meta ON index_meta.indexrelid = index_class.oid
          JOIN pg_class AS table_meta ON table_meta.oid = index_meta.indrelid
          JOIN pg_namespace AS namespace ON namespace.oid = index_class.relnamespace
         WHERE namespace.nspname = current_schema()
           AND index_class.relname = %s
           AND table_meta.relname = %s
        """,
        [
            "project_funding_baseline_one_live_successor_uidx",
            "project_funding_baseline",
        ],
    )
    row = cr.fetchone()
    return bool(
        row
        and row[0] is True
        and tuple(row[1] or ()) == ("supersedes_id",)
        and not tuple(row[2] or ())
        and _predicate_shape(row[3])
        == _predicate_shape("supersedes_id IS NOT NULL AND state != 'cancelled'")
    )


def migrate(cr, installed_version):
    del installed_version
    if not _has_exact_index(cr):
        cr.execute(
            "DROP INDEX IF EXISTS project_funding_baseline_one_live_successor_uidx"
        )
        cr.execute(
            "CREATE UNIQUE INDEX project_funding_baseline_one_live_successor_uidx "
            "ON project_funding_baseline (supersedes_id) "
            "WHERE supersedes_id IS NOT NULL AND state != 'cancelled'"
        )
    cr.execute(
        """
        WITH allocation_totals AS (
            SELECT ledger_id,
                   COALESCE(SUM(allocated_amount), 0) AS allocated_amount,
                   COUNT(*) FILTER (
                       WHERE allocation_state != 'allocated'
                   ) AS unresolved_count
              FROM payment_ledger_allocation
          GROUP BY ledger_id
        ), desired AS (
            SELECT ledger.id AS ledger_id,
                   totals.allocated_amount,
                   GREATEST(
                       ledger.amount - totals.allocated_amount, 0
                   ) AS unallocated_amount,
                   CASE
                       WHEN totals.unresolved_count = 0
                        AND totals.allocated_amount = ledger.amount
                       THEN 'complete'
                       ELSE 'review_required'
                   END AS allocation_status
              FROM payment_ledger AS ledger
              JOIN allocation_totals AS totals ON totals.ledger_id = ledger.id
        )
        UPDATE payment_ledger AS ledger
           SET contract_allocated_amount = desired.allocated_amount,
               contract_unallocated_amount = desired.unallocated_amount,
               contract_allocation_status = desired.allocation_status
          FROM desired
         WHERE desired.ledger_id = ledger.id
           AND (
                ledger.contract_allocated_amount
                    IS DISTINCT FROM desired.allocated_amount
             OR ledger.contract_unallocated_amount
                    IS DISTINCT FROM desired.unallocated_amount
             OR ledger.contract_allocation_status
                    IS DISTINCT FROM desired.allocation_status
           )
        """
    )
