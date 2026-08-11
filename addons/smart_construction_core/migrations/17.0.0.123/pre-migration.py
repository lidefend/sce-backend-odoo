"""Fail closed before removing customer acceptance fields from payroll documents."""

LEGACY_COLUMNS = [
    "legacy_acceptance_label",
    "legacy_acceptance_sort_id",
    "payroll_document_status_display",
    "payroll_document_project_name",
    "payroll_document_no",
    "payroll_document_date",
    "payroll_document_salary_month",
    "payroll_document_net_salary",
    "payroll_document_gross_salary",
    "payroll_document_payment_status",
    "payroll_document_paid_amount",
    "payroll_document_unpaid_amount",
    "payroll_document_note",
    "payroll_document_attachment_text",
    "payroll_document_source_created_by",
    "payroll_document_source_created_at",
] + ["legacy_visible_%02d" % index for index in range(1, 61)]
TABLE = "sc_hr_payroll_document"


def migrate(cr, version):
    cr.execute(
        """SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND column_name=ANY(%s) ORDER BY column_name""",
        [TABLE, LEGACY_COLUMNS],
    )
    existing = [row[0] for row in cr.fetchall()]
    if not existing:
        return
    predicate = " OR ".join(
        "NULLIF(BTRIM(COALESCE(\"%s\"::text, '')), '') IS NOT NULL" % column.replace('"', '""')
        for column in existing
    )
    cr.execute('SELECT COUNT(*) FROM "%s" WHERE ' % TABLE + predicate)
    row_count = int(cr.fetchone()[0] or 0)
    if row_count:
        raise RuntimeError(
            "HR_PAYROLL_DOCUMENT_P2_HISTORY_NOT_EXTRACTED: table=%s rows=%s" % (TABLE, row_count)
        )
