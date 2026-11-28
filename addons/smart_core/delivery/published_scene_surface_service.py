# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy

from odoo.addons.smart_core.core.platform_minimum_nav_contract import WORKSPACE_SCENE_KEY
from odoo.addons.smart_core.utils.extension_hooks import call_extension_hook_first

from .menu_service import MenuService
from .navigation_contract_compiler import NavigationContractCompiler


class _UncachedSceneRequestContext:
    @staticmethod
    def resolve(_key, loader):
        return loader(), True


class PublishedSceneSurfaceService:
    """Compile published candidate entries into the single client scene surface."""

    def __init__(self, env):
        self.env = env
        self.menu_service = MenuService(env)

    def build(self, delivery_payload: dict, *, request_context=None) -> dict:
        payload = delivery_payload if isinstance(delivery_payload, dict) else {}
        nav = payload.get("nav")
        authority = payload.get("route_authority")
        if not isinstance(nav, list):
            raise RuntimeError("canonical navigation is unavailable")
        if not isinstance(authority, dict):
            raise RuntimeError("effective delivery authority is unavailable")

        scene_request_context = (
            request_context
            if request_context is not None and hasattr(request_context, "resolve")
            else _UncachedSceneRequestContext()
        )
        policy = payload.get("product_policy") if isinstance(payload.get("product_policy"), dict) else {}
        designed_scene_keys = {
            str(key or "").strip()
            for key in (policy.get("scene_keys") or [])
            if str(key or "").strip()
        }
        designed_scene_keys.add(WORKSPACE_SCENE_KEY)
        designed_scene_keys.update(
            str(row.get("scene_key") or row.get("key") or "").strip()
            for row in (payload.get("scenes") or [])
            if isinstance(row, dict)
            and str(row.get("scene_key") or row.get("key") or "").strip()
        )
        declared_scenes = call_extension_hook_first(
            self.env,
            "smart_core_delivery_scene_declarations",
            self.env,
            request_context=scene_request_context,
        )
        if isinstance(declared_scenes, list):
            designed_scene_keys.update(
                str(row.get("code") or row.get("key") or "").strip()
                for row in declared_scenes
                if isinstance(row, dict)
                and str(row.get("code") or row.get("key") or "").strip()
            )

        navigation_seed = {
            "product_key": str(payload.get("product_key") or "").strip(),
            "base_product_key": str(payload.get("base_product_key") or "").strip(),
            "edition_key": str(payload.get("edition_key") or "").strip(),
            "role_code": str(payload.get("role_code") or "").strip(),
            "role_codes": deepcopy(payload.get("role_codes") or []),
            "contextual_routes": deepcopy(payload.get("contextual_routes") or []),
            "meta": deepcopy(payload.get("meta") or {}),
        }
        compilation = NavigationContractCompiler(
            self.menu_service,
            scenario_surface_provider=lambda current_nav, current_authority: call_extension_hook_first(
                self.env,
                "smart_core_scenario_surface_projection",
                self.env,
                current_nav,
                current_authority,
                request_context=scene_request_context,
            ),
            action_pair_walker=MenuService._walk_nav_action_refs,
        ).compile(
            nav=deepcopy(nav),
            delivery_payload=navigation_seed,
            company_id=int(self.env.company.id),
            designed_scene_keys=designed_scene_keys,
            effective_authority=deepcopy(authority),
        )
        return {
            "nav": compilation.nav,
            "route_authority": compilation.route_authority,
            "navigation": compilation.navigation,
            "scene_shells": compilation.scene_shells,
        }
