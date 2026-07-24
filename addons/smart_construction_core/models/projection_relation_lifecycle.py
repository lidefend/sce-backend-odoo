"""Fail-closed lifecycle helpers for product-owned projection relations.

The project AR/AP summary is a product-owned, physical read model.  It is not
an optional external view.  These helpers deliberately preserve an existing
table in place and only create the table for a genuinely absent relation.
"""

import hashlib
import json


AR_AP_SCHEMA = "public"
AR_AP_RELATION = "sc_ar_ap_project_summary"
AR_AP_QUALIFIED = '"public"."sc_ar_ap_project_summary"'
AR_AP_EVIDENCE_STRUCTURE_FINGERPRINT = (
    "14ddeb6a0830f368a0613af8159aff60ad7d5a82d60addeddaf1aa6c5044b126"
)
AR_AP_LOCK_KEY = 82507314436192311

AR_AP_COLUMNS = (
    ("id", "bigint", False),
    ("display_name", "text", True),
    ("project_id", "integer", True),
    ("project_name", "text", True),
    ("partner_id", "integer", True),
    ("partner_key", "text", True),
    ("partner_name", "character varying", True),
    ("income_contract_amount", "numeric", True),
    ("output_invoice_amount", "numeric", True),
    ("receipt_amount", "numeric", True),
    ("receivable_unpaid_amount", "numeric", True),
    ("invoiced_unreceived_amount", "numeric", True),
    ("received_uninvoiced_amount", "numeric", True),
    ("payable_contract_amount", "numeric", True),
    ("payable_pricing_method_text", "text", True),
    ("input_invoice_amount", "numeric", True),
    ("paid_amount", "numeric", True),
    ("payable_unpaid_amount", "numeric", True),
    ("paid_uninvoiced_amount", "numeric", True),
    ("output_tax_amount", "numeric", True),
    ("input_tax_amount", "numeric", True),
    ("deduction_tax_amount", "double precision", True),
    ("tax_deduction_rate", "double precision", True),
    ("output_surcharge_amount", "double precision", True),
    ("input_surcharge_amount", "double precision", True),
    ("deduction_surcharge_amount", "double precision", True),
    ("self_funding_income_amount", "double precision", True),
    ("self_funding_refund_amount", "double precision", True),
    ("self_funding_unreturned_amount", "double precision", True),
    ("actual_available_balance", "double precision", True),
)

_CREATE_TABLE_SQL = """
CREATE TABLE "public"."sc_ar_ap_project_summary" (
    id bigint NOT NULL,
    display_name text,
    project_id integer,
    project_name text,
    partner_id integer,
    partner_key text,
    partner_name character varying,
    income_contract_amount numeric,
    output_invoice_amount numeric,
    receipt_amount numeric,
    receivable_unpaid_amount numeric,
    invoiced_unreceived_amount numeric,
    received_uninvoiced_amount numeric,
    payable_contract_amount numeric,
    payable_pricing_method_text text,
    input_invoice_amount numeric,
    paid_amount numeric,
    payable_unpaid_amount numeric,
    paid_uninvoiced_amount numeric,
    output_tax_amount numeric,
    input_tax_amount numeric,
    deduction_tax_amount double precision,
    tax_deduction_rate double precision,
    output_surcharge_amount double precision,
    input_surcharge_amount double precision,
    deduction_surcharge_amount double precision,
    self_funding_income_amount double precision,
    self_funding_refund_amount double precision,
    self_funding_unreturned_amount double precision,
    actual_available_balance double precision,
    CONSTRAINT sc_ar_ap_project_summary_pkey PRIMARY KEY (id)
)
"""

_INDEX_SQL = (
    'CREATE INDEX sc_ar_ap_project_summary_project_id_idx '
    'ON "public"."sc_ar_ap_project_summary" (project_id)',
    'CREATE INDEX sc_ar_ap_project_summary_project_name_idx '
    'ON "public"."sc_ar_ap_project_summary" (project_name)',
    'CREATE INDEX sc_ar_ap_project_summary_partner_key_idx '
    'ON "public"."sc_ar_ap_project_summary" (partner_key)',
    'CREATE INDEX sc_ar_ap_project_summary_partner_name_idx '
    'ON "public"."sc_ar_ap_project_summary" (partner_name)',
)


def _relation_identity(cr):
    cr.execute(
        """
        SELECT relation.relkind, namespace.nspname, relation.relname
          FROM pg_class relation
          JOIN pg_namespace namespace ON namespace.oid = relation.relnamespace
         WHERE relation.oid = to_regclass(%s)
        """,
        ("%s.%s" % (AR_AP_SCHEMA, AR_AP_RELATION),),
    )
    return cr.fetchone()


def _column_signature(cr):
    cr.execute(
        """
        SELECT attribute.attname,
               pg_catalog.format_type(attribute.atttypid, attribute.atttypmod),
               NOT attribute.attnotnull
          FROM pg_attribute attribute
         WHERE attribute.attrelid = to_regclass(%s)
           AND attribute.attnum > 0
           AND NOT attribute.attisdropped
         ORDER BY attribute.attnum
        """,
        ("%s.%s" % (AR_AP_SCHEMA, AR_AP_RELATION),),
    )
    return tuple((name, pg_type, nullable) for name, pg_type, nullable in cr.fetchall())


def _runtime_fingerprint(signature):
    payload = json.dumps(signature, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _raise_relation_error(stage, relkind, signature=()):
    raise RuntimeError(
        "AR_AP_PROJECTION_RELATION_INVALID:"
        "schema=%s:relation=%s:relkind=%s:fingerprint=%s:stage=%s"
        % (
            AR_AP_SCHEMA,
            AR_AP_RELATION,
            relkind or "absent",
            _runtime_fingerprint(signature),
            stage,
        )
    )


def _assert_supported_table(cr, stage):
    signature = _column_signature(cr)
    if signature != AR_AP_COLUMNS:
        _raise_relation_error(stage, "r", signature)
    cr.execute(
        """
        SELECT count(*)
          FROM pg_constraint
         WHERE conrelid = to_regclass(%s)
           AND contype = 'p'
           AND pg_get_constraintdef(oid) = 'PRIMARY KEY (id)'
        """,
        ("%s.%s" % (AR_AP_SCHEMA, AR_AP_RELATION),),
    )
    if cr.fetchone()[0] != 1:
        _raise_relation_error("%s_primary_key" % stage, "r", signature)
    return signature


def ensure_ar_ap_project_summary_provider(cr):
    """Preserve the legacy table or create the core-owned physical provider."""
    cr.execute("SELECT pg_advisory_xact_lock(%s)", (AR_AP_LOCK_KEY,))
    identity = _relation_identity(cr)
    if identity:
        relkind, schema, relation = identity
        if schema != AR_AP_SCHEMA or relation != AR_AP_RELATION:
            _raise_relation_error("identity", relkind)
        if relkind == "r":
            _assert_supported_table(cr, "existing_table")
            return "preserved"
        # No view is converted here, including the obsolete typed-empty
        # placeholder.  No released environment is known to own that object,
        # and replacing it would itself be an unversioned ownership transfer.
        _raise_relation_error("unsupported_relation_kind", relkind)

    cr.execute(_CREATE_TABLE_SQL)
    for statement in _INDEX_SQL:
        cr.execute(statement)
    _assert_supported_table(cr, "created_table")
    return "created"


def refresh_ar_ap_project_summary(cr, projection_select_sql, minimum_row_count=0):
    """Atomically refresh the physical provider without replacing its identity.

    The caller supplies a versioned, reviewed SELECT.  PostgreSQL MVCC keeps
    readers on the previous committed contents until the transaction commits.
    Any validation or write error rolls the entire refresh back.
    """
    if not isinstance(projection_select_sql, str):
        raise TypeError("projection_select_sql must be a string")
    normalized = projection_select_sql.lstrip().lower()
    if not (normalized.startswith("select ") or normalized.startswith("with ")):
        raise ValueError("projection_select_sql must be a read-only SELECT/CTE")

    cr.execute("SELECT pg_advisory_xact_lock(%s)", (AR_AP_LOCK_KEY,))
    identity = _relation_identity(cr)
    if not identity or identity[0] != "r":
        _raise_relation_error("refresh_identity", identity[0] if identity else None)
    _assert_supported_table(cr, "refresh_existing_table")

    cr.execute(
        'CREATE TEMP TABLE "sc_ar_ap_project_summary_stage" '
        "ON COMMIT DROP AS %s" % projection_select_sql
    )
    cr.execute(
        """
        SELECT count(*),
               count(*) FILTER (WHERE id IS NULL),
               count(*) - count(DISTINCT id),
               count(*) - count(DISTINCT (project_id, partner_key))
          FROM "sc_ar_ap_project_summary_stage"
        """
    )
    row_count, null_ids, duplicate_ids, duplicate_business_keys = cr.fetchone()
    if (
        row_count < minimum_row_count
        or null_ids
        or duplicate_ids
        or duplicate_business_keys
    ):
        raise RuntimeError(
            "AR_AP_PROJECTION_REFRESH_VALIDATION_FAILED:"
            "schema=%s:relation=%s:relkind=r:"
            "fingerprint=%s:stage=staging:"
            "rows=%s:null_ids=%s:duplicate_ids=%s:duplicate_business_keys=%s"
            % (
                AR_AP_SCHEMA,
                AR_AP_RELATION,
                AR_AP_EVIDENCE_STRUCTURE_FINGERPRINT,
                row_count,
                null_ids,
                duplicate_ids,
                duplicate_business_keys,
            )
        )
    cr.execute(
        """
        SELECT count(*)
          FROM "sc_ar_ap_project_summary_stage" stage
          LEFT JOIN project_project project ON project.id = stage.project_id
         WHERE stage.project_id IS NOT NULL
           AND project.id IS NULL
        """
    )
    if cr.fetchone()[0]:
        raise RuntimeError(
            "AR_AP_PROJECTION_REFRESH_VALIDATION_FAILED:"
            "schema=%s:relation=%s:relkind=r:"
            "fingerprint=%s:stage=project_isolation"
            % (
                AR_AP_SCHEMA,
                AR_AP_RELATION,
                AR_AP_EVIDENCE_STRUCTURE_FINGERPRINT,
            )
        )

    column_names = [item[0] for item in AR_AP_COLUMNS]
    columns = ", ".join('"%s"' % name for name in column_names)
    assignments = ", ".join(
        '"%s" = EXCLUDED."%s"' % (name, name)
        for name in column_names
        if name != "id"
    )
    cr.execute(
        'INSERT INTO "public"."sc_ar_ap_project_summary" (%s) '
        'SELECT %s FROM "sc_ar_ap_project_summary_stage" '
        "ON CONFLICT (id) DO UPDATE SET %s" % (columns, columns, assignments)
    )
    cr.execute(
        'DELETE FROM "public"."sc_ar_ap_project_summary" current '
        "WHERE NOT EXISTS ("
        'SELECT 1 FROM "sc_ar_ap_project_summary_stage" stage '
        "WHERE stage.id = current.id"
        ")"
    )
    return row_count
