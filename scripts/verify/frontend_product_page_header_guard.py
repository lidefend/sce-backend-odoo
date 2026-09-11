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
    if 'v-if="headerOverflowItems.length && !isNarrowViewport"' not in contract:
        failures.append("contract header desktop overflow must be structurally excluded on narrow viewports")
    if 'v-if="headerOverflowItems.length" class="form-header-more-actions"' in contract:
        failures.append("contract header must not rely on CSS to hide a parallel desktop overflow control")
    if "...(mobileActionAuthority.value.keys.includes('back:form.back') ? [{ value: 'builtin:back', label: props.backLabel" not in contract:
        failures.append("contract header mobile action settlement can hide the only exit action")
    if 'role="menu"' in contract or 'role="menuitem"' in contract:
        failures.append("contract header disclosure must preserve native button semantics")
    action_view = source("frontend/apps/web/src/views/ActionView.vue")
    if "<ProductPageHeader" not in action_view or '<h1 class="sc-visually-hidden">{{ vm.page.title }}</h1>' in action_view:
        failures.append("ActionView does not delegate collection/scene identity to ProductPageHeader")
    contract_page = source("frontend/apps/web/src/pages/ContractFormPage.vue")
    contract_page_style = source("frontend/apps/web/src/pages/contractForm/ContractFormPage.css")
    if '<h1 v-if="initialFormLoading"' not in contract_page:
        failures.append("ContractForm loading identity may duplicate the stable page header h1")
    for marker in ('actions-in-header', '@canonical-save="saveRecord()"', ':status-interactive="nativeStatusbar.visible && !nativeStatusbar.readonly"'):
        if marker not in contract_page:
            failures.append(f"ContractForm does not project direct edit actions into header: {marker}")
    if ":deep(.template-page-header" in contract_page_style:
        failures.append("ContractForm page must not patch shared header internals through deep selectors")
    for stale_selector in ("template-page-header-main", "template-page-header-status", "template-page-header-actions"):
        if stale_selector in contract_page_style:
            failures.append(f"ContractForm page retains stale header DOM selector: {stale_selector}")
    for marker in ("position: sticky", "data-has-status", "product-page-header__actions"):
        if marker not in component:
            failures.append(f"ProductPageHeader does not own shared internal header layout: {marker}")
    canonical_actions = source("frontend/apps/web/src/pages/contractForm/contractFormHeaderCanonicalActions.ts")
    for marker in ("input.floorplan?.decisionMode", "input.floorplan.directActions", "input.floorplan.overflowActions", "['primary', 'secondary'].includes(action.tier)", "['overflow', 'configuration'].includes(action.tier)"):
        if marker not in canonical_actions:
            failures.append(f"canonical header action floorplan rendering misses {marker}")
    if "localSavePrimary" in canonical_actions or "authorizedLocalSave" in canonical_actions:
        failures.append("canonical header actions must not invent local save orchestration")
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
    canonical_presenter = source("frontend/apps/web/src/app/presentation/contractFormPresenter.ts")
    canonical_bridge = source("frontend/apps/web/src/pages/contractForm/canonicalNativeFormBridge.ts")
    canonical_driver = source("frontend/apps/web/src/pages/contractForm/ContractFormDriverHost.vue")
    if "/\\/header(?:\\[|\\/|$)/.test(nativeLocator)" not in canonical_presenter:
        failures.append("native form-header actions are not projected into the product header action channel")
    if "claimedStatusbarNodeIdentity && canonicalNodeIdentity === claimedStatusbarNodeIdentity" not in canonical_bridge:
        failures.append("canonical body statusbar de-duplication is not bound to the exact header-claimed node")
    if "text(node.widget || attrs.widget).toLowerCase() === 'statusbar'" in canonical_bridge:
        failures.append("canonical body still hides every statusbar instead of the exact header claim")
    if ':claimed-statusbar-node-identity="nativeStatusbarNodeIdentity"' not in contract_page:
        failures.append("ContractForm does not pass the exact claimed statusbar node into the body bridge")
    if canonical_driver.count(':authoritative-business-section-mode="nativeBridge.authoritativeBusinessSectionMode"') != 2:
        failures.append("canonical primary and subordinate renderers do not share the page-level business section mode")
    if 'v-bind="nativeActionEvidenceAttributes' not in native_renderer:
        failures.append("native action controls must expose canonical action evidence attributes")
    for marker in ("data-action-key", "data-action-ref", "data-backend-identity"):
        if marker not in native_renderer:
            failures.append(f"native action evidence is missing {marker}")
    for marker in ("line-break: strict", "text-wrap: balance", "font-size: 24px"):
        if marker not in native_renderer:
            failures.append(f"native record title responsive treatment is missing {marker}")
    app_shell = source("frontend/apps/web/src/layouts/AppShell.vue")
    router = source("frontend/apps/web/src/router/index.ts")
    for page_route in ("home", "scene-home", "my-work", "scene-my-work", "api-key-management", "action", "record", "model-form", "not-found"):
        route_declaration = next(
            (line for line in router.splitlines() if f"name: '{page_route}'" in line),
            "",
        )
        if "pageHeadingOwner: 'content'" not in route_declaration:
            failures.append(f"page-header route does not declare content heading authority: {page_route}")
    for view in ("frontend/apps/web/src/views/HomeView.vue", "frontend/apps/web/src/views/MyWorkView.vue"):
        view_source = source(view)
        for marker in ("<ProductPageHeader", "usePageIdentityRuntime"):
            if marker not in view_source:
                failures.append(f"workspace page does not consume content heading authority: {view}: {marker}")
    for marker in ("contentOwnsPageHeading", "route.meta?.pageHeadingOwner === 'content'", "!contentOwnsPageHeading.value"):
        if marker not in app_shell:
            failures.append(f"AppShell does not consume route heading authority: {marker}")
    if "formDesignerKeepsHeadline" in app_shell or "BUSINESS_CONFIG_MODES.lowCode" in app_shell:
        failures.append("AppShell must not override content heading authority for low-code form routes")
    return failures


if __name__ == "__main__":
    errors = validate()
    if errors:
        print("[frontend_product_page_header_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("[frontend_product_page_header_guard] PASS adapters=3")
