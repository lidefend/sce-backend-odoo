#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE = ROOT / "addons/smart_core/utils/contract_governance.py"
LIST_SURFACE = ROOT / "addons/smart_core/utils/contract_governance_list_surface.py"
INDUSTRY_PROFILES = ROOT / "addons/smart_construction_core/core_extension.py"
CI = ROOT / "make/ci.mk"

MAX_GOVERNANCE_LINES = 1973

# The construction-industry default product owns the project lifecycle
# value-to-tone map; the kernel only projects it.  This guard proves both
# halves of that split so neither side can drift silently.
PROJECT_LIST_PROFILE_KEY = "project.project.list"
STATUS_TONE_VOCABULARY = frozenset({"neutral", "info", "success", "warning", "danger"})


def _declared_list_profiles(source: Path) -> dict[str, dict]:
    """Read the literal `register_legacy_standard_list_profile` declarations."""
    if not source.is_file():
        return {}
    tree = ast.parse(source.read_text(encoding="utf-8"))
    profiles: dict[str, dict] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "register_legacy_standard_list_profile":
            continue
        if not node.args:
            continue
        try:
            payload = ast.literal_eval(node.args[0])
        except (ValueError, SyntaxError):
            continue
        if not isinstance(payload, dict):
            continue
        key = str(payload.get("profile_key") or payload.get("model_name") or "").strip()
        if key:
            profiles[key] = payload
    return profiles


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
    list_surface_text = _read(LIST_SURFACE)
    ci_text = _read(CI)

    if not governance_text:
        errors.append(f"missing governance file: {GOVERNANCE.relative_to(ROOT)}")
    if not list_surface_text:
        errors.append(f"missing list surface module: {LIST_SURFACE.relative_to(ROOT)}")

    if governance_text:
        line_count = len(governance_text.splitlines())
        if line_count > MAX_GOVERNANCE_LINES:
            errors.append(f"contract_governance.py line budget exceeded: {line_count} > {MAX_GOVERNANCE_LINES}")
        for token in [
            "def _load_list_surface_module()",
            "contract_governance_list_surface.py",
            "_list_surface.govern_standard_list_for_user(",
            "def _apply_standard_search_toolbar_labels(data: dict) -> None:",
            "_list_surface.apply_standard_search_toolbar_labels(data)",
            "def _govern_tier_review_list_for_user(data: dict) -> None:",
            "_list_surface.govern_tier_review_list_for_user(",
            "nav_action_prefixes=_TIER_REVIEW_LIST_NAV_ACTION_PREFIXES",
        ]:
            if token not in governance_text:
                errors.append(f"contract_governance.py missing list surface split token: {token}")

    if list_surface_text:
        for token in [
            "def apply_standard_search_toolbar_labels(",
            "def govern_standard_list_for_user(",
            "def govern_tier_review_list_for_user(",
            "STATUS_TONE_VOCABULARY",
            "def normalize_status_tone_by_value(",
            "\"source\": \"contract_governance.curated_list_facts\"",
            "\"owner_layer\"] = \"scene_orchestration\"",
            "\"row_open\": \"打开\"",
            "payload[\"view_mode\"] = payload.get(\"view_mode\") or \"form\"",
            "mark_legacy_industry_governance_profile(data, \"tier.review.list\")",
            "key.startswith(prefix) for prefix in nav_action_prefixes",
        ]:
            if token not in list_surface_text:
                errors.append(f"list surface module missing token: {token}")
        for token in (".search(", ".write(", "requests.", "env[", "registry["):
            if token in list_surface_text:
                errors.append(f"list surface module must remain projection-only; found token: {token}")
        # Status tone authority belongs to the declaring profile.  The kernel
        # projects a declaration; it must never carry a business value-to-tone
        # map of its own, so any known lifecycle value reappearing here is a
        # re-introduced silent default.
        for token in ('"draft"', '"in_progress"', '"paused"', '"done"', '"closing"', '"warranty"', '"closed"'):
            if token in list_surface_text:
                errors.append(
                    "list surface must not hardcode business status values; found token: " + token
                )

    if "python3 scripts/verify/contract_governance_list_surface_split_guard.py" not in ci_text:
        errors.append("ci.local.quick must run contract_governance_list_surface_split_guard.py")

    if not errors:
        governance = _load(GOVERNANCE, "contract_governance_list_surface_split_under_guard")
        data = {
            "search": {},
            "views": {
                "tree": {
                    "row_actions": [
                        {"name": "open_form", "payload": {}},
                    ],
                },
            },
        }
        governance._apply_standard_search_toolbar_labels(data)
        labels = ((data.get("search") or {}).get("ui_labels") or {})
        action = (((data.get("views") or {}).get("tree") or {}).get("row_actions") or [{}])[0]
        if labels.get("row_open") != "打开":
            errors.append("list surface labels must include row_open")
        if action.get("label") != "打开" or (action.get("payload") or {}).get("view_mode") != "form":
            errors.append("list surface row open action semantics were not applied")

        tier_data = {
            "model": "tier.review",
            "view_type": "tree",
            "buttons": [
                {"key": "open_record", "label": "Open"},
                {"key": "action_tier_review_open_form", "label": "Open form"},
            ],
            "toolbar": {
                "header": [
                    {"key": "action_tier_review_open_form"},
                    {"key": "bulk_approve"},
                ],
                "footer": [{"key": "action_tier_review_open_related"}],
            },
            "action_groups": [
                {
                    "name": "main",
                    "actions": [
                        {"key": "action_tier_review_open_form"},
                        {"key": "approve"},
                    ],
                },
                {
                    "name": "empty",
                    "actions": [{"key": "action_tier_review_open_related"}],
                },
            ],
        }
        governance._govern_tier_review_list_for_user(tier_data)
        if [row.get("key") for row in tier_data.get("buttons", [])] != [
            "open_record",
            "action_tier_review_open_form",
        ]:
            errors.append("tier review facade must preserve actions when no navigation prefixes are configured")
        profiles = (tier_data.get("governance_diagnostics") or {}).get("legacy_industry_profiles") or []
        if "tier.review.list" not in profiles:
            errors.append("tier review list must keep its legacy governance profile marker")

        list_surface = _load(LIST_SURFACE, "contract_governance_list_surface_direct_under_guard")
        filtered_data = {
            "buttons": [
                {"key": "open_record", "label": "Open"},
                {"key": "action_tier_review_open_form", "label": "Open form"},
            ],
            "toolbar": {
                "header": [
                    {"key": "action_tier_review_open_form"},
                    {"key": "bulk_approve"},
                ],
                "footer": [{"key": "action_tier_review_open_related"}],
            },
            "action_groups": [
                {
                    "name": "main",
                    "actions": [
                        {"key": "action_tier_review_open_form"},
                        {"key": "approve"},
                    ],
                },
                {
                    "name": "empty",
                    "actions": [{"key": "action_tier_review_open_related"}],
                },
            ],
        }
        marked: list[str] = []
        list_surface.govern_tier_review_list_for_user(
            filtered_data,
            is_model_tree_contract=lambda data, model: model == "tier.review",
            mark_legacy_industry_governance_profile=lambda data, profile: marked.append(profile),
            nav_action_prefixes=("action_tier_review_",),
        )
        if [row.get("key") for row in filtered_data.get("buttons", [])] != ["open_record"]:
            errors.append("tier review list buttons must drop navigation actions when prefixes are configured")
        if [row.get("key") for row in filtered_data.get("toolbar", {}).get("header", [])] != ["bulk_approve"]:
            errors.append("tier review list toolbar must drop navigation actions when prefixes are configured")
        if filtered_data.get("toolbar", {}).get("footer") != []:
            errors.append("tier review list footer must preserve an empty filtered slot")
        groups = filtered_data.get("action_groups") or []
        if len(groups) != 1 or [row.get("key") for row in groups[0].get("actions", [])] != ["approve"]:
            errors.append("tier review list action groups must drop empty navigation-only groups")
        if marked != ["tier.review.list"]:
            errors.append("tier review list direct module path must invoke profile marker callback")

        list_data = {
            "head": {"model": "project.project", "view_type": "tree"},
            "model": "project.project",
            "governance": {"primary_model": "project.project"},
            "views": {
                "tree": {
                    "columns": [{"name": "name"}, {"name": "amount_total"}],
                    "columns_schema": [
                        {"name": "name", "label": "Native Name"},
                        {"name": "stage_id", "label": "Native Stage"},
                    ],
                    "row_actions": [{"name": "open_form", "payload": {}}],
                }
            },
            "fields": {
                "name": {"type": "char", "string": "Name"},
                "amount_total": {"type": "float", "string": "Amount"},
                "stage_id": {"type": "selection", "string": "Stage", "selection": [("draft", "Draft")]},
                "active": {"type": "boolean", "string": "Active"},
                "user_id": {"type": "many2one", "string": "Assignee"},
            },
            "permissions": {"effective": {"rights": {"write": True, "unlink": True}}},
            "delete_policy": {"delete_mode": "unlink"},
            "search": {},
        }
        list_surface.govern_standard_list_for_user(
            list_data,
            model_name="project.project",
            columns_order=["name", "stage_id", "amount_total"],
            column_labels={"amount_total": "Total"},
            row_primary="name",
            row_secondary="stage_id",
            status_field="stage_id",
            is_model_tree_contract=lambda data, model: model == "project.project",
            legacy_field_presentation=lambda model, name: {"widget": "monetary"} if name == "amount_total" else {},
            deep_clone_json_like=lambda value: dict(value) if isinstance(value, dict) else value,
            apply_standard_search_toolbar_labels=list_surface.apply_standard_search_toolbar_labels,
        )
        tree = (list_data.get("views") or {}).get("tree") or {}
        if tree.get("columns") != ["name", "stage_id", "amount_total"]:
            errors.append("standard list must merge configured columns with native columns")
        schema_by_name = {row.get("name"): row for row in tree.get("columns_schema", []) if isinstance(row, dict)}
        if schema_by_name.get("amount_total", {}).get("widget") != "monetary":
            errors.append("standard list must apply field presentation widgets")
        if schema_by_name.get("stage_id", {}).get("cell_role") != "status":
            errors.append("standard list must mark status column schema")
        batch_policy = ((list_data.get("surface_policies") or {}).get("batch_policy")) or {}
        if batch_policy.get("available_actions") != ["export", "archive", "activate", "delete"]:
            errors.append("standard list batch policy must derive export/archive/activate/delete actions")
        if batch_policy.get("execution_intents") != {
            "export": "api.data",
            "archive": "api.data.batch",
            "activate": "api.data.batch",
            "delete": "api.data.unlink",
        }:
            errors.append("standard list batch actions must bind to executable backend intents")
        if batch_policy.get("execution_operations") != {"export": "export_csv"}:
            errors.append("standard list export must bind to api.data export_csv")
        selection_policy = ((list_data.get("surface_policies") or {}).get("selection_policy")) or {}
        if not selection_policy.get("enabled") or selection_policy.get("requires_batch_action") is not False:
            errors.append("standard list selection must not disappear when no batch action is available")
        list_profile = list_data.get("list_profile") or {}
        if list_profile.get("primary_field") != "name" or list_profile.get("status_field") != "stage_id":
            errors.append("standard list profile must expose primary/status fields")
        semantics = ((list_data.get("semantic_page") or {}).get("list_semantics")) or {}
        if semantics.get("owner_layer") != "scene_orchestration":
            errors.append("standard list semantics must stay scene_orchestration owned")
        labels = ((list_data.get("search") or {}).get("ui_labels")) or {}
        if labels.get("row_open") != "打开":
            errors.append("standard list must keep toolbar/search label normalization")

        # --- status tone authority is owned by the declaring profile ---
        # 1) No declaration -> the kernel must omit tone_by_value entirely so
        #    the renderer falls back to a neutral badge instead of the kernel
        #    inventing which business states mean success or warning.
        if "tone_by_value" in schema_by_name.get("stage_id", {}):
            errors.append(
                "standard list must omit tone_by_value when the profile declares no tone map"
            )

        def _govern_with_tone_map(tone_map):
            run_data = {
                "head": {"model": "project.project", "view_type": "tree"},
                "model": "project.project",
                "governance": {"primary_model": "project.project"},
                "views": {
                    "tree": {
                        "columns": [{"name": "name"}, {"name": "stage_id"}],
                        "columns_schema": [
                            {"name": "name", "label": "Native Name"},
                            {"name": "stage_id", "label": "Native Stage"},
                        ],
                        "row_actions": [{"name": "open_form", "payload": {}}],
                    }
                },
                "fields": {
                    "name": {"type": "char", "string": "Name"},
                    "stage_id": {
                        "type": "selection",
                        "string": "Stage",
                        "selection": [("draft", "Draft"), ("closed", "Closed")],
                    },
                },
                "permissions": {"effective": {"rights": {"write": True, "unlink": True}}},
                "delete_policy": {"delete_mode": "unlink"},
                "search": {},
            }
            list_surface.govern_standard_list_for_user(
                run_data,
                model_name="project.project",
                columns_order=["name", "stage_id"],
                column_labels={},
                row_primary="name",
                row_secondary="",
                status_field="stage_id",
                status_tone_by_value=tone_map,
                is_model_tree_contract=lambda data, model: model == "project.project",
                legacy_field_presentation=lambda model, name: {},
                deep_clone_json_like=lambda value: dict(value) if isinstance(value, dict) else value,
                apply_standard_search_toolbar_labels=list_surface.apply_standard_search_toolbar_labels,
            )
            run_tree = (run_data.get("views") or {}).get("tree") or {}
            return {
                row.get("name"): row
                for row in run_tree.get("columns_schema", [])
                if isinstance(row, dict)
            }.get("stage_id") or {}

        declared = _govern_with_tone_map({"draft": "warning", "closed": "success"})
        if declared.get("tone_by_value") != {"draft": "warning", "closed": "success"}:
            errors.append("standard list must project the declared status tone map verbatim")

        filtered = _govern_with_tone_map({"draft": "primary", "closed": "success", "": "danger"})
        if filtered.get("tone_by_value") != {"closed": "success"}:
            errors.append(
                "standard list must drop tones outside the published vocabulary and empty keys"
            )

        absent = _govern_with_tone_map(None)
        if "tone_by_value" in absent:
            errors.append("standard list must not synthesize a tone map when none is declared")

        # --- the declaring profile is the counterpart owner ---
        # The kernel must not invent a tone map, so the industry default
        # product must actually declare one; otherwise the relocation would
        # quietly drop project lifecycle tones instead of moving them.
        profiles = _declared_list_profiles(INDUSTRY_PROFILES)
        if not profiles:
            errors.append(
                "industry module must declare literal register_legacy_standard_list_profile payloads"
            )
        project_profile = profiles.get(PROJECT_LIST_PROFILE_KEY) or {}
        if not project_profile:
            errors.append(f"industry module must declare the {PROJECT_LIST_PROFILE_KEY} profile")
        declared_tones = project_profile.get("tone_by_value")
        if not isinstance(declared_tones, dict) or not declared_tones:
            errors.append(
                "project.project.list must own its status tone map; the kernel no longer supplies one"
            )
        else:
            invalid = sorted(
                f"{key}={value}"
                for key, value in declared_tones.items()
                if str(value).strip().lower() not in STATUS_TONE_VOCABULARY
            )
            if invalid:
                errors.append(
                    "project.project.list declares tones outside the published vocabulary: "
                    + ", ".join(invalid)
                )
            empty_keys = [key for key in declared_tones if not str(key).strip()]
            if empty_keys:
                errors.append("project.project.list declares an empty status value key")
            projections = _govern_with_tone_map(declared_tones)
            if projections.get("tone_by_value") != declared_tones:
                errors.append(
                    "project.project.list declared tones must project verbatim into the contract"
                )

    if errors:
        print("[contract_governance_list_surface_split_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[contract_governance_list_surface_split_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
