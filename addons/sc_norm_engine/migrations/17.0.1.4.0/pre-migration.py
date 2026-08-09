def migrate(cr, version):
    """Allow the catalog-scoped specialty uniqueness constraint to replace legacy scope."""
    cr.execute(
        "ALTER TABLE sc_norm_specialty "
        "DROP CONSTRAINT IF EXISTS sc_norm_specialty_code_uniq"
    )
