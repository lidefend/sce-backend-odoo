# -*- coding: utf-8 -*-
"""Compile already-produced navigation authority into one client contract."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


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


def _add_scene_internal_authority(authority: dict, actions: dict | None) -> None:
    if not isinstance(actions, dict):
        return
    bucket = authority.setdefault("contextual_actions", [])
    for internal_row in actions.values():
        if not isinstance(internal_row, dict):
            continue
        try:
            action_id = int(internal_row.get("action_id") or 0)
        except (TypeError, ValueError):
            action_id = 0
        if action_id <= 0:
            continue
        entry = dict(internal_row)
        entry["route_kind"] = "CONTEXTUAL_ROUTE"
        entry["source"] = "scene_internal_action_authority"
        entry.setdefault("scene_key", str(internal_row.get("scene_key") or ""))
        bucket.append(entry)


@dataclass(frozen=True)
class NavigationContractCompilation:
    nav: list[dict]
    route_authority: dict
    navigation: dict


class NavigationContractCompiler:
    """Seal supplied authority into one final navigation contract.

    The compiler does not select menus, grant access, enable tenants or publish
    products. It combines authority producers that have already run, filters
    the navigation once, then derives route and final product-policy
    projections from the same scenarioized tree.
    """

    def __init__(
        self,
        menu_service,
        *,
        scenario_surface_provider: Callable[[list[dict], dict], dict | None],
        platform_duty_merger: Callable[[dict, dict], dict],
        release_node_filter: Callable[[list[dict]], list[dict]],
        action_pair_walker: Callable[[list[dict]], object],
        authority_finalizer: Callable[[dict], dict | None] | None = None,
    ):
        self.menu_service = menu_service
        self.scenario_surface_provider = scenario_surface_provider
        self.platform_duty_merger = platform_duty_merger
        self.release_node_filter = release_node_filter
        self.action_pair_walker = action_pair_walker
        self.authority_finalizer = authority_finalizer

    def compile(
        self,
        *,
        nav: list[dict],
        role_surface: dict,
        delivery_payload: dict,
        release_gate: dict,
        platform_duty: dict | None,
        scene_internal_actions: dict | None,
        company_id: int,
    ) -> NavigationContractCompilation:
        if not isinstance(nav, list):
            raise RuntimeError("canonical navigation is unavailable")

        authority = self.menu_service.build_route_authority(
            role_surface,
            nav=nav,
        )
        authority = self.menu_service.filter_route_authority_by_publication(
            authority,
            filter_nodes=self.release_node_filter,
        )
        authority = self.platform_duty_merger(
            authority,
            platform_duty if isinstance(platform_duty, dict) else {},
        )
        _add_scene_internal_authority(authority, scene_internal_actions)
        if self.authority_finalizer is not None:
            finalized = self.authority_finalizer(authority)
            if isinstance(finalized, dict):
                authority = finalized
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
        if not isinstance(scenario_surface, dict):
            return NavigationContractCompilation(
                nav=nav,
                route_authority=authority,
                navigation=navigation,
            )

        navigation["scenario_surface"] = scenario_surface
        scenarioized_nav = scenario_surface.get("nav")
        if not isinstance(scenarioized_nav, list):
            return NavigationContractCompilation(
                nav=nav,
                route_authority=authority,
                navigation=navigation,
            )

        scenarioized_nav, authority = (
            self.menu_service.project_final_navigation_routes(
                scenarioized_nav,
                authority,
            )
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
        )
