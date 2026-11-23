# -*- coding: utf-8 -*-
from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Dict

try:
    from .source_authority import build_source_authority_contract
except ImportError:
    _source_spec = spec_from_file_location(
        "action_target_source_authority",
        Path(__file__).with_name("source_authority.py"),
    )
    if _source_spec is None or _source_spec.loader is None:
        raise
    _source_module = module_from_spec(_source_spec)
    _source_spec.loader.exec_module(_source_module)
    build_source_authority_contract = (
        _source_module.build_source_authority_contract
    )

SOURCE_KIND = "ui_action_target_schema_projection"
SOURCE_AUTHORITIES = ("static_action_target_schema", "scene_key", "route_path")
NO_BUSINESS_FACT_AUTHORITY = True
STATIC_TARGET_KINDS = frozenset({
    "scene.key",
    "route.path",
    "page.refresh",
    "menu.first_reachable",
})
FORBIDDEN_PUBLIC_KEYS = frozenset({"authorizationSubject", "authorization_subject"})


class ActionTargetSchemaError(ValueError):
    """Raised when a declared action target is incomplete or unsupported."""


def source_authority_contract() -> Dict[str, Any]:
    return build_source_authority_contract(
        kind=SOURCE_KIND,
        authorities=SOURCE_AUTHORITIES,
        no_business_fact_authority=NO_BUSINESS_FACT_AUTHORITY,
        runtime_carrier="action_target_schema",
    )


def scene_target(scene_key: str) -> Dict[str, Any]:
    return {"kind": "scene.key", "scene_key": str(scene_key or "").strip()}


def route_path_target(path: str) -> Dict[str, Any]:
    return {"kind": "route.path", "path": str(path or "").strip()}


def page_refresh_target() -> Dict[str, Any]:
    return {"kind": "page.refresh"}


def menu_first_reachable_target() -> Dict[str, Any]:
    return {"kind": "menu.first_reachable"}


def _reject_server_identity(value: Any, path: str) -> None:
    if isinstance(value, dict):
        forbidden = sorted(set(value) & FORBIDDEN_PUBLIC_KEYS)
        if forbidden:
            raise ActionTargetSchemaError(
                f"{path} exposes server-only authorization identity: {', '.join(forbidden)}"
            )
        for key, item in value.items():
            _reject_server_identity(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_server_identity(item, f"{path}[{index}]")


def validate_action_target(target: Any, *, path: str = "target") -> Dict[str, Any]:
    """Validate the existing action-target vocabulary without a fallback."""

    if not isinstance(target, dict) or not target:
        raise ActionTargetSchemaError(f"{path} is required")
    _reject_server_identity(target, path)
    kind = str(target.get("kind") or "").strip()
    target_type = str(target.get("type") or target.get("_name") or "").strip()
    if kind:
        if kind not in STATIC_TARGET_KINDS:
            raise ActionTargetSchemaError(f"{path}.kind is unsupported")
        allowed_by_kind = {
            "scene.key": {"kind", "scene_key"},
            "route.path": {"kind", "path"},
            "page.refresh": {"kind"},
            "menu.first_reachable": {"kind"},
        }
        unknown = sorted(set(target) - allowed_by_kind[kind])
        if unknown:
            raise ActionTargetSchemaError(
                f"{path} has unknown fields for {kind}: {', '.join(unknown)}"
            )
        if kind == "scene.key" and not str(target.get("scene_key") or "").strip():
            raise ActionTargetSchemaError(f"{path}.scene_key is required")
        if kind == "route.path" and not str(target.get("path") or "").strip():
            raise ActionTargetSchemaError(f"{path}.path is required")
        return dict(target)
    if target_type == "action":
        if not str(target.get("action_xmlid") or target.get("action_id") or "").strip():
            raise ActionTargetSchemaError(f"{path} action identity is required")
        return dict(target)
    if target_type == "intent":
        if not str(target.get("intent") or "").strip():
            raise ActionTargetSchemaError(f"{path}.intent is required")
        if target.get("params") is not None and not isinstance(target.get("params"), dict):
            raise ActionTargetSchemaError(f"{path}.params must be an object")
        return dict(target)
    raise ActionTargetSchemaError(
        f"{path} must be an existing ContractV2ActionRule target"
    )


def resolve_action_target(action_key: str, page_key: str) -> Dict[str, Any]:
    key = str(action_key or "").strip().lower()
    page = str(page_key or "").strip().lower()
    if key == "open_login":
        return route_path_target("/login")
    if key == "open_account_activation":
        return route_path_target("/activate-account")
    if key == "open_password_recovery":
        return route_path_target("/password-recovery")
    if key == "open_risk_dashboard":
        return scene_target("workspace.home")
    if key == "open_my_work":
        return scene_target("my_work.workspace")
    if key == "apply_filters":
        return scene_target(page)
    if key == "open_list":
        if page in {"usage_analytics", "scene_health"}:
            return scene_target(page)
        return scene_target("workspace.home")
    if key == "open_workbench":
        return scene_target("workspace.home")
    if key == "open_workspace_overview":
        return scene_target("my_work.workspace")
    if key == "open_menu":
        return menu_first_reachable_target()
    if key in {"refresh_page", "refresh"}:
        return page_refresh_target()
    if key == "open_usage_analytics":
        return route_path_target("/admin/usage-analytics")
    if key == "open_landing":
        return scene_target("workspace.home")
    if key == "open_scene":
        return scene_target("workspace.home")
    return scene_target(page)
