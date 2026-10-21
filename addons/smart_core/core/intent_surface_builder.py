# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Dict, List, Tuple

from ..security.intent_authorization import handler_group_decision, registered_handlers


class IntentSurfaceBuilder:
    SOURCE_KIND = "intent_surface_projection"
    SOURCE_AUTHORITIES = ("handler_registry", "ir.model.data", "res.groups", "intent_authorization")
    NO_BUSINESS_FACT_AUTHORITY = True

    @classmethod
    def source_authority_contract(cls) -> dict:
        return {
            "kind": cls.SOURCE_KIND,
            "authorities": list(cls.SOURCE_AUTHORITIES),
            "projection_only": True,
            "rebuildable": True,
            "no_business_fact_authority": cls.NO_BUSINESS_FACT_AUTHORITY,
            "runtime_carrier": "intent_surface_builder",
        }

    @staticmethod
    def _safe_aliases(handler_cls) -> list[str]:
        try:
            raw = list(getattr(handler_cls, "ALIASES") or [])
        except Exception:
            raw = []
        aliases: list[str] = []
        for item in raw:
            alias = str(item or "").strip()
            if alias:
                aliases.append(alias)
        return aliases

    def collect(self, env, user) -> Tuple[List[str], Dict[str, dict]]:
        canonical_rows: dict[str, dict] = {}
        alias_rows: dict[str, set[str]] = {}

        for name, cls in registered_handlers(env).items():
            primary = str(getattr(cls, "INTENT_TYPE", None) or name).strip()
            if not primary:
                continue
            if primary not in canonical_rows:
                canonical_rows[primary] = {
                    "version": getattr(cls, "VERSION", None),
                    "group_decision": handler_group_decision(env, user, cls),
                    "enabled": bool(getattr(cls, "IS_ENABLED", True)),
                }
            alias_set = alias_rows.setdefault(primary, set())
            for alias in self._safe_aliases(cls):
                if alias != primary:
                    alias_set.add(alias)
            if name != primary:
                alias_set.add(str(name))

        intents: List[str] = []
        meta: Dict[str, dict] = {}
        for primary, row in canonical_rows.items():
            if not bool(row.get("enabled")):
                continue
            required = row["group_decision"]["required_groups"]
            if not row["group_decision"]["allowed"]:
                continue
            intents.append(primary)
            meta[primary] = {
                "version": row.get("version"),
                "aliases": sorted(alias_rows.get(primary) or set()),
                "required_groups_xmlids": required,
                "status": "canonical",
                "canonical": primary,
            }

        intents_sorted = sorted(set(intents))
        meta_sorted = {k: meta[k] for k in intents_sorted if k in meta}
        return intents_sorted, meta_sorted

    def collect_catalog(self, env, user) -> list[dict]:
        intents, intents_meta = self.collect(env, user)
        rows: list[dict] = []
        for canonical in intents:
            row = intents_meta.get(canonical) if isinstance(intents_meta.get(canonical), dict) else {}
            rows.append({
                "name": canonical,
                "status": "canonical",
                "canonical": canonical,
                "version": row.get("version"),
                "required_groups_xmlids": row.get("required_groups_xmlids") or [],
            })
            for alias in row.get("aliases") or []:
                rows.append({
                    "name": str(alias),
                    "status": "alias",
                    "canonical": canonical,
                    "version": row.get("version"),
                    "required_groups_xmlids": row.get("required_groups_xmlids") or [],
                })
        rows.sort(key=lambda item: (str(item.get("name") or ""), str(item.get("status") or "")))
        return rows
