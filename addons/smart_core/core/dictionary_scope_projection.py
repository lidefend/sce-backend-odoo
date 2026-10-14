# -*- coding: utf-8 -*-
"""The one scope vocabulary for ``sc.dictionary`` startup projection.

``sc.dictionary.scope_type`` is ``global`` / ``company`` / ``role``. All three
have a delivery meaning in the startup contract:

* ``global`` — the platform-level (and industry-module published) reference set
  publishes under the ``__global__`` bucket;
* ``company`` — a company-level reference publishes for exactly the companies
  the acting principal is authorized for, and for no other principal;
* ``role`` — publishes under its own role code.

The company case has no bucket of its own because the startup contract is built
per principal: a company-level row is delivered *for that principal's own
company*, which is what the ``__global__`` bucket already means inside a
per-principal payload. It is therefore delivered only when the row's
``scope_ref`` names a company in the caller's authorized company reference set,
and withheld (never promoted) otherwise.

``scope_ref`` for a company row is the ``res.company`` id rendered as a string.
The authorized set comes from the single data-space authority
(``res.users._sc_data_company_ids()``) through ``authorized_company_references``
below — the one adapter both producers call, so no producer can widen a scope to
make delivery succeed. The bucket decision itself stays pure. An unknown scope,
a company row without authority and a company row without a usable reference are
all *withheld and reported*, never published as global.
"""
from __future__ import annotations

from typing import Iterable, Optional, Tuple

GLOBAL_SCOPE = "global"
COMPANY_SCOPE = "company"
ROLE_SCOPE = "role"
GLOBAL_BUCKET = "__global__"
DELIVERED_SCOPES = (GLOBAL_SCOPE, COMPANY_SCOPE, ROLE_SCOPE)

DISPOSITION_DELIVERED = "delivered"
DISPOSITION_UNKNOWN_SCOPE = "unknown_scope"
DISPOSITION_MISSING_REFERENCE = "missing_reference"
DISPOSITION_UNAUTHORIZED_COMPANY = "unauthorized_company"

_WITHHELD_DISPOSITIONS = (
    DISPOSITION_UNKNOWN_SCOPE,
    DISPOSITION_MISSING_REFERENCE,
    DISPOSITION_UNAUTHORIZED_COMPANY,
)


def company_scope_references(company_ids: Iterable) -> frozenset:
    """Normalize an authorized company id collection into ``scope_ref`` form."""
    return frozenset(str(int(company_id)) for company_id in company_ids or ())


def authorized_company_references(env) -> Tuple[frozenset, str]:
    """Resolve the acting principal's company reference set from the authority.

    ``res.users._sc_data_company_ids()`` is the data-space company authority
    (registered, active, purpose-bounded, bootstrap company excluded). Resolution
    is fail-closed: an unavailable or failing authority yields the empty set, so
    company-level rows are withheld and counted instead of published to everyone.
    """
    user = getattr(env, "user", None)
    resolver = getattr(user, "_sc_data_company_ids", None)
    if not callable(resolver):
        return frozenset(), "unavailable"
    try:
        return company_scope_references(resolver()), "res_users_sc_data_company_ids"
    except Exception:
        return frozenset(), "unresolved"


def scope_disposition(
    scope_type: str,
    scope_ref: str,
    authorized_company_refs: Iterable = (),
) -> Tuple[Optional[str], str]:
    """Return ``(bucket, reason)`` for one row; ``bucket`` is ``None`` on withhold."""
    scope = (scope_type or "").strip()
    ref = (scope_ref or "").strip()
    if scope == GLOBAL_SCOPE:
        return GLOBAL_BUCKET, DISPOSITION_DELIVERED
    if scope == ROLE_SCOPE:
        if ref:
            return ref, DISPOSITION_DELIVERED
        return None, DISPOSITION_MISSING_REFERENCE
    if scope == COMPANY_SCOPE:
        if not ref:
            return None, DISPOSITION_MISSING_REFERENCE
        if ref in company_scope_references(authorized_company_refs):
            return GLOBAL_BUCKET, DISPOSITION_DELIVERED
        return None, DISPOSITION_UNAUTHORIZED_COMPANY
    return None, DISPOSITION_UNKNOWN_SCOPE


def projection_bucket(
    scope_type: str,
    scope_ref: str,
    authorized_company_refs: Iterable = (),
) -> Optional[str]:
    """Return the delivery bucket for a row, or ``None`` when undeliverable."""
    bucket, _reason = scope_disposition(scope_type, scope_ref, authorized_company_refs)
    return bucket
