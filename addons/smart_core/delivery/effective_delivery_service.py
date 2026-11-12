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
from ..core.platform_minimum_nav_contract import is_platform_minimum_surface_mode, build_platform_minimum_nav_contract
from .delivery_engine import DeliveryEngine
from .effective_delivery_inputs import _resolve_startup_delivery_identity, _load_platform_release_gate, _filter_nav_by_release_gate


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

    def _internal_actions(self, nav, authority, menu_service, role):
        sources = call_extension_hook_first(self.env, "smart_core_delivery_scene_declarations", self.env)
        if not isinstance(sources, list):
            return []
        scene_keys = set()
        def walk(nodes):
            for node in nodes:
                meta = node.get("meta") or {}
                target = node.get("entry_target") or meta.get("entry_target") or {}
                key = node.get("scene_key") or meta.get("scene_key") or target.get("scene_key")
                if key:
                    scene_keys.add(str(key))
                walk(node.get("children") or [])
        walk(nav)
        for bucket in ("primary_actions", "role_home_actions", "contextual_actions", "admin_actions"):
            walk(authority.get(bucket) or [])
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

    def resolve(self, params=None):
        env = self.env
        identity = _resolve_startup_delivery_identity(env, {**dict(env.context or {}), **(params or {})})
        resolver = IdentityResolver(env)
        role = resolver.build_role_surface(resolver.user_group_xmlids(env.user), [], {"workspace.home"})
        engine = DeliveryEngine(env)
        role = engine._runtime_role_surface({"role_surface": role})
        payload = engine.build(
            data={"role_surface": role},
            **{key: identity[key] for key in ("product_key", "base_product_key", "edition_key")},
        )
        if is_platform_minimum_surface_mode(env, delivery_identity=identity) or not payload["nav"]:
            payload["nav"] = build_platform_minimum_nav_contract()["nav"]
            payload["route_authority"] = engine.menu_service.build_route_authority(role, nav=payload["nav"])
        gate = _load_platform_release_gate(env, product_key=payload["product_key"])

        def released(nodes):
            if gate.get("fail_closed"):
                return []
            return _filter_nav_by_release_gate(nodes, gate, env=env)[0]

        nav = released(payload["nav"])
        authority = engine.menu_service.filter_route_authority_by_publication(
            payload["route_authority"], filter_nodes=released,
        )
        duty = build_platform_duty_surface(
            is_platform_control_admin=bool(role.get("is_platform_admin")),
            is_tenant_config_admin=bool(role.get("is_tenant_config_admin")),
        )
        authority = merge_platform_duty_route_authority(authority, env=env, surface=duty)
        authority.setdefault("contextual_actions", []).extend(self._internal_actions(nav, authority, engine.menu_service, role))
        finalized = call_extension_hook_first(env, "smart_core_navigation_authority_filter", env, authority)
        if isinstance(finalized, dict):
            authority = finalized
        authority = deepcopy(authority)
        authority.setdefault("principal_scope", {})["company_id"] = int(env.company.id)
        payload["nav"] = engine.menu_service.filter_nav_by_route_authority(nav, authority)
        payload["route_authority"] = authority
        payload["scene_internal_actions"] = {
            f"{row['scene_key']}:{row['item_key']}": deepcopy(row)
            for row in authority.get("contextual_actions", [])
            if row.get("source") == "scene_internal_action_authority" and row.get("allowed") is True
        }
        payload.setdefault("meta", {})["platform_release_gate"] = {
            key: value for key, value in gate.items() if key != "allowed"
        }
        payload["meta"]["qualification_authority"] = "effective_delivery"
        return EffectiveDeliveryResult(identity, role, payload, gate, authority)
