#!/usr/bin/env python3
"""Static scope and architecture guard for the isolated scene-driver lab."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GENERIC_ROOT = ROOT / "frontend/packages/ui"
SPIKE_ROOT = ROOT / "frontend/apps/scene-ui5-spike"

ALLOWED_PREFIXES = (
    "frontend/packages/ui/",
    "frontend/apps/scene-ui5-spike/",
    "frontend/pnpm-lock.yaml",
    "make/frontend.mk",
    "docs/ops/iterations/delivery_context_switch_log_v1.md",
    "docs/architecture/scene_component_driver_foundation_v1.md",
    "scripts/verify/frontend_ui5_scene_spike_",
)

FORBIDDEN_GENERIC_TERMS = (
    "payment.request",
    "sc.payment.execution",
    "action_create_payment_execution",
    "fixture_role_finance",
    "FE Company A",
    "华东智造中心",
    "付款申请记录",
)

FORBIDDEN_RUNTIME_TERMS = (
    "fetch(",
    "axios",
    "/api/",
    "xmlrpc",
    "jsonrpc",
    "sessionStorage",
)


def fail(message: str) -> None:
    raise SystemExit(f"[verify.frontend.ui5_scene_spike.guard] FAIL {message}")


def changed_paths() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return paths


def read_sources(root: Path) -> str:
    suffixes = {".ts", ".vue", ".js", ".mjs", ".css", ".html", ".json"}
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.suffix in suffixes
        and not {"node_modules", "dist"}.intersection(path.parts)
    )


def main() -> None:
    if not GENERIC_ROOT.is_dir() or not SPIKE_ROOT.is_dir():
        fail("expected generic UI package and isolated spike app")

    outside = [
        path
        for path in changed_paths()
        if not any(path == prefix or path.startswith(prefix) for prefix in ALLOWED_PREFIXES)
    ]
    if outside:
        fail(f"change outside spike allowlist: {outside}")

    generic = read_sources(GENERIC_ROOT)
    fixture = read_sources(SPIKE_ROOT)

    leaked = [term for term in FORBIDDEN_GENERIC_TERMS if term in generic]
    if leaked:
        fail(f"industry facts leaked into generic package: {leaked}")

    runtime_calls = [term for term in FORBIDDEN_RUNTIME_TERMS if term in generic or term in fixture]
    if runtime_calls:
        fail(f"spike must remain static and side-effect free: {runtime_calls}")

    component = GENERIC_ROOT / "src/components/SceneObjectPage.vue"
    contract = GENERIC_ROOT / "src/contracts/sceneObjectPage.ts"
    payment_fixture = SPIKE_ROOT / "src/fixtures/paymentRequestScene.ts"
    notice_component = GENERIC_ROOT / "src/components/primitives/SceneNotice.vue"
    table_component = GENERIC_ROOT / "src/components/primitives/SceneRelationTable.vue"
    review_component = GENERIC_ROOT / "src/components/primitives/SceneReviewPanel.vue"
    collection_component = GENERIC_ROOT / "src/components/SceneCollectionSurface.vue"
    hierarchy_component = GENERIC_ROOT / "src/components/SceneHierarchySurface.vue"
    collection_contract = GENERIC_ROOT / "src/contracts/sceneCollection.ts"
    normalized_adapter = GENERIC_ROOT / "src/contracts/normalizedCollectionAdapter.ts"
    for expected in (
        component,
        contract,
        payment_fixture,
        notice_component,
        table_component,
        review_component,
        collection_component,
        hierarchy_component,
        collection_contract,
        normalized_adapter,
    ):
        if not expected.is_file():
            fail(f"missing {expected.relative_to(ROOT)}")

    component_text = component.read_text(encoding="utf-8")
    if "ui5-" in component_text or "@ui5/" in component_text:
        fail("SceneObjectPage must depend only on renderer-neutral component ports")

    provider_text = (GENERIC_ROOT / "src/components/SceneUiProvider.vue").read_text(encoding="utf-8")
    registry_text = (GENERIC_ROOT / "src/kits/registry.ts").read_text(encoding="utf-8")
    if "loadSceneUiDriver" not in provider_text:
        fail("provider must consume the renderer-neutral driver registry")
    if "import('./ui5/register')" not in registry_text or "import('./tdesign/register')" not in registry_text:
        fail("vendor drivers must remain behind dynamic import boundaries")
    if "isUi5" in generic:
        fail("generic components must not branch through a vendor-specific boolean")
    if "row.values.document" in generic or "row.values.name" in generic or "row.values.status" in generic:
        fail("collection surfaces must not infer row semantics from business field names")

    vendor_import_violations = []
    for path in sorted((GENERIC_ROOT / "src").rglob("*")):
        if not path.is_file() or path.suffix not in {".ts", ".vue"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "@ui5/" in text and "/kits/ui5/" not in path.as_posix():
            vendor_import_violations.append(path.relative_to(ROOT).as_posix())
        if "tdesign-vue-next" in text and "/kits/tdesign/" not in path.as_posix():
            vendor_import_violations.append(path.relative_to(ROOT).as_posix())
    if vendor_import_violations:
        fail(f"vendor imports escaped driver adapters: {sorted(set(vendor_import_violations))}")

    preference = (SPIKE_ROOT / "src/driverPreference.ts").read_text(encoding="utf-8")
    if preference.count("localStorage.setItem") != 2:
        fail("lab may persist only the explicit driver and design-token preferences")
    if "sc.scene.ui.driver" not in preference or "sc.scene.ui.tokens" not in preference:
        fail("lab preference storage keys must stay explicit and non-sensitive")
    app_text = (SPIKE_ROOT / "src/App.vue").read_text(encoding="utf-8")
    state_ports = ("fieldValues", "reviewPanelOpen", "selectedRowIds", "expandedNodeIds")
    if any(state_port not in app_text for state_port in state_ports):
        fail("editable, collection, hierarchy, and panel state must remain above the replaceable driver provider")
    adapter_text = normalized_adapter.read_text(encoding="utf-8")
    if "adaptReadonlyNormalizedCollection" not in app_text or "scene_collection_pilot" not in app_text:
        fail("normalized collection pilot must require both the adapter and explicit feature flag")
    adapter_guards = (
        "pilot requires explicit read-only page authority",
        "read-only pilot forbids row selection",
        "read-only pilot forbids normalized actions",
        "list profile lacks formal normalized source authority",
    )
    if any(marker not in adapter_text for marker in adapter_guards):
        fail("normalized collection adapter must fail closed on authority, selection, and actions")
    if "sourceTrace" not in adapter_text or "normalized-collection" not in adapter_text:
        fail("normalized collection source identity must remain observable")

    preference_contract = (GENERIC_ROOT / "src/kits/preference.ts").read_text(encoding="utf-8")
    preference_order = (
        "'organization-lock'",
        "'preview'",
        "'user'",
        "'organization-default'",
        "'system-default'",
        "'safe-default'",
    )
    positions = [preference_contract.find(source) for source in preference_order]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        fail("driver preference authority must be organization lock -> preview -> user -> organization -> system -> safe")
    if "data-preference-source" not in app_text:
        fail("resolved driver preference authority must remain observable")

    token_contract = (GENERIC_ROOT / "src/kits/tokens.ts").read_text(encoding="utf-8")
    if "SceneDesignTokenProfileId" not in token_contract or "accessible-contrast" not in token_contract:
        fail("renderer-neutral design-token compatibility profile is missing")
    if "ui5" in token_contract.lower() or "tdesign" in token_contract.lower():
        fail("design-token profiles must not contain vendor identities")
    if "data-scene-token-profile" not in provider_text or "--sc-scene-focus" not in provider_text:
        fail("provider must expose the active semantic token profile and focus token")

    package = json.loads((GENERIC_ROOT / "package.json").read_text(encoding="utf-8"))
    dependencies = package.get("dependencies", {})
    if dependencies.get("tdesign-vue-next") != "1.20.5":
        fail("TDesign driver dependency must stay exact and reviewable")
    if dependencies.get("@ui5/webcomponents") != "2.25.0":
        fail("UI5 driver dependency must stay exact and reviewable")
    ui5_register = (GENERIC_ROOT / "src/kits/ui5/register.ts").read_text(encoding="utf-8")
    ui5_bootstrap = (GENERIC_ROOT / "src/kits/ui5/bootstrap.ts").read_text(encoding="utf-8")
    if "@ui5/webcomponents/dist/Assets.js" in ui5_register:
        fail("UI5 all-locale asset catalog must not inflate the optional driver bundle")
    if "setDefaultFontLoading(false)" not in ui5_bootstrap:
        fail("UI5 must not load default fonts from a third-party CDN")
    if "registerLocaleDataLoader('zh_CN'" not in ui5_bootstrap or "registerI18nLoader('@ui5/webcomponents'" not in ui5_bootstrap:
        fail("UI5 supported locale assets must be explicitly self-hosted")
    ui5_primitive_modules = {
        "./primitives/alert": "MessageStrip.js",
        "./primitives/table": "Table.js",
        "./primitives/drawer": "Dialog.js",
    }
    for module, vendor_primitive in ui5_primitive_modules.items():
        primitive_path = GENERIC_ROOT / "src/kits/ui5" / f"{module[2:]}.ts"
        if module not in ui5_register or not primitive_path.is_file():
            fail(f"UI5 primitive must be dynamically registered: {module}")
        if vendor_primitive not in primitive_path.read_text(encoding="utf-8"):
            fail(f"UI5 primitive adapter is incomplete: {module}")
    tdesign_register = (GENERIC_ROOT / "src/kits/tdesign/register.ts").read_text(encoding="utf-8")
    tdesign_primitives = ("es/alert", "es/table", "es/drawer")
    if any(primitive not in tdesign_register for primitive in tdesign_primitives):
        fail("TDesign driver must register alert, relation-table, and review-panel primitives")
    if "defineAsyncComponent" not in tdesign_register:
        fail("TDesign heavy enterprise primitives must remain lazy inside the driver")
    if "data-scene-driver-fallback" not in provider_text or "fallbackKit" not in provider_text:
        fail("provider must expose an observable safe driver fallback")
    theme_bridge = GENERIC_ROOT / "src/kits/tdesign/theme.css"
    if "--td-brand-color: var(--sc-scene-brand)" not in theme_bridge.read_text(encoding="utf-8"):
        fail("TDesign visual values must be bridged from SC scene tokens")

    required_markers = (
        "data-task-canvas",
        "data-context-rail",
        "data-activity-tabs",
        "data-relation-zone",
        "data-scene-notices",
        "scene-worktabs",
        "@media (max-width: 640px)",
    )
    missing = [marker for marker in required_markers if marker not in component_text]
    if missing:
        fail(f"missing scene foundation markers: {missing}")

    print(
        "[verify.frontend.ui5_scene_spike.guard] PASS "
        "scope=isolated drivers=3 generic_contract=true renderer_port=true business_runtime_io=0"
    )


if __name__ == "__main__":
    main()
