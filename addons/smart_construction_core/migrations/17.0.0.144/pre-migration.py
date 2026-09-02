"""Replace unconditional legacy constraints before the 0.144 registry pass."""


def migrate(cr, installed_version):
    del installed_version
    cr.execute(
        "ALTER TABLE project_funding_baseline "
        "DROP CONSTRAINT IF EXISTS project_funding_baseline_successor_unique"
    )
    cr.execute(
        """
        SELECT pg_get_constraintdef(constraint_meta.oid)
          FROM pg_constraint AS constraint_meta
          JOIN pg_class AS table_meta ON table_meta.oid = constraint_meta.conrelid
          JOIN pg_namespace AS namespace ON namespace.oid = table_meta.relnamespace
         WHERE namespace.nspname = current_schema()
           AND table_meta.relname = 'project_funding_baseline'
           AND constraint_meta.conname = 'project_funding_baseline_total_amount_positive'
        """
    )
    row = cr.fetchone()
    if row and "normalization_state" not in (row[0] or ""):
        cr.execute(
            "ALTER TABLE project_funding_baseline "
            "DROP CONSTRAINT project_funding_baseline_total_amount_positive"
        )
