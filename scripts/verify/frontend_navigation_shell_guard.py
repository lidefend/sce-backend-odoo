#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = (
    "ProductAppShell",
    "ProductSideNavigation",
    "ProductMobileNavigationDrawer",
    "NavigationBreadcrumb",
    "WorkspaceContextIndicator",
)
BUSINESS_IDENTITY = re.compile(
    r"\b(?:project\.project|payment\.request|construction\.contract|action_id\s*===|menu_id\s*===)\b",
    re.IGNORECASE,
)


def read(root: Path, relative: str) -> str:
    path = root / relative
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    shell = read(root, "frontend/apps/web/src/layouts/AppShell.vue")
    shell_style = read(root, "frontend/apps/web/src/layouts/AppShell.css")
    tree = read(root, "frontend/apps/web/src/components/MenuTree.vue")
    menu_node = read(root, "frontend/apps/web/src/components/product-shell/CanonicalNavigationMenuNode.vue")
    primitive_bridge = read(root, "frontend/apps/web/src/components/design-system/tdesignPrimitiveBridge.ts")
    theme = read(root, "frontend/packages/ui/src/kits/tdesign/theme.css")
    ui_primitives = read(root, "frontend/packages/ui/src/primitives.ts")
    session = read(root, "frontend/apps/web/src/stores/session.ts")
    canonical = read(root, "frontend/apps/web/src/app/canonicalNavigation.ts")
    menu_service = read(root, "addons/smart_core/delivery/menu_service.py")
    system_init = read(root, "addons/smart_core/handlers/system_init.py")
    component_root = root / "frontend/apps/web/src/components/product-shell"

    for component in COMPONENTS:
        source = component_root / f"{component}.vue"
        text = source.read_text(encoding="utf-8") if source.is_file() else ""
        if not text:
            errors.append(f"missing product shell component: {component}")
            continue
        if f'data-semantic-component="{component}"' not in text:
            errors.append(f"{component} lacks exact semantic identity")
        if BUSINESS_IDENTITY.search(text):
            errors.append(f"{component} contains business-specific identity")
        if f"<{component}" not in shell and component != "ProductSideNavigation":
            errors.append(f"AppShell does not consume {component}")

    if "<ProductSideNavigation" not in shell or ':nodes="filteredNavigation"' not in shell:
        errors.append("AppShell must render ProductSideNavigation from the canonical filtered model")
    context_indicator = read(root, "frontend/apps/web/src/components/product-shell/WorkspaceContextIndicator.vue")
    context_projection = shell.split("<WorkspaceContextIndicator", 1)[-1].split("/>", 1)[0]
    if ':show-record="showRecordContext"' not in context_projection or "v-if=" in context_projection:
        errors.append("AppShell must keep the company context authority visible while gating only record context")
    for marker in ('v-if="showRecord"', "@company=\"openWorkspacePanel('company')\""):
        if marker not in context_indicator + context_projection:
            errors.append(f"workspace context authority missing capability split: {marker}")

    side_navigation = (root / "frontend/apps/web/src/components/product-shell/ProductSideNavigation.vue").read_text(encoding="utf-8")
    for marker in (
        "grid-template-rows: max-content minmax(0, 1fr)",
        "var(--sc-nav-row-gap)",
        "overscroll-behavior: contain",
        "<template #prefix><ScIcon name=\"search\"",
        "clearable",
        'appearance="navigation-search"',
    ):
        if marker not in side_navigation:
            errors.append(f"ProductSideNavigation must retain canonical rendering detail: {marker}")
    for marker in (".sc-input[data-appearance='navigation-search']", "var(--sc-app-focus-ring)"):
        if marker not in theme:
            errors.append(f"navigation search appearance must be owned by the TDesign theme bridge: {marker}")
    if "border-color:" in side_navigation or "box-shadow:" in side_navigation or ":deep(.sc-input:hover)" in side_navigation:
        errors.append("ProductSideNavigation must not own ScInput visual chrome")
    if "product-side-navigation__search > .sc-icon" in side_navigation or "padding-left: 34px" in side_navigation:
        errors.append("navigation search must use the ScInput prefix adapter instead of manual icon positioning")
    for marker in (
        ".shell :deep(.sidebar)",
        "grid-template-columns: minmax(0, 1fr)",
        ".published-app__content",
        "height: 100vh",
        "overflow: hidden",
        ".product-side-navigation__tree",
        "overflow: auto",
    ):
        if marker not in (shell_style + "\n" + side_navigation):
            errors.append(f"navigation shell lost bounded scroll ownership: {marker}")
    if not re.search(r"\.topbar\s*\{[^}]*flex-shrink:\s*0", shell_style, re.DOTALL):
        errors.append("responsive topbar must not shrink over the activity page tabs")
    if ".t-button__text" in shell_style:
        errors.append("published app layout must use owned content markup instead of vendor internals")
    if re.search(r"(?m)^\.sidebar\s*\{", shell_style):
        errors.append("navigation drawer root styling bypasses the child-component deep boundary")
    desktop_shell = shell_style[shell_style.find("@media (min-width: 961px)") :]
    if "grid-template-columns: 48px minmax(0, 1fr)" in desktop_shell or not re.search(
        r"\.workspace-activity-rail\s*\{[^}]*display:\s*none\s*!important", desktop_shell, re.DOTALL
    ):
        errors.append("desktop navigation must retain the single-column product menu")
    if (component_root / "PrimaryNavigation.vue").exists() or "<PrimaryNavigation" in shell:
        errors.append("legacy PrimaryNavigation must not remain as a parallel shell authority")
    if "session.navigationModel?.nodes" not in shell:
        errors.append("AppShell must consume the normalized session navigation model")
    if "createNavigationSelectionSnapshot(node.source, session.routeAuthority)" not in shell:
        errors.append("canonical menu selection must retain the immutable authority snapshot chain")

    for forbidden in ("useSessionStore", "evaluateCapabilityPolicy", "capabilityTooltip", "console.info"):
        if forbidden in tree + menu_node:
            errors.append(f"MenuTree must remain presentation-only: {forbidden}")
    for required in ("TDesignMenu", 'data-semantic-driver="tdesign-menu"', "expandedKeys", "emit('toggle'", ".parentChain"):
        if required not in tree:
            errors.append(f"MenuTree missing canonical interaction token: {required}")
    for required in ("TDesignSubmenu", "TDesignMenuItem", "node.disabledReason", 'data-navigation-node="canonical"'):
        if required not in menu_node:
            errors.append(f"canonical navigation adapter missing standard menu projection: {required}")
    if re.search(r"<(?:ul|li|button|ScButton)\b", tree + menu_node):
        errors.append("canonical navigation must not retain a hand-built menu interaction tree")
    for required in ("TDesignMenu", "TDesignSubmenu", "TDesignMenuItem"):
        if required not in primitive_bridge or required not in ui_primitives:
            errors.append(f"standard navigation driver is not exported through the project bridge: {required}")

    canonical_required = (
        "CANONICAL_NAVIGATION_CARRIER_MISSING",
        "CANONICAL_NAVIGATION_AUTHORITY_MISSING",
        "CANONICAL_NAVIGATION_CARRIER_IDENTITY_MISMATCH",
        "CANONICAL_NAVIGATION_AUTHORITY_MISMATCH",
        "CANONICAL_NAVIGATION_ROUTE_MISMATCH",
    )
    for token in canonical_required:
        if token not in canonical:
            errors.append(f"canonical navigation decoder missing fail-closed boundary: {token}")
    if "route.query" in canonical or "URLSearchParams" in canonical:
        errors.append("canonical navigation authority must not consume URL/query hints")

    session_order = (
        session.find("this.routeAuthority = routeAuthorityForPrincipal("),
        session.find("this.navigationModel = createCanonicalNavigationModel("),
        session.find("this.isReady = true;", session.find("this.navigationModel = createCanonicalNavigationModel(")),
    )
    if min(session_order) < 0 or session_order != tuple(sorted(session_order)):
        errors.append("session must resolve principal authority, build canonical navigation, then become ready")

    if "def project_canonical_navigation(" not in menu_service:
        errors.append("backend canonical navigation projection is missing")
    filter_index = system_init.find("filter_nav_by_route_authority(")
    project_index = system_init.find("project_canonical_navigation(")
    payload_index = system_init.find('data["navigation"] = {')
    if min(filter_index, project_index, payload_index) < 0 or not filter_index < project_index < payload_index:
        errors.append("system.init must filter authority, project canonical navigation, then seal payload")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("[frontend_navigation_shell_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"[frontend_navigation_shell_guard] PASS components={len(COMPONENTS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
