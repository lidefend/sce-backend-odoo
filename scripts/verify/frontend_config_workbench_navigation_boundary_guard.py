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
    }
    for token, message in forbidden.items():
        if token in text:
            errors.append(f"{APP_SHELL.relative_to(ROOT)}: {message}: {token}")

    required = {
        "function businessConfigWorkbenchRoute": "前端仍需保留后端菜单节点到配置工作台路由的解释能力",
        "function isBusinessConfigWorkbenchNode": "前端必须只识别后端返回的配置工作台菜单节点",
        "v-if=\"businessConfigWorkbenchNode\"": "配置中心快捷入口必须由后端菜单节点控制可见性",
        "@click=\"handleSelect(businessConfigWorkbenchNode)\"": "配置中心快捷入口必须复用统一菜单选择与权限快照链路",
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
