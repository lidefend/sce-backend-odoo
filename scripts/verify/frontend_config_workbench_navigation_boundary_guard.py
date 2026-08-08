#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_SHELL = ROOT / "frontend" / "apps" / "web" / "src" / "layouts" / "AppShell.vue"
APP_SHELL_CSS = ROOT / "frontend" / "apps" / "web" / "src" / "layouts" / "AppShell.css"


def main() -> int:
    text = APP_SHELL.read_text(encoding="utf-8")
    css_text = APP_SHELL_CSS.read_text(encoding="utf-8")
    errors: list[str] = []

    forbidden = {
        "admin-shortcuts": "配置工作台不能通过 AppShell 侧边栏硬编码快捷入口发布",
        "showAdminShortcuts": "配置工作台入口必须来自后端菜单树，不允许前端按权限合成",
        "openBusinessConfigWorkbench": "配置工作台跳转不能绕过后端菜单节点",
        "@click=\"router.push('/admin/business-config')\"": "配置中心快捷入口不能硬编码前端路由",
        "businessConfigWorkbenchNode": "产品配置只能由主菜单树发布，不允许重复投影快捷入口",
        "workspace-activity-settings": "活动栏不得重复发布配置中心入口",
        "aria-label=\"配置中心\"": "活动栏不得以旧名称重复发布产品配置入口",
    }
    for token, message in forbidden.items():
        if token in text:
            errors.append(f"{APP_SHELL.relative_to(ROOT)}: {message}: {token}")

    required = {
        "<PrimaryNavigation": "产品配置必须随统一主导航发布",
        ':nodes="filteredMenu"': "主导航必须使用后端菜单树的统一过滤结果",
        '@select="handleSelect"': "产品配置必须复用统一菜单选择与权限快照链路",
    }
    for token, message in required.items():
        if token not in text:
            errors.append(f"{APP_SHELL.relative_to(ROOT)}: {message}")

    required_css = {
        "display: flex;\n  flex-direction: column;": "侧边栏必须使用可变区块布局，避免可选区块挤压遮挡菜单",
        "flex: 1 1 auto;": "主菜单区域必须占用侧边栏剩余空间",
    }
    for token, message in required_css.items():
        if token not in css_text:
            errors.append(f"{APP_SHELL_CSS.relative_to(ROOT)}: {message}")

    if errors:
        print("[frontend_config_workbench_navigation_boundary_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("[frontend_config_workbench_navigation_boundary_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
