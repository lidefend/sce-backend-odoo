#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT / "frontend/apps/web/src/components/role-home/WorkspaceHome.vue"
HOME_VIEW = ROOT / "frontend/apps/web/src/views/HomeView.vue"
MY_WORK_VIEW = ROOT / "frontend/apps/web/src/views/MyWorkView.vue"
APP_SHELL = ROOT / "frontend/apps/web/src/layouts/AppShell.vue"
ROUTER = ROOT / "frontend/apps/web/src/router/index.ts"


def main() -> int:
    text = HOME.read_text(encoding="utf-8", errors="ignore") if HOME.is_file() else ""
    app_shell = APP_SHELL.read_text(encoding="utf-8", errors="ignore") if APP_SHELL.is_file() else ""
    home_view = HOME_VIEW.read_text(encoding="utf-8", errors="ignore") if HOME_VIEW.is_file() else ""
    my_work_view = MY_WORK_VIEW.read_text(encoding="utf-8", errors="ignore") if MY_WORK_VIEW.is_file() else ""
    router = ROUTER.read_text(encoding="utf-8", errors="ignore") if ROUTER.is_file() else ""
    required = [
        'class="role-home-surface__tasks"',
        'class="role-home-surface__overview"',
        'class="role-home-surface__access"',
        'v-if="loading"',
        'v-else-if="error"',
        'v-else-if="tasks.length"',
        '@media (max-width: 960px)',
        'class="role-home-surface__entry-copy"',
        'grid-template-columns: auto minmax(0, 1fr) auto',
    ]
    forbidden = [
        "legacy_home",
        "HUD:",
        "contract-role-home__",
        "<h1",
    ]
    errors = [f"missing token: {token}" for token in required if token not in text]
    errors += [f"forbidden token: {token}" for token in forbidden if token in text]
    if re.search(r"\b(?:role|role_code)\s*===", text):
        errors.append("forbidden role branch")
    shell_required = [
        "const routeUsesMinimalTopbar = computed(() => route.meta?.shellDensity === 'minimal')",
        "|| routeUsesMinimalTopbar.value",
        "<h1 v-if=\"showTopbarHeadline\"",
    ]
    errors += [f"missing app shell token: {token}" for token in shell_required if token not in app_shell]
    for route_name in ("home", "scene-home", "my-work", "scene-my-work"):
        declaration = next((line for line in router.splitlines() if f"name: '{route_name}'" in line), "")
        for token in ("shellDensity: 'minimal'", "pageHeadingOwner: 'content'"):
            if token not in declaration:
                errors.append(f"equivalent route presentation missing: {route_name}: {token}")
    for label, source in (("HomeView", home_view), ("MyWorkView", my_work_view)):
        for token in ("<ProductPageHeader", "<DashboardPattern>", 'data-product-page-mode="dashboard"'):
            if token not in source:
                errors.append(f"{label} missing shared page expression: {token}")
    if errors:
        print("[frontend_home_layout_section_coverage_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[frontend_home_layout_section_coverage_guard] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
