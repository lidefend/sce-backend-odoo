"""Fail closed before removing RFQ customer-history projection fields."""


LEGACY_COLUMNS = ["legacy_acceptance_label", "legacy_acceptance_sort_id"] + [
    "legacy_visible_%02d" % index for index in range(1, 61)
]


def migrate(cr, version):
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = 'sc_material_rfq'
           AND column_name = ANY(%s)
         ORDER BY column_name
        """,
        [LEGACY_COLUMNS],
    )
    existing = [row[0] for row in cr.fetchall()]
    if not existing:
        return
    nonempty = " OR ".join(
        "NULLIF(BTRIM(COALESCE(\"%s\"::text, '')), '') IS NOT NULL"
        % column.replace('"', '""')
        for column in existing
    )
    cr.execute("SELECT COUNT(*) FROM sc_material_rfq WHERE " + nonempty)
    row_count = int(cr.fetchone()[0] or 0)
    if row_count:
        raise RuntimeError(
            "MATERIAL_RFQ_P2_HISTORY_NOT_EXTRACTED: %s rows still contain customer-history values"
            % row_count
        )
