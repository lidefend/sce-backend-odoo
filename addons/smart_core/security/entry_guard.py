# -*- coding: utf-8 -*-
"""One entry guard for every ``/api/`` request (ADR-007 batch C).

The namespace check must not be re-implemented per controller: one public route
that forgot to resolve the entry would silently answer from whichever database
the instance holds (a request to an undeclared alias would get the default
upstream's 200).  ``ir.http._pre_dispatch`` calls this module once per request,
before any controller runs, so an unknown, suspended, conflicting or
foreign-target namespace can never reach business code.

Direct-to-Odoo API traffic is refused for the same reason: the entry is the only
selector, so a request without an entry stamp has no namespace at all.
"""

from __future__ import annotations

from .namespace_errors import NamespaceError, NamespaceRequired
from .namespace_resolver import declared_namespace, resolve_entry

ENTRY_API_PREFIX = "/api/"


def requires_entry_namespace(path: str) -> bool:
    """Only the public API surface is entry-scoped."""

    return str(path or "").startswith(ENTRY_API_PREFIX)


def enforce_entry_namespace(env, path: str, headers):
    """Resolve the request namespace, or raise ``NamespaceError``.

    Returns the resolved ``NamespaceRef`` for API requests and ``None`` for any
    other path (``/web/login``, ``/report`` ...), which keep their native
    behaviour.
    """

    if not requires_entry_namespace(path):
        return None
    if not declared_namespace(headers):
        raise NamespaceRequired("the request reached the application without an entry namespace")
    return resolve_entry(env, headers)


def namespace_error_body(exc: NamespaceError, trace_id: str = "") -> dict:
    return exc.payload(trace_id=trace_id or None)
