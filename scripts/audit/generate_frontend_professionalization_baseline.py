#!/usr/bin/env python3
"""Generate the Phase 0 frontend-professionalization baseline.

This is a static, reproducible inventory.  It deliberately does not start a
runtime, query a database, authenticate a user, or infer business authority
from labels.  Runtime-only facts are reported as evidence gaps rather than
invented by the scanner.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"
DEFAULT_OUTPUT = "docs/frontend_productization"
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".vue", ".css", ".scss", ".sass"}
SKIP_PARTS = {"node_modules", "dist", ".git", ".runtime", "artifacts"}
EXCLUDED_SCOPES = [
    "demo_addons",
    "external customer_addons",
    "runtime installed-module state",
    "user-specific visibility",
]
COLOR_RE = re.compile(r"(?<![\w-])(#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\))")
CSS_VAR_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+)")
Z_INDEX_RE = re.compile(r"\bz-index\s*:\s*([^;{}]+)")
BREAKPOINT_RE = re.compile(r"@media\s*\(([^)]*(?:width|height)[^)]*)\)")
TDESIGN_RE = re.compile(r"(?:from\s+['\"]tdesign-vue-next|<t-[A-Za-z])")
COMPONENT_KEY_RE = re.compile(r"(?:componentKey|component_key)\s*[:=]\s*['\"]([^'\"]+)")
FIELD_TYPE_RE = re.compile(r"(?:fieldType|field_type|type)\s*[:=]\s*['\"]([A-Za-z0-9_.-]+)")
SPACING_RE = re.compile(r"\b(?:margin|padding|gap|row-gap|column-gap)\s*:\s*([^;{}]+)")
RADIUS_RE = re.compile(r"\bborder-radius\s*:\s*([^;{}]+)")
SHADOW_RE = re.compile(r"\bbox-shadow\s*:\s*([^;{}]+)")
WIDTH_RE = re.compile(r"\b(?:width|max-width|min-width)\s*:\s*([^;{}]+)")
ROUTE_RE = re.compile(
    r"\{\s*path:\s*['\"](?P<path>[^'\"]+)['\"],\s*name:\s*['\"](?P<name>[^'\"]+)['\"],\s*"
    r"component:\s*(?P<component>[^,}]+)(?P<meta>,\s*meta:\s*\{[^}]*\})?\s*\}"
)
IMPORT_VIEW_RE = re.compile(r"(?:import\s+\w+\s+from\s+|import\()['\"]?\.\./views/([^'\")]+)")


def repo_path(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, text=True, stdout=subprocess.PIPE
    ).stdout.strip()


def baseline_commit(root: Path) -> str:
    """Keep source identity on the mainline base, not on report-only commits."""
    return git(root, "merge-base", "HEAD", "origin/main")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def source_files(root: Path, relative: str = "frontend/apps/web/src") -> list[Path]:
    base = root / relative
    return sorted(
        path
        for path in base.rglob("*")
        if path.is_file() and path.suffix in SOURCE_SUFFIXES and not (set(path.parts) & SKIP_PARTS)
    )


def line_numbers(text: str, pattern: re.Pattern[str] | str) -> list[int]:
    regex = re.compile(pattern) if isinstance(pattern, str) else pattern
    return [index for index, line in enumerate(text.splitlines(), 1) if regex.search(line)]


def samples(items: Iterable[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    return list(items)[:limit]


def source_digest(root: Path, paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted({path.resolve() for path in paths}):
        digest.update(repo_path(root, path).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def generator_digest() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def dirty_worktree(root: Path) -> bool:
    return bool(git(root, "status", "--porcelain=v1", "--untracked-files=all"))


def inventory_metadata(root: Path, input_paths: Iterable[Path], input_scopes: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "baselineScope": "repository formal-product declarative baseline",
        "generatorDigest": generator_digest(),
        "inputDigest": source_digest(root, input_paths),
        "inputScopes": input_scopes,
        "generatedFromDirtyWorktree": dirty_worktree(root),
        "excludedScopes": EXCLUDED_SCOPES,
    }


def declarative_xml_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in (root / "addons").rglob("*.xml")
        if not (set(path.parts) & {"migrations", "static"})
    )


def classify_surface(route_name: str, route_path: str, component: str) -> str:
    needle = " ".join((route_name, route_path, component)).lower()
    if "action" in needle or "list" in needle:
        return "collection"
    if "model-form" in needle or route_path.startswith("/f/"):
        return "form_edit_or_create"
    if route_name == "record" or route_path.startswith("/r/"):
        return "form_readonly"
    if "scene" in needle:
        return "scene"
    if "workbench" in needle or "home" in needle or "my-work" in needle:
        return "workspace"
    if "analytics" in needle or "health" in needle:
        return "dashboard_or_admin"
    return "utility"


def route_component(raw: str) -> str:
    match = re.search(r"(?:import\()?['\"]\.\./([^'\")]+)", raw)
    if match:
        return match.group(1)
    return raw.strip()


def component_evidence(root: Path, component: str) -> dict[str, Any]:
    target = root / "frontend/apps/web/src" / component
    if not target.exists():
        return {"source": component, "header": "unknown", "renderer": "unknown", "mobile": "unknown"}
    text = read(target)
    header = "ScPageHeader" if "ScPageHeader" in text else "PageHeader" if "PageHeader" in text else "none_detected"
    renderer = next(
        (name for name in ("ContractFormRoute", "ActionView", "NativeFormTreeRenderer", "ActionSurfaceRendererHost", "PageRenderer") if name in text),
        "not_directly_declared",
    )
    mobile = "component_media_query" if "@media" in text else "shell_or_shared_css"
    return {"source": component, "header": header, "renderer": renderer, "mobile": mobile}


def read_runtime_surface_csv(root: Path) -> list[dict[str, str]]:
    path = runtime_surface_csv_path(root)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def runtime_surface_csv_path(root: Path) -> Path:
    return root / "docs/frontend_productization/frontend_surface_inventory_v1.csv"


def action_model_inventory(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Read declarative XML action/menu definitions without claiming runtime visibility."""
    actions: dict[str, dict[str, Any]] = {}
    menus: list[dict[str, Any]] = []
    for path in declarative_xml_files(root):
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        rel = repo_path(root, path)
        for node in tree.getroot().iter():
            if node.tag == "record" and node.attrib.get("model") == "ir.actions.act_window" and node.attrib.get("id"):
                fields = {
                    field.attrib.get("name", ""): field.attrib.get("ref") or (field.text or "").strip()
                    for field in node.findall("field")
                }
                actions[node.attrib["id"]] = {
                    "actionXmlidLocal": node.attrib["id"],
                    "model": fields.get("res_model") or None,
                    "viewMode": fields.get("view_mode") or None,
                    "viewRef": fields.get("view_id") or None,
                    "source": rel,
                    "authority": "declarative_action_definition",
                }
            if node.tag == "menuitem" and node.attrib.get("id"):
                action_ref = node.attrib.get("action") or None
                menus.append(
                    {
                        "menuXmlidLocal": node.attrib["id"],
                        "actionRef": action_ref,
                        "parentRef": node.attrib.get("parent") or None,
                        "label": node.attrib.get("name") or None,
                        "source": rel,
                        "authority": "declarative_menu_definition_not_runtime_visibility",
                    }
                )
    return [actions[key] for key in sorted(actions)], sorted(menus, key=lambda item: (item["source"], item["menuXmlidLocal"]))


def page_surface_inventory(root: Path, frontend_files: list[Path]) -> dict[str, Any]:
    router = root / "frontend/apps/web/src/router/index.ts"
    xml_files = declarative_xml_files(root)
    runtime_csv = runtime_surface_csv_path(root)
    router_text = read(router)
    runtime_rows = read_runtime_surface_csv(root)
    routes: list[dict[str, Any]] = []
    for match in ROUTE_RE.finditer(router_text):
        component = route_component(match.group("component"))
        evidence = component_evidence(root, component)
        route_path = match.group("path")
        route_name = match.group("name")
        routes.append(
            {
                "routeName": route_name,
                "route": route_path,
                "surfaceType": classify_surface(route_name, route_path, component),
                "component": component,
                "shell": "AppShell" if "layout: 'shell'" in (match.group("meta") or "") else "none",
                "header": evidence["header"],
                "renderer": evidence["renderer"],
                "mobileState": evidence["mobile"],
                "presentationMode": "runtime_contract_required" if route_name in {"record", "model-form"} else "not_applicable_or_runtime",
                "renderProfile": (
                    "readonly" if route_name == "record" else "edit_or_create" if route_name == "model-form" else "runtime_or_not_applicable"
                ),
                "evidence": {"source": repo_path(root, router), "line": router_text.count("\n", 0, match.start()) + 1},
            }
        )
    runtime_actions: list[dict[str, Any]] = []
    for row in runtime_rows:
        runtime_actions.append(
            {
                "menuId": row.get("menu_id") or None,
                "actionId": row.get("action_id") or None,
                "menuXmlid": row.get("menu_xmlid") or None,
                "actionXmlid": row.get("action_xmlid") or None,
                "model": row.get("model") or None,
                "route": row.get("route") or None,
                "pageType": row.get("page_type") or None,
                "component": row.get("actual_component") or None,
                "role": row.get("role") or None,
                "reachable": row.get("reachable") == "true",
                "writeCapable": row.get("write_capable") == "true",
                "authority": "observed_runtime_evidence_not_full_catalog",
                "source": "docs/frontend_productization/frontend_surface_inventory_v1.csv",
            }
        )
    actions, menus = action_model_inventory(root)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "page_surface_inventory",
        "sourceCommit": baseline_commit(root),
        **inventory_metadata(
            root,
            frontend_files + xml_files + ([runtime_csv] if runtime_csv.exists() else []),
            [
                {"scope": "frontend_source", "path": "frontend/apps/web/src"},
                {"scope": "formal_product_declarative_xml", "path": "addons/**/*.xml excluding migrations/static"},
                {"scope": "historical_runtime_sample", "path": "docs/frontend_productization/frontend_surface_inventory_v1.csv"},
            ],
        ),
        "scope": {
            "staticRoutes": "frontend/apps/web/src/router/index.ts",
            "declarativeActionsAndMenus": "addons/**/data/*.xml and addons/**/views/*.xml",
            "runtimeEvidence": "docs/frontend_productization/frontend_surface_inventory_v1.csv",
        },
        "routes": routes,
        "runtimeObservedActionSurfaces": runtime_actions,
        "declarativeActionDefinitions": actions,
        "declarativeMenuDefinitions": menus,
        "limitations": [
            "Static XML cannot prove a current user's runtime menu visibility, inherited view identity, action numeric ID, or record-level render profile.",
            "Runtime CSV is historical sampled evidence, not a complete current runtime catalog.",
            "Task/workspace classification for record forms is Contract V2 runtime authority and is intentionally not inferred by this inventory.",
        ],
    }


def navigation_inventory(root: Path, frontend_files: list[Path]) -> dict[str, Any]:
    candidates = [
        path for path in frontend_files
        if any(token in repo_path(root, path).lower() for token in ("navigation", "menu", "shell", "route", "session", "activity"))
    ]
    entries: list[dict[str, Any]] = []
    patterns = {
        "runtime_menu_authority": re.compile(r"menuTree|navigation|/api/.+menu|menu_orchestration", re.I),
        "route_identity": re.compile(r"menu_id|action_id|route|router\.push", re.I),
        "user_preference_or_local_state": re.compile(r"localStorage|sessionStorage|collapsed|sidebarHidden", re.I),
        "mobile_drawer_or_sidebar": re.compile(r"mobile.*(?:drawer|sidebar)|drawer|sidebar", re.I),
        "favorites_or_recent": re.compile(r"favorite|recent|activityPages|registerActivity", re.I),
        "access_denial": re.compile(r"access-denied|disabled_reason|authority", re.I),
    }
    for path in candidates:
        text = read(path)
        matched = []
        for label, pattern in patterns.items():
            lines = line_numbers(text, pattern)
            if lines:
                matched.append({"topic": label, "lines": lines[:16]})
        if matched:
            entries.append({"source": repo_path(root, path), "topics": matched})
    shell = root / "frontend/apps/web/src/layouts/AppShell.vue"
    shell_text = read(shell)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "navigation_authority_inventory",
        "sourceCommit": baseline_commit(root),
        **inventory_metadata(
            root,
            candidates,
            [{"scope": "navigation_candidate_source", "path": "frontend/apps/web/src/**/*navigation|menu|shell|route|session|activity*"}],
        ),
        "canonicalRuntimeAuthority": {
            "declared": "backend runtime navigation response / session.menuTree",
            "frontendConsumers": [
                "frontend/apps/web/src/stores/session.ts",
                "frontend/apps/web/src/layouts/AppShell.vue",
                "frontend/apps/web/src/components/product-shell/PrimaryNavigation.vue",
                "frontend/apps/web/src/app/menu.ts",
            ],
            "staticEvidence": "AppShell passes session-derived filteredMenu to PrimaryNavigation; final visibility requires runtime inspection.",
        },
        "shell": {
            "component": "AppShell",
            "source": repo_path(root, shell),
            "sidebar": "PrimaryNavigation in desktop sidebar; dialog-style mobile sidebar",
            "mobileDrawerEvidenceLines": line_numbers(shell_text, re.compile(r"mobileSidebar|aria-modal|sidebar", re.I))[:24],
            "deepLinkAuthority": "router keeps menu_id/action_id query context; runtime menu identity remains server/session supplied",
        },
        "navigationSources": entries,
        "knownStaticGaps": [
            "No static scan can prove the current leaf menu is exactly one after runtime authorization and user preference application.",
            "Favorites/recent and collapsed state need explicit schema ownership before they become canonical navigation inputs.",
            "A future Canonical Navigation Model must make backend authority, disabled reason, parent chain, and route identity explicit instead of relying on scattered adapter shapes.",
        ],
    }


def design_token_inventory(root: Path, frontend_files: list[Path]) -> dict[str, Any]:
    css_files = [path for path in frontend_files if path.suffix in {".css", ".scss", ".sass", ".vue"}]
    variables: dict[str, dict[str, Any]] = {}
    colors: Counter[str] = Counter()
    color_sources: dict[str, list[dict[str, Any]]] = defaultdict(list)
    z_indexes: Counter[str] = Counter()
    breakpoints: Counter[str] = Counter()
    spacing: Counter[str] = Counter()
    radius: Counter[str] = Counter()
    shadows: Counter[str] = Counter()
    widths: Counter[str] = Counter()
    tdesign_sources: list[dict[str, Any]] = []
    component_style_sources: Counter[str] = Counter()
    for path in css_files:
        text = read(path)
        rel = repo_path(root, path)
        for index, line in enumerate(text.splitlines(), 1):
            for name, value in CSS_VAR_RE.findall(line):
                item = variables.setdefault(name, {"name": name, "values": set(), "sources": []})
                item["values"].add(value.strip())
                if len(item["sources"]) < 12:
                    item["sources"].append({"source": rel, "line": index})
            for value in COLOR_RE.findall(line):
                normalized = value.lower()
                colors[normalized] += 1
                if len(color_sources[normalized]) < 8:
                    color_sources[normalized].append({"source": rel, "line": index, "excerpt": line.strip()[:160]})
            for value in Z_INDEX_RE.findall(line):
                z_indexes[value.strip()] += 1
            for breakpoint in BREAKPOINT_RE.findall(line):
                breakpoints[breakpoint.strip()] += 1
            for value in SPACING_RE.findall(line):
                spacing[value.strip()] += 1
            for value in RADIUS_RE.findall(line):
                radius[value.strip()] += 1
            for value in SHADOW_RE.findall(line):
                shadows[value.strip()] += 1
            for value in WIDTH_RE.findall(line):
                widths[value.strip()] += 1
        if TDESIGN_RE.search(text):
            tdesign_sources.append({"source": rel, "lines": line_numbers(text, TDESIGN_RE)[:20]})
        if "/components/" in rel:
            component_style_sources[rel] += text.count("<style") + text.count("class=")
    primitive = sorted(name for name in variables if not name.startswith("--sc-"))
    semantic = sorted(name for name in variables if name.startswith("--sc-"))
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "design_token_inventory",
        "sourceCommit": baseline_commit(root),
        **inventory_metadata(
            root,
            css_files,
            [{"scope": "style_bearing_frontend_source", "path": "frontend/apps/web/src/**/*.{css,scss,sass,vue}"}],
        ),
        "cssVariableDefinitions": [
            {"name": name, "values": sorted(item["values"]), "sources": item["sources"]}
            for name, item in sorted(variables.items())
        ],
        "classification": {
            "existingScPrefixedVariables": semantic,
            "otherVariablesNeedingTaxonomy": primitive,
            "hardcodedColorValues": [
                {"value": value, "count": count, "samples": color_sources[value]}
                for value, count in colors.most_common()
            ],
            "zIndexValues": [{"value": value, "count": count} for value, count in z_indexes.most_common()],
            "breakpoints": [{"condition": value, "count": count} for value, count in breakpoints.most_common()],
            "spacingValues": [{"value": value, "count": count} for value, count in spacing.most_common()],
            "radiusValues": [{"value": value, "count": count} for value, count in radius.most_common()],
            "shadowValues": [{"value": value, "count": count} for value, count in shadows.most_common()],
            "pageWidthValues": [{"value": value, "count": count} for value, count in widths.most_common()],
            "tdesignDirectUse": tdesign_sources,
            "componentStyleSurface": [{"source": source, "score": score} for source, score in component_style_sources.most_common()],
        },
        "interpretationRules": {
            "hardcodedColor": "A lexical CSS value; this report does not claim every occurrence is invalid before an allowlist exists.",
            "spacingRadiusShadow": "Phase 0 records variables and direct CSS evidence. Token hierarchy classification is a Phase 1 design decision.",
            "mobile": "Breakpoint inventory is static only; overflow requires later browser evidence.",
        },
    }


def component_coverage_inventory(root: Path, frontend_files: list[Path]) -> dict[str, Any]:
    design_dir = root / "frontend/apps/web/src/components/design-system"
    design_components = sorted(design_dir.glob("Sc*.vue"))
    declared: list[dict[str, Any]] = []
    for path in design_components:
        name = path.stem
        declared.append(
            {
                "componentKey": name,
                "sourcePresent": True,
                "assessmentStatus": "unassessed",
                "semanticType": "not_declared",
                "supportedFieldTypes": "not_declared",
                "supportedPresentationModes": "not_declared",
                "supportedRenderProfiles": "not_declared",
                "fallback": "not_declared",
                "sourceFiles": [repo_path(root, path)],
                "evidence": {"sourcePresentOnly": True, "formalRegistryAbsent": True},
            }
        )
    requested_primitives = [
        "ScButton", "ScInput", "ScSelect", "ScDialog", "ScDrawer", "ScTabs", "ScTable", "ScBadge", "ScTooltip", "ScDropdown",
        "ScFormField", "ScLoading", "ScEmptyState", "ScErrorState",
    ]
    existing = {row["componentKey"] for row in declared}
    missing = [
        {
            "componentKey": name,
            "sourcePresent": False,
            "assessmentStatus": "unassessed",
            "reason": "No exact Sc* source file exists; an adapter or alias remains a Phase 2 decision, not a current capability assertion.",
        }
        for name in requested_primitives
        if name not in existing
    ]
    component_key_occurrences: list[dict[str, Any]] = []
    for path in frontend_files:
        text = read(path)
        keys = sorted(set(COMPONENT_KEY_RE.findall(text)))
        if keys:
            component_key_occurrences.append({"source": repo_path(root, path), "componentKeys": keys, "lines": line_numbers(text, COMPONENT_KEY_RE)[:24]})
    registry_files = [
        repo_path(root, path) for path in frontend_files
        if any(token in repo_path(root, path).lower() for token in ("registry", "renderer", "fieldrenderer", "component"))
        and ("componentKey" in read(path) or "renderer" in path.name.lower())
    ]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "kind": "component_coverage_inventory",
        "sourceCommit": baseline_commit(root),
        **inventory_metadata(
            root,
            frontend_files,
            [{"scope": "component_and_renderer_candidate_source", "path": "frontend/apps/web/src"}],
        ),
        "declaredComponents": declared,
        "phase2PrimitiveGaps": missing,
        "phase2TargetPrimitives": [
            {
                "componentKey": name,
                "targetState": "planned_phase_2_adapter_api",
                "currentExactSourcePresent": name in existing,
                "notCurrentCapability": True,
            }
            for name in requested_primitives
        ],
        "componentKeyUseSites": component_key_occurrences,
        "candidateRegistryOrRendererFiles": sorted(set(registry_files)),
        "coveragePolicy": {
            "currentState": "Source presence is inventoried only. Phase 0 has no formal registry or test authority for readiness, capability, fallback, or supported-mode assertions.",
            "futureRequirement": "Phase 6 registry must declare key, semantic type, supported field types, presentation modes, render profiles, capability requirements, renderer, fallback, and readiness.",
            "noSilentFallback": True,
        },
    }


def markdown_plan(page: dict[str, Any], navigation: dict[str, Any], design: dict[str, Any], components: dict[str, Any]) -> str:
    route_count = len(page["routes"])
    observed = len(page["runtimeObservedActionSurfaces"])
    action_count = len(page["declarativeActionDefinitions"])
    menu_count = len(page["declarativeMenuDefinitions"])
    token_count = len(design["cssVariableDefinitions"])
    color_count = sum(item["count"] for item in design["classification"]["hardcodedColorValues"])
    primitive_gaps = len(components["phase2PrimitiveGaps"])
    component_count = len(components["declaredComponents"])
    sha = page["sourceCommit"]
    return f"""# 全系统前端专业化 Phase 0 基线与缺口计划\n\n+## 身份与范围\n\n+- 基线提交：`{sha}`\n+- 审计类型：静态、可复现、只读；未启动浏览器、服务、数据库或 fixture。\n+- Formal Product Layer：P4（工程盘点与证据）；后续 Tokens/Primitives/Shell 等产品实现应分别按 P0 立项。\n+- 扫描器：`scripts/audit/generate_frontend_professionalization_baseline.py`。\n+- 输出：`page-surface-inventory.json`、`navigation-authority-inventory.json`、`design-token-inventory.json`、`component-coverage-inventory.json`。\n\n+## 当前证据摘要\n\n+| 维度 | 静态证据 | 解释 |\n+| --- | ---: | --- |\n+| 路由页面面 | {route_count} | Vue Router 的正式静态入口；record 的 task/workspace 必须由运行时 Contract V2 判定。 |\n+| 已观察 action/menu 表面 | {observed} | 历史角色旅程 CSV，不能视为全量当前权限目录。 |\n+| 声明式 window action | {action_count} | XML 静态定义；不等于当前用户可访问的 action。 |\n+| 声明式菜单 | {menu_count} | XML 静态定义；运行时可见性应以后端导航解释为准。 |\n+| CSS 变量 | {token_count} | 需要 Phase 1 归类为 primitive / semantic / component / pattern。 |\n+| 硬编码色彩词法命中 | {color_count} | 先作为 allowlist 输入；不把扫描命中直接等同为违规。 |\n+| 已有 `Sc*` 组件 | {component_count} | 有基础目录，但无统一 readiness/capability registry。 |\n+| Phase 2 精确 primitive 缺口 | {primitive_gaps} | 以请求 API 名称严格比对；别名须显式决定。 |\n+\n+## P0 缺口（平台通用机制）\n\n+1. **Design Token v1 权威层缺失。** 现有变量、硬编码值和组件样式共存；Phase 1 应先建立四层 token taxonomy 与 allowlist，再迁移，而不批量改业务布局。\n+2. **Primitive Adapter API 尚未完整。** `components/design-system` 已提供一部分 `Sc*` 组件，但请求的输入、tabs、table、badge、tooltip、dropdown、form field、loading 等精确 API 未全部存在。Phase 2 应先声明 alias/缺口，再只迁移 Shell 所需组件。\n+3. **导航权威尚未被一个 Canonical Navigation Model 显式收束。** 静态代码已有 session/menu、router、AppShell、PrimaryNavigation 和 activity 等路径；Phase 3 应仅由后端提供可见性、父链、action/menu 配对、disabled reason、排序和层级，前端仅保留交互状态。\n+4. **页面 Header 存在多个呈现入口。** Shell 顶栏、`PageHeader`、`ScPageHeader`、列表 Header 和表单/场景 Header 应在 Phase 4 统一 presentation model；本审计不决定视觉重构。\n+5. **组件能力登记不完整。** 组件和 renderer 已散布在多个目录，但没有一份能声明 `componentKey → capability → fallback → readiness` 的唯一机器可读 registry。Phase 6 需要建立该 registry 和 fail-closed guard。\n+\n+## P1 缺口（行业能力，等待 P0 registry）\n\n+1. 项目、合同、付款、结算等领域表面已通过 action/model 被观察到，但其 component profile 不能由模型名或标签在前端推断；应在 Phase 9 由行业模块以正式契约声明。\n+2. x2many、workflow、audit、collaboration 等复杂业务能力需要在 Phase 7/8 建立通用 capability 后再按领域接入；当前仅记录 renderer 位置与缺口，未提出模型特判。\n+\n+## 运行态证据缺口\n\n+- 当前用户最终导航树、菜单父链、无权入口、收藏/最近使用、折叠偏好及深链恢复需要未来受管运行态抽样。\n+- action/view/role/presentationMode 组合需要 Contract V2 trace；静态扫描不得推测 task/workspace。\n+- 390px overflow、键盘焦点、Drawer Escape 与业务 mutation 需要后续每个 P0 批次的受管浏览器证据。\n+\n+## 实施顺序与独立 PR 边界\n\n+1. Tokens → 2. Primitives → 3. Navigation Shell → 4. Page Header → 5. Page Patterns → 6. Component Registry → 7/8. 通用组件能力 → 9. 行业组件 → 10. 业务域推广。\n+\n+每项均独立分支/PR、独立指纹和回滚点；Phase 0 不承载任何产品改动。任何业务域发现 P0 缺口时，应暂停业务域批次，回到独立 P0 修复。\n+\n+## 下一步\n\n+对本审计进行只读评审，确认四份 JSON 的字段边界与 P0/P1 分类。通过后仅启动 `feature/p0-design-token-system-v1`，不并行启动 Shell 或行业组件写入。\n+"""


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = (root / args.output_dir).resolve()
    if output.parent != (root / "docs/frontend_productization").resolve() and output != (root / "docs/frontend_productization").resolve():
        raise SystemExit("output directory must remain under docs/frontend_productization")
    output.mkdir(parents=True, exist_ok=True)
    frontend_files = source_files(root)
    page = page_surface_inventory(root, frontend_files)
    navigation = navigation_inventory(root, frontend_files)
    design = design_token_inventory(root, frontend_files)
    components = component_coverage_inventory(root, frontend_files)
    write_json(output / "page-surface-inventory.json", page)
    write_json(output / "navigation-authority-inventory.json", navigation)
    write_json(output / "design-token-inventory.json", design)
    write_json(output / "component-coverage-inventory.json", components)
    (output / "professionalization-gap-plan.md").write_text(
        markdown_plan(page, navigation, design, components).replace("\n+", "\n"), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
