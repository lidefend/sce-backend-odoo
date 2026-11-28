# -*- coding: utf-8 -*-
"""Compile already-produced navigation authority into one client contract."""
from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from typing import Callable

from .scene_shell_compiler import SceneShellCompiler


def _authority_pairs(authority: dict) -> set[tuple[int, int]]:
    pairs = set()
    for bucket in (
        "primary_actions",
        "role_home_actions",
        "contextual_actions",
        "admin_actions",
    ):
        for row in authority.get(bucket) or []:
            if not isinstance(row, dict):
                continue
            try:
                pairs.add(
                    (
                        int(row.get("menu_id") or 0),
                        int(row.get("action_id") or 0),
                    )
                )
            except (TypeError, ValueError):
                continue
    return pairs


def _reconcile_route_carriers(nav: list[dict]) -> None:
    """Keep every route carrier on the final node route."""
    for node in nav or []:
        if not isinstance(node, dict):
            continue
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        entry_target = (
            node.get("entry_target")
            if isinstance(node.get("entry_target"), dict)
            else {}
        )
        route = str(
            node.get("route")
            or meta.get("route")
            or entry_target.get("route")
            or ""
        ).strip()
        scene_key = str(
            node.get("scene_key")
            or meta.get("scene_key")
            or entry_target.get("scene_key")
            or ""
        ).strip()
        if route:
            node["route"] = route
            meta["route"] = route
            if entry_target:
                next_target = dict(entry_target)
                next_target["route"] = route
                if scene_key:
                    next_target["scene_key"] = scene_key
                node["entry_target"] = next_target
        if scene_key:
            node["scene_key"] = scene_key
            meta["scene_key"] = scene_key
        if meta:
            node["meta"] = meta
        _reconcile_route_carriers(
            node.get("children") if isinstance(node.get("children"), list) else []
        )


def _final_target_index(nav: list[dict]) -> tuple[dict[tuple[int, int], dict], dict[str, dict]]:
    by_pair: dict[tuple[int, int], dict] = {}
    by_scene: dict[str, dict] = {}

    def remember(index: dict, key, row: dict, label: str) -> None:
        existing = index.get(key)
        if existing is not None and existing["route"] != row["route"]:
            raise RuntimeError(
                "conflicting final routes for %s %s: %s != %s"
                % (label, key, existing["route"], row["route"])
            )
        index[key] = row

    pending = list(nav or [])
    index = 0
    while index < len(pending):
        node = pending[index]
        index += 1
        if not isinstance(node, dict):
            continue
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        entry_target = (
            node.get("entry_target")
            if isinstance(node.get("entry_target"), dict)
            else {}
        )
        try:
            pair = (
                int(node.get("menu_id") or meta.get("menu_id") or 0),
                int(node.get("action_id") or meta.get("action_id") or 0),
            )
        except (TypeError, ValueError):
            pair = (0, 0)
        scene_key = str(
            node.get("scene_key")
            or meta.get("scene_key")
            or entry_target.get("scene_key")
            or ""
        ).strip()
        row = {
            "route": str(
                node.get("route")
                or meta.get("route")
                or entry_target.get("route")
                or ""
            ).strip(),
            "scene_key": scene_key,
            "entry_target": deepcopy(entry_target),
        }
        if pair != (0, 0) and row["route"]:
            remember(by_pair, pair, row, "menu/action")
        if scene_key and row["route"]:
            remember(by_scene, scene_key, row, "scene")
        pending.extend(
            node.get("children") if isinstance(node.get("children"), list) else []
        )
    return by_pair, by_scene


def _sync_scenario_surface_routes(surface: dict, nav: list[dict]) -> None:
    """Project final routes onto the presentation-only scenario tree."""
    by_pair, by_scene = _final_target_index(nav)
    surface["nav"] = deepcopy(nav)
    seen: set[int] = set()

    def visit(value) -> None:
        if isinstance(value, list):
            marker = id(value)
            if marker in seen:
                return
            seen.add(marker)
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        marker = id(value)
        if marker in seen:
            return
        seen.add(marker)
        try:
            pair = (
                int(value.get("menu_id") or 0),
                int(value.get("action_id") or 0),
            )
        except (TypeError, ValueError):
            pair = (0, 0)
        scene_key = str(value.get("scene_key") or "").strip()
        target = by_pair.get(pair) if pair != (0, 0) else None
        target = target or (by_scene.get(scene_key) if scene_key else None)
        if target:
            value["route"] = target["route"]
            if target["scene_key"]:
                value["scene_key"] = target["scene_key"]
            if target["entry_target"]:
                value["entry_target"] = deepcopy(target["entry_target"])
        for key, child in value.items():
            if key == "entry_target":
                continue
            visit(child)

    tree = surface.get("tree")
    if isinstance(tree, dict):
        visit(tree)


@dataclass(frozen=True)
class NavigationContractCompilation:
    nav: list[dict]
    route_authority: dict
    navigation: dict
    scene_shells: list[dict] = field(default_factory=list)


class NavigationContractCompiler:
    """Seal supplied authority into one final navigation contract.

    The compiler consumes the shared effective delivery authority, filters
    the navigation once, and derives route and final product-policy projections.
    It cannot select products, enable tenants or recompute native admission.
    """

    def __init__(
        self,
        menu_service,
        *,
        scenario_surface_provider: Callable[[list[dict], dict], dict | None],
        action_pair_walker: Callable[[list[dict]], object],
        scene_shell_compiler: SceneShellCompiler | None = None,
    ):
        self.menu_service = menu_service
        self.scenario_surface_provider = scenario_surface_provider
        self.action_pair_walker = action_pair_walker
        self.scene_shell_compiler = scene_shell_compiler or SceneShellCompiler()

    def compile(
        self,
        *,
        nav: list[dict],
        delivery_payload: dict,
        company_id: int,
        designed_scene_keys=None,
        effective_authority: dict,
    ) -> NavigationContractCompilation:
        if not isinstance(nav, list):
            raise RuntimeError("canonical navigation is unavailable")

        if not isinstance(effective_authority, dict):
            raise RuntimeError("effective delivery authority is unavailable")
        authority = deepcopy(effective_authority)
        authority = dict(authority)
        authority["principal_scope"] = dict(authority.get("principal_scope") or {})
        authority["principal_scope"]["company_id"] = int(company_id)

        # Every authority producer has completed before this single nav filter.
        nav = self.menu_service.filter_nav_by_route_authority(nav, authority)
        nav = self.menu_service.project_canonical_navigation(nav, authority)
        authorized_pairs = _authority_pairs(authority)
        visible_pairs = set(self.action_pair_walker(nav))
        missing = sorted(visible_pairs - authorized_pairs)
        if missing:
            raise RuntimeError(
                "canonical navigation contains unauthorized menu/action pairs: %s"
                % missing[:20]
            )

        delivery_meta = (
            delivery_payload.get("meta")
            if isinstance(delivery_payload, dict)
            and isinstance(delivery_payload.get("meta"), dict)
            else {}
        )
        navigation = {
            "contract_version": "2.0.0",
            "schema_version": "2.0.0",
            "source": "system_init.navigation",
            "nav": nav,
            "route_authority": authority,
            "contextual_routes": list(
                delivery_payload.get("contextual_routes") or []
            ),
            "integrity": {
                "visible_action_count": len(visible_pairs),
                "authorized_action_count": len(authorized_pairs),
                "missing_authority_count": 0,
            },
            "meta": {
                **dict(delivery_meta),
                "product_key": str(delivery_payload.get("product_key") or ""),
                "edition_key": str(delivery_payload.get("edition_key") or ""),
                "role_code": str(delivery_payload.get("role_code") or ""),
                "system_init_nav_boundary": {
                    "authority": "navigation",
                    "semantic_post_processing": False,
                },
            },
        }

        scenario_surface = self.scenario_surface_provider(nav, authority)
        scenarioized_nav = nav
        if isinstance(scenario_surface, dict):
            navigation["scenario_surface"] = scenario_surface
            provided_nav = scenario_surface.get("nav")
            if isinstance(provided_nav, list):
                # Business composition may have no centers for a restricted
                # principal, but it must not erase an already-authorized
                # platform landing leaf from the final scene surface.
                scenarioized_nav = provided_nav or nav

        scene_shells = self.scene_shell_compiler.compile(
            scenarioized_nav,
            designed_scene_keys=designed_scene_keys,
        )
        scenarioized_nav = scene_shells.nav

        scenarioized_nav, authority = (
            self.menu_service.project_final_navigation_routes(
                scenarioized_nav,
                authority,
            )
        )
        _reconcile_route_carriers(scenarioized_nav)
        if isinstance(navigation.get("scenario_surface"), dict):
            _sync_scenario_surface_routes(
                navigation["scenario_surface"],
                scenarioized_nav,
            )
        navigation["product_policy"] = (
            self.menu_service.project_navigation_product_policy(
                scenarioized_nav,
                product_key=str(delivery_payload.get("product_key") or ""),
                edition_key=str(delivery_payload.get("edition_key") or ""),
                role_code=str(delivery_payload.get("role_code") or ""),
                role_codes=list(delivery_payload.get("role_codes") or []),
            )
        )
        scenarioized_pairs = set(self.action_pair_walker(scenarioized_nav))
        missing = sorted(scenarioized_pairs - authorized_pairs)
        if missing:
            raise RuntimeError(
                "scenario navigation contains unauthorized menu/action pairs: %s"
                % missing[:20]
            )
        navigation.update(
            {
                "nav": scenarioized_nav,
                "route_authority": authority,
                "integrity": {
                    "visible_action_count": len(scenarioized_pairs),
                    "authorized_action_count": len(authorized_pairs),
                    "missing_authority_count": 0,
                },
            }
        )
        return NavigationContractCompilation(
            nav=scenarioized_nav,
            route_authority=authority,
            navigation=navigation,
            scene_shells=scene_shells.scene_shell_rows,
        )
