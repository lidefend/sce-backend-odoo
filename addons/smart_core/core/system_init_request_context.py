# -*- coding: utf-8 -*-
"""Explicit request-scoped facts for one system.init execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

try:
    from odoo.addons.smart_core.core.source_authority import (
        build_source_authority_contract,
    )
except Exception:
    def build_source_authority_contract(**kwargs):
        return dict(kwargs)


SOURCE_KIND = "system_init_request_fact_scope"
SOURCE_AUTHORITIES = ("system_init_request", "extension_fact_loader")
NO_BUSINESS_FACT_AUTHORITY = True


def source_authority_contract() -> dict:
    return build_source_authority_contract(
        kind=SOURCE_KIND,
        authorities=SOURCE_AUTHORITIES,
        no_business_fact_authority=NO_BUSINESS_FACT_AUTHORITY,
        runtime_carrier="system_init_request_context",
    )


@dataclass(frozen=True)
class RequestFact:
    key: str
    value: Any


class SystemInitRequestContext:
    """Own request-local facts without using env.context or module globals.

    The context is created by SystemInitHandler and passed explicitly to
    consumers. A fact loader runs once for the request. Loader failures are not
    cached, so a caller may surface the failure without poisoning later reads.
    """

    SOURCE_KIND = SOURCE_KIND
    SOURCE_AUTHORITIES = SOURCE_AUTHORITIES
    NO_BUSINESS_FACT_AUTHORITY = NO_BUSINESS_FACT_AUTHORITY

    @classmethod
    def source_authority_contract(cls) -> dict:
        return source_authority_contract()

    def __init__(self, env, request_identity: dict | None = None):
        self.env = env
        self._facts: dict[str, RequestFact] = {}
        self.identity = {
            "database": str(getattr(getattr(env, "cr", None), "dbname", "") or ""),
            "user_id": int(getattr(getattr(env, "user", None), "id", 0) or 0),
            "company_id": int(getattr(getattr(env, "company", None), "id", 0) or 0),
            "product_key": "",
            "base_product_key": "",
            "edition_key": "",
        }
        for key in ("product_key", "base_product_key", "edition_key"):
            self.identity[key] = str((request_identity or {}).get(key) or "").strip()

    def resolve(self, key: str, loader: Callable[[], Any]) -> tuple[Any, bool]:
        """Return ``(fact, loaded)`` for this request."""
        normalized = str(key or "").strip()
        if not normalized:
            raise ValueError("request fact key is required")
        if not callable(loader):
            raise TypeError("request fact loader must be callable")
        existing = self._facts.get(normalized)
        if existing is not None:
            return existing.value, False
        value = loader()
        self._facts[normalized] = RequestFact(key=normalized, value=value)
        return value, True

    def fact(self, key: str) -> RequestFact | None:
        return self._facts.get(str(key or "").strip())

    def loaded_keys(self) -> tuple[str, ...]:
        return tuple(self._facts)
