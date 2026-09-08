#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HOME = ROOT / "frontend/apps/web/src/components/role-home/WorkspaceHome.vue"
APP_SHELL = ROOT / "frontend/apps/web/src/layouts/AppShell.vue"


def main() -> int:
    text = HOME.read_text(encoding="utf-8", errors="ignore") if HOME.is_file() else ""
    app_shell = APP_SHELL.read_text(encoding="utf-8", errors="ignore") if APP_SHELL.is_file() else ""
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
        "role ===",
        "role_code ===",
        "legacy_home",
        "HUD:",
        "contract-role-home__",
        "<h1",
    ]
    errors = [f"missing token: {token}" for token in required if token not in text]
    errors += [f"forbidden token: {token}" for token in forbidden if token in text]
    shell_required = [
        "const compactRouteKeepsHeadline = computed(() => [",
        "  'home',",
        "<h1 v-if=\"showTopbarHeadline\"",
    ]
    errors += [f"missing app shell token: {token}" for token in shell_required if token not in app_shell]
    if errors:
        print("[frontend_home_layout_section_coverage_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[frontend_home_layout_section_coverage_guard] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
