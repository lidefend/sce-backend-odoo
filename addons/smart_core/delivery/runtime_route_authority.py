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

from weakref import WeakKeyDictionary

ROUTE_AUTHORITY_BUCKETS = (
    "primary_actions",
    "role_home_actions",
    "contextual_actions",
    "admin_actions",
)


_GROUP_XMLID_REQUEST_MEMO: "WeakKeyDictionary[object, dict]" = WeakKeyDictionary()


def _request_cached_user_group_xmlids(env) -> set:
    """Resolve the principal's effective group xmlids once per request.

    The memo is keyed by the cursor object, which is scoped to one request
    transaction. A pooled cursor reused for a different principal or a changed
    group-id set recomputes instead of reusing a stale snapshot; the entry is
    released with the cursor object, so no identity ever crosses an HTTP
    request. The returned value is identical to
    ``IdentityResolver.user_group_xmlids`` for the same principal, so the
    ``published_route_authority`` cache-key semantics are unchanged.
    """
    from ..identity.identity_resolver import IdentityResolver

    user = env.user
    if user is None:
        return set()
    memo = _GROUP_XMLID_REQUEST_MEMO.get(env.cr)
    if memo is None:
        memo = {}
        _GROUP_XMLID_REQUEST_MEMO[env.cr] = memo
    uid = int(user.id)
    group_ids = tuple(sorted(int(group_id) for group_id in (user.groups_id.ids or ())))
    key = (uid, group_ids)
    cached = memo.get(key)
    if cached is not None and cached[0] == group_ids:
        return cached[1]
    xmlids = IdentityResolver(env).user_group_xmlids(user)
    memo[key] = (group_ids, xmlids)
    return xmlids


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


def coalesce_effective_route_authority(authority: dict) -> dict:
    """One route per native target and execution meaning after tenant selection.

    Multiple scene references are provenance, not ambiguous execution. Different
    context requirements or native execution payloads remain separate so direct
    validation can still reject a genuinely ambiguous request.
    """
    from copy import deepcopy
    import json

    result = deepcopy(authority)
    seen = {}
    for bucket in ROUTE_AUTHORITY_BUCKETS:
        kept = []
        for row in result.get(bucket) or []:
            menu_id, action_id = _positive_int(row.get("menu_id")), _positive_int(row.get("action_id"))
            if not action_id:
                kept.append(row)
                continue
            meaning = [menu_id, action_id, row.get("model") or "",
                       row.get("allowed_operation") or "read", row.get("context_requirements") or {},
                       row.get("domain") or "[]", row.get("context") or "{}",
                       row.get("entry_target") or {}, row.get("delivery_scope") or ""]
            key = json.dumps(meaning, sort_keys=True, ensure_ascii=False, default=str)
            reference = {"scene_key": row.get("scene_key"), "item_key": row.get("item_key")}
            existing = seen.get(key)
            if existing is None:
                seen[key] = row
                kept.append(row)
                existing = row
            # Contextual admission also permits an action-only URL. Preserve
            # that existing grant when the same pair occupies primary nav.
            if row.get("route_kind") == "CONTEXTUAL_ROUTE":
                existing["route_kind"] = "CONTEXTUAL_ROUTE"
            if reference["scene_key"]:
                references = existing.setdefault("scene_references", [])
                if reference not in references:
                    references.append(reference)
        result[bucket] = kept
    # A contextual representative must also satisfy the client's strict bucket
    # schema. Moving it retains primary navigation by the same native pair.
    buckets = {bucket: [] for bucket in ROUTE_AUTHORITY_BUCKETS}
    for bucket in ROUTE_AUTHORITY_BUCKETS:
        for row in result.get(bucket) or []:
            target = "contextual_actions" if row.get("route_kind") == "CONTEXTUAL_ROUTE" else bucket
            buckets[target].append(row)
    result.update(buckets)
    return result


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
    """Stable signature of native group IDs and their XMLID projection.

    Effective groups include implied groups, which this Odoo build does not
    signal through ``registry.clear_cache()`` on their own writes. Binding the
    signature into the cache key keeps the cached authority from outliving a
    group-membership or implied-group change. Never raises: an unavailable
    signature is an empty string, and the caller keeps the declared cache.
    """
    try:
        import hashlib

        xmlids = _request_cached_user_group_xmlids(env)
        # Native groups without XMLIDs still change ACL/action reachability.
        group_ids = sorted(int(value) for value in env.user.groups_id.ids)
        joined = repr((group_ids, sorted(str(item) for item in (xmlids or ()) if item)))
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
        policy = env["sc.product.policy"]
        try:
            authority = policy.published_route_authority()
        except Exception:
            authority = _build_runtime_route_authority(env)
        return authority
    except Exception:
        return {}


def build_runtime_route_authority(env) -> dict:
    """Public entrypoint returning the current principal's route authority."""
    return published_route_authority(env)


def _build_runtime_route_authority(env) -> dict:
    """Read the same effective qualification used by startup navigation."""
    # Let the outer consumer fail closed. An exception must not become an
    # apparently valid empty result stored by the principal's ormcache.
    from .effective_delivery_service import EffectiveDeliveryService
    return EffectiveDeliveryService(env).resolve(dict(env.context or {})).route_authority
