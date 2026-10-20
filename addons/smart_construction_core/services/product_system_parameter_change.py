# -*- coding: utf-8 -*-
"""Company-authority write/read for backed product system parameters.

The controlled parameter catalog declares which parameter is backed by company
fields. This module is the single write/read authority for those backed
parameters: publish writes the company fields and returns the previous value,
rollback restores the previous value. Nothing here exposes raw
ir.config_parameter or credential material.
"""

from __future__ import annotations

from typing import Any


COST_LEDGER_SOURCE_FIELD_MAP = {
    "account_move": "sc_cost_from_account_move",
    "purchase_order": "sc_cost_from_purchase",
    "stock_move": "sc_cost_from_stock",
}


def read_parameter_value(company: Any, parameter_key: str):
    """Return the current value of a backed parameter, or None if not backed."""
    key = str(parameter_key or "").strip()
    if key == "cost_ledger_source":
        enabled = {
            source: bool(getattr(company, field, False))
            for source, field in COST_LEDGER_SOURCE_FIELD_MAP.items()
        }
        selected = [source for source, value in enabled.items() if value]
        return selected[0] if len(selected) == 1 else "disabled"
    return None


def apply_parameter_value(company: Any, parameter_key: str, value: Any):
    """Apply a backed parameter value and return the previous value.

    ``company`` may be a duck-typed object exposing ``sudo().write({...})`` so
    the same function can be exercised by offline unit tests.
    """
    key = str(parameter_key or "").strip()
    previous = read_parameter_value(company, key)
    if key == "cost_ledger_source":
        writable = company.sudo() if callable(getattr(company, "sudo", None)) else company
        writable.write(
            {
                field: value == source
                for source, field in COST_LEDGER_SOURCE_FIELD_MAP.items()
            }
        )
        return previous
    raise ValueError("parameter %s has no company authority backing" % key)
