#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "frontend/apps/web/src/app/renderers/actionSurfaceRendererRegistry.ts"
HOST = ROOT / "frontend/apps/web/src/components/action/ActionSurfaceRendererHost.vue"
ACTION_VIEW = ROOT / "frontend/apps/web/src/views/ActionView.vue"
ACTION_DRIVER = ROOT / "frontend/apps/web/src/app/action_runtime/useActionViewSceneComponentDriverRuntime.ts"
V2_TYPES = ROOT / "frontend/apps/web/src/app/contracts/v2/types.ts"
V2_SCHEMA = ROOT / "frontend/apps/web/src/app/contracts/v2/schema.ts"
V2_ASSEMBLER = ROOT / "addons/smart_core/core/unified_page_contract_v2_assembler.py"


def main() -> int:
    registry = REGISTRY.read_text(encoding="utf-8")
    host = HOST.read_text(encoding="utf-8")
    action_view = ACTION_VIEW.read_text(encoding="utf-8")
    action_driver = ACTION_DRIVER.read_text(encoding="utf-8")
    v2_types = V2_TYPES.read_text(encoding="utf-8")
    v2_schema = V2_SCHEMA.read_text(encoding="utf-8")
    v2_assembler = V2_ASSEMBLER.read_text(encoding="utf-8")
    errors: list[str] = []
    for semantic in ("table", "card", "workflow_board", "hierarchy_browser", "hierarchy_planner", "pivot", "graph", "calendar", "gantt", "activity", "dashboard"):
        if f"semantic: '{semantic}'" not in registry:
            errors.append(f"missing renderer registration: {semantic}")
    for semantic in ("pivot", "graph", "calendar", "gantt", "dashboard"):
        marker = f"semantic: '{semantic}'"
        row = next((line for line in registry.splitlines() if marker in line), "")
        if "status: 'fallback'" not in row or "core.readable_records" not in row:
            errors.append(f"complex renderer must use governed readable fallback: {semantic}")
        if f"'{semantic}'" not in v2_types or f"value === '{semantic}'" not in v2_schema or f'"{semantic}"' not in v2_assembler:
            errors.append(f"complex renderer semantic is not synchronized through contract v2: {semantic}")
    activity_row = next((line for line in registry.splitlines() if "semantic: 'activity'" in line), "")
    if "status: 'ready'" not in activity_row or "activeRendererKey: 'core.activity'" not in activity_row or "outlet: 'standard'" not in activity_row:
        errors.append("activity renderer must use the native ready standard outlet")
    frontend_map = (ROOT / "contracts/product/native-view-frontend-capability-map-v1.yaml").read_text(encoding="utf-8")
    activity_mapping = next((line for line in frontend_map.splitlines() if "id: activity," in line), "")
    if "renderer_key: 'registry:core.activity'" not in activity_mapping or "reason_code: CAPABILITY_INTERACTION_EVIDENCE_MISSING" not in activity_mapping:
        errors.append("activity capability classification must identify the professional renderer without claiming static interaction readiness")
    for activity_marker in ("activityProfile", "ActivityPage", "resolveActivitySurfaceModel"):
        target = v2_assembler if activity_marker == "activityProfile" else action_view
        if activity_marker not in target:
            errors.append(f"activity renderer terminal chain missing: {activity_marker}")
    for needle, message in (
        ("ACTION_SURFACE_RENDERER_COMPONENTS", "renderer host must use the centralized component map"),
        (":is=\"rendererComponent\"", "renderer host must dispatch components dynamically"),
        ("data-renderer-status", "renderer host must expose renderer status for acceptance"),
        ("ActionSurfaceRendererHost", "ActionView must delegate surface selection to the renderer host"),
        ("surfaceRendererDescriptor", "ActionView must consume the centralized renderer descriptor"),
    ):
        if needle in {"ACTION_SURFACE_RENDERER_COMPONENTS", ':is="rendererComponent"', "data-renderer-status"}:
            target = host
        elif needle == "resolveActionSurfaceRenderer":
            target = action_driver
        else:
            target = action_view
        if needle not in target:
            errors.append(message)
    for forbidden, message in (
        ("hierarchyBrowserConfig", "ActionView must not keep a hierarchy-specific dispatch branch"),
        ('v-else-if="hierarchyBrowserConfig"', "ActionView must not dispatch hierarchy directly"),
        ("import HierarchyBrowser", "ActionView must not import a specialized surface renderer"),
    ):
        if forbidden in action_view:
            errors.append(message)
    if "ACTION_SURFACE_RENDERER_NOT_REGISTERED" not in registry:
        errors.append("unknown renderer semantics must fail closed with a stable reason code")
    if errors:
        print("[action-surface-renderer-architecture] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[action-surface-renderer-architecture] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
