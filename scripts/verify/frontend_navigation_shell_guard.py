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
    tree = read(root, "frontend/apps/web/src/components/MenuTree.vue")
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

    side_navigation = (root / "frontend/apps/web/src/components/product-shell/ProductSideNavigation.vue").read_text(encoding="utf-8")
    for marker in (
        "grid-template-rows: max-content minmax(0, 1fr)",
        "var(--sc-nav-row-gap)",
        "var(--sc-app-focus-ring)",
        "overscroll-behavior: contain",
    ):
        if marker not in side_navigation:
            errors.append(f"ProductSideNavigation must retain canonical rendering detail: {marker}")
    if (component_root / "PrimaryNavigation.vue").exists() or "<PrimaryNavigation" in shell:
        errors.append("legacy PrimaryNavigation must not remain as a parallel shell authority")
    if "session.navigationModel?.nodes" not in shell:
        errors.append("AppShell must consume the normalized session navigation model")
    if "createNavigationSelectionSnapshot(node.source, session.routeAuthority)" not in shell:
        errors.append("canonical menu selection must retain the immutable authority snapshot chain")

    for forbidden in ("useSessionStore", "evaluateCapabilityPolicy", "capabilityTooltip", "console.info"):
        if forbidden in tree:
            errors.append(f"MenuTree must remain presentation-only: {forbidden}")
    for required in ("expandedKeys", "emit('toggle'", "node.disabledReason", ".parentChain"):
        if required not in tree:
            errors.append(f"MenuTree missing canonical interaction token: {required}")

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
