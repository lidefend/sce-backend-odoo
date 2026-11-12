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
                scenarioized_nav = provided_nav

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
