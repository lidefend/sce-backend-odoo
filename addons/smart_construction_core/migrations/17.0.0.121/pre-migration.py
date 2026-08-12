"""Fail closed before removing customer acceptance fields from labor usage."""

LEGACY_COLUMNS = ["legacy_acceptance_label", "legacy_acceptance_sort_id"] + [
    "legacy_visible_%02d" % index for index in range(1, 61)
] + [
    "legacy_settlement_status", "legacy_settlement_state", "legacy_settlement_amount",
    "document_date_text",
] + [
    "labor_usage_%s" % suffix for suffix in (
        "status_display", "document_no", "project_name", "document_date", "title",
        "labor_team_name", "work_type", "construction_part", "quantity", "price_unit",
        "amount", "work_content", "settlement_status", "note", "attachment_text",
        "source_created_by", "source_created_at",
    )
]
TABLE = "sc_labor_usage"


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
        % column.replace('"', '""') for column in existing
    )
    cr.execute('SELECT COUNT(*) FROM "%s" WHERE ' % TABLE + predicate)
    row_count = int(cr.fetchone()[0] or 0)
    if row_count:
        raise RuntimeError("LABOR_USAGE_P2_HISTORY_NOT_EXTRACTED: table=%s rows=%s" % (TABLE, row_count))
