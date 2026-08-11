"""Fail closed before removing pass-through customer-history fields."""

LEGACY_COLUMNS = ["legacy_acceptance_label", "legacy_acceptance_sort_id"] + [
    "legacy_visible_%02d" % index for index in range(1, 61)
]
TABLES = (
    "sc_fund_account_operation",
    "sc_receipt_income",
    "sc_invoice_registration",
    "construction_contract_expense",
)


def migrate(cr, version):
    for table in TABLES:
        cr.execute(
            """SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                  AND column_name = ANY(%s) ORDER BY column_name""",
            [table, LEGACY_COLUMNS],
        )
        existing = [row[0] for row in cr.fetchall()]
        if not existing:
            continue
        predicate = " OR ".join(
            "NULLIF(BTRIM(COALESCE(\"%s\"::text, '')), '') IS NOT NULL"
            % column.replace('"', '""') for column in existing
        )
        safe_table = table.replace('"', '""')
        cr.execute('SELECT COUNT(*) FROM "%s" WHERE ' % safe_table + predicate)
        row_count = int(cr.fetchone()[0] or 0)
        if row_count:
            raise RuntimeError(
                "PASS_THROUGH_P2_HISTORY_NOT_EXTRACTED: table=%s rows=%s"
                % (table, row_count)
            )
