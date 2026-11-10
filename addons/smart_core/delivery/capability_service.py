# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.addons.smart_core.core.delivery_capability_entry_defaults import (
    build_delivery_capability_entry,
)
from odoo.addons.smart_core.core.source_authority import build_source_authority_contract


ENTRY_ALIAS_PREFIXES = ("construction.menu.", "catalog.menu.")
IDENTITY_BUSINESS = "business_capability"
IDENTITY_ENTRY_ALIAS = "entry_compatibility_alias"
IDENTITY_UNCLASSIFIED = "unclassified_capability"


def capability_identity(key: str, row: dict, runtime: dict) -> tuple[str, bool]:
    if key.startswith(ENTRY_ALIAS_PREFIXES):
        return IDENTITY_ENTRY_ALIAS, False
    for source in (row, runtime):
        identity_kind = str(source.get("identity_kind") or "").strip()
        if identity_kind == IDENTITY_BUSINESS:
            return IDENTITY_BUSINESS, source.get("business_capability") is True
        if identity_kind == IDENTITY_ENTRY_ALIAS:
            return IDENTITY_ENTRY_ALIAS, False
    return IDENTITY_UNCLASSIFIED, False


class CapabilityService:
    SOURCE_KIND = "delivery_capability_projection"
    SOURCE_AUTHORITIES = ("delivery_product_policy_projection", "capability_startup_surface_projection")
    NO_BUSINESS_FACT_AUTHORITY = True

    @classmethod
    def source_authority_contract(cls) -> dict:
        return build_source_authority_contract(
            kind=cls.SOURCE_KIND,
            authorities=cls.SOURCE_AUTHORITIES,
            no_business_fact_authority=cls.NO_BUSINESS_FACT_AUTHORITY,
            runtime_carrier="delivery_engine.capabilities",
        )

    def build_entries(self, *, policy: dict, capabilities: list[dict]) -> list[dict]:
        runtime_index = {}
        for item in capabilities or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if key and key not in runtime_index:
                runtime_index[key] = item

        entries: list[dict] = []
        for row in policy.get("capabilities") or []:
            if not isinstance(row, dict):
                continue
            key = str(row.get("capability_key") or row.get("key") or "").strip()
            if not key:
                continue
            runtime = runtime_index.get(key) or {}
            entry = build_delivery_capability_entry(row, runtime)
            if entry:
                identity_kind, business_capability = capability_identity(key, row, runtime)
                entry["capability_identity"] = {
                    "contract_version": str(
                        row.get("identity_contract_version")
                        or runtime.get("identity_contract_version")
                        or "capability.identity.v1"
                    ).strip(),
                    "identity_kind": identity_kind,
                    "business_capability": business_capability,
                    "definition_authority": str(
                        row.get("definition_authority")
                        or runtime.get("definition_authority")
                        or "product_policy_entry_projection"
                    ).strip(),
                    "qualification_authority": str(
                        row.get("qualification_authority")
                        or runtime.get("qualification_authority")
                        or "published_product_release"
                    ).strip(),
                    "provider_authority": str(
                        row.get("provider_authority")
                        or runtime.get("provider_authority")
                        or "product_policy_entry_projection"
                    ).strip(),
                }
                entry["source_authority"] = self.source_authority_contract()
                entries.append(entry)
        return entries
