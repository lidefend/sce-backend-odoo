# -*- coding: utf-8 -*-
from __future__ import annotations

from odoo.addons.smart_core.core.delivery_capability_entry_defaults import (
    build_delivery_capability_entry,
)
from odoo.addons.smart_core.core.source_authority import build_source_authority_contract


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
                identity_kind = str(
                    row.get("identity_kind")
                    or runtime.get("identity_kind")
                    or ("business_capability" if runtime else "entry_compatibility_alias")
                ).strip()
                entry["capability_identity"] = {
                    "contract_version": str(
                        row.get("identity_contract_version")
                        or runtime.get("identity_contract_version")
                        or "capability.identity.v1"
                    ).strip(),
                    "identity_kind": identity_kind,
                    "business_capability": bool(
                        row.get("business_capability", runtime.get("business_capability", identity_kind == "business_capability"))
                    ),
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
