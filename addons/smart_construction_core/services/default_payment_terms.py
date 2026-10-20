# -*- coding: utf-8 -*-
"""Resolve the company's default payment terms into an account.payment.term.

``default_payment_terms`` is a company-scoped product parameter whose value is
an abstract payment-terms code. This module is the single declared mapping from
those codes to real ``account.payment.term`` records; consumers must not
hardcode payment-term ids or names.
"""

from __future__ import annotations

from typing import Any


PAYMENT_TERMS_XMLID = {
    "net30": "account.account_payment_term_30days",
    "net60": "smart_construction_core.account_payment_term_60days",
    "advance": "account.account_payment_term_immediate",
    "custom": "",
}


def resolve_default_payment_term(env: Any, company: Any = None):
    """Return the payment term backing the company default, or an empty set."""
    company = company or env.company
    code = str(getattr(company, "sc_default_payment_terms", "") or "").strip()
    xmlid = PAYMENT_TERMS_XMLID.get(code)
    if not xmlid:
        return env["account.payment.term"].browse()
    return env.ref(xmlid, raise_if_not_found=False) or env["account.payment.term"].browse()
