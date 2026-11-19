# -*- coding: utf-8 -*-
"""Read-only Odoo-native Platform Capability Explorer projection."""
from __future__ import annotations

import hashlib
import importlib
import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from .platform_catalog_action_contract import add_catalog_entry_action_contract

PROJECTION_VERSION = "platform.capability.explorer.projection.v1"
LIST_SCHEMA = "platform.capability.explorer.list.v1"
DETAIL_SCHEMA = "platform.capability.explorer.detail.v1"
DIAGNOSE_SCHEMA = "platform.capability.explorer.diagnose.v1"

SUPPORTED_ACTION_TYPES = {
    "ir.actions.act_window",
    "ir.actions.client",
    "ir.actions.server",
    "ir.actions.report",
    "ir.actions.act_url",
}
INSTALLED_MODULE_STATES = {"installed", "to upgrade", "to remove"}
CLASSIFICATION_CONFIDENCES = {
    "authoritative_scene_binding",
    "center_only",
    "unclassified",
}
SCENE_STATUSES = {"bound", "unbound"}
CATALOG_SCOPES = {"platform", "product"}

ALLOWED_SORT_FIELDS = {
    "center_sequence",
    "label",
    "menu_sequence",
    "menu_xmlid",
    "action_xmlid",
    "module",
    "scene_status",
    "release_state",
    "business_domain_key",
}
DEFAULT_SORT = (
    ("center_sequence", "asc"),
    ("label", "asc"),
    ("menu_xmlid", "asc"),
    ("action_xmlid", "asc"),
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value or default)
    except Exception:
        return default


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def classify_business_domain(
    *,
    scene_bindings: list[dict[str, Any]] | None,
    center_key: str = "",
    center_source: str = "",
) -> dict[str, Any]:
    """Classify only from active product-scene bindings.

    A native or release center is a browse aid, never a business-domain guess.
    """
    candidates_by_key: dict[str, dict[str, Any]] = {}
    for binding in scene_bindings or []:
        binding = _dict(binding)
        if binding.get("scenario_active", True) is False:
            continue
        key = _text(binding.get("scenario_key"))
        if not key:
            continue
        candidates_by_key.setdefault(
            key,
            {
                "key": key,
                "label": _text(binding.get("scenario_name")) or key,
            },
        )
    candidates = [candidates_by_key[key] for key in sorted(candidates_by_key)]
    if len(candidates) == 1:
        candidate = candidates[0]
        return {
            "key": candidate["key"],
            "label": candidate["label"],
            "source": "sc.product.scenario.entry",
            "confidence": "authoritative_scene_binding",
            "reason_code": "",
            "candidates": candidates,
        }
    if len(candidates) > 1:
        return {
            "key": "",
            "label": "",
            "source": "sc.product.scenario.entry",
            "confidence": "unclassified",
            "reason_code": "AMBIGUOUS_SCENE_BINDING",
            "candidates": candidates,
        }
    center = _text(center_key)
    center_source = _text(center_source)
    return {
        "key": "",
        "label": "",
        "source": (
            "native_center_only"
            if center and center_source == "ir.ui.menu"
            else "release_center_only"
            if center
            else ""
        ),
        "confidence": "center_only" if center else "unclassified",
        "reason_code": "NO_SCENE_BINDING" if center else "NO_CLASSIFICATION_EVIDENCE",
        "candidates": [],
    }


def native_selection_assessment(
    *,
    menu_xmlid: Any,
    action_xmlid: Any,
    action_type: Any,
    res_model: Any,
    module_state: Any,
    action_exists: bool,
    menu_action_matches: bool,
    model_exists: bool,
) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    if not _text(menu_xmlid):
        blockers.append("MENU_XMLID_MISSING")
    if not _text(action_xmlid):
        blockers.append("ACTION_XMLID_MISSING")
    if _text(module_state) not in INSTALLED_MODULE_STATES:
        blockers.append("MODULE_NOT_INSTALLED")
    if not action_exists:
        blockers.append("ACTION_NOT_FOUND")
    elif _text(action_type) not in SUPPORTED_ACTION_TYPES:
        blockers.append("ACTION_TYPE_UNSUPPORTED")
    if not menu_action_matches:
        blockers.append("MENU_ACTION_MISMATCH")
    if _text(action_type) == "ir.actions.act_window":
        if not _text(res_model):
            blockers.append("WINDOW_ACTION_MODEL_MISSING")
        elif not model_exists:
            blockers.append("MODEL_NOT_FOUND")
    return not blockers, blockers


def access_layer_assessment(
    *,
    native_present: bool,
    native_blockers: list[str],
    consumer_supported: bool,
    entry_group_ids: list[int] | None = None,
    held_group_ids: list[int],
    acl_rows: list[dict[str, Any]],
    standard_qualified: str,
    enterprise_enablement: dict[str, Any],
    menu_group_ids: list[int] | None = None,
    action_group_ids: list[int] | None = None,
    menu_groups_allowed: bool | None = None,
    action_groups_allowed: bool | None = None,
) -> dict[str, Any]:
    """Explain access from independent facts without inventing a grant.

    The ACL check proves model access rows available to the current principal.
    Record-level visibility still executes in Odoo at query time.
    """
    held = {_int(value) for value in held_group_ids if _int(value) > 0}
    legacy_required = {
        _int(value) for value in (entry_group_ids or []) if _int(value) > 0
    }
    menu_required = {
        _int(value) for value in (menu_group_ids or []) if _int(value) > 0
    }
    action_required = {
        _int(value) for value in (action_group_ids or []) if _int(value) > 0
    }
    required = menu_required | action_required | legacy_required
    menu_allowed = (
        bool(menu_groups_allowed)
        if menu_groups_allowed is not None
        else not menu_required or bool(menu_required & held)
    )
    action_allowed = (
        bool(action_groups_allowed)
        if action_groups_allowed is not None
        else not action_required or bool(action_required & held)
    )
    # Odoo menu groups are an OR set and action groups are a separate OR set.
    # The two independent layers must both authorize the entry. The legacy
    # entry_group_ids value is diagnostic only when callers provide neither
    # layered group set; it must never collapse menu and action restrictions.
    entry_allowed = (
        menu_allowed and action_allowed
        if menu_group_ids is not None or action_group_ids is not None
        or menu_groups_allowed is not None or action_groups_allowed is not None
        else legacy_required.issubset(held)
    )
    read_row_found = False
    read_allowed = False
    for row in acl_rows:
        if not isinstance(row, dict) or not bool(row.get("read")):
            continue
        read_row_found = True
        group_id = _int(row.get("group_id"))
        if group_id <= 0 or group_id in held:
            read_allowed = True
            break
    enterprise = _dict(enterprise_enablement)
    enterprise_status = (
        _text(enterprise.get("status"))
        or ("enabled" if enterprise.get("enabled") is True else "not_applicable")
    )
    blockers = list(native_blockers)
    if not native_present:
        blockers.append("NATIVE_ENTRY_NOT_READY")
    if not consumer_supported:
        blockers.append("CONSUMER_SURFACE_UNSUPPORTED")
    if standard_qualified != "qualified":
        blockers.append(
            "PRODUCT_QUALIFICATION_NOT_VERIFIED"
            if standard_qualified == "not_verified"
            else "PRODUCT_NOT_QUALIFIED"
        )
    if enterprise_status == "disabled":
        blockers.append("ENTERPRISE_SCENARIO_NOT_ENABLED")
    if not entry_allowed:
        blockers.append("ENTRY_GROUP_DENIED")
    if not read_row_found:
        blockers.append("MODEL_READ_ACL_MISSING")
    elif not read_allowed:
        blockers.append("MODEL_READ_ACL_DENIED")
    blockers = list(dict.fromkeys(blockers))
    return {
        "entry_groups_allowed": entry_allowed,
        "menu_groups_allowed": menu_allowed,
        "action_groups_allowed": action_allowed,
        "menu_group_ids": sorted(menu_required),
        "action_group_ids": sorted(action_required),
        "required_group_ids": sorted(required),
        "held_group_ids": sorted(held),
        "model_read_acl_present": read_row_found,
        "model_read_allowed": read_allowed,
        "record_scope": "runtime_acl_and_record_rules",
        "reason_code": blockers[0] if blockers else "CURRENT_USER_ENTRY_AVAILABLE",
        "blockers": blockers,
    }


class PlatformCapabilityExplorerError(ValueError):
    code = "CAPABILITY_EXPLORER_ERROR"
    http_status = 400


class CatalogStaleError(PlatformCapabilityExplorerError):
    code = "CATALOG_STALE"
    http_status = 409


class CapabilityEntryNotFound(PlatformCapabilityExplorerError):
    code = "CAPABILITY_ENTRY_NOT_FOUND"
    http_status = 404


class InvalidExplorerRequest(PlatformCapabilityExplorerError):
    code = "INVALID_REQUEST"
    http_status = 400


class CatalogScopeDenied(PlatformCapabilityExplorerError):
    code = "CATALOG_SCOPE_DENIED"
    http_status = 403


@dataclass(frozen=True)
class CatalogProjection:
    meta: dict[str, Any]
    rows: list[dict[str, Any]]
    details: dict[tuple[str, str], dict[str, Any]]
    diagnostics: dict[str, Any]

    @property
    def token(self) -> str:
        return _text(self.meta.get("catalog_token"))


def _external_id_map(
    env,
    model_name: str,
    record_ids: list[int],
    ambiguities: dict[str, dict[str, Any]] | None = None,
) -> dict[int, str]:
    ids = sorted({_int(value) for value in record_ids if _int(value) > 0})
    if not ids:
        return {}
    rows = env["ir.model.data"].sudo().search(
        [("model", "=", model_name), ("res_id", "in", ids)],
        order="res_id, module, name, id",
    )
    values_by_id = defaultdict(set)
    for row in rows:
        if row.module and row.name:
            values_by_id[int(row.res_id)].add(f"{row.module}.{row.name}")
    result = {}
    for res_id, xmlids in values_by_id.items():
        ordered = sorted(xmlids)
        if len(ordered) == 1:
            result[res_id] = ordered[0]
            continue
        if ambiguities is not None:
            ambiguities[f"{model_name}:{res_id}"] = {
                "model": model_name,
                "res_id": res_id,
                "xmlids": ordered,
            }
    return result


def _group_xmlids(groups, group_xmlids: dict[int, str]) -> list[str]:
    return sorted(
        {
            _text(group_xmlids.get(_int(getattr(group, "id", 0))))
            for group in groups or []
            if _text(group_xmlids.get(_int(getattr(group, "id", 0))))
        }
    )


def _xmlid_aliases(env, model_name: str, res_id: int) -> list[str]:
    rows = env["ir.model.data"].sudo().search(
        [("model", "=", model_name), ("res_id", "=", int(res_id))],
        order="module, name, id",
    )
    return sorted(
        {
            f"{row.module}.{row.name}"
            for row in rows
            if row.module and row.name
        }
    )


def _source_revision(identity: dict[str, Any]) -> str:
    return _text(identity.get("source_revision")) or "unknown"


def _extension_modules(env) -> list[str]:
    from odoo.addons.smart_core.utils.extension_hooks import iter_extension_modules

    return iter_extension_modules(env)


def _runtime_identity(env) -> dict[str, Any]:
    from odoo.addons.smart_core.utils.product_release import runtime_release_identity

    database = _text(getattr(getattr(env, "cr", None), "dbname", ""))
    identity = runtime_release_identity(database)
    lang = env["res.lang"].sudo().search(
        [("code", "=", _text(getattr(env, "lang", "")) )], limit=1
    )
    return {
        **identity,
        "database": database,
        "language": {
            "code": _text(getattr(env, "lang", "")),
            "name": _text(getattr(lang, "name", "")),
            "active": bool(getattr(lang, "active", False)),
        },
    }


def _load_extension_scopes(env) -> tuple[list[str], list[dict[str, Any]]]:
    roots: set[str] = set()
    diagnostics: list[dict[str, Any]] = []
    try:
        extension_modules = _extension_modules(env)
    except Exception as exc:
        return [], [
            {
                "module": "",
                "hook": "get_platform_capability_explorer_scope",
                "status": "resolver_unavailable",
                "reason": _text(exc),
            }
        ]
    for module_name in extension_modules:
        try:
            module = importlib.import_module(f"odoo.addons.{module_name}")
        except Exception as exc:
            diagnostics.append(
                {
                    "module": module_name,
                    "hook": "get_platform_capability_explorer_scope",
                    "status": "import_error",
                    "reason": _text(exc),
                }
            )
            continue
        hook = getattr(module, "get_platform_capability_explorer_scope", None)
        if not callable(hook):
            continue
        try:
            payload = hook(env)
        except Exception as exc:
            diagnostics.append(
                {
                    "module": module_name,
                    "hook": "get_platform_capability_explorer_scope",
                    "status": "error",
                    "reason": _text(exc),
                }
            )
            continue
        payload = _dict(payload)
        if _text(payload.get("root_menu_xmlid")):
            roots.add(_text(payload.get("root_menu_xmlid")))
        for xmlid in payload.get("root_menu_xmlids") or []:
            if _text(xmlid):
                roots.add(_text(xmlid))
        diagnostics.append(
            {
                "module": module_name,
                "hook": "get_platform_capability_explorer_scope",
                "status": "ok",
            }
        )
    return sorted(roots), diagnostics


def _merge_extension_contributions(
    env,
    rows: list[dict[str, Any]],
    catalog_scope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    menu_ids = sorted({_int(row.get("menu_id")) for row in rows if _int(row.get("menu_id")) > 0})
    menu_xmlids = {
        _int(row.get("menu_id")): _text(row.get("menu_xmlid"))
        for row in rows
        if _int(row.get("menu_id")) > 0
    }
    merged: dict[str, Any] = {
        "scene_bindings": {},
        "enterprise_enablement": {},
        "company_context": {},
        "release_states": {},
        "release_centers": {},
        "product_qualifications": {},
        "release_snapshots": [],
        "scene_authority_available": False,
        "release_authority_available": False,
        "providers": [],
        "conflicts": [],
        "token_facts": [],
    }
    conflicted_release_centers = set()
    for module_name in _extension_modules(env):
        try:
            module = importlib.import_module(f"odoo.addons.{module_name}")
        except Exception as exc:
            merged["providers"].append(
                {"module": module_name, "status": "import_error", "reason": _text(exc)}
            )
            continue
        hook = getattr(module, "get_platform_capability_explorer_contributions", None)
        if not callable(hook):
            continue
        try:
            try:
                payload = hook(
                    env,
                    menu_ids,
                    menu_xmlids,
                    catalog_scope=catalog_scope,
                )
            except TypeError:
                payload = hook(env, menu_ids, menu_xmlids)
        except Exception as exc:
            merged["providers"].append(
                {"module": module_name, "status": "error", "reason": _text(exc)}
            )
            continue
        payload = _dict(payload)
        merged["providers"].append(
            {
                "module": module_name,
                "status": "ok",
                "source_module": _text(payload.get("source_module")) or module_name,
            }
        )
        merged["scene_authority_available"] = bool(
            merged["scene_authority_available"]
            or payload.get("scene_authority_available")
        )
        merged["release_authority_available"] = bool(
            merged["release_authority_available"]
            or payload.get("release_authority_available")
        )
        for raw_menu_id, bindings in _dict(payload.get("scene_bindings")).items():
            menu_id = _int(raw_menu_id)
            if menu_id <= 0:
                continue
            target = merged["scene_bindings"].setdefault(menu_id, [])
            for binding in _list(bindings):
                if isinstance(binding, dict):
                    target.append(dict(binding))
        for raw_menu_id, enablement in _dict(payload.get("enterprise_enablement")).items():
            menu_id = _int(raw_menu_id)
            if menu_id > 0 and isinstance(enablement, dict):
                merged["enterprise_enablement"][str(menu_id)] = dict(enablement)
        company_context = _dict(payload.get("company_context"))
        if company_context:
            previous_company = _dict(merged.get("company_context"))
            if previous_company and previous_company != company_context:
                merged["conflicts"].append(
                    {
                        "kind": "company_context",
                        "company_ids": sorted(
                            {
                                _int(previous_company.get("company_id")),
                                _int(company_context.get("company_id")),
                            }
                        ),
                    }
                )
                merged["company_context"] = {}
            else:
                merged["company_context"] = company_context
        for menu_xmlid, state in _dict(payload.get("release_states")).items():
            menu_xmlid = _text(menu_xmlid)
            state = _text(state)
            if not menu_xmlid:
                continue
            previous = merged["release_states"].get(menu_xmlid)
            if previous and state and previous != state:
                merged["conflicts"].append(
                    {
                        "kind": "release_state",
                        "menu_xmlid": menu_xmlid,
                        "values": sorted({previous, state}),
                    }
                )
                merged["release_states"][menu_xmlid] = ""
            else:
                merged["release_states"][menu_xmlid] = previous or state
        for menu_xmlid, center in _dict(payload.get("release_centers")).items():
            menu_xmlid = _text(menu_xmlid)
            if menu_xmlid and isinstance(center, dict):
                if menu_xmlid in conflicted_release_centers:
                    continue
                previous = merged["release_centers"].get(menu_xmlid)
                normalized_center = dict(center)
                if previous and previous != normalized_center:
                    merged["conflicts"].append(
                        {
                            "kind": "release_center",
                            "menu_xmlid": menu_xmlid,
                            "center_keys": sorted(
                                {
                                    _text(previous.get("key")),
                                    _text(normalized_center.get("key")),
                                }
                            ),
                        }
                    )
                    merged["release_centers"].pop(menu_xmlid, None)
                    conflicted_release_centers.add(menu_xmlid)
                else:
                    merged["release_centers"][menu_xmlid] = normalized_center
        for menu_xmlid, qualification in _dict(payload.get("product_qualifications")).items():
            menu_xmlid = _text(menu_xmlid)
            if menu_xmlid and isinstance(qualification, dict):
                merged["product_qualifications"].setdefault(menu_xmlid, dict(qualification))
        merged["release_snapshots"].extend(
            row for row in _list(payload.get("release_snapshots")) if isinstance(row, dict)
        )
        merged["token_facts"].append(payload.get("token_facts") or {})
        for conflict in _list(payload.get("conflicts")):
            if isinstance(conflict, dict):
                merged["conflicts"].append(dict(conflict))
    for bindings in merged["scene_bindings"].values():
        bindings.sort(
            key=lambda item: (
                _int(item.get("scenario_sequence"), 10),
                _int(item.get("sequence"), 10),
                _text(item.get("scenario_key")),
                _int(item.get("entry_id")),
            )
        )
    merged["release_snapshots"].sort(
        key=lambda item: (_text(item.get("product_key")), _int(item.get("snapshot_id")))
    )
    merged["token_facts"].sort(key=_canonical_json)
    merged["conflicts"] = sorted(
        {
            _canonical_json(conflict): conflict
            for conflict in merged["conflicts"]
            if isinstance(conflict, dict)
        }.values(),
        key=_canonical_json,
    )
    return merged


class PlatformCapabilityExplorerService:
    """Request-scoped adaptive projection over Odoo and extension facts."""

    def __init__(
        self,
        env,
        *,
        native_collector: Callable[[], Any] | None = None,
        facts_loader: Callable[[list[dict[str, Any]], list[int]], dict[str, Any]] | None = None,
        contribution_loader: Callable[[list[dict[str, Any]]], dict[str, Any]] | None = None,
        identity_loader: Callable[[], dict[str, Any]] | None = None,
        clock: Callable[[], datetime] | None = None,
    ):
        self.env = env
        self._native_collector = native_collector
        self._facts_loader = facts_loader
        self._contribution_loader = contribution_loader
        self._identity_loader = identity_loader
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @classmethod
    def source_authority_contract(cls) -> dict[str, Any]:
        return {
            "kind": "odoo_native_capability_explorer_projection",
            "authorities": [
                "ir.module.module",
                "ir.ui.menu",
                "ir.actions",
                "ir.model",
                "ir.model.fields",
                "ir.ui.view",
                "ir.model.access",
                "ir.rule",
                "res.lang",
                "extension_hook:scene_and_release_facts",
            ],
            "projection_only": True,
            "persisted_discovery_rows": 0,
            "no_business_record_authority": True,
            "no_capability_registry": True,
        }

    def _query_count(self) -> int:
        try:
            return int(
                getattr(
                    self.env.cr,
                    "sql_log_count",
                    getattr(self.env.cr, "query_count", 0),
                )
                or 0
            )
        except Exception:
            return 0

    def _authorization(self, params: dict[str, Any]) -> dict[str, Any]:
        return _dict(params.get("_authorization"))

    @staticmethod
    def _authorization_mode(params: dict[str, Any]) -> str:
        authorization = _dict(params.get("_authorization"))
        platform = _dict(authorization.get("platform"))
        tenant = _dict(authorization.get("tenant"))
        requested = _text(params.get("catalog_scope"))
        if requested and requested not in CATALOG_SCOPES:
            raise InvalidExplorerRequest(
                "catalog_scope must be platform or product"
            )
        if not authorization:
            return requested or "platform"
        if requested:
            if requested == "platform" and not platform.get("is_platform_control_admin"):
                raise CatalogScopeDenied(
                    "platform catalog scope requires a platform control administrator"
                )
            if requested == "product" and not (
                platform.get("is_platform_control_admin")
                or tenant.get("is_tenant_config_admin")
            ):
                raise CatalogScopeDenied(
                    "product catalog scope requires an enterprise configuration administrator"
                )
            return requested
        if platform.get("is_platform_control_admin"):
            return "platform"
        return "product"

    def _product_policy_context(
        self,
        *,
        requested_product_key: str = "",
    ) -> dict[str, Any]:
        try:
            Model = self.env["sc.product.policy"]
            products = Model.sudo().search(
                [("active", "=", True)],
                order="base_product_key, edition_key, product_key",
            )
        except (KeyError, AttributeError, TypeError):
            products = []
        options = []
        for policy in products:
            if not _text(policy.product_key):
                continue
            option_payload = policy.to_runtime_dict()
            options.append(
                {
                    "product_key": _text(policy.product_key),
                    "label": _text(policy.label) or _text(policy.product_key),
                    "base_product_key": _text(policy.base_product_key),
                    "edition_key": _text(policy.edition_key),
                    "groups": [
                        {
                            "group_key": _text(
                                group.get("center_key")
                                or group.get("group_key")
                            ),
                            "label": _text(
                                group.get("group_label") or group.get("label")
                            ),
                            "sequence": _int(group.get("sequence"), 10),
                            "entry_count": len(_list(group.get("menus"))),
                        }
                        for group in _list(option_payload.get("menu_groups"))
                        if isinstance(group, dict)
                    ],
                }
            )
        requested = _text(requested_product_key)
        selected = next(
            (
                policy
                for policy in products
                if _text(policy.product_key) == requested
            ),
            None,
        )
        if selected is None and not requested:
            selected = next(
                (
                    policy
                    for policy in products
                    if _text(policy.product_key) == "construction.standard"
                ),
                products[0] if products else None,
            )
        if selected is None and requested:
            raise InvalidExplorerRequest(
                f"product policy not found: {requested or '<default>'}"
            )
        if selected is None:
            return {
                "product_key": "",
                "product_label": "",
                "products": options,
                "groups": [],
                "menu_xmlids": set(),
                "policy_sha256": "",
            }
        payload = selected.to_runtime_dict()
        groups = [
            {
                "group_key": _text(
                    group.get("center_key") or group.get("group_key")
                ),
                "label": _text(
                    group.get("group_label") or group.get("label")
                ),
                "sequence": _int(group.get("sequence"), 10),
                "entry_count": len(_list(group.get("menus"))),
            }
            for group in _list(payload.get("menu_groups"))
            if isinstance(group, dict)
        ]
        menu_xmlids = {
            _text(menu.get("menu_xmlid"))
            for group in _list(payload.get("menu_groups"))
            if isinstance(group, dict)
            for menu in _list(group.get("menus"))
            if isinstance(menu, dict)
            and _text(menu.get("menu_xmlid"))
        }
        return {
            "product_key": _text(selected.product_key),
            "product_label": _text(selected.label) or _text(selected.product_key),
            "products": options,
            "groups": groups,
            "menu_xmlids": menu_xmlids,
            "policy_sha256": canonical_sha256(payload),
        }

    def catalog_scope_context(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = _dict(params)
        mode = self._authorization_mode(params)
        industry_roots, industry_diagnostics = _load_extension_scopes(self.env)
        product_context = self._product_policy_context(
            requested_product_key=_text(params.get("product_key"))
        )
        if mode == "platform":
            product_context = {
                **product_context,
                "product_key": "",
                "product_label": "",
                "groups": [],
                "menu_xmlids": set(),
                "policy_sha256": "",
            }
        authorization = self._authorization(params)
        products = _list((product_context or {}).get("products"))
        groups = _list((product_context or {}).get("groups"))
        return {
            "mode": mode,
            "label": "平台原生目录" if mode == "platform" else "产品选用清单",
            "identity_scope": (
                "current_instance_installed_native_entries"
                if mode == "platform"
                else "selected_product_policy_entries"
            ),
            "source_authority": {
                "kind": "platform_catalog_scope_resolution",
                "authorities": (
                    ["ir.ui.menu", "ir.actions", "ir.module.module"]
                    if mode == "platform"
                    else [
                        "sc.product.policy.menu_groups",
                        "sc.product.policy.capabilities",
                        "ir.ui.menu",
                    ]
                ),
                "platform_control_admin": bool(
                    _dict(authorization.get("platform")).get(
                        "is_platform_control_admin"
                    )
                ),
                "tenant_config_admin": bool(
                    _dict(authorization.get("tenant")).get(
                        "is_tenant_config_admin"
                    )
                ),
            },
            "product_key": _text((product_context or {}).get("product_key")),
            "product_label": _text((product_context or {}).get("product_label")),
            "products": products,
            "groups": groups,
            "policy_sha256": _text((product_context or {}).get("policy_sha256")),
            "management_actions": {
                "add_to_product_draft": add_catalog_entry_action_contract(
                    enabled=bool(
                        products
                        and _dict(authorization.get("platform")).get(
                            "is_platform_control_admin"
                        )
                    ),
                    reason_code=(
                        "OK"
                        if products
                        and _dict(authorization.get("platform")).get(
                            "is_platform_control_admin"
                        )
                        else "PRODUCT_MAINTENANCE_AUTHORITY_REQUIRED"
                    ),
                ),
                "open_product_draft": {
                    "route": "/admin/release-operator",
                    "product_key": _text((product_context or {}).get("product_key")),
                },
            },
            "industry_scope_contributions": {
                "root_menu_xmlids": industry_roots,
                "diagnostics": industry_diagnostics,
                "used_as_catalog_boundary": False,
            },
        }

    def _collect_native(self) -> Any:
        if self._native_collector:
            return self._native_collector()
        from odoo.addons.smart_core.delivery.runtime_capability_catalog import (
            RuntimeCapabilityCatalogService,
        )

        declared_industry_roots, scope_diagnostics = _load_extension_scopes(
            self.env
        )
        # Platform discovery is the current instance's native inventory. An
        # industry extension's declared root is classification evidence, not a
        # global discovery boundary.
        roots: list[str] = []
        menus_by_id = {}
        missing_roots = []
        for root_xmlid in roots:
            root = self.env.ref(root_xmlid, raise_if_not_found=False)
            if not root or root._name != "ir.ui.menu":
                missing_roots.append(root_xmlid)
                continue
            menus = self.env["ir.ui.menu"].sudo().search(
                [("id", "child_of", int(root.id))]
            )
            for menu in menus:
                menus_by_id[int(menu.id)] = menu
        if not roots:
            self.env.cr.execute("SELECT id FROM ir_ui_menu ORDER BY sequence, id")
            all_menus = self.env["ir.ui.menu"].sudo().browse(
                [row[0] for row in self.env.cr.fetchall()]
            ).exists()
            for menu in all_menus:
                menus_by_id[int(menu.id)] = menu
        candidate_menus = [menus_by_id[key] for key in sorted(menus_by_id)]
        xmlid_maps: dict[str, dict[int, str]] = {}
        xmlid_ambiguities: dict[str, dict[str, Any]] = {}
        if candidate_menus:
            menu_records = self.env["ir.ui.menu"].sudo().browse(
                [int(menu.id) for menu in candidate_menus]
            ).exists()
            menu_records.fetch(
                [
                    "action",
                    "parent_id",
                    "child_id",
                    "groups_id",
                    "active",
                    "sequence",
                    "name",
                    "parent_path",
                ]
            )
            actions_by_model = {}
            for menu in menu_records:
                action = menu.action
                if not action:
                    continue
                model_name = _text(action._name)
                actions_by_model[model_name] = (
                    actions_by_model.get(model_name, self.env[model_name].sudo())
                    | action
                )
            actions = [
                action
                for action_rows in actions_by_model.values()
                for action in action_rows.exists()
            ]
            xmlid_maps["ir.ui.menu"] = _external_id_map(
                self.env,
                "ir.ui.menu",
                menu_records.ids,
                xmlid_ambiguities,
            )
            action_ids_by_model = defaultdict(list)
            for action in actions:
                action_ids_by_model[_text(action._name)].append(int(action.id))
            action_facts = {}
            for model_name, action_ids in action_ids_by_model.items():
                if model_name:
                    xmlid_maps[model_name] = _external_id_map(
                        self.env,
                        model_name,
                        action_ids,
                        xmlid_ambiguities,
                    )
                    action_rows = self.env[model_name].sudo().browse(
                        sorted(set(action_ids))
                    ).exists()
                    read_fields = [
                        field_name
                        for field_name in ("res_model", "model_name", "view_mode", "groups_id")
                        if field_name in action_rows._fields
                    ]
                    action_values = {
                        int(values["id"]): values
                        for values in action_rows.read(read_fields)
                    }
                    action_group_ids = {
                        int(group_id)
                        for values in action_values.values()
                        for group_id in values.get("groups_id") or []
                    }
                    action_group_xmlids = _external_id_map(
                        self.env,
                        "res.groups",
                        sorted(action_group_ids),
                        xmlid_ambiguities,
                    )
                    for action_id in action_ids:
                        values = action_values.get(action_id, {})
                        view_mode = _text(values.get("view_mode"))
                        action_facts[action_id] = {
                            "id": action_id,
                            "type": model_name,
                            "res_model": _text(
                                values.get("res_model")
                                or values.get("model_name")
                            ),
                            "view_modes": [
                                item.strip()
                                for item in view_mode.split(",")
                                if item.strip()
                            ],
                            "group_xmlids": sorted(
                                {
                                    _text(action_group_xmlids.get(group_id))
                                    for group_id in values.get("groups_id") or []
                                    if _text(action_group_xmlids.get(group_id))
                                }
                            ),
                        }
            group_ids = {
                int(group.id)
                for menu in menu_records
                for group in menu.groups_id
            }
            group_ids.update(
                int(group.id)
                for action in actions
                for group in (getattr(action, "groups_id", []) or [])
            )
            xmlid_maps["res.groups"] = _external_id_map(
                self.env,
                "res.groups",
                sorted(group_ids),
                xmlid_ambiguities,
            )
            owner_modules = {
                _text(xmlid).split(".", 1)[0]
                for xmlid in xmlid_maps.get("ir.ui.menu", {}).values()
                if "." in _text(xmlid)
            }
            owner_modules.update(
                _text(xmlid).split(".", 1)[0]
                for model_name, xmlid_map in xmlid_maps.items()
                if model_name.startswith("ir.actions.")
                for xmlid in xmlid_map.values()
                if "." in _text(xmlid)
            )
            modules = self.env["ir.module.module"].sudo().search(
                [("name", "in", sorted(owner_modules))]
            )
            module_states = {_text(module.name): _text(module.state) for module in modules}
            model_names = sorted(
                {
                    _text(action_fact.get("res_model"))
                    for action_fact in action_facts.values()
                    if _text(action_fact.get("res_model"))
                }
            )
            existing_models = set(
                self.env["ir.model"].sudo().search(
                    [("model", "in", model_names)]
                ).mapped("model")
            )
            menu_xmlids = xmlid_maps.get("ir.ui.menu", {})
            candidate_menu_facts = []
            for menu in menu_records:
                action = menu.action
                action_id = _int(getattr(action, "id", 0))
                action_fact = action_facts.get(action_id) or {}
                menu_xmlid = _text(menu_xmlids.get(int(menu.id)))
                action_xmlid = _text(
                    xmlid_maps.get(_text(action_fact.get("type")), {}).get(action_id)
                )
                owner_module = (
                    menu_xmlid.split(".", 1)[0]
                    if "." in menu_xmlid
                    else action_xmlid.split(".", 1)[0]
                    if "." in action_xmlid
                    else ""
                )
                action_type = _text(action_fact.get("type"))
                res_model = _text(action_fact.get("res_model"))
                candidate_menu_facts.append(
                    {
                        "menu_id": int(menu.id),
                        "menu_xmlid": menu_xmlid,
                        "menu_label": _text(menu.name),
                        "menu_sequence": int(menu.sequence or 0),
                        "action_id": action_id,
                        "action_xmlid": action_xmlid,
                        "action_exists": bool(action),
                        "action_type": action_type,
                        "res_model": res_model,
                        "model_exists": bool(
                            _text(action_type) != "ir.actions.act_window"
                            or not res_model
                            or res_model in existing_models
                        ),
                        "module": owner_module,
                        "module_state": module_states.get(owner_module, ""),
                        "active": bool(menu.active),
                        "has_active_children": any(
                            bool(getattr(child, "active", True))
                            for child in (getattr(menu, "child_id", None) or [])
                        ),
                    }
                )
            candidate_menu_facts.sort(
                key=lambda item: (item["menu_id"], item["action_id"])
            )
        else:
            action_facts = {}
            candidate_menu_facts = []
        projection = RuntimeCapabilityCatalogService(self.env).collect(
            leaf_actions_only=True,
            candidate_menus=candidate_menus if roots else None,
            xmlid_maps=xmlid_maps,
            action_facts=action_facts,
        )
        projection.diagnostics["capability_explorer_scope"] = {
            "root_menu_xmlids": roots,
            "missing_root_menu_xmlids": missing_roots,
            "fallback_all_menus": not bool(roots),
            "mode": "current_instance_full_native_catalog",
            "declared_industry_root_menu_xmlids": declared_industry_roots,
            "industry_roots_used_as_catalog_boundary": False,
            "provider_diagnostics": scope_diagnostics,
        }
        projection.diagnostics["root_menu_ids"] = sorted(
            int(menu.id)
            for menu in menus_by_id.values()
            if not menu.parent_id
        )
        projection.diagnostics["xmlid_ambiguities"] = [
            xmlid_ambiguities[key] for key in sorted(xmlid_ambiguities)
        ]
        projection.diagnostics["candidate_menu_facts"] = candidate_menu_facts
        return projection

    def _load_native_facts(
        self,
        rows: list[dict[str, Any]],
        root_menu_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        env = self.env
        leaf_menu_ids = sorted({_int(row.get("menu_id")) for row in rows if _int(row.get("menu_id"))})
        root_ids = sorted({_int(value) for value in root_menu_ids or [] if _int(value) > 0})
        center_ids = []
        if root_ids:
            center_ids = env["ir.ui.menu"].sudo().search(
                [("parent_id", "in", root_ids)]
            ).ids
        menu_ids = sorted(set(leaf_menu_ids) | set(root_ids) | set(center_ids))
        model_names = sorted({_text(row.get("res_model")) for row in rows if _text(row.get("res_model"))})
        module_names = sorted({_text(row.get("owner_module")) for row in rows if _text(row.get("owner_module"))})

        installed_modules = env["ir.module.module"].sudo().search(
            [("state", "in", sorted(INSTALLED_MODULE_STATES))]
        )
        modules = env["ir.module.module"].sudo().search([("name", "in", module_names)])
        models = env["ir.model"].sudo().search([("model", "in", model_names)])
        model_ids = models.ids
        menus = env["ir.ui.menu"].sudo().browse(menu_ids).exists()
        action_ids_by_model = defaultdict(list)
        for row in rows:
            action_model = _text(row.get("action_model"))
            action_id = _int(row.get("action_id"))
            if action_model and action_id > 0:
                action_ids_by_model[action_model].append(action_id)
        action_records = []
        action_xmlids: dict[int, str] = {}
        xmlid_ambiguities: dict[str, dict[str, Any]] = {}
        for action_model, typed_action_ids in action_ids_by_model.items():
            typed_ids = sorted(set(typed_action_ids))
            records = env[action_model].sudo().browse(typed_ids).exists()
            action_records.extend(records)
            action_xmlids.update(
                _external_id_map(
                    env,
                    action_model,
                    typed_ids,
                    xmlid_ambiguities,
                )
            )

        module_dependencies = defaultdict(list)
        if modules.ids:
            dependencies = env["ir.module.module.dependency"].sudo().search(
                [("module_id", "in", modules.ids)]
            )
            for dependency in dependencies:
                module_dependencies[_int(dependency.module_id.id)].append(
                    _text(dependency.name)
                )

        field_counts: Counter = Counter()
        if model_ids:
            for group in env["ir.model.fields"].sudo().read_group(
                [("model_id", "in", model_ids)],
                ["model_id"],
                ["model_id"],
            ):
                model_name = _text((group.get("model_id") or [False, False])[1])
                if model_name:
                    field_counts[model_name] = int(group.get("__count") or 0)

        views_by_model: dict[str, dict[str, Any]] = {}
        if model_names:
            views = env["ir.ui.view"].sudo().search([("model", "in", model_names)])
            grouped_views = defaultdict(list)
            for view in views:
                grouped_views[_text(view.model)].append(
                    {
                        "id": int(view.id),
                        "type": _text(view.type),
                        "priority": int(view.priority or 0),
                        "active": bool(view.active),
                        "inherit_id": _int(view.inherit_id.id),
                    }
                )
            for model_name, values in grouped_views.items():
                values.sort(key=lambda item: (item["type"], item["priority"], item["id"]))
                views_by_model[model_name] = {
                    "count": len(values),
                    "sha256": canonical_sha256(values),
                }

        acl_by_model: dict[str, dict[str, Any]] = {}
        acl_group_ids: set[int] = set()
        access_rows = []
        if model_ids:
            access_rows = list(
                env["ir.model.access"].sudo().search([("model_id", "in", model_ids)])
            )
            for access in access_rows:
                if access.group_id:
                    acl_group_ids.add(int(access.group_id.id))
        rules_by_model: dict[str, dict[str, Any]] = {}
        rule_group_ids: set[int] = set()
        rule_rows = []
        if model_ids:
            rule_rows = list(env["ir.rule"].sudo().search([("model_id", "in", model_ids)]))
            for rule in rule_rows:
                for group in rule.groups:
                    rule_group_ids.add(int(group.id))

        menu_group_ids: set[int] = set()
        action_group_ids: set[int] = set()
        for menu in menus:
            for group in menu.groups_id:
                menu_group_ids.add(int(group.id))
        for action in action_records:
            for group in getattr(action, "groups_id", []) or []:
                action_group_ids.add(int(group.id))
        group_ids = sorted(acl_group_ids | rule_group_ids | menu_group_ids | action_group_ids)
        group_xmlids = _external_id_map(
            env,
            "res.groups",
            group_ids,
            xmlid_ambiguities,
        )

        grouped_access = defaultdict(list)
        for access in access_rows:
            model_name = _text(access.model_id.model)
            grouped_access[model_name].append(
                {
                    "id": int(access.id),
                    "group_id": _int(access.group_id.id),
                    "group_xmlid": _text(group_xmlids.get(_int(access.group_id.id))),
                    "read": bool(access.perm_read),
                    "write": bool(access.perm_write),
                    "create": bool(access.perm_create),
                    "unlink": bool(access.perm_unlink),
                }
            )
        for model_name, values in grouped_access.items():
            values.sort(key=lambda item: item["id"])
            acl_by_model[model_name] = {
                "row_count": len(values),
                "group_xmlids": sorted(
                    {
                        _text(group_xmlids.get(item["group_id"]))
                        for item in values
                        if _text(group_xmlids.get(item["group_id"]))
                    }
                ),
                "read_group_ids": sorted(
                    {
                        _int(item["group_id"])
                        for item in values
                        if item["read"] and _int(item["group_id"]) > 0
                    }
                ),
                "sha256": canonical_sha256(values),
            }

        grouped_rules = defaultdict(list)
        for rule in rule_rows:
            model_name = _text(rule.model_id.model)
            grouped_rules[model_name].append(
                {
                    "id": int(rule.id),
                    "active": bool(rule.active),
                    "groups": sorted(int(group.id) for group in rule.groups),
                    "global": bool(getattr(rule, "global", False)),
                    "perm_read": bool(rule.perm_read),
                    "perm_write": bool(rule.perm_write),
                    "perm_create": bool(rule.perm_create),
                    "perm_unlink": bool(rule.perm_unlink),
                }
            )
        for model_name, values in grouped_rules.items():
            values.sort(key=lambda item: item["id"])
            rules_by_model[model_name] = {
                "count": len(values),
                "group_xmlids": sorted(
                    {
                        _text(group_xmlids.get(group_id))
                        for item in values
                        for group_id in item["groups"]
                        if _text(group_xmlids.get(group_id))
                    }
                ),
                "sha256": canonical_sha256(values),
            }

        menu_xmlids = _external_id_map(
            env,
            "ir.ui.menu",
            menu_ids,
            xmlid_ambiguities,
        )
        menu_facts = {}
        from odoo.addons.smart_core.delivery.menu_service import MenuService

        menu_group_service = MenuService(env)
        for menu in menus:
            groups = menu.groups_id
            menu_facts[int(menu.id)] = {
                "id": int(menu.id),
                "xmlid": _text(menu_xmlids.get(int(menu.id))),
                "name": _text(menu.name),
                "parent_id": _int(menu.parent_id.id),
                "parent_path": _text(menu.parent_path),
                "sequence": int(menu.sequence or 0),
                "active": bool(menu.active),
                "groups": _group_xmlids(groups, group_xmlids),
                "group_ids": sorted(int(group.id) for group in groups),
                "groups_allowed": menu_group_service._groups_authorize_current_user(groups),
            }
        action_facts = {}
        for action in action_records:
            groups = getattr(action, "groups_id", []) or []
            action_facts[int(action.id)] = {
                "id": int(action.id),
                "xmlid": _text(action_xmlids.get(int(action.id))),
                "type": _text(action._name),
                "res_model": _text(getattr(action, "res_model", "")),
                "groups": _group_xmlids(groups, group_xmlids),
                "group_ids": sorted(
                    int(group.id)
                    for group in groups
                ),
                "groups_allowed": menu_group_service._groups_authorize_current_user(groups),
            }
        module_facts = {}
        for module in modules:
            module_facts[_text(module.name)] = {
                "name": _text(module.name),
                "state": _text(module.state),
                "version": _text(module.latest_version),
                "dependencies": sorted(module_dependencies[_int(module.id)]),
            }
        model_facts = {
            _text(model.model): {
                "name": _text(model.model),
                "description": _text(model.name),
            }
            for model in models
        }
        user = getattr(env, "user", None)
        company = getattr(env, "company", None)
        actor = {
            "user_id": _int(getattr(user, "id", 0)),
            "login": _text(getattr(user, "login", "")),
            "name": _text(getattr(user, "name", "")),
            "company_id": _int(getattr(company, "id", 0)),
            "company_name": _text(getattr(company, "name", "")),
            "allowed_company_ids": sorted(
                {
                    int(company_id)
                    for company_id in (
                        getattr(getattr(user, "company_ids", None), "ids", []) or []
                    )
                    if _int(company_id) > 0
                }
            ),
            "group_ids": sorted(
                {
                    int(group.id)
                    for group in (getattr(user, "groups_id", []) or [])
                    if _int(getattr(group, "id", 0)) > 0
                }
            ),
            "group_xmlids": _group_xmlids(
                getattr(user, "groups_id", []) or [],
                group_xmlids,
            ),
            "source": "ir.ui.menu + ir.actions + ir.model.access + current principal",
        }
        return {
            "menus": menu_facts,
            "actions": action_facts,
            "modules": module_facts,
            "models": model_facts,
            "field_counts": dict(field_counts),
            "views": views_by_model,
            "acl": acl_by_model,
            "acl_rows": dict(grouped_access),
            "rules": rules_by_model,
            "installed_modules": [
                {
                    "name": _text(module.name),
                    "state": _text(module.state),
                    "version": _text(module.latest_version),
                }
                for module in installed_modules
            ],
            "actor": actor,
            "root_menu_ids": root_ids,
            "xmlid_ambiguities": [
                xmlid_ambiguities[key] for key in sorted(xmlid_ambiguities)
            ],
        }

    def _center_for_menu(
        self,
        menu_fact: dict[str, Any],
        menu_facts: dict[int, dict[str, Any]],
        root_menu_ids: list[int],
    ) -> dict[str, Any]:
        parent_path = _text(menu_fact.get("parent_path"))
        for root_id in sorted(root_menu_ids):
            root = menu_facts.get(int(root_id)) or {}
            root_path = _text(root.get("parent_path"))
            if not root_path or not parent_path.startswith(root_path):
                continue
            suffix = parent_path[len(root_path):].strip("/")
            if not suffix:
                break
            center_id = _int(suffix.split("/", 1)[0])
            center = menu_facts.get(center_id)
            if center:
                return {
                    "key": _text(center.get("xmlid")),
                    "label": _text(center.get("name")),
                    "sequence": _int(center.get("sequence"), 10),
                    "source": "ir.ui.menu",
                }
        return {}

    def _release_center(
        self,
        menu_xmlid: str,
        contributions: dict[str, Any],
    ) -> dict[str, Any]:
        center = _dict(_dict(contributions.get("release_centers")).get(menu_xmlid))
        if not center:
            return {}
        return {
            "key": _text(center.get("key")),
            "label": _text(center.get("label")),
            "sequence": _int(center.get("sequence"), 10),
            "product_key": _text(center.get("product_key")),
            "snapshot_id": _int(center.get("snapshot_id")),
            "version": _text(center.get("version")),
            "source": _text(center.get("source")) or "unknown",
            "config_ref": dict(center.get("config_ref") or {}),
        }

    def _build_row(
        self,
        native_row: dict[str, Any],
        *,
        facts: dict[str, Any],
        contributions: dict[str, Any],
        root_menu_ids: list[int],
        include_detail: bool,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        menu_id = _int(native_row.get("menu_id"))
        action_id = _int(native_row.get("action_id"))
        menu = _dict(_dict(facts.get("menus")).get(menu_id))
        action = _dict(_dict(facts.get("actions")).get(action_id))
        module_name = _text(native_row.get("owner_module"))
        module = _dict(_dict(facts.get("modules")).get(module_name))
        model_name = _text(native_row.get("res_model"))
        model = _dict(_dict(facts.get("models")).get(model_name))
        menu_xmlid = _text(native_row.get("menu_xmlid"))
        action_xmlid = _text(native_row.get("action_xmlid"))
        scene_map = _dict(contributions.get("scene_bindings"))
        scene_bindings = [
            dict(item)
            for item in (
                scene_map.get(menu_id)
                or scene_map.get(str(menu_id))
                or []
            )
        ]
        active_scene_bindings = [
            item for item in scene_bindings if item.get("scenario_active", True) is not False
        ]
        native_center = self._center_for_menu(menu, _dict(facts.get("menus")), root_menu_ids)
        release_center = self._release_center(menu_xmlid, contributions)
        center = release_center or native_center
        classification = classify_business_domain(
            scene_bindings=scene_bindings,
            center_key=_text(center.get("key")),
            center_source=_text(center.get("source")),
        )
        module_state = _text(module.get("state"))
        action_exists = bool(action)
        menu_action_matches = bool(
            action_exists
            and action_xmlid
            and action.get("xmlid") == action_xmlid
            and menu_xmlid
            and menu.get("xmlid") == menu_xmlid
        )
        native_valid, native_blockers = native_selection_assessment(
            menu_xmlid=menu_xmlid,
            action_xmlid=action_xmlid,
            action_type=native_row.get("action_model"),
            res_model=model_name,
            module_state=module_state,
            action_exists=action_exists,
            menu_action_matches=menu_action_matches,
            model_exists=bool(model),
        )
        scene_authority_available = bool(
            contributions.get("scene_authority_available")
        )
        scene_assignable_blockers = list(native_blockers)
        if not scene_authority_available:
            scene_assignable_blockers.append("SCENE_AUTHORITY_UNAVAILABLE")
        scene_assignable = not scene_assignable_blockers
        release_state = _text(
            _dict(contributions.get("release_states")).get(menu_xmlid)
        ) or "unknown"
        release_center_conflicts = [
            conflict
            for conflict in (contributions.get("conflicts") or [])
            if _text(conflict.get("kind")) == "release_center"
            and _text(conflict.get("menu_xmlid")) == menu_xmlid
        ]
        release_blockers = (
            ["RELEASE_CENTER_AMBIGUOUS"]
            if release_center_conflicts
            else []
        )
        qualification = _dict(
            _dict(contributions.get("product_qualifications")).get(menu_xmlid)
        )
        preview_qualified = _text(qualification.get("preview")) or "not_verified"
        standard_qualified = _text(qualification.get("standard")) or "not_verified"
        selected_product_key = _text(qualification.get("selected_product_key"))
        selected_qualified = (
            _text(qualification.get("selected_status"))
            or (
                standard_qualified
                if not selected_product_key
                else "not_verified"
            )
        )
        qualification_reason = (
            _text(qualification.get("reason_code"))
            or "PRODUCT_QUALIFICATION_UNVERIFIED"
        )
        qualification_evidence = [
            dict(item)
            for item in _list(qualification.get("evidence"))
            if isinstance(item, dict)
        ]
        views = _dict(_dict(facts.get("views")).get(model_name))
        acl = _dict(_dict(facts.get("acl")).get(model_name))
        rules = _dict(_dict(facts.get("rules")).get(model_name))
        acl_rows = [
            dict(item)
            for item in _list(_dict(facts.get("acl_rows")).get(model_name))
            if isinstance(item, dict)
        ]
        if not acl_rows:
            acl_rows = [
                {"read": True, "group_id": group_id}
                for group_id in _list(acl.get("read_group_ids"))
                if _int(group_id) > 0
            ]
        actor = _dict(facts.get("actor"))
        held_group_ids = [
            _int(value) for value in _list(actor.get("group_ids"))
        ]
        menu_group_ids = sorted(
            _int(value) for value in _list(menu.get("group_ids")) if _int(value) > 0
        )
        action_group_ids = sorted(
            _int(value) for value in _list(action.get("group_ids")) if _int(value) > 0
        )
        entry_group_ids = sorted({*menu_group_ids, *action_group_ids})
        module_installed = module_state in INSTALLED_MODULE_STATES
        native_present = bool(action_exists and menu_action_matches and module_installed)
        consumer_supported = bool(
            _text(native_row.get("action_model")) in SUPPORTED_ACTION_TYPES
            and (
                _text(native_row.get("action_model")) != "ir.actions.act_window"
                or bool(model)
            )
        )
        enterprise_enablement = _dict(
            _dict(contributions.get("enterprise_enablement")).get(str(menu_id))
        )
        company_context = _dict(contributions.get("company_context"))
        access = access_layer_assessment(
            native_present=native_present,
            native_blockers=native_blockers,
            consumer_supported=consumer_supported,
            entry_group_ids=entry_group_ids,
            held_group_ids=held_group_ids,
            acl_rows=acl_rows,
            standard_qualified=selected_qualified,
            enterprise_enablement=enterprise_enablement,
            menu_group_ids=menu_group_ids,
            action_group_ids=action_group_ids,
            menu_groups_allowed=menu.get("groups_allowed"),
            action_groups_allowed=action.get("groups_allowed"),
        )
        enterprise_status = (
            _text(enterprise_enablement.get("status"))
            or ("enabled" if enterprise_enablement.get("enabled") is True else "not_applicable")
        )
        fact_layers = [
            {
                "key": "native_presence",
                "label": "原生存在",
                "status": "present" if native_present else "missing",
                "reason_code": (
                    "NATIVE_ENTRY_PRESENT"
                    if native_present
                    else native_blockers[0]
                    if native_blockers
                    else "NATIVE_ENTRY_NOT_READY"
                ),
                "evidence": {
                    "menu_xmlid": menu_xmlid,
                    "action_xmlid": action_xmlid,
                    "module_state": module_state,
                },
            },
            {
                "key": "consumer_support",
                "label": "前端/消费者支持",
                "status": "supported" if consumer_supported else "unsupported",
                "reason_code": (
                    "CONSUMER_SUPPORTED"
                    if consumer_supported
                    else "CONSUMER_SURFACE_UNSUPPORTED"
                ),
                "evidence": {
                    "action_type": _text(native_row.get("action_model")),
                    "view_modes": list(native_row.get("view_modes") or []),
                },
            },
            {
                "key": "product_qualification",
                "label": "产品资格",
                "status": selected_qualified,
                "reason_code": qualification_reason,
                "evidence": qualification_evidence,
            },
            {
                "key": "product_release",
                "label": "入口发布",
                "status": release_state,
                "reason_code": (
                    "ENTRY_RELEASED"
                    if release_state == "released"
                    else "ENTRY_PREVIEW"
                    if release_state == "preview"
                    else "ENTRY_NOT_RELEASED"
                ),
                "evidence": {
                    "release_state": release_state,
                    "snapshots": list(contributions.get("release_snapshots") or []),
                },
            },
            {
                "key": "enterprise_enablement",
                "label": "企业启用",
                "status": enterprise_status,
                "reason_code": _text(enterprise_enablement.get("reason_code"))
                or (
                    "ENTERPRISE_ENABLEMENT_NOT_APPLICABLE"
                    if enterprise_status == "not_applicable"
                    else "ENTERPRISE_SCENARIO_NOT_ENABLED"
                ),
                "evidence": enterprise_enablement,
            },
            {
                "key": "current_user_access",
                "label": "当前用户权限",
                "status": "allowed" if not access["blockers"] else "denied",
                "reason_code": access["reason_code"],
                "evidence": access,
            },
        ]
        field_count = _int(_dict(facts.get("field_counts")).get(model_name))
        scene_count = len(
            {
                _text(binding.get("scenario_key"))
                for binding in active_scene_bindings
                if _text(binding.get("scenario_key"))
            }
        )
        row = {
            "entry_ref": {
                "menu_xmlid": menu_xmlid,
                "action_xmlid": action_xmlid,
            },
            "label": _text(native_row.get("menu_name")),
            "origin": {
                "module": module_name,
                "model": model_name,
            },
            "center": center,
            "business_domain": {
                "key": classification["key"] or None,
                "label": classification["label"] or None,
                "confidence": classification["confidence"],
                "reason_code": classification["reason_code"],
            },
            "scene_usage": {
                "bound": bool(active_scene_bindings),
                "count": scene_count,
            },
            "release_state": release_state,
            "draft_eligibility": {
                "selectable": native_valid,
                "blockers": native_blockers,
            },
            "product_qualification": {
                "preview": preview_qualified,
                "standard": standard_qualified,
                "selected_product_key": selected_product_key,
                "selected_status": selected_qualified,
                "by_product": _dict(qualification.get("by_product")),
                "reason_code": qualification_reason,
                "evidence": qualification_evidence,
            },
            "fact_layers": fact_layers,
            "availability": {
                "available_to_current_user": not access["blockers"],
                "reason_code": access["reason_code"],
                "blockers": list(access["blockers"]),
                "actor": actor,
                "target_company": _dict(contributions.get("company_context")),
            },
        }
        detail = None if not include_detail else {
            **row,
            "native_facts": {
                "menu": {
                    "id": menu_id,
                    "xmlid": menu_xmlid,
                    "label": _text(menu.get("name")),
                    "sequence": _int(menu.get("sequence")),
                    "path": native_row.get("menu_path") or [],
                    "group_xmlids": list(menu.get("groups") or []),
                },
                "action": {
                    "id": action_id,
                    "xmlid": action_xmlid,
                    "type": _text(native_row.get("action_model")),
                    "view_modes": list(native_row.get("view_modes") or []),
                    "group_xmlids": list(action.get("groups") or []),
                },
                "module": {
                    "name": module_name,
                    "state": module_state,
                    "version": _text(module.get("version")),
                    "dependencies": list(module.get("dependencies") or []),
                },
                "model": {
                    "name": model_name,
                    "description": _text(model.get("description")),
                    "exists": bool(model),
                    "field_count": field_count,
                },
                "views": {
                    "count": _int(views.get("count")),
                    "sha256": _text(views.get("sha256")),
                },
                "acl": {
                    "row_count": _int(acl.get("row_count")),
                    "group_xmlids": list(acl.get("group_xmlids") or []),
                    "sha256": _text(acl.get("sha256")),
                },
                "record_rules": {
                    "count": _int(rules.get("count")),
                    "group_xmlids": list(rules.get("group_xmlids") or []),
                    "sha256": _text(rules.get("sha256")),
                },
            },
            "classification": {
                "source": classification["source"],
                "candidates": classification["candidates"],
                "reason_code": classification["reason_code"],
                "center_source": _text(center.get("source")),
                "native_center": native_center or None,
                "release_center": release_center or None,
            },
            "scenario_usage": {
                "bound": bool(active_scene_bindings),
                "scenarios": active_scene_bindings,
                "ambiguous": classification["reason_code"] == "AMBIGUOUS_SCENE_BINDING",
            },
            "release": {
                "state": release_state,
                "entry_published": release_state in {"released", "preview"},
                "center": release_center or None,
                "snapshots": list(contributions.get("release_snapshots") or []),
                "blockers": release_blockers,
                "ambiguous_center": bool(release_center_conflicts),
            },
            "scene_assignment": {
                "assignable": scene_assignable,
                "blockers": scene_assignable_blockers,
            },
            "qualification": {
                "preview": preview_qualified,
                "standard": standard_qualified,
                "selected_product_key": selected_product_key,
                "selected_status": selected_qualified,
                "by_product": _dict(qualification.get("by_product")),
                "reason_code": qualification_reason,
                "evidence": qualification_evidence,
            },
            "enterprise_enablement": enterprise_enablement or {
                "applicable": False,
                "enabled": False,
                "status": "not_applicable",
                "reason_code": "ENTERPRISE_ENABLEMENT_NOT_APPLICABLE",
                "company_id": _int(company_context.get("company_id")),
                "company_name": _text(company_context.get("company_name")),
                "source": "res.company",
                "scenes": [],
            },
            "current_user_access": access,
            "visibility": {
                "can_use": not access["blockers"],
                "reason_code": access["reason_code"],
                "blockers": list(access["blockers"]),
                "actor": actor,
                "target_company": company_context,
                "record_scope": "runtime_acl_and_record_rules",
            },
            "diagnostics": {
                "native_valid": native_valid,
                "native_blockers": native_blockers,
                "release_blockers": release_blockers,
                "blockers": native_blockers + release_blockers,
                "draft_selectable": native_valid,
                "scene_assignable": scene_assignable,
                "entry_published": release_state in {"released", "preview"},
                "preview_qualified": preview_qualified,
                "standard_qualified": standard_qualified,
                "current_user_access": access,
                "visibility_reason": access["reason_code"],
                "visibility_blockers": list(access["blockers"]),
                "classification_reason": classification["reason_code"],
            },
        }
        row["_sort"] = {
            "center_sequence": _int(center.get("sequence"), 10),
            "label": _text(row.get("label")).casefold(),
            "menu_sequence": _int(menu.get("sequence")),
            "menu_xmlid": menu_xmlid,
            "action_xmlid": action_xmlid,
            "module": module_name,
            "scene_status": "bound" if active_scene_bindings else "unbound",
            "release_state": release_state,
            "business_domain_key": classification["key"],
            "_search": " ".join(
                [
                    _text(row.get("label")),
                    menu_xmlid,
                    action_xmlid,
                    model_name,
                    module_name,
                    _text(center.get("key")),
                    _text(center.get("label")),
                    _text(classification.get("key")),
                    _text(classification.get("label")),
                    " ".join(
                        _text(binding.get("scenario_key"))
                        for binding in active_scene_bindings
                    ),
                ]
            ).casefold(),
        }
        return row, detail

    def _diagnose_menu_xmlid(
        self,
        menu_xmlid: str,
        expected_action_xmlid: str = "",
        scene_authority_available: bool = False,
    ) -> dict[str, Any]:
        requested_xmlid = _text(menu_xmlid)
        module_name, separator, record_name = requested_xmlid.partition(".")
        if not separator or not module_name or not record_name:
            return {
                "entry_ref": {
                    "menu_xmlid": requested_xmlid,
                    "action_xmlid": expected_action_xmlid or None,
                },
                "native_valid": False,
                "draft_selectable": False,
                "scene_assignable": False,
                "entry_published": False,
                "preview_qualified": "not_verified",
                "standard_qualified": "not_verified",
                "blockers": ["XMLID_INVALID"],
                "classification_reason": "NO_CLASSIFICATION_EVIDENCE",
                "native_facts": {},
                "sections": {
                    "native": {
                        "valid": False,
                        "blockers": ["XMLID_INVALID"],
                    },
                    "release": {
                        "state": "unknown",
                        "entry_published": False,
                        "blockers": ["XMLID_INVALID"],
                    },
                },
            }
        data_rows = self.env["ir.model.data"].sudo().search(
            [
                ("module", "=", module_name),
                ("name", "=", record_name),
                ("model", "=", "ir.ui.menu"),
            ],
            order="id",
        )
        if not data_rows:
            blockers = ["XMLID_NOT_FOUND"]
            return {
                "entry_ref": {
                    "menu_xmlid": requested_xmlid,
                    "action_xmlid": expected_action_xmlid or None,
                },
                "native_valid": False,
                "draft_selectable": False,
                "scene_assignable": False,
                "entry_published": False,
                "preview_qualified": "not_verified",
                "standard_qualified": "not_verified",
                "blockers": blockers,
                "classification_reason": "NO_CLASSIFICATION_EVIDENCE",
                "native_facts": {},
                "sections": {
                    "native": {"valid": False, "blockers": blockers},
                    "release": {
                        "state": "unknown",
                        "entry_published": False,
                        "blockers": blockers,
                    },
                },
            }
        menu = self.env["ir.ui.menu"].sudo().browse(
            sorted({int(row.res_id) for row in data_rows})
        ).exists()
        if len(menu) != 1:
            blockers = ["XMLID_AMBIGUOUS"]
            return {
                "entry_ref": {
                    "menu_xmlid": requested_xmlid,
                    "action_xmlid": expected_action_xmlid or None,
                },
                "native_valid": False,
                "draft_selectable": False,
                "scene_assignable": False,
                "entry_published": False,
                "preview_qualified": "not_verified",
                "standard_qualified": "not_verified",
                "blockers": blockers,
                "classification_reason": "NO_CLASSIFICATION_EVIDENCE",
                "native_facts": {
                    "candidate_res_ids": sorted(
                        {int(row.res_id) for row in data_rows}
                    )
                },
                "sections": {
                    "native": {"valid": False, "blockers": blockers},
                    "release": {
                        "state": "unknown",
                        "entry_published": False,
                        "blockers": blockers,
                    },
                },
            }
        aliases = _xmlid_aliases(self.env, "ir.ui.menu", int(menu.id))
        action = menu.action
        action_aliases = (
            _xmlid_aliases(self.env, _text(action._name), int(action.id))
            if action
            else []
        )
        action_xmlid = action_aliases[0] if len(action_aliases) == 1 else ""
        action_type = _text(getattr(action, "_name", ""))
        res_model = _text(getattr(action, "res_model", ""))
        model_exists = True
        if action_type == "ir.actions.act_window" and res_model:
            model_exists = bool(
                self.env["ir.model"].sudo().search_count(
                    [("model", "=", res_model)],
                    limit=1,
                )
            )
        module = self.env["ir.module.module"].sudo().search(
            [("name", "=", module_name)],
            limit=1,
        )
        expected_action_xmlid = _text(expected_action_xmlid)
        menu_action_matches = not expected_action_xmlid or (
            action_xmlid and expected_action_xmlid == action_xmlid
        )
        native_valid, blockers = native_selection_assessment(
            menu_xmlid=requested_xmlid,
            action_xmlid=action_xmlid,
            action_type=action_type,
            res_model=res_model,
            module_state=module.state if module else "",
            action_exists=bool(action),
            menu_action_matches=menu_action_matches,
            model_exists=model_exists,
        )
        if len(aliases) > 1 or len(action_aliases) > 1:
            blockers = ["XMLID_AMBIGUOUS"] + blockers
            native_valid = False
        return {
            "entry_ref": {
                "menu_xmlid": requested_xmlid,
                "action_xmlid": action_xmlid or expected_action_xmlid or None,
            },
            "native_valid": native_valid,
            "draft_selectable": native_valid,
            "scene_assignable": bool(native_valid and scene_authority_available),
            "entry_published": False,
            "preview_qualified": "not_verified",
            "standard_qualified": "not_verified",
            "blockers": blockers,
            "classification_reason": "NO_CLASSIFICATION_EVIDENCE",
            "native_facts": {
                "menu": {
                    "id": int(menu.id),
                    "xmlid": requested_xmlid,
                    "xmlid_aliases": aliases,
                    "label": _text(menu.name),
                    "active": bool(menu.active),
                    "has_active_children": any(
                        bool(getattr(child, "active", True))
                        for child in (menu.child_id or [])
                    ),
                },
                "action": {
                    "id": int(action.id) if action else 0,
                    "xmlid": action_xmlid,
                    "xmlid_aliases": action_aliases,
                    "exists": bool(action),
                    "type": action_type,
                    "res_model": res_model,
                },
                "module": {
                    "name": module_name,
                    "state": module.state if module else "",
                    "installed": bool(
                        module and module.state in INSTALLED_MODULE_STATES
                    ),
                },
                "model": {
                    "name": res_model,
                    "exists": model_exists,
                },
            },
            "sections": {
                "native": {
                    "valid": native_valid,
                    "blockers": blockers,
                },
                "release": {
                    "state": "unknown",
                    "entry_published": False,
                    "blockers": blockers,
                },
            },
        }

    def project(
        self,
        *,
        include_details: bool = False,
        catalog_scope: dict[str, Any] | None = None,
    ) -> CatalogProjection:
        started = time.perf_counter()
        scope_params = _dict(catalog_scope)
        scope_context = self.catalog_scope_context(scope_params)
        query_start = self._query_count()
        native_started = time.perf_counter()
        native = self._collect_native()
        native_ms = int((time.perf_counter() - native_started) * 1000)
        query_after_native = self._query_count()
        all_native_rows = [
            dict(row) for row in _list(getattr(native, "rows", []))
        ]
        rows = [
            row for row in all_native_rows if row.get("identity_stable", True)
        ]
        platform_native_entry_count = len(rows)
        selected_menu_xmlids: set[str] | None = None
        if scope_context["mode"] == "product":
            selected_menu_xmlids = self._product_policy_context(
                requested_product_key=_text(scope_params.get("product_key"))
            )["menu_xmlids"]
            rows = [
                row
                for row in rows
                if _text(row.get("menu_xmlid")) in selected_menu_xmlids
            ]
        native_diagnostics = _dict(getattr(native, "diagnostics", {}))
        native_diagnostics["excluded_unstable_entry_count"] = (
            len(all_native_rows) - len(rows)
        )
        root_menu_ids = [
            _int(value)
            for value in (
                native_diagnostics.get("root_menu_ids")
                or []
            )
            if _int(value) > 0
        ]
        facts_started = time.perf_counter()
        facts = (
            self._facts_loader(rows, root_menu_ids)
            if self._facts_loader
            else self._load_native_facts(rows, root_menu_ids)
        )
        facts_ms = int((time.perf_counter() - facts_started) * 1000)
        query_after_facts = self._query_count()
        contributions_started = time.perf_counter()
        contributions = (
            self._contribution_loader(rows)
            if self._contribution_loader
            else _merge_extension_contributions(
                self.env,
                rows,
                catalog_scope=scope_context,
            )
        )
        contributions_ms = int((time.perf_counter() - contributions_started) * 1000)
        query_after_contributions = self._query_count()
        root_menu_ids = [
            _int(value)
            for value in (
                facts.get("root_menu_ids")
                or root_menu_ids
            )
            if _int(value) > 0
        ]
        identity = (
            self._identity_loader()
            if self._identity_loader
            else _runtime_identity(self.env)
        )
        built_rows = []
        details = {}
        for native_row in rows:
            row, detail = self._build_row(
                native_row,
                facts=facts,
                contributions=contributions,
                root_menu_ids=root_menu_ids,
                include_detail=include_details,
            )
            built_rows.append(row)
            if detail is not None:
                entry_ref = row["entry_ref"]
                details[(entry_ref["menu_xmlid"], entry_ref["action_xmlid"])] = detail
        scope_context["platform_native_entry_count"] = platform_native_entry_count
        scope_context["visible_entry_count"] = len(built_rows)
        token_facts = {
            "projection_version": PROJECTION_VERSION,
            "catalog_scope": scope_context,
            "database": _text(identity.get("database")),
            "language": identity.get("language") or {},
            "modules": facts.get("modules") or {},
            "installed_modules": facts.get("installed_modules") or [],
            "native_entries": [
                {
                    "menu_id": _int(row.get("menu_id")),
                    "menu_xmlid": _text(row.get("menu_xmlid")),
                    "menu_name": _text(row.get("menu_name")),
                    "menu_path": row.get("menu_path") or [],
                    "menu_sequence": _int(row.get("menu_sequence")),
                    "action_id": _int(row.get("action_id")),
                    "action_xmlid": _text(row.get("action_xmlid")),
                    "action_type": _text(row.get("action_model")),
                    "res_model": _text(row.get("res_model")),
                    "view_modes": row.get("view_modes") or [],
                    "owner_module": _text(row.get("owner_module")),
                }
                for row in rows
            ],
            "menu_facts": facts.get("menus") or {},
            "action_facts": facts.get("actions") or {},
            "models": facts.get("models") or {},
            "field_counts": facts.get("field_counts") or {},
            "views": facts.get("views") or {},
            "acl": facts.get("acl") or {},
            "acl_rows": facts.get("acl_rows") or {},
            "rules": facts.get("rules") or {},
            "actor": facts.get("actor") or {},
            "scene_and_release": {
                "scene_bindings": contributions.get("scene_bindings") or {},
                "enterprise_enablement": contributions.get("enterprise_enablement") or {},
                "company_context": contributions.get("company_context") or {},
                "release_states": contributions.get("release_states") or {},
                "release_centers": contributions.get("release_centers") or {},
                "product_qualifications": contributions.get("product_qualifications") or {},
                "release_snapshots": contributions.get("release_snapshots") or [],
                "provider_token_facts": contributions.get("token_facts") or [],
            },
            "authority": {
                "scene_authority_available": bool(
                    contributions.get("scene_authority_available")
                ),
                "release_authority_available": bool(
                    contributions.get("release_authority_available")
                ),
                "providers": sorted(
                    contributions.get("providers") or [],
                    key=_canonical_json,
                ),
                "conflicts": sorted(
                    contributions.get("conflicts") or [],
                    key=_canonical_json,
                ),
                "root_scope": native_diagnostics.get("capability_explorer_scope") or {},
                "xmlid_ambiguities": native_diagnostics.get("xmlid_ambiguities") or [],
                "candidate_menu_facts": native_diagnostics.get("candidate_menu_facts") or [],
            },
        }
        catalog_token = f"sha256:{canonical_sha256(token_facts)}"
        query_count = max(0, self._query_count() - query_start)
        generated_at = self._clock().astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        diagnostics = {
            "source_authority": self.source_authority_contract(),
            "native": native_diagnostics,
            "providers": contributions.get("providers") or [],
            "conflicts": contributions.get("conflicts") or [],
            "scene_authority_available": bool(
                contributions.get("scene_authority_available")
            ),
            "release_authority_available": bool(
                contributions.get("release_authority_available")
            ),
            "release_snapshots": contributions.get("release_snapshots") or [],
            "catalog_scope": scope_context,
            "performance": {
                "query_count": query_count,
                "native_query_count": max(0, query_after_native - query_start),
                "metadata_query_count": max(
                    0, query_after_facts - query_after_native
                ),
                "contribution_query_count": max(
                    0, query_after_contributions - query_after_facts
                ),
                "native_projection_ms": native_ms,
                "metadata_load_ms": facts_ms,
                "contribution_load_ms": contributions_ms,
                "projection_ms": int((time.perf_counter() - started) * 1000),
            },
        }
        return CatalogProjection(
            meta={
                "schema": LIST_SCHEMA,
                "generated_at": generated_at,
                "runtime_database": _text(identity.get("database")),
                "source_revision": _source_revision(identity),
                "language": identity.get("language") or {},
                "catalog_token": catalog_token,
                "total": len(built_rows),
                "catalog_scope": scope_context,
                "freshness": "request_time_projection",
                "persistence": "none",
                "diagnostics": diagnostics,
            },
            rows=built_rows,
            details=details,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _ensure_token(projection: CatalogProjection, expected: Any) -> None:
        expected = _text(expected)
        if expected and expected != projection.token:
            raise CatalogStaleError("catalog token no longer matches current runtime facts")

    @staticmethod
    def _parse_sort(raw: Any) -> list[tuple[str, str]]:
        value = _text(raw)
        if not value:
            return list(DEFAULT_SORT)
        entries = []
        for chunk in value.split(","):
            field_name, separator, direction = chunk.strip().partition(":")
            field_name = _text(field_name)
            direction = _text(direction).lower() if separator else "asc"
            if field_name not in ALLOWED_SORT_FIELDS or direction not in {"asc", "desc"}:
                raise InvalidExplorerRequest(f"unsupported sort field: {chunk}")
            entries.append((field_name, direction))
        if len(entries) > 6:
            raise InvalidExplorerRequest("at most six sort fields are allowed")
        for required in ("menu_xmlid", "action_xmlid"):
            if required not in {field_name for field_name, _direction in entries}:
                entries.append((required, "asc"))
        return entries

    @staticmethod
    def _matches(row: dict[str, Any], filters: dict[str, Any], query: str) -> bool:
        sort_values = _dict(row.get("_sort"))
        center_key = _text(_dict(row.get("center")).get("key")) or "unclassified"
        domain_key = _text(_dict(row.get("business_domain")).get("key")) or "unclassified"
        confidence = _text(_dict(row.get("business_domain")).get("confidence"))
        scene_status = "bound" if _dict(row.get("scene_usage")).get("bound") else "unbound"
        center_keys = {_text(value) for value in filters.get("center_keys") or []}
        if center_keys and center_key not in center_keys:
            return False
        domain_keys = {_text(value) for value in filters.get("business_domain_keys") or []}
        if domain_keys and domain_key not in domain_keys:
            return False
        scene_statuses = {_text(value) for value in filters.get("scene_status") or []}
        if scene_statuses and scene_status not in scene_statuses:
            return False
        release_states = {_text(value) for value in filters.get("release_states") or []}
        if release_states and _text(row.get("release_state")) not in release_states:
            return False
        confidences = {
            _text(value) for value in filters.get("classification_confidence") or []
        }
        if confidences and confidence not in confidences:
            return False
        if filters.get("draft_selectable") is not None:
            expected = bool(filters.get("draft_selectable"))
            actual = bool(_dict(row.get("draft_eligibility")).get("selectable"))
            if actual != expected:
                return False
        return not query or query in _text(sort_values.get("_search"))

    @staticmethod
    def _sorted(rows: list[dict[str, Any]], sort_fields: list[tuple[str, str]]) -> list[dict[str, Any]]:
        result = list(rows)
        for field_name, direction in reversed(sort_fields):
            result.sort(
                key=lambda row: _dict(row.get("_sort")).get(field_name, ""),
                reverse=direction == "desc",
            )
        return result

    @staticmethod
    def _public_row(row: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in row.items() if key != "_sort"}

    @staticmethod
    def _facets(rows: list[dict[str, Any]]) -> dict[str, Any]:
        centers: dict[str, dict[str, Any]] = {}
        domains: dict[str, dict[str, Any]] = {}
        scene_status = Counter({"bound": 0, "unbound": 0})
        release_states = Counter()
        confidence = Counter({value: 0 for value in CLASSIFICATION_CONFIDENCES})
        for row in rows:
            center = _dict(row.get("center"))
            center_key = _text(center.get("key")) or "unclassified"
            center_fact = centers.setdefault(
                center_key,
                {"key": center_key, "label": _text(center.get("label")) or center_key, "count": 0},
            )
            center_fact["count"] += 1
            business = _dict(row.get("business_domain"))
            domain_key = _text(business.get("key")) or "unclassified"
            domain_fact = domains.setdefault(
                domain_key,
                {
                    "key": domain_key,
                    "label": _text(business.get("label")) or domain_key,
                    "count": 0,
                },
            )
            domain_fact["count"] += 1
            scene_status["bound" if _dict(row.get("scene_usage")).get("bound") else "unbound"] += 1
            release_states[_text(row.get("release_state")) or "unknown"] += 1
            confidence[_text(business.get("confidence")) or "unclassified"] += 1
        return {
            "centers": sorted(centers.values(), key=lambda item: (item["label"], item["key"])),
            "business_domains": sorted(
                domains.values(), key=lambda item: (item["label"], item["key"])
            ),
            "scene_status": dict(sorted(scene_status.items())),
            "release_states": dict(sorted(release_states.items())),
            "classification_confidence": dict(sorted(confidence.items())),
        }

    def list_entries(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = _dict(params)
        projection = self.project(catalog_scope=params)
        self._ensure_token(projection, params.get("expected_catalog_token"))
        query = _text(params.get("query")).casefold()
        filters = _dict(params.get("filters"))
        allowed_filters = {
            "center_keys",
            "business_domain_keys",
            "scene_status",
            "release_states",
            "draft_selectable",
            "classification_confidence",
        }
        unknown_filters = set(filters) - allowed_filters
        if unknown_filters:
            raise InvalidExplorerRequest(
                f"unsupported filters: {','.join(sorted(unknown_filters))}"
            )
        for key in (
            "center_keys",
            "business_domain_keys",
            "scene_status",
            "release_states",
            "classification_confidence",
        ):
            value = filters.get(key)
            if value is not None and not isinstance(value, list):
                raise InvalidExplorerRequest(f"filters.{key} must be an array")
        scene_statuses = {_text(value) for value in filters.get("scene_status") or []}
        if scene_statuses - SCENE_STATUSES:
            raise InvalidExplorerRequest("filters.scene_status contains an unsupported value")
        confidences = {
            _text(value) for value in filters.get("classification_confidence") or []
        }
        if confidences - CLASSIFICATION_CONFIDENCES:
            raise InvalidExplorerRequest(
                "filters.classification_confidence contains an unsupported value"
            )
        try:
            limit = int(params.get("limit", 50))
            offset = int(params.get("offset", 0))
        except Exception as exc:
            raise InvalidExplorerRequest("limit and offset must be integers") from exc
        if not 1 <= limit <= 100:
            raise InvalidExplorerRequest("limit must be between 1 and 100")
        if offset < 0:
            raise InvalidExplorerRequest("offset must be non-negative")
        sort_fields = self._parse_sort(params.get("sort"))
        filtered = [
            row for row in projection.rows if self._matches(row, filters, query)
        ]
        ordered = self._sorted(filtered, sort_fields)
        page = ordered[offset: offset + limit]
        next_offset = offset + len(page)
        has_more = next_offset < len(ordered)
        return {
            "meta": {
                **projection.meta,
                "schema": LIST_SCHEMA,
                "sort": [f"{field_name}:{direction}" for field_name, direction in sort_fields],
                "filtered_total": len(ordered),
                "offset": offset,
                "limit": limit,
                "next_offset": next_offset if has_more else None,
                "has_more": has_more,
            },
            "facets": self._facets(projection.rows),
            "rows": [self._public_row(row) for row in page],
        }

    def detail(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = _dict(params)
        projection = self.project(include_details=True, catalog_scope=params)
        self._ensure_token(projection, params.get("expected_catalog_token"))
        entry_ref = _dict(params.get("entry_ref"))
        key = (_text(entry_ref.get("menu_xmlid")), _text(entry_ref.get("action_xmlid")))
        if not all(key):
            raise InvalidExplorerRequest("entry_ref.menu_xmlid and action_xmlid are required")
        detail = projection.details.get(key)
        if not detail:
            raise CapabilityEntryNotFound(
                f"entry not found: {key[0]} / {key[1]}"
            )
        return {
            "meta": {
                **projection.meta,
                "schema": DETAIL_SCHEMA,
            },
            "entry": detail,
        }

    def diagnose(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        params = _dict(params)
        projection = self.project(include_details=True, catalog_scope=params)
        self._ensure_token(projection, params.get("expected_catalog_token"))
        menu_xmlid = _text(params.get("menu_xmlid"))
        if menu_xmlid:
            result = self._diagnose_menu_xmlid(
                menu_xmlid,
                _text(params.get("action_xmlid")),
                bool(projection.diagnostics.get("scene_authority_available")),
            )
            return {
                "meta": {
                    **projection.meta,
                    "schema": DIAGNOSE_SCHEMA,
                },
                **result,
            }
        entry_ref = _dict(params.get("entry_ref"))
        key = (
            _text(entry_ref.get("menu_xmlid")),
            _text(entry_ref.get("action_xmlid")),
        )
        if not all(key):
            raise InvalidExplorerRequest(
                "diagnose requires menu_xmlid or entry_ref.menu_xmlid/action_xmlid"
            )
        entry = projection.details.get(key)
        if not entry:
            raise CapabilityEntryNotFound(
                f"entry not found: {key[0]} / {key[1]}"
            )
        diagnostics = entry["diagnostics"]
        return {
            "meta": {
                **projection.meta,
                "schema": DIAGNOSE_SCHEMA,
            },
            "entry_ref": entry["entry_ref"],
            "native_valid": diagnostics["native_valid"],
            "draft_selectable": diagnostics["draft_selectable"],
            "scene_assignable": diagnostics["scene_assignable"],
            "entry_published": diagnostics["entry_published"],
            "preview_qualified": diagnostics["preview_qualified"],
            "standard_qualified": diagnostics["standard_qualified"],
            "blockers": diagnostics["blockers"],
            "classification_reason": diagnostics["classification_reason"],
            "sections": {
                "native": {
                    "valid": diagnostics["native_valid"],
                    "blockers": diagnostics["native_blockers"],
                },
                "scene_assignment": entry["scene_assignment"],
                "release": entry["release"],
                "qualification": entry["qualification"],
                "enterprise_enablement": entry["enterprise_enablement"],
                "current_user_access": entry["current_user_access"],
                "fact_layers": entry["fact_layers"],
                "visibility": entry["visibility"],
            },
        }
