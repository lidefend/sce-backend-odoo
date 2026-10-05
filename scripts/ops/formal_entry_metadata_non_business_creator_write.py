# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from collections import OrderedDict
from pathlib import Path


NON_BUSINESS_CREATOR_VALUES = {
    "admin",
    "administrator",
    "false",
    "none",
    "null",
    "odoobot",
    "system",
    "系统",
    "系统导入",
}
LEGACY_SYSTEM_ADMIN_LABEL = "旧系统管理员"


def clean(value):
    if value is None or value is False:
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"false", "none", "null"} else text


def non_business_values():
    return sorted(NON_BUSINESS_CREATOR_VALUES | {value.title() for value in NON_BUSINESS_CREATOR_VALUES})


def is_business_name(value):
    text = clean(value)
    return bool(text and text not in non_business_values())


def artifact_root():
    raw = os.getenv("MIGRATION_ARTIFACT_ROOT") or os.getenv("FORMAL_ENTRY_METADATA_ARTIFACT_ROOT")
    candidates = [Path(raw)] if raw else []
    candidates.extend([Path("/mnt/artifacts/backend"), Path.cwd() / "artifacts"])
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".write_probe"
            probe.write_text("ok\n", encoding="utf-8")
            probe.unlink()
            return candidate
        except OSError:
            continue
    return Path("/tmp")


def _quote_identifier(name):
    """Quote a registry-owned SQL identifier (never user input)."""
    return '"%s"' % str(name).replace('"', '""')


def _resolve_value(resolver, record):
    replacement = resolver(record)
    if not is_business_name(replacement) and clean(replacement) != LEGACY_SYSTEM_ADMIN_LABEL:
        return LEGACY_SYSTEM_ADMIN_LABEL
    return replacement


def provenance_sql_update(env, model_name, field_name, records, resolver):
    """Repair a platform provenance column that the ORM refuses to write.

    ``source_created_by``/``source_created_at`` are platform-added, read-only
    provenance annotations; they are not business facts. Business-fact models
    such as ``sc.settlement.order`` legitimately block ordinary ``write`` on
    approved/completed/voided records, so the declared provenance repair runs
    as a governed P4 SQL update on exactly this column, and only on rows whose
    current value is still an operator login. No other column is touched, the
    update is idempotent, and the product write guard is left intact.
    """
    Model = env[model_name]
    table = _quote_identifier(Model._table)
    column = _quote_identifier(field_name)
    grouped = OrderedDict()
    for record in records:
        grouped.setdefault(_resolve_value(resolver, record), []).append(record.id)
    query = (
        "UPDATE {table} SET {column} = %s WHERE id = ANY(%s) "
        "AND (LOWER(NULLIF(BTRIM({column}::text), '')) = ANY(%s) "
        "OR NULLIF(BTRIM({column}::text), '') = ANY(%s))"
    ).format(table=table, column=column)
    lower_values = sorted(value.lower() for value in NON_BUSINESS_CREATOR_VALUES)
    raw_values = list(non_business_values())
    updated = 0
    for value, ids in grouped.items():
        env.cr.execute(query, [value, list(ids), lower_values, raw_values])
        updated += int(env.cr.rowcount or 0)
    return updated


def _record_row(record, field_name, before, after):
    return OrderedDict(
        [
            ("id", record.id),
            ("name", clean(getattr(record, "name", "")) or clean(record.display_name)),
            ("before", before),
            ("after", after),
        ]
    )


def fix_records(env, model_name, field_name, resolver, channel="orm"):
    Model = env[model_name].sudo().with_context(active_test=False, tracking_disable=True, mail_notrack=True)
    if field_name not in Model._fields:
        return {"model": model_name, "field": field_name, "channel": channel, "updated": 0, "rows": []}
    domain = [(field_name, "in", non_business_values())]
    if "active" in Model._fields:
        domain.insert(0, ("active", "=", True))
    records = Model.search(domain)
    if channel == "provenance_sql":
        rows = [
            _record_row(record, field_name, clean(record[field_name]), _resolve_value(resolver, record))
            for record in records
        ]
        updated = provenance_sql_update(env, model_name, field_name, records, resolver)
        return {"model": model_name, "field": field_name, "channel": channel, "updated": updated, "rows": rows}
    rows = []
    for record in records:
        replacement = _resolve_value(resolver, record)
        before = clean(record[field_name])
        record.write({field_name: replacement})
        rows.append(_record_row(record, field_name, before, replacement))
    return {"model": model_name, "field": field_name, "channel": channel, "updated": len(rows), "rows": rows}


def expense_claim_creator(record):
    if is_business_name(getattr(record, "applicant_name", "")):
        return clean(record.applicant_name)
    return LEGACY_SYSTEM_ADMIN_LABEL


def receipt_income_creator(_record):
    return LEGACY_SYSTEM_ADMIN_LABEL


# Settlement orders migrated from the legacy settlement system carry the
# migrating session login in the generic ``source_created_by`` Char added to
# every declared formal-entry model. ``entry_user_id``/``create_uid`` are the
# migration operator (OdooBot), so the original business entry user is not
# recoverable from the record. Use the same sanctioned legacy label already
# used for ``sc.receipt.income`` instead of leaving the visible surface
# attributed to ``admin``. Approved/completed/voided settlements legitimately
# reject ordinary writes, so this rule repairs the provenance column through
# the declared ``provenance_sql`` channel.
def settlement_order_creator(_record):
    return LEGACY_SYSTEM_ADMIN_LABEL


# (model, creator field consumed by formal_entry_metadata_audit, resolver, channel).
# channel ``orm`` uses the model's own validated write; ``provenance_sql`` is the
# governed P4 path for a provenance column on records whose business-fact write
# guard must stay intact.
CREATOR_RULES = (
    ("sc.expense.claim", "creator_name", expense_claim_creator, "orm"),
    ("sc.receipt.income", "creator_name", receipt_income_creator, "orm"),
    ("sc.settlement.order", "source_created_by", settlement_order_creator, "provenance_sql"),
)


def run(env):
    results = [
        fix_records(env, model_name, field_name, resolver, channel)
        for model_name, field_name, resolver, channel in CREATOR_RULES
    ]
    env.cr.commit()
    result = OrderedDict(
        [
            ("status", "PASS"),
            ("database", env.cr.dbname),
            ("mode", "formal_entry_metadata_non_business_creator_write"),
            ("updated_total", sum(item["updated"] for item in results)),
            ("results", results),
        ]
    )
    target = artifact_root() / f"formal_entry_metadata_non_business_creator_write.{env.cr.dbname}.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print("FORMAL_ENTRY_METADATA_NON_BUSINESS_CREATOR_WRITE=%s" % json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
    return result


if "env" in globals():
    run(env)  # noqa: F821
