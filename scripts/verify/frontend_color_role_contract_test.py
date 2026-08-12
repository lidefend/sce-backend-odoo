#!/usr/bin/env python3
"""Behavioral source contract for shared semantic color roles."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOKENS = ROOT / "frontend/packages/design-tokens"
WEB = ROOT / "frontend/apps/web/src"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def css_block(source: str, selector: str) -> str:
    start = source.find(selector)
    assert start >= 0, f"missing selector: {selector}"
    opening = source.find("{", start)
    closing = source.find("}", opening)
    assert opening >= 0 and closing > opening, f"invalid CSS block: {selector}"
    return source[opening + 1 : closing]


def exact_css_block(source: str, selector: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(selector)}\s*\{{", source)
    assert match, f"missing exact selector: {selector}"
    opening = source.find("{", match.start())
    closing = source.find("}", opening)
    assert closing > opening, f"invalid exact CSS block: {selector}"
    return source[opening + 1 : closing]


def assert_no_info_role(source: str, label: str) -> None:
    assert "--sc-app-info-" not in source, f"{label} uses state.info outside informational feedback"


negative_fixture_detected = False
try:
    assert_no_info_role(
        ".ordinary-surface { background: var(--sc-app-info-bg); }",
        "negative ordinary surface fixture",
    )
except AssertionError:
    negative_fixture_detected = True
assert negative_fixture_detected, "ordinary-surface info-role negative fixture was not detected"


light = json.loads(read(TOKENS / "tokens/semantic.light.json"))
dark = json.loads(read(TOKENS / "tokens/semantic.dark.json"))

expected = {
    "light": {
        ("surface", "hover"): "{color.slate_100}",
        ("surface", "selected"): "{color.blue_50}",
        ("surface", "navigation_active"): "{color.blue_50}",
        ("border", "selected"): "{color.blue_500}",
        ("border", "interactive"): "{color.blue_500}",
        ("text", "selected"): "{color.blue_700}",
        ("focus", "ring"): "{color.blue_700}",
        ("state", "info"): "{color.cyan_700}",
        ("state", "info_bg"): "{color.cyan_50}",
        ("state", "info_border"): "{color.cyan_700}",
        ("state", "info_text"): "{color.slate_800}",
    },
    "dark": {
        ("surface", "hover"): "rgba(148, 163, 184, 0.12)",
        ("surface", "selected"): "rgba(0, 182, 254, 0.16)",
        ("surface", "navigation_active"): "rgba(0, 182, 254, 0.16)",
        ("border", "selected"): "{color.cyan_500}",
        ("border", "interactive"): "{color.cyan_500}",
        ("text", "selected"): "#67d8ff",
        ("focus", "ring"): "{color.cyan_500}",
        ("state", "info"): "{color.blue_500}",
        ("state", "info_bg"): "rgba(37, 99, 235, 0.18)",
        ("state", "info_border"): "{color.blue_500}",
        ("state", "info_text"): "{color.blue_200}",
    },
}
for theme, document in (("light", light), ("dark", dark)):
    for (group, key), value in expected[theme].items():
        actual = document.get(group, {}).get(key)
        assert actual == value, f"{theme}.{group}.{key}: expected {value!r}, got {actual!r}"

design_system = read(WEB / "styles/design-system.css")
for alias in ("--sc-app-selected-bg", "--sc-app-selected-border", "--sc-app-selected-text"):
    assert alias in design_system, f"missing selected semantic alias: {alias}"

surface_files = {
    "home": read(WEB / "components/role-home/WorkspaceHome.vue"),
    "toolbar": read(WEB / "components/action/ActionSurfaceToolbar.vue"),
    "shell": read(WEB / "layouts/AppShell.css"),
}
for name, source in surface_files.items():
    assert_no_info_role(source, name)

list_header = read(WEB / "components/product-list/ListSurfaceHeader.vue")
assert list_header.count("--sc-app-info-") == 3, "only the saving feedback state may consume the three info roles"
saving = css_block(list_header, ".list-surface-save-badge.is-saving")
for role in ("--sc-app-info-border", "--sc-app-info-bg", "--sc-app-info-text"):
    assert role in saving, f"saving feedback lost {role}"
for selector in (".list-surface-column-menu", ".list-surface-column-reset"):
    assert "--sc-app-info-" not in css_block(list_header, selector), f"{selector} must be neutral"

home = surface_files["home"]
assert "--sc-app-selected-" not in css_block(home, ".role-home-surface__summary-list article"), "summary cards are not selected state"
assert "--sc-app-focus-ring" in css_block(home, ".role-home-surface button:focus-visible"), "home actions require explicit focus-visible"

toolbar = surface_files["toolbar"]
for selector in (
    ".search-facet",
    ".search-menu-item.selected",
    ".toolbar-overflow-section button.active",
    ".contract-chip.active",
):
    block = css_block(toolbar, selector)
    assert "--sc-app-selected-" in block, f"{selector} must consume selected semantics"
for selector in (".toolbar-search-submit", ".contract-chip.primary"):
    block = exact_css_block(toolbar, selector)
    assert "--sc-semantic-surface-interactive" in block, f"{selector} must retain primary interactive semantics"

shell = surface_files["shell"]
assert "--sc-navigation-active-bg" in css_block(shell, ".workspace-activity-rail button.active"), "navigation leaf must retain navigation active role"
assert "inset 0 3px 0 var(--sc-semantic-surface-interactive)" not in css_block(shell, ".topbar--minimal"), "global topbar must not carry a brand stripe"
assert "inset 0 3px 0 var(--sc-app-border)" in exact_css_block(shell, ".topbar--minimal"), "color-only batch must preserve topbar inset geometry"
assert "0 4px 16px" in shell, "color-only batch must preserve the desktop topbar elevation geometry"

for theme in ("light", "dark"):
    generated = read(TOKENS / f"dist/web/tokens.{theme}.css")
    for generated_name in (
        "--sc-semantic-surface-selected",
        "--sc-semantic-border-selected",
        "--sc-semantic-text-selected",
    ):
        assert generated_name in generated, f"generated {theme} tokens missing {generated_name}"

assert not re.search(r"--sc-semantic-focus-ring:\s*rgba\(", read(TOKENS / "dist/web/tokens.light.css")), "light focus ring must be opaque"
assert not re.search(r"--sc-semantic-focus-ring:\s*rgba\(", read(TOKENS / "dist/web/tokens.dark.css")), "dark focus ring must be opaque"

print("[frontend_color_role_contract_test] PASS")
