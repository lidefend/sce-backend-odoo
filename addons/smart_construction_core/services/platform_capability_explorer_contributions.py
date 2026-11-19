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
    "sc.scene.company.enablement",
    "data/product_menu_source.json",
    "ir.config_parameter",
)
RELEASE_CENTER_SOURCE = "construction.product_menu_source.v1"


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
    conflicted_menu_xmlids = set()
    for center in ((source.get("product_contract") or {}).get("centers") or []):
        if not isinstance(center, dict):
            continue
        center_fact = {
            "key": _text(center.get("key")),
            "label": _text(center.get("name")),
            "sequence": _int(center.get("sequence"), 10),
            "source": RELEASE_CENTER_SOURCE,
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
                    centers.pop(menu_xmlid, None)
                    conflicted_menu_xmlids.add(menu_xmlid)
                    continue
                if menu_xmlid in conflicted_menu_xmlids:
                    continue
                centers[menu_xmlid] = dict(center_fact)
    return centers, conflicts


def _published_release_center_map(
    release_projection: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Project the effective published product center without seed inference."""
    centers: dict[str, dict[str, Any]] = {}
    raw_centers = (
        release_projection.get("release_centers")
        if isinstance(release_projection.get("release_centers"), dict)
        else {}
    )
    for menu_xmlid, raw_center in raw_centers.items():
        center = dict(raw_center) if isinstance(raw_center, dict) else {}
        center_key = _text(center.get("center_key") or center.get("key"))
        if not menu_xmlid or not center_key:
            continue
        product_key = _text(center.get("product_key"))
        centers[menu_xmlid] = {
            "key": center_key,
            "label": _text(center.get("center_label") or center.get("label")),
            "sequence": _int(
                center.get("center_sequence")
                if center.get("center_sequence") is not None
                else center.get("sequence"),
                10,
            ),
            "product_key": product_key,
            "snapshot_id": _int(center.get("snapshot_id")),
            "version": _text(center.get("version")),
            "source": "published_product_policy",
            "config_ref": {
                "kind": "release_operator_action",
                "intent": "release.operator.update_policy",
                "product_key": product_key,
                "editor_contract": "product_center_editor.v1",
            },
        }
    return centers, []


def _unavailable_release_projection(reason_code: str) -> dict[str, Any]:
    return {
        "menu_release_states": {},
        "release_centers": {},
        "product_centers": [],
        "snapshots": [
            {
                "product_key": product_key,
                "applied": False,
                "fail_closed": False,
                "snapshot_id": 0,
                "version": "",
                "fingerprint": "",
                "platform_db": "",
                "reason": reason_code,
            }
            for product_key in ("construction.standard", "construction.preview")
        ],
        "standard_applied": False,
        "preview_applied": False,
        "authority_available": False,
        "authority_reason": reason_code,
    }


def load_capability_explorer_release_projection(
    env,
    *,
    product_keys=None,
    platform_database_resolver=None,
    projection_loader=None,
):
    """Read release facts only from the current registry.

    The Explorer is never allowed to open a second database or use a
    superuser environment belonging to another database. When the declared
    platform release database differs from the current tenant registry, the
    authority is explicitly unavailable.
    """
    if platform_database_resolver is None:
        from odoo.addons.smart_core.core.platform_database_contract import (
            resolve_platform_database,
        )

        platform_database_resolver = resolve_platform_database
    if projection_loader is None:
        from .product_menu_source import load_published_menu_release_projection

        projection_loader = load_published_menu_release_projection
    current_database = _text(getattr(getattr(env, "cr", None), "dbname", ""))
    if not current_database:
        return _unavailable_release_projection("CURRENT_DATABASE_UNAVAILABLE")
    try:
        platform_database = _text(platform_database_resolver(env))
    except Exception:
        return _unavailable_release_projection("PLATFORM_RELEASE_DATABASE_UNRESOLVED")
    if not platform_database or platform_database != current_database:
        return _unavailable_release_projection("PLATFORM_RELEASE_DB_ISOLATED")
    try:
        try:
            projection = projection_loader(env, product_keys=product_keys)
        except TypeError:
            projection = projection_loader(env)
    except Exception:
        return _unavailable_release_projection("RELEASE_SNAPSHOT_READ_FAILED")
    projection = dict(projection) if isinstance(projection, dict) else {}
    applied_snapshot = any(
        isinstance(row, dict) and bool(row.get("applied"))
        for row in projection.get("snapshots") or []
    )
    projection["authority_available"] = bool(
        applied_snapshot
        or projection.get("standard_applied")
        or projection.get("preview_applied")
    )
    projection["authority_reason"] = (
        "OK" if projection["authority_available"] else "ACTIVE_RELEASE_SNAPSHOT_NOT_FOUND"
    )
    return projection


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


def _company_fact(env) -> dict[str, Any]:
    company = getattr(env, "company", None)
    company_id = _int(getattr(company, "id", 0))
    return {
        "company_id": company_id,
        "company_name": _text(getattr(company, "name", "")),
        "source": "res.company",
    }


def _enterprise_enablement(env, scene_bindings: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Project the current company's scenario decisions per native menu.

    Enablement is only the enterprise's choice to expose an eligible released
    scenario. It is not a user or role grant; ordinary access remains a runtime
    navigation + ACL/rule decision.
    """
    from odoo.addons.smart_construction_scene.services.tenant_scene_activation import (
        read_tenant_enablement,
    )

    company = _company_fact(env)
    company_id = company["company_id"]
    result: dict[str, dict[str, Any]] = {}
    cache: dict[str, bool] = {}
    for menu_id, bindings in scene_bindings.items():
        scenes = []
        for binding in bindings:
            scene_key = _text(binding.get("scenario_key"))
            if not scene_key or binding.get("scenario_active", True) is False:
                continue
            if scene_key not in cache:
                cache[scene_key] = (
                    bool(read_tenant_enablement(env, company_id, scene_key))
                    if company_id
                    else False
                )
            scenes.append(
                {
                    "scene_key": scene_key,
                    "enabled": cache[scene_key],
                    "source": "sc.scene.company.enablement",
                }
            )
        if not scenes:
            continue
        result[str(menu_id)] = {
            "applicable": True,
            "enabled": any(row["enabled"] for row in scenes),
            "status": "enabled" if any(row["enabled"] for row in scenes) else "disabled",
            "reason_code": (
                "ENTERPRISE_SCENARIO_ENABLED"
                if any(row["enabled"] for row in scenes)
                else "ENTERPRISE_SCENARIO_NOT_ENABLED"
            ),
            **company,
            "scenes": scenes,
        }
    return result


def _product_qualifications(
    menu_xmlids: list[str],
    release_projection: dict[str, Any],
    product_keys: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Resolve product qualification only from active published snapshots."""
    product_keys = list(
        product_keys
        or [
            _text(row.get("product_key"))
            for row in release_projection.get("snapshots") or []
            if isinstance(row, dict) and _text(row.get("product_key"))
        ]
        or ["construction.standard", "construction.preview"]
    )
    states_by_product = release_projection.get("menu_release_states_by_product") or {}
    snapshots_by_product = {
        _text(row.get("product_key")): row
        for row in release_projection.get("snapshots") or []
        if isinstance(row, dict) and _text(row.get("product_key"))
    }
    authority_available = bool(release_projection.get("authority_available"))
    result: dict[str, dict[str, Any]] = {}
    for menu_xmlid in sorted({_text(value) for value in menu_xmlids if _text(value)}):
        evidence = []
        qualities: dict[str, str] = {}
        for product_key in product_keys:
            snapshot = snapshots_by_product.get(product_key) or {}
            release_state = _text(
                (states_by_product.get(product_key) or {}).get(menu_xmlid)
            )
            applied = bool(snapshot.get("applied"))
            qualified = bool(applied and release_state == "released")
            status = (
                "qualified"
                if qualified
                else "not_qualified"
                if authority_available
                else "not_verified"
            )
            qualities[product_key] = status
            evidence.append(
                {
                    "product_key": product_key,
                    "qualified": qualified,
                    "status": status,
                    "release_state": release_state,
                    "snapshot_id": _int(snapshot.get("snapshot_id")),
                    "version": _text(snapshot.get("version")),
                    "fingerprint": _text(snapshot.get("fingerprint")),
                    "applied": applied,
                    "reason_code": (
                        "PRODUCT_QUALIFIED"
                        if qualified
                        else "PRODUCT_NOT_RELEASED"
                        if applied
                        else _text(snapshot.get("reason"))
                        or "ACTIVE_RELEASE_SNAPSHOT_NOT_FOUND"
                    ),
                    "source": "sc.edition.release.snapshot",
                    "qualification_authority": "published_product_release",
                }
            )
        selected_key = _text(release_projection.get("selected_product_key"))
        selected_status = (
            qualities.get(selected_key)
            if selected_key
            else ""
        )
        result[menu_xmlid] = {
            "standard": qualities.get("construction.standard", "not_verified"),
            "preview": qualities.get("construction.preview", "not_verified"),
            "selected_product_key": selected_key,
            "selected_status": selected_status or "not_verified",
            "by_product": dict(qualities),
            "authority_available": authority_available,
            "reason_code": (
                "PRODUCT_QUALIFIED"
                if (
                    selected_status == "qualified"
                    if selected_key
                    else qualities.get("construction.standard") == "qualified"
                )
                else "PRODUCT_NOT_QUALIFIED"
                if authority_available
                else _text(release_projection.get("authority_reason"))
                or "PRODUCT_QUALIFICATION_UNVERIFIED"
            ),
            "evidence": evidence,
        }
    return result


def get_platform_capability_explorer_contributions(
    env,
    menu_ids,
    menu_xmlids,
    catalog_scope=None,
):
    """Contribute existing scene and publication facts without persisting discovery."""
    normalized_menu_ids = sorted(
        {
            _int(menu_id)
            for menu_id in (menu_ids or [])
            if _int(menu_id) > 0
        }
    )
    scene_bindings = _scene_bindings(env, normalized_menu_ids)
    enterprise_enablement = _enterprise_enablement(env, scene_bindings)
    scope = catalog_scope if isinstance(catalog_scope, dict) else {}
    selected_product_key = _text(scope.get("product_key"))
    product_keys = (
        [selected_product_key]
        if _text(scope.get("mode")) == "product" and selected_product_key
        else [
            _text(row.get("product_key"))
            for row in scope.get("products") or []
            if isinstance(row, dict) and _text(row.get("product_key"))
        ]
        or ["construction.standard", "construction.preview"]
    )
    release_projection = load_capability_explorer_release_projection(
        env,
        product_keys=product_keys,
    )
    release_projection["selected_product_key"] = selected_product_key
    release_centers, center_conflicts = _published_release_center_map(
        release_projection
    )
    relevant_release_states = {
        menu_xmlid: state
        for menu_xmlid, state in (
            release_projection.get("menu_release_states") or {}
        ).items()
        if _text(menu_xmlid) in {
            _text(value) for value in (menu_xmlids or {}).values()
        }
    }
    product_qualifications = _product_qualifications(
        sorted(
            {
                *relevant_release_states,
                *[
                    _text(value)
                    for value in (menu_xmlids or {}).values()
                    if _text(value)
                ],
            }
        ),
        release_projection,
        product_keys,
    )
    return {
        "source_module": "smart_construction_core",
        "source_authority": source_authority_contract(),
        "scene_authority_available": "sc.product.scenario.entry" in env,
        "release_authority_available": bool(
            release_projection.get("authority_available")
        ),
        "release_authority_reason": _text(
            release_projection.get("authority_reason")
        ),
        "scene_bindings": scene_bindings,
        "enterprise_enablement": enterprise_enablement,
        "company_context": _company_fact(env),
        "release_states": relevant_release_states,
        "release_centers": {
            menu_xmlid: center
            for menu_xmlid, center in release_centers.items()
            if menu_xmlid in {
                _text(value) for value in (menu_xmlids or {}).values()
            }
        },
        "product_qualifications": product_qualifications,
        "release_snapshots": release_projection.get("snapshots") or [],
        "token_facts": {
            "scene_bindings": scene_bindings,
            "enterprise_enablement": enterprise_enablement,
            "company_context": _company_fact(env),
            "release_states": relevant_release_states,
            "release_centers": {
                menu_xmlid: release_centers[menu_xmlid]
                for menu_xmlid in sorted(release_centers)
                if menu_xmlid in {
                    _text(value) for value in (menu_xmlids or {}).values()
                }
            },
            "release_snapshots": release_projection.get("snapshots") or [],
            "product_qualifications": product_qualifications,
        },
        "conflicts": center_conflicts,
    }
