# -*- coding: utf-8 -*-
"""Resolve effective entry qualification without building a startup page.

Consumers may project navigation or inspect the authority. Personal display
preferences are applied after this result and cannot grant or revoke access.
No capability-list consumer or system.init handler is called here.
"""
from copy import deepcopy
from dataclasses import dataclass

from ..identity.identity_resolver import IdentityResolver
from ..utils.extension_hooks import call_extension_hook_first
from ..core.platform_duty_contract import build_platform_duty_surface, merge_platform_duty_route_authority
from ..core.platform_minimum_nav_contract import merge_authenticated_safe_landing
from .delivery_engine import DeliveryEngine
from .effective_delivery_inputs import _resolve_startup_delivery_identity, _load_platform_release_gate
from .published_scene_surface_service import PublishedSceneSurfaceService


@dataclass(frozen=True)
class EffectiveDeliveryResult:
    identity: dict
    role_surface: dict
    payload: dict
    release_gate: dict
    route_authority: dict


class EffectiveDeliveryService:
    def __init__(self, env):
        self.env = env

    @staticmethod
    def _scene_keys(nav, authority):
        scene_keys = set()
        def walk(nodes):
            for node in nodes:
                if node.get("allowed") is False or node.get("allowed_operation") == "none":
                    continue
                meta = node.get("meta") or {}
                target = node.get("entry_target") or {}
                key = node.get("scene_key") or meta.get("scene_key") or target.get("scene_key")
                if key:
                    scene_keys.add(str(key))
                walk(node.get("children") or [])
        walk(nav)
        for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
            walk(authority.get(bucket) or [])
        return scene_keys

    @staticmethod
    def _native_execution_surface(payload: dict) -> tuple[list, dict]:
        """Return installed/SEC-qualified native navigation and authority.

        Product publication does not re-authorize installed native actions.
        Business-scene composition is applied later by the P1 authority hook.
        """
        source = payload if isinstance(payload, dict) else {}
        nav = source.get("nav") if isinstance(source.get("nav"), list) else []
        authority = (
            source.get("route_authority")
            if isinstance(source.get("route_authority"), dict)
            else {}
        )
        return deepcopy(nav), deepcopy(authority)

    def _internal_actions(
        self,
        nav,
        authority,
        menu_service,
        role,
        *,
        request_context=None,
    ):
        sources = call_extension_hook_first(
            self.env,
            "smart_core_delivery_scene_declarations",
            self.env,
            request_context=request_context,
        )
        if not isinstance(sources, list):
            return []
        scene_keys = self._scene_keys(nav, authority)
        scene_keys.update(
            str(source.get("code") or source.get("key") or "").strip()
            for source in sources
            if isinstance(source, dict)
            and source.get("enablement_scope") == "enterprise_initialization"
        )
        scene_keys.discard("")
        from ..core.native_handling_entry_catalog import project_native_handling_catalog
        from ..core.scene_internal_action_authority import build_scene_internal_actions
        qualified = []
        for source in sources:
            key = str(source.get("code") or source.get("key") or "")
            if key not in scene_keys:
                continue
            native_catalog = project_native_handling_catalog(self.env, source)
            catalog = native_catalog if native_catalog is not None else source.get("handling_entry_catalog")
            if native_catalog is None and (not isinstance(catalog, dict) or not catalog.get("groups")):
                from ..core.scene_ready_contract_builder import _resolve_scene_provider_payload
                provider = _resolve_scene_provider_payload(key, {
                    "role_code": role.get("role_code"), "company_id": self.env.company.id,
                })
                catalog = provider.get("handling_entry_catalog")
            if not isinstance(catalog, dict):
                continue
            actions = build_scene_internal_actions(self.env, [{"code": key, "handling_entry_catalog": catalog}])
            for action in actions.values():
                entry = menu_service._route_entry_from_action_spec(action, route_kind="CONTEXTUAL_ROUTE")
                if entry:
                    entry.update(scene_key=key, item_key=action["item_key"], allowed=True,
                                 source="scene_internal_action_authority",
                                 decision_source="effective_delivery")
                    qualified.append(entry)
        return qualified

    def resolve(self, params=None, *, request_context=None):
        env = self.env
        identity = _resolve_startup_delivery_identity(env, {**dict(env.context or {}), **(params or {})})
        resolver = IdentityResolver(env)
        user_xmlids = resolver.user_group_xmlids(env.user)
        role = resolver.build_role_surface(user_xmlids, [], set())
        engine = DeliveryEngine(env)
        role = engine._runtime_role_surface({"role_surface": role})
        payload = engine.build(
            data={"role_surface": role},
            **{key: identity[key] for key in ("product_key", "base_product_key", "edition_key")},
            request_context=request_context,
        )
        gate = _load_platform_release_gate(env, product_key=payload["product_key"])
        # Native capability execution is installed/SEC/ACL authority. A
        # product release owns business-scenario composition, not a second
        # native capability allowlist; never convert a missing product page
        # record into a route-authority denial here.
        nav, authority = self._native_execution_surface(payload)
        duty = build_platform_duty_surface(
            is_platform_control_admin=bool(role.get("is_platform_admin")),
            is_tenant_config_admin=bool(role.get("is_tenant_config_admin")),
        )
        authority = merge_platform_duty_route_authority(authority, env=env, surface=duty)
        authority.setdefault("contextual_actions", []).extend(
            self._internal_actions(
                nav,
                authority,
                engine.menu_service,
                role,
                request_context=request_context,
            )
        )
        finalized = call_extension_hook_first(
            env,
            "smart_core_navigation_authority_filter",
            env,
            authority,
            request_context=request_context,
        )
        if isinstance(finalized, dict):
            authority = finalized
        authority = deepcopy(authority)
        authority.setdefault("principal_scope", {})["company_id"] = int(env.company.id)
        nav = engine.menu_service.filter_nav_by_route_authority(nav, authority)
        nav, authority = merge_authenticated_safe_landing(
            nav, authority, authenticated=bool(env.user) and not env.user._is_public(),
        )
        payload["nav"] = nav
        payload["route_authority"] = authority
        payload["scene_internal_actions"] = {
            f"{row['scene_key']}:{row['item_key']}": deepcopy(row)
            for row in authority.get("contextual_actions", [])
            if row.get("source") == "scene_internal_action_authority" and row.get("allowed") is True
        }
        from .runtime_route_authority import coalesce_effective_route_authority
        authority = coalesce_effective_route_authority(authority)
        payload["route_authority"] = authority
        published_scene_surface = PublishedSceneSurfaceService(env).build(
            payload,
            request_context=request_context,
        )
        payload.update(published_scene_surface)
        nav = payload["nav"]
        authority = payload["route_authority"]
        # Landing preference consumes the same final scene surface. It cannot
        # make an unpublished or unauthorized candidate executable.
        role = engine._runtime_role_surface({"role_surface": resolver.build_role_surface(
            user_xmlids, nav, self._scene_keys(nav, authority),
        )})
        payload.setdefault("meta", {})["platform_release_gate"] = {
            key: value for key, value in gate.items() if key != "allowed"
        }
        payload["meta"]["qualification_authority"] = "effective_delivery"
        return EffectiveDeliveryResult(identity, role, payload, gate, authority)
