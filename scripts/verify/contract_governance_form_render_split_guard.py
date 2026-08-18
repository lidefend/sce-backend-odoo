#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "addons/smart_core/utils/contract_governance.py"
FORM_RENDER = ROOT / "addons/smart_core/utils/contract_governance_form_render.py"
UI_CONTRACT_V2 = ROOT / "addons/smart_core/handlers/ui_contract_v2.py"
CI = ROOT / "make/ci.mk"

MAX_GOVERNANCE_LINES = 3169


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    errors: list[str] = []
    governance_text = _read(GOVERNANCE)
    form_render_text = _read(FORM_RENDER)
    ui_contract_v2_text = _read(UI_CONTRACT_V2)
    ci_text = _read(CI)

    if not governance_text:
        errors.append(f"missing governance file: {GOVERNANCE.relative_to(ROOT)}")
    if not form_render_text:
        errors.append(f"missing form render module: {FORM_RENDER.relative_to(ROOT)}")

    if governance_text:
        line_count = len(governance_text.splitlines())
        if line_count > MAX_GOVERNANCE_LINES:
            errors.append(f"contract_governance.py line budget exceeded: {line_count} > {MAX_GOVERNANCE_LINES}")
        for token in [
            "def _load_form_render_module()",
            "contract_governance_form_render.py",
            "return _form_render.to_bool(value, fallback=fallback)",
            "return _form_render.resolve_render_profile(data)",
            "_form_render.apply_form_view_capabilities(data)",
        ]:
            if token not in governance_text:
                errors.append(f"contract_governance.py missing form render split token: {token}")

    if form_render_text:
        for token in [
            "def to_bool(",
            "def resolve_render_profile(",
            "def apply_form_view_capabilities(",
            "_RENDER_PROFILE_CREATE",
            "_RENDER_PROFILE_EDIT",
            "_RENDER_PROFILE_READONLY",
            'capabilities["modelRights"] = model_rights',
            'capabilities["recordRights"] = record_rights',
            'capabilities["viewCapabilities"] = view_capabilities',
            'capabilities["entryCapabilities"] = entry_capabilities',
            'capabilities["effectiveRecordCapabilities"] = effective_capabilities',
            'capabilities["effectiveRenderProfile"] = effective_profile',
        ]:
            if token not in form_render_text:
                errors.append(f"form render module missing token: {token}")
        for token in (".search(", ".write(", "requests.", "env[", "registry["):
            if token in form_render_text:
                errors.append(f"form render module must remain projection-only; found token: {token}")

    if "python3 scripts/verify/contract_governance_form_render_split_guard.py" not in ci_text:
        errors.append("ci.local.quick must run contract_governance_form_render_split_guard.py")
    if "PageAssembler._merge_entry_context(current_context, request_context)" not in ui_contract_v2_text:
        errors.append("V2 request context merge must preserve sticky action CRUD restrictions")

    if not errors:
        governance = _load(GOVERNANCE, "contract_governance_form_render_split_under_guard")
        if not governance._to_bool("yes") or governance._to_bool("off", fallback=True):
            errors.append("boolean coercion must preserve existing truthy/falsy tokens")
        if governance._resolve_render_profile({"head": {"view_type": "tree"}}) != governance._RENDER_PROFILE_EDIT:
            errors.append("non-form views must resolve to edit render profile")
        readonly = {
            "head": {"view_type": "form", "permissions": {"write": False, "create": False}},
            "permissions": {"effective": {"rights": {"write": False, "create": False}}},
        }
        if governance._resolve_render_profile(readonly) != governance._RENDER_PROFILE_READONLY:
            errors.append("no write/create rights must resolve readonly profile")
        create = {
            "head": {"view_type": "form", "permissions": {"write": True, "create": True}},
            "permissions": {"effective": {"rights": {"write": True, "create": True}}},
            "res_id": "new",
        }
        if governance._resolve_render_profile(create) != governance._RENDER_PROFILE_CREATE:
            errors.append("new record must resolve create profile")
        edit = dict(create)
        edit["res_id"] = "42"
        if governance._resolve_render_profile(edit) != governance._RENDER_PROFILE_EDIT:
            errors.append("persisted record id must resolve edit profile")

        operations = ("read", "write", "create", "unlink", "duplicate")

        def project(*, profile="edit", record_id="42", native=None, acl=None, record=None, context=None):
            native_rights = {
                "can_create": True,
                "can_write": True,
                "can_delete": True,
                "can_duplicate": True,
                **(native or {}),
            }
            acl_rights = {
                "read": True,
                "write": True,
                "create": True,
                "unlink": True,
                **(acl or {}),
            }
            row = {
                "render_profile": profile,
                "res_id": record_id,
                "context": dict(context or {}),
                "views": {"form": {"capabilities": native_rights}},
                "permissions": {
                    "effective": {"rights": dict(acl_rights)},
                    "record": {"rights": {**{operation: True for operation in operations}, **(record or {})}},
                },
                "head": {"permissions": dict(acl_rights)},
            }
            governance._apply_form_view_capabilities(row)
            if row["permissions"]["effective"]["rights"] != acl_rights:
                errors.append("capability projection must not overwrite model ACL facts")
            if row["head"]["permissions"] != acl_rights:
                errors.append("capability projection must not overwrite head ACL facts")
            return row["views"]["form"]["capabilities"]

        expected_by_profile = {
            "create": {"read": True, "write": False, "create": True, "unlink": False, "duplicate": False},
            "edit": {operation: True for operation in operations},
            "readonly": {operation: True for operation in operations},
        }
        for profile, expected in expected_by_profile.items():
            projected = project(profile=profile, record_id="new" if profile == "create" else "42")
            actual = projected["effectiveRecordCapabilities"]
            if actual != expected:
                errors.append(f"{profile} capability matrix mismatch: {actual!r} != {expected!r}")
            expected_profile = "readonly" if profile == "readonly" else profile
            if projected["effectiveRenderProfile"] != expected_profile:
                errors.append(f"{profile} effective render profile mismatch")

        native_denied = project(native={"can_write": False, "can_duplicate": False})["effectiveRecordCapabilities"]
        if native_denied["write"] or native_denied["duplicate"]:
            errors.append("native form root denial must survive permissive ACL/context/profile layers")
        acl_denied_projection = project(acl={"write": False, "create": False})
        acl_denied = acl_denied_projection["effectiveRecordCapabilities"]
        if acl_denied["write"] or acl_denied["create"] or acl_denied["duplicate"]:
            errors.append("model ACL denial must survive permissive native/context/profile layers")
        if acl_denied_projection["effectiveRenderProfile"] != "readonly":
            errors.append("backend must downgrade an unauthorized edit request to readonly")
        create_denied_projection = project(profile="create", record_id="new", acl={"create": False})
        if create_denied_projection["effectiveRecordCapabilities"]["create"]:
            errors.append("create denial must remain fail closed")
        if create_denied_projection["effectiveRenderProfile"] != "create":
            errors.append("denied create must keep create identity for explicit access rejection")
        create_only_edit = project(profile="edit", native={"can_write": False, "can_create": True})
        if create_only_edit["effectiveRenderProfile"] != "readonly" or not create_only_edit["effectiveRecordCapabilities"]["create"]:
            errors.append("create-only native form must downgrade persisted edit while retaining create capability")
        edit_only_edit = project(profile="edit", native={"can_write": True, "can_create": False})
        if edit_only_edit["effectiveRenderProfile"] != "edit" or edit_only_edit["effectiveRecordCapabilities"]["create"]:
            errors.append("edit-only native form must retain edit while denying create")
        edit_only_create = project(profile="create", record_id="new", native={"can_write": True, "can_create": False})
        if edit_only_create["effectiveRenderProfile"] != "create" or edit_only_create["effectiveRecordCapabilities"]["create"]:
            errors.append("edit-only native form must explicitly reject a create entry")
        record_denied = project(record={"write": False, "unlink": False, "duplicate": False})["effectiveRecordCapabilities"]
        if record_denied["write"] or record_denied["unlink"] or record_denied["duplicate"]:
            errors.append("record-rule denial must survive permissive model/view/entry layers")
        record_read_denied = project(record={"read": False})["effectiveRecordCapabilities"]
        if record_read_denied["read"] or record_read_denied["write"] or record_read_denied["unlink"] or record_read_denied["duplicate"]:
            errors.append("record read denial must close every persisted-record mutation capability")
        context_denied = project(context={"edit": "false", "delete": 0, "no_duplicate": True})["effectiveRecordCapabilities"]
        if context_denied["write"] or context_denied["unlink"] or context_denied["duplicate"]:
            errors.append("action context denial must survive permissive native/ACL/profile layers")
        invalid_record = project(profile="edit", record_id="not-a-record")["effectiveRecordCapabilities"]
        if invalid_record["unlink"] or invalid_record["duplicate"]:
            errors.append("invalid record identity must fail closed for unlink and duplicate")

    if errors:
        print("[contract_governance_form_render_split_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[contract_governance_form_render_split_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
