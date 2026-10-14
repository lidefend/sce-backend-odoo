# -*- coding: utf-8 -*-
# smart_core/core/system_init_dictionary_data_helper.py

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .dictionary_scope_projection import (
    DELIVERED_SCOPES,
    DISPOSITION_UNKNOWN_SCOPE,
    authorized_company_references,
    scope_disposition,
)
from .source_authority import build_source_authority_contract

SOURCE_KIND = "system_init_dictionary_data_projection"
SOURCE_AUTHORITIES = ("sc.dictionary",)
NO_BUSINESS_FACT_AUTHORITY = True


def source_authority_contract() -> Dict[str, Any]:
    return build_source_authority_contract(
        kind=SOURCE_KIND,
        authorities=SOURCE_AUTHORITIES,
        no_business_fact_authority=NO_BUSINESS_FACT_AUTHORITY,
        runtime_carrier="system.init.dictionary_data",
    )


def count_undelivered_scope(undelivered: Dict[str, int], scope_type: str) -> None:
    """Record a row whose scope has no delivery bucket, so it stays visible.

    An undeliverable scope is never silently promoted to ``__global__``: the
    startup contract carries the count so the gap is a declared fact instead of
    a widening nobody can see.
    """
    key = scope_type or "unknown"
    undelivered[key] = undelivered.get(key, 0) + 1


def count_withheld_scope(withheld: Dict[str, int], reason: str) -> None:
    """Record a row the principal is not authorized to receive.

    Withholding is a decision, not a gap: a company-level row for a company the
    acting principal is not authorized for must never reach their contract, and
    the count keeps that decision observable instead of indistinguishable from
    "no row exists".
    """
    key = reason or "unknown"
    withheld[key] = withheld.get(key, 0) + 1


def _count_withheld(
    withheld: Dict[str, int],
    undelivered: Dict[str, int],
    scope_type: str,
    reason: str,
) -> None:
    """Route one withhold decision to the bucket that describes it."""
    if reason == DISPOSITION_UNKNOWN_SCOPE:
        count_undelivered_scope(undelivered, scope_type)
        return
    count_withheld_scope(withheld, f"{(scope_type or 'unknown').strip()}:{reason}")


def _fetch_role_entries(
    env, undelivered: Dict[str, int], withheld: Dict[str, int], authorized_companies: frozenset
) -> List[dict]:
    rows = env["sc.dictionary"].sudo().search_read(
        [("type", "=", "role_entry"), ("active", "=", True)],
        fields=["code", "name", "scope_type", "scope_ref", "value_json", "sequence"],
        limit=200,
        order="sequence asc, id asc",
    )
    grouped: Dict[str, List[dict]] = {}
    for row in rows:
        scope_type = str(row.get("scope_type") or "").strip() or "global"
        scope_ref = str(row.get("scope_ref") or "").strip()
        role_code, reason = scope_disposition(scope_type, scope_ref, authorized_companies)
        if role_code is None:
            _count_withheld(withheld, undelivered, scope_type, reason)
            continue
        value_json = row.get("value_json") if isinstance(row.get("value_json"), dict) else {}
        entry_key = (
            str(row.get("code") or "").strip()
            or str(value_json.get("entry_key") or "").strip()
            or str(row.get("name") or "").strip()
        )
        if not entry_key:
            continue
        grouped.setdefault(role_code, []).append(
            {
                "entry_key": entry_key,
                "entry_type": str(value_json.get("entry_type") or "menu").strip() or "menu",
                "is_enabled": bool(value_json.get("is_enabled", True)),
                "sequence": int(row.get("sequence") or 10),
            }
        )

    if not grouped:
        return []

    return [
        {"role_code": role_code, "entries": entries}
        for role_code, entries in sorted(grouped.items(), key=lambda item: str(item[0]))
    ]


def _fetch_home_blocks(
    env, undelivered: Dict[str, int], withheld: Dict[str, int], authorized_companies: frozenset
) -> List[dict]:
    rows = env["sc.dictionary"].sudo().search_read(
        [("type", "=", "home_block"), ("active", "=", True)],
        fields=["code", "name", "scope_type", "scope_ref", "value_json", "sequence"],
        limit=200,
        order="sequence asc, id asc",
    )
    grouped: Dict[str, List[Tuple[int, str]]] = {}
    for row in rows:
        scope_type = str(row.get("scope_type") or "").strip() or "global"
        scope_ref = str(row.get("scope_ref") or "").strip()
        role_code, reason = scope_disposition(scope_type, scope_ref, authorized_companies)
        if role_code is None:
            _count_withheld(withheld, undelivered, scope_type, reason)
            continue

        value_json = row.get("value_json") if isinstance(row.get("value_json"), dict) else {}
        is_enabled = value_json.get("is_enabled")
        if isinstance(is_enabled, bool) and not is_enabled:
            continue

        block_key = (
            str(row.get("code") or "").strip()
            or str(value_json.get("block_key") or "").strip()
            or str(row.get("name") or "").strip()
        )
        if not block_key:
            continue

        sequence = int(row.get("sequence") or 10)
        grouped.setdefault(role_code, []).append((sequence, block_key))

    if not grouped:
        return []

    return [
        {
            "role_code": role_code,
            "blocks": [item[1] for item in sorted(blocks, key=lambda pair: (pair[0], pair[1]))],
        }
        for role_code, blocks in sorted(grouped.items(), key=lambda item: str(item[0]))
    ]


def apply_dictionary_startup_data(env, data: Dict[str, Any]) -> Dict[str, Any]:
    if "sc.dictionary" not in env:
        return data

    undelivered: Dict[str, int] = {}
    withheld: Dict[str, int] = {}
    authorized_companies, company_authority = authorized_company_references(env)
    try:
        role_entries = _fetch_role_entries(env, undelivered, withheld, authorized_companies)
        if role_entries:
            data["role_entries"] = role_entries
    except Exception:
        pass

    try:
        home_blocks = _fetch_home_blocks(env, undelivered, withheld, authorized_companies)
        if home_blocks:
            data["home_blocks"] = home_blocks
    except Exception:
        pass

    diagnostics = data.get("dictionary_data_meta") if isinstance(data.get("dictionary_data_meta"), dict) else {}
    diagnostics["source_authority"] = source_authority_contract()
    diagnostics["delivered_scopes"] = list(DELIVERED_SCOPES)
    diagnostics["undelivered_scope_counts"] = dict(sorted(undelivered.items()))
    diagnostics["withheld_scope_counts"] = dict(sorted(withheld.items()))
    diagnostics["company_scope_authority"] = {
        "source": company_authority,
        "authorized_company_count": len(authorized_companies),
    }
    data["dictionary_data_meta"] = diagnostics
    return data
