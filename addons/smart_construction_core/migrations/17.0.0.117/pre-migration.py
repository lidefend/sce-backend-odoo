"""Fail closed before removing customer acceptance fields from subcontract requests."""

LEGACY_COLUMNS = ["legacy_acceptance_label", "legacy_acceptance_sort_id"] + [
    "legacy_visible_%02d" % index for index in range(1, 61)
]
TABLE = "sc_subcontract_request"


def migrate(cr, version):
    cr.execute(
        """SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
              AND column_name = ANY(%s) ORDER BY column_name""",
        [TABLE, LEGACY_COLUMNS],
    )
    existing = [row[0] for row in cr.fetchall()]
    if not existing:
        return
    predicate = " OR ".join(
        "NULLIF(BTRIM(COALESCE(\"%s\"::text, '')), '') IS NOT NULL"
        % column.replace('"', '""')
        for column in existing
    )
    cr.execute('SELECT COUNT(*) FROM "%s" WHERE ' % TABLE + predicate)
    row_count = int(cr.fetchone()[0] or 0)
    if row_count:
        raise RuntimeError(
            "SUBCONTRACT_REQUEST_P2_HISTORY_NOT_EXTRACTED: table=%s rows=%s"
            % (TABLE, row_count)
        )
