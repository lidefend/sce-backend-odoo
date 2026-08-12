"""Fail closed before removing customer acceptance fields from material rental orders."""

LEGACY_COLUMNS = [
    "legacy_acceptance_label",
    "legacy_acceptance_sort_id",
    "invoiced_amount_text",
    "paid_amount_text",
    "unpaid_amount_text",
    "uninvoiced_amount_text",
    "contract_sign_date_text",
    "rental_material_name",
    "rental_material_spec",
    "rental_quantity_text",
    "rental_unit_price_text",
    "rental_deposit_amount_text",
    "rental_order_status_display",
    "rental_order_document_no",
    "rental_order_document_date",
    "rental_order_partner_name",
    "rental_order_use_unit_name",
    "rental_order_material_name",
    "rental_order_material_spec",
    "rental_order_quantity",
    "rental_order_unit_price",
    "rental_order_deposit_amount",
    "rental_order_settlement_status",
    "rental_order_settlement_amount",
    "rental_order_compensation_fee",
    "rental_order_repair_fee",
    "rental_order_transport_fee",
    "rental_order_deposit_deduction",
    "rental_order_note",
    "rental_order_attachment_text",
    "rental_order_project_name",
    "rental_order_source_created_by",
    "rental_order_source_created_at",
] + [
    "legacy_visible_%02d" % index for index in range(1, 61)
]
TABLE = "sc_material_rental_order"


def migrate(cr, version):
    cr.execute("""SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND column_name=ANY(%s) ORDER BY column_name""", [TABLE, LEGACY_COLUMNS])
    existing = [row[0] for row in cr.fetchall()]
    if not existing:
        return
    predicate = " OR ".join("NULLIF(BTRIM(COALESCE(\"%s\"::text, '')), '') IS NOT NULL" % column.replace('"', '""') for column in existing)
    cr.execute('SELECT COUNT(*) FROM "%s" WHERE ' % TABLE + predicate)
    row_count = int(cr.fetchone()[0] or 0)
    if row_count:
        raise RuntimeError("MATERIAL_RENTAL_ORDER_P2_HISTORY_NOT_EXTRACTED: table=%s rows=%s" % (TABLE, row_count))
