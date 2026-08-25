#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def validate() -> list[str]:
    failures: list[str] = []
    component = source("frontend/apps/web/src/components/product-page-header/ProductPageHeader.vue")
    model = source("frontend/apps/web/src/app/presentation/productPageHeader.ts")
    required_component = [
        "data-product-page-header", "data-presentation-mode", "data-render-profile",
        "data-dirty-state", "data-header-variant", "data-workspace-action-bar",
        ":class=\"{ 'sc-visually-hidden': hideTitle }\"", "data-title-visibility",
        "product-page-header--title-hidden", "product-page-header__status:empty",
    ]
    required_model = [
        "title", "subtitle", "breadcrumb", "presentationMode", "renderProfile", "dirtyState",
        "statusbar", "primaryAction", "overflowActions", "exitAction",
        "PRODUCT_PAGE_HEADER_PRIMARY_ACTION_MULTIPLE", "PRODUCT_PAGE_HEADER_READONLY_SAVE_FORBIDDEN",
    ]
    for marker in required_component:
        if marker not in component:
            failures.append(f"ProductPageHeader missing {marker}")
    for marker in required_model:
        if marker not in model:
            failures.append(f"header model missing {marker}")
    for adapter in (
        "frontend/apps/web/src/components/design-system/ScPageHeader.vue",
        "frontend/apps/web/src/components/page/PageHeader.vue",
        "frontend/apps/web/src/components/template/PageHeader.vue",
    ):
        if "ProductPageHeader" not in source(adapter):
            failures.append(f"header adapter bypasses ProductPageHeader: {adapter}")
    if "presentation-mode=\"collection\"" not in source("frontend/apps/web/src/components/design-system/ScPageHeader.vue"):
        failures.append("collection header does not declare collection presentation mode")
    contract = source("frontend/apps/web/src/pages/contractForm/ContractFormProductHeader.vue")
    for marker in (':presentation-mode="presentationMode"', ':render-profile="mode"', ':dirty-state="headerDirtyState"'):
        if marker not in contract:
            failures.append(f"contract header misses formal axis {marker}")
    for marker in ('canonicalActionEvidenceAttributes(action)', "'data-action-method'", "'data-action-enabled'", "'data-action-allowed'"):
        if marker not in contract:
            failures.append(f"canonical header action misses evidence marker {marker}")
    for marker in ('form-header-mobile-actions', 'mobileActionAuthority', 'mobilePresentedDirectActions', 'aria-label="更多页面操作"', ':data-mobile-action-count', ':data-mobile-action-keys'):
        if marker not in contract:
            failures.append(f"contract header mobile action settlement misses {marker}")
    if 'role="menu"' in contract or 'role="menuitem"' in contract:
        failures.append("contract header disclosure must preserve native button semantics")
    for marker in ('data-action-ref="form.save"', 'data-action-tier="primary"', ':data-action-enabled="String(!busy)"'):
        if marker not in contract:
            failures.append(f"canonical local save misses primary-action evidence {marker}")
    action_view = source("frontend/apps/web/src/views/ActionView.vue")
    if "<ProductPageHeader" not in action_view or '<h1 class="sc-visually-hidden">{{ vm.page.title }}</h1>' in action_view:
        failures.append("ActionView does not delegate collection/scene identity to ProductPageHeader")
    contract_page = source("frontend/apps/web/src/pages/ContractFormPage.vue")
    if '<h1 v-if="initialFormLoading"' not in contract_page:
        failures.append("ContractForm loading identity may duplicate the stable page header h1")
    for marker in ('actions-in-header', '@canonical-save="saveRecord()"'):
        if marker not in contract_page:
            failures.append(f"ContractForm does not project direct edit actions into header: {marker}")
    canonical_actions = source("frontend/apps/web/src/pages/contractForm/contractFormHeaderCanonicalActions.ts")
    for marker in ("input.renderProfile === 'create'", "input.renderProfile === 'edit'", "authorizedLocalSave?.enabled"):
        if marker not in canonical_actions:
            failures.append(f"canonical edit/create save authority misses {marker}")
    if "input.renderProfile === 'edit' && input.dirty" in canonical_actions:
        failures.append("canonical edit save authority must not wait for dirty state")
    driver = source("frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue")
    for marker in ('showProductActions && !actionsInHeader', 'visibleActions.length && !actionsInHeader'):
        if marker not in driver:
            failures.append(f"DriverHost still owns a parallel action bar: {marker}")
    if "action.actionRef.actionId === 'form.save' && action.enabled" not in driver:
        failures.append("DriverHost local save is not bound to authorized canonical form.save")
    if "props.renderModel?.identity.mode === 'create' || props.dirty" in driver:
        failures.append("DriverHost edit save must not wait for dirty state")
    nested_heading_paths = (
        "frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue",
        "frontend/packages/ui/src/components/SceneHierarchySurface.vue",
        "frontend/packages/ui/src/components/SceneCollectionSurface.vue",
        "frontend/packages/ui/src/components/SceneObjectPage.vue",
    )
    for nested in nested_heading_paths:
        if "<h1" in source(nested):
            failures.append(f"nested renderer competes with ProductPageHeader h1: {nested}")
    native_renderer = source("frontend/apps/web/src/components/template/NativeFormTreeRenderer.vue")
    if 'v-bind="nativeActionEvidenceAttributes' not in native_renderer:
        failures.append("native action controls must expose canonical action evidence attributes")
    for marker in ("data-action-key", "data-action-ref", "data-backend-identity"):
        if marker not in native_renderer:
            failures.append(f"native action evidence is missing {marker}")
    for marker in ("line-break: strict", "text-wrap: balance", "font-size: 24px"):
        if marker not in native_renderer:
            failures.append(f"native record title responsive treatment is missing {marker}")
    app_shell = source("frontend/apps/web/src/layouts/AppShell.vue")
    for page_route in ("'action'", "'record'", "'model-form'", "'not-found'"):
        compact_section = app_shell.split("const compactRouteKeepsHeadline", 1)[1].split(");", 1)[0]
        if page_route in compact_section:
            failures.append(f"AppShell still owns h1 for page-header route {page_route}")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_product_page_header_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_product_page_header_guard] PASS adapters=3")
