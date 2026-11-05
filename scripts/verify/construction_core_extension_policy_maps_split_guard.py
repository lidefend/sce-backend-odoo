#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import ast
import tempfile
from xml.etree import ElementTree as ET
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import line_budgets  # noqa: E402


ROOT = Path(__file__).resolve().parents[2]
CORE_EXTENSION = ROOT / "addons/smart_construction_core/core_extension.py"
POLICY_MAPS = ROOT / "addons/smart_construction_core/core_extension_policy_maps.py"
CI = ROOT / "make/ci.mk"



def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def my_work_fact_errors(root: Path, policy_maps) -> list[str]:
    """PR #800 moved this entry to native facts, not a critical-route override.

    Exercise the real XML reader, public scene list and runtime projector with
    two different native declarations. No repository or database is mutated.
    """
    errors: list[str] = []
    scene_key = "my_work.workspace"
    if scene_key in policy_maps.CRITICAL_SCENE_TARGET_ROUTE_OVERRIDES:
        errors.append("my-work route must come from native action facts, not policy-map override")
    core = root / "addons/smart_construction_core"
    relative = "views/support/my_work_views.xml"
    try:
        manifest = ast.literal_eval(_read(core / "__manifest__.py"))
        if relative not in manifest.get("data", []):
            errors.append("native my-work action/menu must be loaded by the module manifest")
        xml = ET.parse(core / relative)
        action = xml.find(".//record[@id='action_sc_my_work']")
        menu = xml.find(".//menuitem[@id='menu_sc_my_work']")
        if action is None or action.get("model") != "ir.actions.act_window":
            raise ValueError("missing native my-work action declaration")
        if menu is None or menu.get("action") != "smart_construction_core.action_sc_my_work":
            raise ValueError("native my-work menu must bind its declared action")
        name = action.find("field[@name='name']")
        context = action.find("field[@name='context']")
        if name is None or context is None:
            raise ValueError("native my-work name/context declaration is missing")
        declared = ast.literal_eval(context.text or "")
        if (not isinstance(declared, dict) or not isinstance(declared.get("sc_web_route"), str)
                or not declared["sc_web_route"].startswith("/") or not declared.get("sc_web_surface")):
            raise ValueError("native my-work route/surface declaration is incomplete")
        # The scene extension must not reintroduce the same second authority.
        scene_extension = ast.parse(_read(root / "addons/smart_construction_scene/core_extension.py"))
        maps = [node.value for node in scene_extension.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "CRITICAL_SCENE_TARGET_ROUTE_OVERRIDES"
                        for target in node.targets)]
        if len(maps) != 1 or scene_key in ast.literal_eval(maps[0]):
            errors.append("scene extension must not override the native my-work route")
        projection = _load(root / "addons/smart_construction_scene/profiles/scene_registry_content.py",
                           "native_my_work_scene_projection_under_guard")
        runtime = _load(root / "addons/smart_core/core/navigation_entry_target.py",
                        "native_my_work_runtime_projection_under_guard")

        def verify_projection(expected_context, expected_name):
            rows = [row for row in projection.list_scene_entries() if row.get("code") == scene_key]
            if len(rows) != 1:
                errors.append("native my-work facts must produce exactly one public scene entry")
                return
            row = rows[0]
            target = row.get("target", {})
            expected = {"route": expected_context["sc_web_route"],
                        "menu_xmlid": "smart_construction_core.menu_sc_my_work",
                        "action_xmlid": "smart_construction_core.action_sc_my_work"}
            if row.get("name") != expected_name or any(target.get(k) != v for k, v in expected.items()):
                errors.append("scene projection must consume native my-work route/name and entry identities")
            projected = runtime.build_web_surface_entry_target(expected_context)
            if (projected.get("route") != expected_context["sc_web_route"]
                    or projected.get("surface") != expected_context["sc_web_surface"]):
                errors.append("runtime entry must consume the declared route and surface")

        verify_projection(declared, (name.text or "").strip())
        original_core = projection._CORE_DIR
        with tempfile.TemporaryDirectory(prefix="my-work-fact-guard-") as directory:
            fixture = Path(directory) / relative
            fixture.parent.mkdir(parents=True)
            changed = {**declared, "sc_web_route": "/__fact_guard__/maintained-work"}
            context.text = repr(changed)
            name.text = "Maintained workspace fixture"
            xml.write(fixture, encoding="unicode")
            projection._CORE_DIR = Path(directory)
            try:
                verify_projection(changed, name.text)
            finally:
                projection._CORE_DIR = original_core
    except (OSError, ValueError, TypeError, SyntaxError, ET.ParseError, AttributeError) as exc:
        errors.append(f"native my-work source/projection cannot be verified: {exc}")
    return errors


def main() -> int:
    errors: list[str] = []
    core_text = _read(CORE_EXTENSION)
    policy_text = _read(POLICY_MAPS)
    ci_text = _read(CI)

    if not core_text:
        errors.append(f"missing core extension file: {CORE_EXTENSION.relative_to(ROOT)}")
    if not policy_text:
        errors.append(f"missing policy maps module: {POLICY_MAPS.relative_to(ROOT)}")

    if core_text:
        line_count = len(core_text.splitlines())
        line_budgets.advise_size("addons/smart_construction_core/core_extension.py", line_count, label="core_extension.py")
        for token in [
            "core_extension_policy_maps as _policy_maps",
            "ROLE_SURFACE_OVERRIDES = _policy_maps.ROLE_SURFACE_OVERRIDES",
            "NAV_MENU_SCENE_MAP = _policy_maps.NAV_MENU_SCENE_MAP",
            "FILE_ATTACHMENT_ALLOWED_MODEL_EXACT = _policy_maps.FILE_ATTACHMENT_ALLOWED_MODEL_EXACT",
            "API_DATA_WRITE_ALLOWLIST = _policy_maps.API_DATA_WRITE_ALLOWLIST",
            "API_DATA_UNLINK_POLICIES = _policy_maps.API_DATA_UNLINK_POLICIES",
            "CRITICAL_SCENE_TARGET_OVERRIDES = _policy_maps.CRITICAL_SCENE_TARGET_OVERRIDES",
            "CRITICAL_SCENE_TARGET_ROUTE_OVERRIDES = _policy_maps.CRITICAL_SCENE_TARGET_ROUTE_OVERRIDES",
            "INDUSTRY_CREATE_FIELD_FALLBACKS = _policy_maps.INDUSTRY_CREATE_FIELD_FALLBACKS",
            "register_legacy_standard_list_profile({",
        ]:
            if token not in core_text:
                errors.append(f"core_extension.py missing policy-map split token: {token}")

    if policy_text:
        for token in [
            "ROLE_SURFACE_OVERRIDES = {",
            "ROLE_GROUPS_EXPLICIT = {",
            "NAV_MENU_SCENE_MAP = {",
            "LEGACY_VISIBLE_BUSINESS_COLUMN_LABELS_BY_MODEL = {",
            "API_DATA_WRITE_ALLOWLIST = {",
            "DRAFT_DELETE_ALLOWED_STATES =",
            "def _state_unlink_policy(",
            "API_DATA_DRAFT_UNLINK_POLICIES = {",
            "API_DATA_UNLINK_POLICIES.update(API_DATA_DRAFT_UNLINK_POLICIES)",
            "API_DATA_UNLINK_ALLOWED_MODELS = list(API_DATA_UNLINK_POLICIES)",
            "INDUSTRY_CREATE_FIELD_FALLBACKS = {",
        ]:
            if token not in policy_text:
                errors.append(f"policy maps module missing token: {token}")
        for forbidden in ("env[", ".search(", ".write(", "requests.", "register_", "AccessError", "fields."):
            if forbidden in policy_text:
                errors.append(f"policy maps module must remain pure constants; forbidden token: {forbidden}")

    if "python3 scripts/verify/construction_core_extension_policy_maps_split_guard.py" not in ci_text:
        errors.append("ci.local.quick must run construction_core_extension_policy_maps_split_guard.py")

    if not errors:
        policy_maps = _load(POLICY_MAPS, "construction_core_extension_policy_maps_under_guard")
        if policy_maps.ROLE_PRECEDENCE != (
            "system_admin",
            "experience",
            "business_full",
            "business_config_admin",
            "executive",
            "owner",
            "pm",
            "finance",
            "cost",
            "accounting",
        ):
            errors.append("policy maps must preserve role precedence")
        if not policy_maps.ROLE_SURFACE_OVERRIDES.get("business_config_admin", {}).get("discover_installed_capabilities"):
            errors.append("business config admin must compose ACL-visible formal product capabilities")
        if policy_maps.NAV_MENU_SCENE_MAP.get("smart_construction_core.menu_payment_request") != "finance.payment_requests":
            errors.append("policy maps must preserve payment menu scene mapping")
        if "project.project" not in policy_maps.FILE_UPLOAD_ALLOWED_MODELS:
            errors.append("policy maps must preserve project upload model")
        if "payment.request" not in policy_maps.API_DATA_UNLINK_POLICIES:
            errors.append("policy maps must preserve payment request unlink policy")
        if policy_maps.API_DATA_UNLINK_POLICIES.get("sc.quality.rectification", {}).get("state_field") != "issue_state":
            errors.append("policy maps must preserve quality rectification state field")
        errors.extend(my_work_fact_errors(ROOT, policy_maps))

    if errors:
        print("[construction_core_extension_policy_maps_split_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[construction_core_extension_policy_maps_split_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
