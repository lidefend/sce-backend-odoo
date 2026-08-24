#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_SHELL = ROOT / "frontend" / "apps" / "web" / "src" / "layouts" / "AppShell.vue"
APP_SHELL_CSS = ROOT / "frontend" / "apps" / "web" / "src" / "layouts" / "AppShell.css"
MENU_SERVICE = ROOT / "addons" / "smart_core" / "delivery" / "menu_service.py"
NATIVE_CONFIG_PROJECTION = ROOT / "addons" / "smart_core" / "delivery" / "native_config_menu_projection.py"
NAVIGATION_ACCEPTANCE = ROOT / "frontend" / "apps" / "web" / "scripts" / "product_navigation_boundary_acceptance.mjs"


def main() -> int:
    text = APP_SHELL.read_text(encoding="utf-8")
    css_text = APP_SHELL_CSS.read_text(encoding="utf-8")
    menu_service_text = MENU_SERVICE.read_text(encoding="utf-8")
    native_projection_text = NATIVE_CONFIG_PROJECTION.read_text(encoding="utf-8")
    acceptance_text = NAVIGATION_ACCEPTANCE.read_text(encoding="utf-8")
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
        "<ProductSideNavigation": "产品配置必须随统一主导航发布",
        ':nodes="filteredNavigation"': "主导航必须使用后端权威生成的 Canonical Navigation Model",
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

    backend_required = {
        'return "产品配置" if normalized == "配置中心" else normalized': "旧配置中心发布分组必须归一到产品配置",
        "self._canonical_group_label(part)": "旧发布路径也必须复用产品配置别名归一",
    }
    for token, message in backend_required.items():
        if token not in menu_service_text:
            errors.append(f"{MENU_SERVICE.relative_to(ROOT)}: {message}")
    if 'CONFIG_GROUP_LABEL = "产品配置"' not in native_projection_text:
        errors.append(f"{NATIVE_CONFIG_PROJECTION.relative_to(ROOT)}: 原生配置投影必须统一命名为产品配置")

    acceptance_required = {
        'product_configuration_entry_count === 1': "浏览器验收必须锁定唯一产品配置入口",
        'legacy_configuration_entry_count === 0': "浏览器验收必须拒绝旧配置中心入口",
        'getByRole("heading", { name: "菜单配置", exact: true })': "浏览器验收必须验证配置入口真实可达",
    }
    for token, message in acceptance_required.items():
        if token not in acceptance_text:
            errors.append(f"{NAVIGATION_ACCEPTANCE.relative_to(ROOT)}: {message}")

    if errors:
        print("[frontend_config_workbench_navigation_boundary_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("[frontend_config_workbench_navigation_boundary_guard] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
