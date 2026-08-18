# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


_RENDER_PROFILE_CREATE = "create"
_RENDER_PROFILE_EDIT = "edit"
_RENDER_PROFILE_READONLY = "readonly"
_RENDER_PROFILES = {_RENDER_PROFILE_CREATE, _RENDER_PROFILE_EDIT, _RENDER_PROFILE_READONLY}


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    if text.lower() in {"undefined", "null"}:
        text = ""
    return text or fallback


def _as_dict(value: Any) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def to_bool(value: Any, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return fallback


def _has_persisted_record(data: dict) -> bool:
    head = _as_dict(data.get("head"))
    for raw in (data.get("res_id"), head.get("res_id"), data.get("id")):
        if raw in (None, "", False):
            continue
        token = str(raw).strip().lower()
        if token in {"", "0", "new", "false", "null", "none"}:
            continue
        try:
            if int(token) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _context_allows(context: dict, *positive_keys: str, negative_keys: tuple[str, ...] = ()) -> bool:
    for key in negative_keys:
        if key in context and to_bool(context.get(key), fallback=False):
            return False
    for key in positive_keys:
        if key in context:
            return to_bool(context.get(key), fallback=True)
    return True


def resolve_render_profile(data: dict) -> str:
    explicit = _safe_text(data.get("render_profile")).lower()
    if explicit in _RENDER_PROFILES:
        return explicit
    head = _as_dict(data.get("head"))
    view_type = _safe_text(head.get("view_type") or data.get("view_type")).lower()
    if view_type and "form" not in view_type:
        return _RENDER_PROFILE_EDIT
    effective = _as_dict(_as_dict(data.get("permissions")).get("effective")).get("rights")
    effective_rights = _as_dict(effective)
    head_permissions = _as_dict(head.get("permissions"))
    can_write = to_bool(
        effective_rights.get("write", head_permissions.get("write")),
        fallback=False,
    )
    can_create = to_bool(
        effective_rights.get("create", head_permissions.get("create")),
        fallback=False,
    )
    if not can_write and not can_create:
        return _RENDER_PROFILE_READONLY
    has_record = _has_persisted_record(data)
    return _RENDER_PROFILE_EDIT if has_record else _RENDER_PROFILE_CREATE


def apply_form_view_capabilities(data: dict) -> None:
    form = _as_dict(_as_dict(data.get("views")).get("form"))
    capabilities = _as_dict(form.get("capabilities"))
    if not capabilities:
        return
    permission_root = _as_dict(data.get("permissions"))
    effective_rights = _as_dict(_as_dict(permission_root.get("effective")).get("rights"))
    record_rights_source = _as_dict(_as_dict(permission_root.get("record")).get("rights"))
    head = _as_dict(data.get("head"))
    head_permissions = _as_dict(head.get("permissions"))

    model_rights = {
        "read": to_bool(effective_rights.get("read", head_permissions.get("read")), fallback=False),
        "write": to_bool(effective_rights.get("write", head_permissions.get("write")), fallback=False),
        "create": to_bool(effective_rights.get("create", head_permissions.get("create")), fallback=False),
        "unlink": to_bool(effective_rights.get("unlink", head_permissions.get("unlink")), fallback=False),
    }
    model_rights["duplicate"] = model_rights["read"] and model_rights["create"]
    has_record = _has_persisted_record(data)
    record_rights = {
        "read": (not has_record) or to_bool(record_rights_source.get("read"), fallback=False),
        "write": has_record and to_bool(record_rights_source.get("write"), fallback=False),
        "create": True,
        "unlink": has_record and to_bool(record_rights_source.get("unlink"), fallback=False),
        "duplicate": has_record and to_bool(record_rights_source.get("duplicate"), fallback=False),
    }
    view_capabilities = {
        "read": True,
        "write": to_bool(capabilities.get("can_write"), fallback=True),
        "create": to_bool(capabilities.get("can_create"), fallback=True),
        "unlink": to_bool(capabilities.get("can_delete"), fallback=True),
        "duplicate": to_bool(capabilities.get("can_duplicate"), fallback=True),
    }
    context = _as_dict(data.get("context") or head.get("context"))
    entry_capabilities = {
        "read": _context_allows(context, "read", negative_keys=("no_read",)),
        "write": _context_allows(context, "edit", "write", negative_keys=("no_edit", "no_write")),
        "create": _context_allows(context, "create", negative_keys=("no_create",)),
        "unlink": _context_allows(context, "delete", "unlink", negative_keys=("no_delete", "no_unlink")),
        "duplicate": _context_allows(context, "duplicate", negative_keys=("no_duplicate",)),
    }
    effective_capabilities = {
        operation: bool(
            view_capabilities[operation]
            and model_rights[operation]
            and record_rights[operation]
            and entry_capabilities[operation]
        )
        for operation in ("read", "write", "create", "unlink", "duplicate")
    }
    if has_record and not effective_capabilities["read"]:
        effective_capabilities["write"] = False
        effective_capabilities["unlink"] = False
        effective_capabilities["duplicate"] = False
    requested_profile = resolve_render_profile(data)
    effective_profile = requested_profile
    if requested_profile == _RENDER_PROFILE_EDIT and not effective_capabilities["write"]:
        effective_profile = _RENDER_PROFILE_READONLY

    capabilities["modelRights"] = model_rights
    capabilities["recordRights"] = record_rights
    capabilities["viewCapabilities"] = view_capabilities
    capabilities["entryCapabilities"] = entry_capabilities
    capabilities["effectiveRecordCapabilities"] = effective_capabilities
    capabilities["effectiveRenderProfile"] = effective_profile
    form["capabilities"] = capabilities
    views = _as_dict(data.get("views"))
    views["form"] = form
    data["views"] = views
    data["effective_render_profile"] = effective_profile
