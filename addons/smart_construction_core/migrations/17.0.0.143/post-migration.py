"""Install exact funding authority indexes after history has been quarantined."""


def _predicate_shape(value):
    normalized = (value or "").lower().replace("::text", "").replace("!=", "<>")
    return "".join(char for char in normalized if char not in " ()")


def _ensure_index(
    cr, name, table, create_sql, *, unique=False, keys=(), include=(), predicate=None
):
    cr.execute(
        """
        SELECT index_meta.indisunique,
               ARRAY(
                   SELECT attribute.attname
                     FROM unnest(index_meta.indkey::smallint[]) WITH ORDINALITY AS key(attnum, position)
                     JOIN pg_attribute AS attribute
                       ON attribute.attrelid = table_meta.oid
                      AND attribute.attnum = key.attnum
                    WHERE key.position <= index_meta.indnkeyatts
                    ORDER BY key.position
               ),
               ARRAY(
                   SELECT attribute.attname
                     FROM unnest(index_meta.indkey::smallint[]) WITH ORDINALITY AS key(attnum, position)
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
        [name, table],
    )
    row = cr.fetchone()
    expected_predicate = _predicate_shape(predicate)
    if row and (
        row[0] is unique
        and tuple(row[1] or ()) == tuple(keys)
        and tuple(row[2] or ()) == tuple(include)
        and _predicate_shape(row[3]) == expected_predicate
    ):
        return
    cr.execute(f'DROP INDEX IF EXISTS "{name}"')
    cr.execute(create_sql)


def migrate(cr, installed_version):
    del installed_version
    _ensure_index(
        cr,
        "project_funding_baseline_one_active_uidx",
        "project_funding_baseline",
        "CREATE UNIQUE INDEX project_funding_baseline_one_active_uidx "
        "ON project_funding_baseline (project_id) WHERE state = 'active'",
        unique=True, keys=("project_id",), predicate="state = 'active'",
    )
    _ensure_index(
        cr,
        "project_funding_allocation_line_effect_idx",
        "project_funding_actual_event_allocation",
        "CREATE INDEX project_funding_allocation_line_effect_idx "
        "ON project_funding_actual_event_allocation (plan_line_id, normalization_state) "
        "INCLUDE (effective_amount, actual_event_id)",
        keys=("plan_line_id", "normalization_state"),
        include=("effective_amount", "actual_event_id"),
    )
    _ensure_index(
        cr,
        "project_funding_allocation_baseline_effect_idx",
        "project_funding_actual_event_allocation",
        "CREATE INDEX project_funding_allocation_baseline_effect_idx "
        "ON project_funding_actual_event_allocation (baseline_id, normalization_state) "
        "INCLUDE (effective_amount, actual_event_id)",
        keys=("baseline_id", "normalization_state"),
        include=("effective_amount", "actual_event_id"),
    )
    _ensure_index(
        cr,
        "project_funding_allocation_event_effect_idx",
        "project_funding_actual_event_allocation",
        "CREATE INDEX project_funding_allocation_event_effect_idx "
        "ON project_funding_actual_event_allocation (actual_event_id, normalization_state) "
        "INCLUDE (effective_amount, plan_line_id)",
        keys=("actual_event_id", "normalization_state"),
        include=("effective_amount", "plan_line_id"),
    )
