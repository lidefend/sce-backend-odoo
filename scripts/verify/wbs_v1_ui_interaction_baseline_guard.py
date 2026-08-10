#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "scripts/verify/baselines/wbs_v1_ui_interaction_baseline.json"


def require(text: str, token: str, message: str, errors: list[str]) -> None:
    if token not in text:
        errors.append(message)


def main() -> int:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    component = (ROOT / "frontend/apps/web/src/components/action/HierarchyPlanner.vue").read_text(encoding="utf-8")
    registry = (ROOT / "frontend/apps/web/src/app/renderers/actionSurfaceRendererRegistry.ts").read_text(encoding="utf-8")
    mapping = (ROOT / "addons/smart_core/app_config_engine/models/app_view_config.py").read_text(encoding="utf-8")
    native_view = (ROOT / "addons/smart_construction_core/views/support/work_breakdown_views.xml").read_text(encoding="utf-8")
    errors: list[str] = []

    if baseline.get("decision") != "feature_baseline_frozen" or baseline.get("release_baseline") is not False:
        errors.append("baseline decision must remain feature-only and must not claim release readiness")
    for token, message in (
        ("planner-grid", "frozen outline grid missing"),
        ("outline-toggle", "frozen hierarchy expansion affordance missing"),
        ("code-cell", "frozen code depth alignment missing"),
        ("selectedEntry", "frozen selected-node context missing"),
        ("toolbarCommands", "frozen toolbar grouping missing"),
        ("activeMenu", "controlled menu state missing"),
        ("planner-drawer", "frozen detail drawer missing"),
        ("hierarchyCollectionDataSource", "contract runtime boundary missing"),
    ):
        require(component, token, message, errors)
    for forbidden in ("WBS", "project_id", "parent_id", "construction."):
        if forbidden in component:
            errors.append(f"shared planner contains business semantic: {forbidden}")
    require(registry, "semantic: 'hierarchy_planner'", "hierarchy planner renderer registration missing", errors)
    require(mapping, "'smart_hierarchy_planner': 'hierarchy_planner'", "native view semantic mapping missing", errors)
    require(native_view, 'js_class="smart_hierarchy_planner"', "WBS native view no longer selects frozen planner", errors)
    if 'js_class="smart_hierarchy_browser"' in native_view:
        errors.append("WBS view regressed to the three-pane hierarchy browser")

    if errors:
        print("[wbs-v1-ui-interaction-baseline] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[wbs-v1-ui-interaction-baseline] PASS")
    print(f"baseline_id={baseline['baseline_id']} release_baseline=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
