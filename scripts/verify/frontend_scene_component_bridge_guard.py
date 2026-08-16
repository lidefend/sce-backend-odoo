#!/usr/bin/env python3
"""Static architecture guard for the production scene-component bridge."""

from __future__ import annotations

import json
import re
import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEB_SRC = ROOT / "frontend/apps/web/src"
UI_SRC = ROOT / "frontend/packages/ui/src"


def source_files(root: Path):
    yield from root.rglob("*.ts")
    yield from root.rglob("*.vue")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"[verify.frontend.scene_component_bridge.guard] FAIL {message}")


vendor_import = re.compile(r"(?:from\s+|import\s*\()['\"](?:@ui5/|tdesign-vue-next)")
web_vendor_hits = [
    str(path.relative_to(ROOT))
    for path in source_files(WEB_SRC)
    if vendor_import.search(path.read_text(encoding="utf-8"))
]
require(not web_vendor_hits, f"vendor imports escaped driver package: {web_vendor_hits}")

business_tokens = ("payment.request", "sc.payment.execution", "付款申请")
ui_business_hits = [
    str(path.relative_to(ROOT))
    for path in source_files(UI_SRC)
    if any(token in path.read_text(encoding="utf-8") for token in business_tokens)
]
require(not ui_business_hits, f"business-specific knowledge entered generic UI package: {ui_business_hits}")

web_package = json.loads((ROOT / "frontend/apps/web/package.json").read_text(encoding="utf-8"))
require(web_package.get("dependencies", {}).get("@sc/ui") == "workspace:*", "web workspace dependency missing")

ui_package = json.loads((ROOT / "frontend/packages/ui/package.json").read_text(encoding="utf-8"))
exports = ui_package.get("exports", {})
require(exports.get("./bridge") == "./src/bridge.ts", "pure bridge export missing")
require(exports.get("./collection") == "./src/collection.ts", "collection export missing")
require(exports.get("./form") == "./src/form.ts", "form export missing")

wrapper = (WEB_SRC / "components/action/SceneReadonlyCollectionRenderer.vue").read_text(encoding="utf-8")
require("from '@sc/ui/collection'" in wrapper, "renderer must use narrow collection export")
form_host = (WEB_SRC / "pages/contractForm/ContractFormDriverHost.vue").read_text(encoding="utf-8")
require("from '@sc/ui/form'" in form_host, "form driver host must use narrow form export")
require("SceneUiProvider" in form_host and "ContractFormNativeCanvas" in form_host, "form driver does not retain the canonical form canvas")
require("data-contract-form-driver-error" in form_host, "invalid normalized form contract does not fail closed")

host = (WEB_SRC / "views/ActionView.vue").read_text(encoding="utf-8")
runtime = (WEB_SRC / "app/action_runtime/useActionViewSceneComponentDriverRuntime.ts").read_text(encoding="utf-8")
require("useActionViewSceneComponentDriverRuntime" in host, "ActionView does not delegate component-driver orchestration")
require("session.featureFlags.scene_component_drivers_v1" in host, "backend policy flag is not consumed")
require("resolveSceneReadonlyCollectionBridge" in runtime, "normalized readonly bridge is not consumed")
require("currentDecision.targeted" in runtime and "contractError" in runtime, "targeted normalized failures do not fail closed")

system_init = (ROOT / "addons/smart_core/handlers/system_init.py").read_text(encoding="utf-8")
require("platform_feature_flags_for_user_readonly" in system_init, "startup flag source is not read-only entitlement")
require("resolve_system_feature_flags" in system_init, "startup flags are not normalized")

policy = (WEB_SRC / "app/renderers/sceneComponentDriverPolicy.ts").read_text(encoding="utf-8")
for reason in (
    "SCENE_DRIVER_POLICY_DISABLED",
    "SCENE_DRIVER_PAGE_NOT_READONLY",
    "SCENE_DRIVER_MUTATION_ACTION_PRESENT",
    "SCENE_DRIVER_SELECTION_PRESENT",
    "SCENE_DRIVER_SCOPE_EMPTY",
):
    require(reason in policy, f"fail-closed reason missing: {reason}")
require("SCENE_DRIVER_FORM_MODE_UNSUPPORTED" in policy, "readonly entitlement does not constrain form mode")
require("SCENE_DRIVER_FORM_MODES_MISSING" in policy, "editable form entitlement does not fail closed without explicit modes")

form_section = (WEB_SRC / "components/template/FormSection.vue").read_text(encoding="utf-8")
require("from '@sc/ui/form'" in form_section, "form fields must consume the narrow driver-neutral UI export")
require("emitFieldChange(field, $event)" in form_section, "driver field does not reuse the canonical field-change path")
require(
    ':model-value="contractFormDriverValue(field)"' in form_section,
    "driver field value bypasses the canonical empty-value normalizer",
)
require(
    form_section.index('v-else-if="usesSceneFieldControl(field)"')
    < form_section.index('v-else-if="field.readonly"'),
    "readonly ContractForm fields bypass the selected component driver",
)
scene_field_control = (UI_SRC / "components/primitives/SceneFieldControl.vue").read_text(encoding="utf-8")
require(
    scene_field_control.count("if (props.field.readonly) return;") >= 2,
    "readonly driver controls do not fail closed before emitting changes",
)
require(
    "normalizeSceneFieldControlValue(value, props.field.kind)" in scene_field_control,
    "driver change events bypass the shared empty-value normalizer",
)
probe_fixture = (ROOT / "addons/smart_construction_acceptance_fixture/tools/component_driver_probe.py").read_text(encoding="utf-8")
probe_tree = ast.parse(probe_fixture)
probe_function = next(
    (node for node in probe_tree.body if isinstance(node, ast.FunctionDef) and node.name == "apply_component_driver_probe"),
    None,
)
require(probe_function is not None, "browser probe fixture function missing")
probe_source = ast.get_source_segment(probe_fixture, probe_function) or ""
require("\"models\": [model]" in probe_source, "browser probe must consume the action-owned model")
require("component driver probe requires a non-payment action model" in probe_source, "browser probe lacks its non-payment boundary")
require("payment.request" not in probe_source, "browser probe drifted into the payment vertical")
acceptance_fixture = (ROOT / "scripts/test/frontend_productization_fixture.sh").read_text(encoding="utf-8")
require("SC_ACCEPTANCE_COMPONENT_DRIVER_PROBE_MODE" in acceptance_fixture, "browser probe is not routed through the governed fixture entry")
browser_probe = (ROOT / "scripts/verify/frontend_scene_component_driver_readonly_browser.mjs").read_text(encoding="utf-8")
for forbidden in ("api.data.create", "api.data.write", "api.data.unlink", "execute_button"):
    require(forbidden in browser_probe, f"readonly browser probe does not detect mutation: {forbidden}")

form_page = (WEB_SRC / "pages/ContractFormPage.vue").read_text(encoding="utf-8")
require(
    form_page.index("const canSave = computed")
    < form_page.index("useContractFormComponentDriverRuntime({"),
    "immediate driver watchers must be installed after render-profile dependencies",
)

collection_surface = (UI_SRC / "components/SceneCollectionSurface.vue").read_text(encoding="utf-8")
collection_wrapper = (WEB_SRC / "components/action/SceneReadonlyCollectionRenderer.vue").read_text(encoding="utf-8")
require("openRow" in collection_surface, "readonly collection does not expose row navigation")
require("'open-record'" in collection_wrapper, "driver row navigation is not returned to the unified host")

print("[verify.frontend.scene_component_bridge.guard] PASS checks=31")
