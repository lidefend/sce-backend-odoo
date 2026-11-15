# -*- coding: utf-8 -*-
"""Construction facts contributed to the generic capability explorer."""
from __future__ import annotations

from collections import defaultdict
from typing import Any


SOURCE_KIND = "construction_platform_capability_explorer_contributions"
SOURCE_AUTHORITIES = (
    "sc.product.scenario.entry",
    "sc.product.scenario",
    "sc.edition.release.snapshot",
    "data/product_menu_source.json",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except Exception:
        return default


def source_authority_contract() -> dict[str, Any]:
    return {
        "kind": SOURCE_KIND,
        "authorities": list(SOURCE_AUTHORITIES),
        "projection_only": True,
        "no_capability_registry": True,
        "no_scene_write": True,
        "no_release_write": True,
    }


def _release_center_map(source: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    centers: dict[str, dict[str, Any]] = {}
    conflicts = []
    for center in ((source.get("product_contract") or {}).get("centers") or []):
        if not isinstance(center, dict):
            continue
        center_fact = {
            "key": _text(center.get("key")),
            "label": _text(center.get("name")),
            "sequence": _int(center.get("sequence"), 10),
        }
        for level_two in center.get("level_two") or []:
            if not isinstance(level_two, dict):
                continue
            leaves = level_two.get("children") or [level_two]
            for leaf in leaves:
                if not isinstance(leaf, dict):
                    continue
                binding = leaf.get("binding") if isinstance(leaf.get("binding"), dict) else {}
                menu_xmlid = _text(binding.get("menu_xmlid") or leaf.get("menu_xmlid"))
                if not menu_xmlid or not center_fact["key"]:
                    continue
                previous = centers.get(menu_xmlid)
                if previous and previous != center_fact:
                    conflicts.append(
                        {
                            "kind": "release_center",
                            "menu_xmlid": menu_xmlid,
                            "center_keys": sorted(
                                {previous["key"], center_fact["key"]}
                            ),
                        }
                    )
                    continue
                centers[menu_xmlid] = dict(center_fact)
    return centers, conflicts


def get_platform_capability_explorer_scope(env):
    """Declare the construction product root without relying on its label."""
    source = None
    try:
        from .product_menu_source import load_source

        source = load_source()
        root_xmlid = _text(source.get("root_menu_xmlid"))
    except Exception:
        root_xmlid = ""
    return {
        "root_menu_xmlids": [root_xmlid] if root_xmlid else [],
    }


def _scene_bindings(env, menu_ids: list[int]) -> dict[str, list[dict[str, Any]]]:
    if not menu_ids:
        return {}
    Entry = env["sc.product.scenario.entry"].sudo()
    entries = Entry.search(
        [("menu_id", "in", menu_ids)],
        order="scenario_id, sequence, id",
    )
    scenario_ids = sorted({_int(entry.scenario_id.id) for entry in entries})
    scenarios = {
        int(scenario.id): scenario
        for scenario in env["sc.product.scenario"].sudo().browse(scenario_ids).exists()
    }
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        scenario = scenarios.get(_int(entry.scenario_id.id))
        if not entry.menu_id or not scenario:
            continue
        result[str(int(entry.menu_id.id))].append(
            {
                "entry_id": int(entry.id),
                "scenario_key": _text(scenario.code),
                "scenario_name": _text(scenario.name),
                "scenario_active": bool(scenario.active),
                "scenario_sequence": _int(scenario.sequence, 10),
                "sequence": _int(entry.sequence, 10),
                "intent": _text(entry.intent),
                "center_key": _text(entry.center_key),
                "center_name": _text(entry.center_name),
            }
        )
    for rows in result.values():
        rows.sort(
            key=lambda row: (
                row["scenario_sequence"],
                row["sequence"],
                row["scenario_key"],
                row["entry_id"],
            )
        )
    return dict(result)


def get_platform_capability_explorer_contributions(env, menu_ids, menu_xmlids):
    """Contribute existing scene and publication facts without persisting discovery."""
    from .product_menu_source import (
        load_published_menu_release_projection,
        load_source,
    )

    normalized_menu_ids = sorted(
        {
            _int(menu_id)
            for menu_id in (menu_ids or [])
            if _int(menu_id) > 0
        }
    )
    scene_bindings = _scene_bindings(env, normalized_menu_ids)
    release_projection = load_published_menu_release_projection(env)
    source = load_source()
    release_centers, center_conflicts = _release_center_map(source)
    relevant_release_states = {
        menu_xmlid: state
        for menu_xmlid, state in (
            release_projection.get("menu_release_states") or {}
        ).items()
        if _text(menu_xmlid) in {
            _text(value) for value in (menu_xmlids or {}).values()
        }
    }
    return {
        "source_module": "smart_construction_core",
        "source_authority": source_authority_contract(),
        "scene_authority_available": "sc.product.scenario.entry" in env,
        "release_authority_available": bool(
            release_projection.get("standard_applied")
            or release_projection.get("preview_applied")
        ),
        "scene_bindings": scene_bindings,
        "release_states": relevant_release_states,
        "release_centers": {
            menu_xmlid: center
            for menu_xmlid, center in release_centers.items()
            if menu_xmlid in {
                _text(value) for value in (menu_xmlids or {}).values()
            }
        },
        "product_qualifications": {},
        "release_snapshots": release_projection.get("snapshots") or [],
        "token_facts": {
            "scene_bindings": scene_bindings,
            "release_states": relevant_release_states,
            "release_centers": {
                menu_xmlid: release_centers[menu_xmlid]
                for menu_xmlid in sorted(release_centers)
                if menu_xmlid in {
                    _text(value) for value in (menu_xmlids or {}).values()
                }
            },
            "release_snapshots": release_projection.get("snapshots") or [],
        },
        "conflicts": center_conflicts,
    }
