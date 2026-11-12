"""Shared native delivery identity and release facts; independent of handlers."""
import json
import os
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.addons.smart_core.utils.backend_contract_boundaries import (
    MENU_CONFIG_CONFIG_ONLY_PARAM,
    MENU_CONFIG_NAV_ENABLED_PARAM,
    MENU_CONFIG_POLICY_MODEL,
    NAV_USER_DATA_ACCEPTANCE_ONLY_PARAM,
)
from odoo.addons.smart_core.core.platform_database_contract import (
    PlatformDatabaseContractError,
    resolve_platform_database,
)
from odoo.addons.smart_core.delivery.edition_release_snapshot_service import EditionReleaseSnapshotService
from odoo.addons.smart_core.delivery.product_identity import LEGACY_DEFAULT_BASE_PRODUCT_KEY
from odoo.addons.smart_core.utils.extension_hooks import call_extension_hook_first

def _resolve_user_acceptance_nav_contract(env) -> dict:
    hook_payload = call_extension_hook_first(env, "smart_core_user_data_acceptance_nav_contract", env)
    if isinstance(hook_payload, dict):
        return hook_payload
    return {}


def _string_set(value) -> set[str]:
    if isinstance(value, (list, tuple, set)):
        return {_text(item) for item in value if _text(item)}
    if isinstance(value, str) and value.strip():
        return {_text(value)}
    return set()


def _int_set(value) -> set[int]:
    values = value if isinstance(value, (list, tuple, set)) else [value]
    out = set()
    for item in values:
        try:
            parsed = int(item or 0)
        except Exception:
            parsed = 0
        if parsed > 0:
            out.add(parsed)
    return out


def _acceptance_surface_matchers(contract: dict | None) -> dict:
    contract = contract if isinstance(contract, dict) else {}
    tokens = set()
    for key in (
        "acceptance_surface_tokens",
        "old_acceptance_group_labels",
        "direct_acceptance_group_labels",
        "joint_acceptance_group_labels",
        "acceptance_root_labels",
    ):
        tokens.update(_string_set(contract.get(key)))
    return {
        "tokens": tokens,
        "menu_ids": _int_set(contract.get("acceptance_surface_menu_ids")),
        "action_ids": _int_set(contract.get("acceptance_surface_action_ids")),
    }


def _resolve_startup_delivery_identity(env, params: dict | None) -> dict:
    raw_params = params if isinstance(params, dict) else {}
    edition_key = str(
        raw_params.get("delivery_edition_key")
        or raw_params.get("edition_key")
        or "standard"
    ).strip() or "standard"
    explicit_product_key = str(
        raw_params.get("delivery_product_key")
        or raw_params.get("product_key")
        or ""
    ).strip()
    explicit_base_product_key = str(
        raw_params.get("delivery_base_product_key")
        or raw_params.get("base_product_key")
        or ""
    ).strip()
    hook_payload = None
    if not explicit_product_key and not explicit_base_product_key:
        hook_result = call_extension_hook_first(env, "smart_core_resolve_startup_delivery_identity", env, raw_params)
        hook_payload = hook_result if isinstance(hook_result, dict) else None
    if not (raw_params.get("delivery_edition_key") or raw_params.get("edition_key")):
        edition_key = str((hook_payload or {}).get("edition_key") or edition_key).strip() or edition_key
    source = "params" if (explicit_product_key or explicit_base_product_key) else "extension_hook" if hook_payload else "legacy_default"
    base_product_key = (
        explicit_base_product_key
        or str((hook_payload or {}).get("base_product_key") or LEGACY_DEFAULT_BASE_PRODUCT_KEY).strip()
        or LEGACY_DEFAULT_BASE_PRODUCT_KEY
    )
    product_key = explicit_product_key or str((hook_payload or {}).get("product_key") or f"{base_product_key}.{edition_key}").strip()
    if "." in product_key and not explicit_base_product_key:
        base_product_key = product_key.split(".", 1)[0] or base_product_key
    return {
        "product_key": product_key,
        "base_product_key": base_product_key,
        "edition_key": edition_key,
        "source": source,
        "projection_only": True,
        "no_business_fact_authority": True,
    }


def _text(value) -> str:
    return str(value or "").strip()


def _release_gate_page_contract_from_snapshot(snapshot: dict) -> dict:
    meta_json = snapshot.get("meta_json") if isinstance(snapshot.get("meta_json"), dict) else {}
    release_draft = meta_json.get("release_draft") if isinstance(meta_json.get("release_draft"), dict) else {}
    pages = release_draft.get("pages") if isinstance(release_draft.get("pages"), list) else []
    frozen = snapshot.get("snapshot_json") if isinstance(snapshot.get("snapshot_json"), dict) else {}
    if "policy_snapshot_schema" in frozen:
        if frozen["policy_snapshot_schema"] != "maintained_product_policy.v1":
            raise ValueError("PUBLISHED_PRODUCT_POLICY_SCHEMA_UNSUPPORTED")
        import hashlib
        policy = frozen.get("policy")
        if not isinstance(policy, dict) or policy.get("product_key") != snapshot.get("product_key"):
            raise ValueError("PUBLISHED_PRODUCT_POLICY_INVALID")
        digest = hashlib.sha256(json.dumps(policy, ensure_ascii=False, sort_keys=True, default=str,
                                           separators=(",", ":")).encode("utf-8")).hexdigest()
        if digest != frozen.get("policy_sha256"):
            raise ValueError("PUBLISHED_PRODUCT_POLICY_DIGEST_MISMATCH")
        if EditionReleaseSnapshotService._draft_fingerprint(policy=policy, pages=pages) != release_draft.get("fingerprint"):
            raise ValueError("PUBLISHED_PRODUCT_PAGES_FINGERPRINT_MISMATCH")
    allowed = {
        "page_keys": set(),
        "menu_keys": set(),
        "menu_xmlids": set(),
        "routes": set(),
        "models": set(),
        "menu_ids": set(),
        "action_ids": set(),
    }
    effective_count = 0
    release_states = {}
    for page in pages:
        if not isinstance(page, dict):
            continue
        enabled = bool(page.get("enabled", True))
        release_state = _text(page.get("release_state")) or ("released" if enabled else "hidden")
        if not enabled or release_state not in {"released", "preview"}:
            continue
        effective_count += 1
        if _text(page.get("menu_xmlid")):
            release_states[_text(page["menu_xmlid"])] = release_state
        for bucket, key in (
            ("page_keys", "page_key"),
            ("menu_keys", "menu_key"),
            ("menu_xmlids", "menu_xmlid"),
            ("routes", "route"),
            ("models", "res_model"),
        ):
            value = _text(page.get(key))
            if value:
                allowed[bucket].add(value)
        menu_id = int(page.get("menu_id") or 0)
        action_id = int(page.get("action_id") or 0)
        if menu_id:
            allowed["menu_ids"].add(f"system.menu_{menu_id}")
        if action_id:
            allowed["action_ids"].add(f"/a/{action_id}")
    return {
        "snapshot_id": int(snapshot.get("id") or 0),
        "version": _text(snapshot.get("version")),
        "product_key": _text(snapshot.get("product_key")),
        "page_count": effective_count,
        "total_page_count": len(pages),
        "menu_release_states": release_states,
        "fingerprint": _text(release_draft.get("fingerprint")),
        "allowed": allowed,
    }


def _load_platform_release_gate(env, *, product_key: str) -> dict:
    requested_product_key = _text(product_key)
    if not requested_product_key:
        return {}
    current_db = _text(getattr(getattr(env, "cr", None), "dbname", ""))
    production = os.environ.get("SC_ENVIRONMENT") == "production"
    try:
        platform_db = resolve_platform_database(env)
    except PlatformDatabaseContractError as exc:
        return {
            "applied": False,
            "fail_closed": production,
            "product_key": requested_product_key,
            "platform_db": "",
            "reason": _text(exc),
        }

    def _read_from(read_env) -> dict:
        try:
            model = read_env["sc.edition.release.snapshot"].sudo()
        except Exception:
            return {}
        snapshot = model.search(
            [
                ("product_key", "=", requested_product_key),
                ("state", "=", "released"),
                ("is_active", "=", True),
                ("active", "=", True),
            ],
            order="released_at desc, activated_at desc, id desc",
            limit=1,
        )
        return snapshot.to_runtime_dict() if snapshot else {}

    if platform_db == current_db:
        snapshot = _read_from(env)
    else:
        snapshot = {}
        try:
            registry = Registry(platform_db)
            with registry.cursor() as cr:
                read_env = api.Environment(cr, SUPERUSER_ID, dict(env.context or {}))
                snapshot = _read_from(read_env)
        except Exception as exc:
            return {
                "applied": False,
                "fail_closed": production,
                "product_key": requested_product_key,
                "platform_db": platform_db,
                "reason": "PLATFORM_RELEASE_DB_UNAVAILABLE",
                "error": _text(exc),
            }
    if not snapshot:
        return {
            "applied": False,
            "fail_closed": production,
            "product_key": requested_product_key,
            "platform_db": platform_db,
            "reason": "ACTIVE_RELEASE_SNAPSHOT_NOT_FOUND",
        }
    contract = _release_gate_page_contract_from_snapshot(snapshot)
    if int(contract.get("page_count") or 0) <= 0:
        return {
            "applied": False,
            "fail_closed": production,
            "product_key": requested_product_key,
            "platform_db": platform_db,
            "reason": "ACTIVE_RELEASE_HAS_NO_PAGES",
            "snapshot_id": contract.get("snapshot_id"),
            "version": contract.get("version"),
        }
    contract["applied"] = True
    contract["platform_db"] = platform_db
    contract["reason"] = "OK"
    return contract


def _node_release_gate_keys(node: dict) -> set[str]:
    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    entry_target = meta.get("entry_target") if isinstance(meta.get("entry_target"), dict) else {}
    compatibility_refs = entry_target.get("compatibility_refs") if isinstance(entry_target.get("compatibility_refs"), dict) else {}
    values = {
        _text(node.get("key")),
        _text(node.get("route")),
        _text(node.get("scene_key")),
        _text(node.get("menu_xmlid")),
        _text(node.get("model")),
        _text(meta.get("route")),
        _text(meta.get("scene_key")),
        _text(meta.get("menu_key")),
        _text(meta.get("menu_xmlid")),
        _text(meta.get("model")),
        _text(entry_target.get("route")),
        _text(entry_target.get("scene_key")),
        _text(compatibility_refs.get("model")),
    }
    menu_id = node.get("menu_id") or meta.get("menu_id") or compatibility_refs.get("menu_id")
    action_id = meta.get("action_id") or compatibility_refs.get("action_id")
    if menu_id:
        values.add(f"system.menu_{menu_id}")
    if action_id:
        values.add(f"/a/{action_id}")
    for option in meta.get("business_category_options") or []:
        if not isinstance(option, dict):
            continue
        option_menu_xmlid = _text(option.get("menu_xmlid"))
        if option_menu_xmlid:
            values.add(option_menu_xmlid)
        option_menu_id = option.get("menu_id")
        if option_menu_id:
            values.add(f"system.menu_{option_menu_id}")
    return {item for item in values if item}


def _node_is_user_acceptance_surface(node: dict, *, acceptance_matchers: dict | None = None) -> bool:
    matchers = acceptance_matchers if isinstance(acceptance_matchers, dict) else {}
    surface_tokens = matchers.get("tokens") if isinstance(matchers.get("tokens"), set) else set()
    surface_menu_ids = matchers.get("menu_ids") if isinstance(matchers.get("menu_ids"), set) else set()
    surface_action_ids = matchers.get("action_ids") if isinstance(matchers.get("action_ids"), set) else set()
    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    entry_target = meta.get("entry_target") if isinstance(meta.get("entry_target"), dict) else {}
    compatibility_refs = entry_target.get("compatibility_refs") if isinstance(entry_target.get("compatibility_refs"), dict) else {}
    menu_id = node.get("menu_id") or meta.get("menu_id") or compatibility_refs.get("menu_id")
    action_id = meta.get("action_id") or compatibility_refs.get("action_id")
    try:
        normalized_menu_id = int(menu_id or 0)
    except Exception:
        normalized_menu_id = 0
    try:
        normalized_action_id = int(action_id or 0)
    except Exception:
        normalized_action_id = 0
    if normalized_menu_id in surface_menu_ids or normalized_action_id in surface_action_ids:
        return True
    text = "/".join(
        _text(value)
        for value in (
            node.get("key"),
            node.get("name"),
            node.get("label"),
            node.get("title"),
            node.get("path"),
            node.get("complete_name"),
            node.get("menu_xmlid"),
            node.get("model"),
            meta.get("menu_xmlid"),
            meta.get("model"),
            compatibility_refs.get("model"),
        )
        if _text(value)
    )
    if surface_tokens and any(token in text for token in surface_tokens):
        return True
    return False


def _runtime_business_config_productization_sources(env) -> set[str]:
    payload = call_extension_hook_first(env, "smart_core_runtime_business_config_productization_sources", env)
    if not isinstance(payload, (list, tuple, set)):
        return set()
    return {_text(item) for item in payload if _text(item)}


def _runtime_business_config_protected_menu_refs(env) -> dict:
    refs = {"menu_ids": set(), "menu_xmlids": set()}
    if env is None:
        return refs
    try:
        from odoo.addons.smart_core.model.ui_menu_config_policy import _lowcode_system_config_menu_xmlids

        xmlids = {_text(xmlid) for xmlid in _lowcode_system_config_menu_xmlids(env) if _text(xmlid)}
    except Exception:
        xmlids = set()
    refs["menu_xmlids"] = xmlids
    if not xmlids:
        return refs
    try:
        ModelData = env["ir.model.data"].sudo()
        modules = {xmlid.split(".", 1)[0] for xmlid in xmlids if "." in xmlid}
        names = {xmlid.split(".", 1)[1] for xmlid in xmlids if "." in xmlid}
        rows = ModelData.search([
            ("model", "=", "ir.ui.menu"),
            ("module", "in", list(modules)),
            ("name", "in", list(names)),
        ])
    except Exception:
        rows = []
    for row in rows or []:
        xmlid = "%s.%s" % (_text(getattr(row, "module", "")), _text(getattr(row, "name", "")))
        try:
            menu_id = int(getattr(row, "res_id", 0) or 0)
        except Exception:
            menu_id = 0
        if xmlid in xmlids and menu_id:
            refs["menu_ids"].add(menu_id)
    return refs


def _node_is_protected_runtime_business_config_menu(node: dict, protected_refs: dict | None = None) -> bool:
    if not isinstance(protected_refs, dict):
        return False
    protected_menu_ids = protected_refs.get("menu_ids") if isinstance(protected_refs.get("menu_ids"), set) else set()
    protected_xmlids = protected_refs.get("menu_xmlids") if isinstance(protected_refs.get("menu_xmlids"), set) else set()
    if not protected_menu_ids and not protected_xmlids:
        return False
    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    entry_target = meta.get("entry_target") if isinstance(meta.get("entry_target"), dict) else {}
    compatibility_refs = entry_target.get("compatibility_refs") if isinstance(entry_target.get("compatibility_refs"), dict) else {}
    menu_id = node.get("menu_id") or meta.get("menu_id") or compatibility_refs.get("menu_id")
    try:
        normalized_menu_id = int(menu_id or 0)
    except Exception:
        normalized_menu_id = 0
    if normalized_menu_id and normalized_menu_id in protected_menu_ids:
        return True
    xmlid = _text(node.get("menu_xmlid") or meta.get("menu_xmlid") or compatibility_refs.get("menu_xmlid"))
    return bool(xmlid and xmlid in protected_xmlids)


def _node_is_runtime_business_config_entry(
    node: dict,
    *,
    env=None,
    productization_sources: set[str] | None = None,
    protected_menu_refs: dict | None = None,
    acceptance_matchers: dict | None = None,
) -> bool:
    """Keep already-authorized runtime configuration entries available."""
    if _node_is_user_acceptance_surface(node, acceptance_matchers=acceptance_matchers):
        return False
    if _node_is_protected_runtime_business_config_menu(node, protected_refs=protected_menu_refs):
        return True
    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    productization_source = _text(meta.get("productization_source"))
    sources = productization_sources if isinstance(productization_sources, set) else _runtime_business_config_productization_sources(env)
    if productization_source and productization_source in sources:
        return True
    if _text(node.get("delivery_bucket")) == "delivery_business_config":
        return True
    if _text(meta.get("delivery_bucket")) == "delivery_business_config":
        return True
    model = _text(node.get("model") or meta.get("model"))
    if model in {MENU_CONFIG_POLICY_MODEL}:
        return True
    return False


def _filter_nav_by_release_gate(nav: list[dict], gate: dict, *, env=None) -> tuple[list[dict], dict]:
    if not isinstance(nav, list) or not gate.get("applied"):
        return nav if isinstance(nav, list) else [], {"applied": False}
    allowed = gate.get("allowed") if isinstance(gate.get("allowed"), dict) else {}
    allowed_values = set()
    for bucket in ("page_keys", "menu_keys", "menu_xmlids", "routes", "menu_ids", "action_ids"):
        values = allowed.get(bucket)
        if isinstance(values, set):
            allowed_values.update(values)
        elif isinstance(values, list):
            allowed_values.update(_text(item) for item in values if _text(item))
    kept_leaf_count = 0
    removed_leaf_count = 0
    runtime_business_config_count = 0
    runtime_business_config_sources = _runtime_business_config_productization_sources(env)
    protected_menu_refs = _runtime_business_config_protected_menu_refs(env)
    acceptance_matchers = _acceptance_surface_matchers(_resolve_user_acceptance_nav_contract(env))

    def _node_has_entry_target(node: dict) -> bool:
        meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
        entry_target = meta.get("entry_target") if isinstance(meta.get("entry_target"), dict) else {}
        route = _text(node.get("route") or meta.get("route") or entry_target.get("route"))
        target_type = _text(entry_target.get("type"))
        return bool(
            node.get("action_id")
            or meta.get("action_id")
            or node.get("scene_key")
            or meta.get("scene_key")
            or entry_target.get("scene_key")
            or node.get("model")
            or meta.get("model")
            or target_type == "scene"
            or (route and not route.startswith("/m/"))
        )

    def _filter_node(node: dict):
        nonlocal kept_leaf_count, removed_leaf_count, runtime_business_config_count
        if not isinstance(node, dict):
            return None
        if _node_is_user_acceptance_surface(node, acceptance_matchers=acceptance_matchers):
            removed_leaf_count += 1
            return None
        children = node.get("children") if isinstance(node.get("children"), list) else []
        next_node = dict(node)
        runtime_business_config_entry = _node_is_runtime_business_config_entry(
            node,
            env=env,
            productization_sources=runtime_business_config_sources,
            protected_menu_refs=protected_menu_refs,
            acceptance_matchers=acceptance_matchers,
        )
        released_entry = bool(_node_release_gate_keys(node) & allowed_values)
        if children:
            next_children = []
            for child in children:
                filtered = _filter_node(child)
                if filtered:
                    next_children.append(filtered)
            if next_children:
                next_node["children"] = next_children
                return next_node
            # A released product entry may also be a tree parent. If every
            # child is filtered out, preserve the parent's own executable
            # target as a leaf instead of silently deleting a released page.
            if _node_has_entry_target(node) and (runtime_business_config_entry or released_entry):
                next_node["children"] = []
                kept_leaf_count += 1
                if runtime_business_config_entry:
                    runtime_business_config_count += 1
                return next_node
            if _node_has_entry_target(node):
                removed_leaf_count += 1
            return None

        if runtime_business_config_entry:
            kept_leaf_count += 1
            runtime_business_config_count += 1
            return next_node
        if released_entry:
            kept_leaf_count += 1
            return next_node
        removed_leaf_count += 1
        return None

    filtered = [_filter_node(node) for node in nav]
    filtered = [node for node in filtered if node]
    return filtered, {
        "applied": True,
        "product_key": _text(gate.get("product_key")),
        "platform_db": _text(gate.get("platform_db")),
        "snapshot_id": int(gate.get("snapshot_id") or 0),
        "snapshot_version": _text(gate.get("version")),
        "fingerprint": _text(gate.get("fingerprint")),
        "allowed_page_count": int(gate.get("page_count") or 0),
        "kept_leaf_count": kept_leaf_count,
        "removed_leaf_count": removed_leaf_count,
        "runtime_business_config_passthrough_count": runtime_business_config_count,
    }
