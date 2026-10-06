# -*- coding: utf-8 -*-
"""Published route authority: the single effective-policy navigation authority.

``handlers/system_init.py`` fixes the product baseline: one navigation contract
owns both the rendered tree and its route authority, so the client never
receives a menu that the server would then deny. Every consumer that decides
whether a published entry may be opened -- the intent permission gate and the
``route.authority.validate`` intent -- must consume this same authority.

``.agent/decisions/contract-first.yaml`` forbids deriving release authorization
from action declarations or native menu existence/visibility, so native
``ir.ui.menu`` facts are resolved only inside the delivery builder below and
never re-used by callers as a publication answer.
"""
from __future__ import annotations

ROUTE_AUTHORITY_BUCKETS = (
    "primary_actions",
    "role_home_actions",
    "contextual_actions",
    "admin_actions",
)


def _positive_int(value) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def iter_published_pairs(authority: dict):
    """Published ``(menu_id, action_id)`` route pairs in bucket order.

    Yields the same pairs as :func:`published_pairs` but keeps the authority's
    own bucket order, so a consumer that must pick one published entry per
    target model resolves it deterministically from the publication surface.
    """
    if not isinstance(authority, dict):
        return
    for bucket in ROUTE_AUTHORITY_BUCKETS:
        for row in authority.get(bucket) or []:
            if isinstance(row, dict):
                yield (_positive_int(row.get("menu_id")), _positive_int(row.get("action_id")))


def published_pairs(authority: dict) -> set:
    """Published ``(menu_id, action_id)`` route pairs, carriers included."""
    return set(iter_published_pairs(authority))


def published_menu_ids(authority: dict) -> set:
    """Published menu carriers: action entries plus authorised containers."""
    menu_ids = {menu_id for menu_id, _action_id in published_pairs(authority) if menu_id}
    if isinstance(authority, dict):
        for row in authority.get("menu_containers") or []:
            if isinstance(row, dict):
                menu_id = _positive_int(row.get("menu_id"))
                if menu_id:
                    menu_ids.add(menu_id)
    return menu_ids


def menu_publication_decision(authority: dict, menu_id, action_id=0):
    """Whether the published navigation authorizes a menu carrier.

    ``True``/``False`` when the authority decides; ``None`` when it could not be
    established, so callers fail closed instead of falling back to native menu
    visibility.
    """
    if not isinstance(authority, dict) or not authority:
        return None
    target_menu_id = _positive_int(menu_id)
    if not target_menu_id:
        return False
    target_action_id = _positive_int(action_id)
    if target_action_id:
        return (target_menu_id, target_action_id) in published_pairs(authority)
    return target_menu_id in published_menu_ids(authority)


def principal_group_signature(env) -> str:
    """Stable signature of the principal's effective group xmlids.

    Effective groups include implied groups, which this Odoo build does not
    signal through ``registry.clear_cache()`` on their own writes. Binding the
    signature into the cache key keeps the cached authority from outliving a
    group-membership or implied-group change. Never raises: an unavailable
    signature is an empty string, and the caller keeps the declared cache.
    """
    try:
        import hashlib

        from ..identity.identity_resolver import IdentityResolver

        xmlids = IdentityResolver(env).user_group_xmlids(env.user)
        joined = "\n".join(sorted(str(item) for item in (xmlids or ()) if item))
        return hashlib.sha1(joined.encode("utf-8")).hexdigest()
    except Exception:
        return ""


def published_route_authority(env) -> dict:
    """Effective published route authority, cached per principal and revision.

    The startup navigation authority is rebuilt only when the principal's
    identity or an input that clears Odoo's default cache bucket changes
    (menus, actions, xmlids, rules, users) or when the smart_core publication
    models signal a change. Any failure keeps the caller fail-closed.
    """
    try:
        return env["sc.product.policy"].published_route_authority()
    except Exception:
        return _build_runtime_route_authority(env)


def build_runtime_route_authority(env) -> dict:
    """Public entrypoint returning the current principal's route authority."""
    return published_route_authority(env)


def _build_runtime_route_authority(env) -> dict:
    """Build the current principal's publication-filtered route authority.

    Mirrors the startup navigation authority: identity -> product policy ->
    platform release gate -> delivery navigation -> publication-filtered route
    authority. Returns ``{}`` when it cannot be established so callers fail
    closed rather than inferring publication from native menus.
    """
    try:
        from ..handlers.system_init import (
            _filter_nav_by_release_gate,
            _load_platform_release_gate,
            _resolve_startup_delivery_identity,
        )
        from ..identity.identity_resolver import IdentityResolver
        from .delivery_engine import DeliveryEngine
        from .menu_service import MenuService
        from .product_policy_service import ProductPolicyService

        resolver = IdentityResolver(env)
        surface = resolver.build_role_surface(
            resolver.user_group_xmlids(env.user), [], {"workspace.home"}
        )
        identity = _resolve_startup_delivery_identity(env, {})
        policy = ProductPolicyService(env).get_policy(
            **{key: identity[key] for key in ("product_key", "base_product_key", "edition_key")},
            role_code=surface.get("role_code"),
            enforce_release=True,
            enforce_access=True,
        )
        release_gate = _load_platform_release_gate(env, product_key=policy["product_key"])
        menu_service = MenuService(env)
        navigation = menu_service.build_nav(policy=policy, role_surface=surface)
        navigation = DeliveryEngine(env)._normalize_delivery_nav_refs(navigation)
        navigation = [] if release_gate.get("fail_closed") else _filter_nav_by_release_gate(
            navigation, release_gate, env=env
        )[0]
        authority = menu_service.build_route_authority(surface, nav=navigation)
        authority = MenuService.filter_route_authority_by_publication(
            authority,
            filter_nodes=lambda nodes: [] if release_gate.get("fail_closed") else
                _filter_nav_by_release_gate(nodes, release_gate, env=env)[0],
        )
        return authority if isinstance(authority, dict) else {}
    except Exception:
        return {}
