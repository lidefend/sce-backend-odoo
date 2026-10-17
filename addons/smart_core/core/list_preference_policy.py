# -*- coding: utf-8 -*-
"""P0 declared list-surface preference policy projection.

This module is the single declared projection of the *preference constraints*
of a resolved list surface. It answers exactly three questions for a validated
``(model, action, view_type)`` identity:

* which columns the surface declares (the eligible set a user may order, hide
  or widen);
* which of them are locked (must stay visible);
* whether visibility / order / width are adjustable at all.

It reads only declared carriers:

* the authenticated identity (``action_id`` -> authoritative ``res_model``);
* the P1-registered standard list profile column order (P0 registry);
* the published business list configuration that governs the surface, when one
  is declared;
* the action's effective native list view columns (permission filtered).

It never runs the page assembler and never returns an implicit empty policy.
When no declared column set can be resolved it raises
:class:`ListPreferencePolicyError` so the caller refuses the preference read or
write instead of falling back to ``{}``.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


class ListPreferencePolicyError(Exception):
    """Explicit refusal of a preference read/write without a declared policy."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = int(code)
        self.message = str(message)


class ListPreferencePolicy:
    SOURCE_KIND = "ui_only_user_preference_policy"
    SOURCE_AUTHORITIES = (
        "ui.business.config.contract",
        "res.users",
        "ir.actions.actions",
        "ir.actions.act_window",
        "ir.ui.view",
    )
    NO_BUSINESS_FACT_AUTHORITY = True
    DEFAULT_SCOPE = "ui_only"

    # ---------------------------------------------------------------- identity
    @classmethod
    def resolve_identity(cls, env, *, action_id: Any = 0, model_name: Any = "") -> tuple[str, Any]:
        """Return ``(model_name, error)``; never guesses a model.

        An ``action_id`` is resolved through ``ir.actions.actions`` into its
        authoritative ``res_model``. A caller-supplied model that disagrees with
        that resolution is refused instead of silently forming a mismatched
        identity.
        """
        try:
            action = int(action_id or 0)
        except (TypeError, ValueError):
            return "", ("400", "action_id 无效")
        requested = str(model_name or "").strip()
        if action <= 0:
            if not requested:
                return "", ("400", "缺少合法 action_id 或 model")
            if requested not in env:
                return "", ("400", f"model 无效: {requested}")
            return requested, None
        if "ir.actions.actions" not in env or "ir.actions.act_window" not in env:
            return "", ("400", "action 身份不可用")
        # Action metadata is a trusted, read-only platform fact. ``type`` lives on
        # the abstract ``ir.actions.actions`` base (admin-only by stock ACL) while
        # ``res_model`` is only declared on the concrete ``ir.actions.act_window``
        # model. The platform reads such metadata through sudo
        # (delivery/menu_service.py, .../action_resolver.py). The caller's
        # authorization is enforced by the surface gate and the model ACL, never
        # by this identity lookup.
        try:
            base = env["ir.actions.actions"].sudo().browse(action)
            if not base.exists():
                return "", ("400", f"action_id 未知: {action}")
            action_type = str(getattr(base, "type", "") or "")
        except Exception:
            return "", ("400", f"action_id 无效: {action}")
        if action_type != "ir.actions.act_window":
            return "", ("400", f"action_id 不承载列表表面: {action}")
        try:
            resolved = str(env["ir.actions.act_window"].sudo().browse(action).res_model or "").strip()
        except Exception:
            return "", ("400", f"action_id 无效: {action}")
        if not resolved:
            return "", ("400", f"action_id 未声明 res_model: {action}")
        if resolved not in env:
            return "", ("400", f"action 声明了未安装的 model: {resolved}")
        if requested and requested != resolved:
            return "", ("400", f"model 与 action 解析不一致: {requested} != {resolved}")
        return resolved, None

    # --------------------------------------------------------------- projection
    @classmethod
    def declared_formal_list_lock(cls, env, *, model_name: str, action_id: Any = 0) -> dict:
        """Return the declared action-scoped list lock for this surface, if any.

        The locking semantic is owned by the layer that declared the surface
        (industry/customer); this reader only matches the action identity and
        resolves the declared external ids in one governed query. It never
        guesses a lock and never re-derives one from the page assembler.
        """
        try:
            action = int(action_id or 0)
        except (TypeError, ValueError):
            return {}
        if action <= 0:
            return {}
        try:
            from ..utils.contract_governance_registry import formal_list_lock_declarations
        except Exception:
            return {}
        declarations = formal_list_lock_declarations()
        if not declarations:
            return {}
        pairs = set()
        for declaration in declarations:
            for xmlid in declaration.get("action_xmlids") or []:
                module, _, name = str(xmlid or "").partition(".")
                if module and name:
                    pairs.add((module, name))
        if not pairs or "ir.model.data" not in env:
            return {}
        try:
            rows = env["ir.model.data"].sudo().search_read(
                [
                    ("model", "=", "ir.actions.act_window"),
                    ("module", "in", sorted({module for module, _name in pairs})),
                    ("name", "in", sorted({name for _module, name in pairs})),
                ],
                ["module", "name", "res_id"],
            )
        except Exception:
            return {}
        resolved = {
            f"{str(row.get('module') or '')}.{str(row.get('name') or '')}": int(row.get("res_id") or 0)
            for row in rows
        }
        for declaration in declarations:
            matched = any(
                resolved.get(str(xmlid or "")) == action
                for xmlid in declaration.get("action_xmlids") or []
            )
            if not matched:
                continue
            declared_model = str(declaration.get("model_name") or "").strip()
            if declared_model and declared_model != model_name:
                continue
            return declaration
        return {}

    @classmethod
    def project(cls, env, *, model_name: str, action_id: Any = 0, view_type: Any = "list") -> dict:
        model_name = str(model_name or "").strip()
        if not model_name or model_name not in env:
            raise ListPreferencePolicyError(400, f"model 无效: {model_name or '?'}")
        cls._assert_caller_can_read(env, model_name)
        view = str(view_type or "list").strip().lower()
        native_view = "list" if view in ("list", "tree", "") else view
        try:
            action = int(action_id or 0)
        except (TypeError, ValueError):
            action = 0

        published, declared_policy = cls._published_columns(env, model_name, action)
        registered = cls._registered_columns(env, model_name)
        native = cls._native_columns(env, model_name, action, native_view)

        columns: list[str] = []
        sources: list[str] = []
        for group, tag in (
            (published, "published_business_list_config"),
            (registered, "legacy_standard_list_profile"),
            (native, "native_list_view"),
        ):
            added = False
            for name in group:
                if name and name not in columns:
                    columns.append(name)
                    added = True
            if added:
                sources.append(tag)
        if not columns:
            raise ListPreferencePolicyError(
                422,
                f"list preference policy unavailable: no declared list surface for {model_name}",
            )

        policy = {
            "scope": cls.DEFAULT_SCOPE,
            "allow_visibility": True,
            "allow_order": True,
            "allow_width": True,
            "locked_columns": [],
        }
        for key, value in (declared_policy or {}).items():
            policy[key] = value
        declared_lock = cls.declared_formal_list_lock(env, model_name=model_name, action_id=action)
        if declared_lock:
            # The owning layer declared this exact surface locked, so the
            # projection must report the same verdict the surface's own
            # contract declares instead of a second, more permissive one.
            policy["allow_visibility"] = declared_lock.get("allow_visibility") is not False
            policy["allow_order"] = declared_lock.get("allow_order") is not False
            policy["allow_width"] = declared_lock.get("allow_width") is not False
            policy["scope"] = str(declared_lock.get("scope") or policy["scope"])
            policy["locked_columns"] = list(columns)
            policy["locked"] = True
        else:
            policy["locked"] = False
        policy["must_request_columns"] = list(columns)
        if declared_lock:
            policy["locked_scope"] = declared_lock.get("declaration_key")
        return {
            "model_name": model_name,
            "action_id": action,
            "view_type": view,
            "columns": list(columns),
            "fact_columns": list(columns),
            "preference_policy": policy,
            "sources": sources,
            "policy_declarations": (
                [declared_lock.get("source")] if declared_lock else []
            ),
            "source_kind": cls.SOURCE_KIND,
        }

    # ------------------------------------------------------------- fact readers
    @classmethod
    def _assert_caller_can_read(cls, env, model_name: str) -> None:
        """Refuse a surface the caller cannot read instead of declaring columns.

        A declared column inventory is only meaningful for a surface the caller
        may actually read. Without this gate a revoked model right would still
        receive the declared columns from a registered profile, which reports a
        surface the principal has no access to. Fail closed instead.
        """
        if model_name not in env:
            raise ListPreferencePolicyError(400, f"model 无效: {model_name or '?'}")
        checker = getattr(env[model_name], "check_access_rights", None)
        if not callable(checker):
            return
        try:
            checker("read", raise_exception=True)
        except Exception:
            raise ListPreferencePolicyError(
                403, f"list preference policy refused: no read access on {model_name}"
            )

    @classmethod
    def _readable_fields(cls, env, model_name: str) -> set[str]:
        if model_name not in env:
            return set()
        model = env[model_name]
        fields_map = getattr(model, "_fields", None)
        if not isinstance(fields_map, dict):
            return set()
        names = [name for name in fields_map if name and not name.startswith("_")]
        checker = getattr(model, "check_field_access_rights", None)
        if not callable(checker):
            return set(names)
        try:
            checker("read", list(names))
            return set(names)
        except Exception:
            readable: set[str] = set()
            for name in names:
                try:
                    checker("read", [name])
                    readable.add(name)
                except Exception:
                    continue
            return readable

    @classmethod
    def _registered_columns(cls, env, model_name: str) -> list[str]:
        try:
            from ..utils.contract_governance_registry import legacy_standard_list_profiles
        except Exception:
            return []
        readable = cls._readable_fields(env, model_name)
        columns: list[str] = []
        for profile in legacy_standard_list_profiles():
            if str(profile.get("model_name") or "").strip() != model_name:
                continue
            for name in profile.get("columns_order") or []:
                name = str(name or "").strip()
                if not name or name in columns:
                    continue
                if readable and name not in readable:
                    continue
                columns.append(name)
        return columns

    @classmethod
    def _native_columns(cls, env, model_name: str, action_id: int, view_type: str) -> list[str]:
        if model_name not in env:
            return []
        view_id = 0
        if action_id > 0 and "ir.actions.act_window" in env:
            try:
                for ref in env["ir.actions.act_window"].browse(action_id).view_ids:
                    if str(ref.view_mode or "") in ("tree", "list"):
                        view_id = int(ref.view_id.id or 0)
                        break
            except Exception:
                view_id = 0
        arch = ""
        try:
            view = env[model_name].get_view(view_id or False, "tree" if view_type in ("list", "tree") else view_type)
            arch = view.get("arch") or ""
        except Exception:
            return []
        if not arch:
            return []
        try:
            root = ET.fromstring(arch)
        except ET.ParseError:
            return []
        ordered: list[str] = []
        for node in root.iter("field"):
            name = str(node.get("name") or "").strip()
            if name and name not in ordered:
                ordered.append(name)
        readable = cls._readable_fields(env, model_name)
        return [name for name in ordered if not readable or name in readable]

    @classmethod
    def _published_columns(cls, env, model_name: str, action_id: int) -> tuple[list[str], dict]:
        if "ui.business.config.contract" not in env:
            return [], {}
        try:
            configs = env["ui.business.config.contract"]._effective_view_orchestration_contracts(
                model_name,
                view_type="tree",
                action_id=action_id or None,
                view_id=None,
                role_key=None,
            )
        except Exception:
            return [], {}
        readable = cls._readable_fields(env, model_name)
        columns: list[str] = []
        policy: dict = {}
        for config in configs or []:
            contract_json = getattr(config, "contract_json", None)
            if not isinstance(contract_json, dict):
                continue
            spec = (((contract_json.get("view_orchestration") or {}).get("views") or {}).get("tree") or {})
            if not isinstance(spec, dict):
                continue
            raw = spec.get("columns")
            ordered: list[tuple[int, str]] = []
            if isinstance(raw, list):
                for index, item in enumerate(raw):
                    if isinstance(item, dict):
                        name = str(item.get("name") or "").strip()
                        try:
                            sequence = int(item.get("sequence"))
                        except (TypeError, ValueError):
                            sequence = index
                    else:
                        name = str(item or "").strip()
                        sequence = index
                    if name:
                        ordered.append((sequence, name))
            for _sequence, name in sorted(ordered, key=lambda row: row[0]):
                if name in columns:
                    continue
                if readable and name not in readable:
                    continue
                columns.append(name)
            declared = spec.get("preference_policy")
            if isinstance(declared, dict):
                policy.update({
                    "scope": str(declared.get("scope") or cls.DEFAULT_SCOPE),
                    "allow_visibility": declared.get("allow_visibility") is not False,
                    "allow_order": declared.get("allow_order") is not False,
                    "allow_width": declared.get("allow_width") is not False,
                    "locked_columns": [
                        str(name or "").strip()
                        for name in (declared.get("locked_columns") if isinstance(declared.get("locked_columns"), list) else [])
                        if str(name or "").strip()
                    ],
                })
        return columns, policy
