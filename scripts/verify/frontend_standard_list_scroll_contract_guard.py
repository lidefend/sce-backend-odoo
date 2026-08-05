#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LIST_PAGE = ROOT / "frontend/apps/web/src/pages/ListPage.vue"
LIST_STYLES = ROOT / "frontend/apps/web/src/pages/ListPage.css"
SHELL_STYLES = ROOT / "frontend/apps/web/src/layouts/AppShell.css"
LIST_HEADER = ROOT / "frontend/apps/web/src/components/product-list/ProductListHeader.vue"


def iter_rules(source: str) -> list[tuple[str, dict[str, str]]]:
    text = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    rules: list[tuple[str, dict[str, str]]] = []
    cursor = 0
    while cursor < len(text):
        opening = text.find("{", cursor)
        if opening < 0:
            break
        selector = text[cursor:opening].strip()
        depth = 1
        closing = opening + 1
        while closing < len(text) and depth:
            depth += (text[closing] == "{") - (text[closing] == "}")
            closing += 1
        if depth:
            raise ValueError(f"unbalanced CSS block near {selector!r}")
        body = text[opening + 1 : closing - 1]
        if selector.startswith("@"):
            rules.extend(iter_rules(body))
        else:
            declarations = {
                match.group(1).strip().lower(): match.group(2).strip().lower()
                for match in re.finditer(r"([\w-]+)\s*:\s*([^;{}]+)\s*;?", body)
            }
            for item in selector.split(","):
                if item.strip():
                    rules.append((item.strip(), declarations))
        cursor = closing
    return rules


def declarations_for(
    rules: list[tuple[str, dict[str, str]]],
    selector: str,
) -> list[dict[str, str]]:
    return [declarations for candidate, declarations in rules if candidate == selector]


def validate_contract(css: str, template: str, header_source: str) -> list[str]:
    errors: list[str] = []
    rules = iter_rules(css)
    table_rules = declarations_for(rules, ".table")
    if not table_rules:
        return ["standard .table rule missing"]
    table = {}
    for declarations in table_rules:
        table.update(declarations)

    if table.get("overflow") != "hidden":
        errors.append("standard list frame must clip horizontal movement to its table surface")
    if table.get("overflow-y") in {"auto", "scroll"}:
        errors.append("standard list must not own vertical scrolling")
    for property_name in ("height", "max-height"):
        value = table.get(property_name, "")
        if value and value not in {"auto", "none"}:
            errors.append(f"standard list must use natural height: {property_name}={value}")
    if any(unit in table.get("height", "") + table.get("max-height", "") for unit in ("vh", "dvh", "svh", "lvh")):
        errors.append("standard list must not use viewport-derived height")

    table_shell = {}
    for declarations in declarations_for(rules, ".table > .sc-table-shell"):
        table_shell.update(declarations)
    if table_shell.get("overflow-x") not in {"auto", "scroll"}:
        errors.append("table shell must be the sole horizontal scrolling owner")
    if table_shell.get("overflow-y") in {"auto", "scroll"}:
        errors.append("table shell must not own vertical scrolling")

    header_rules = declarations_for(rules, ".table thead th")
    header = {}
    for declarations in header_rules:
        header.update(declarations)
    if header.get("position") != "sticky":
        errors.append("standard table header must use native sticky positioning")
    if header.get("top") != "0":
        errors.append("standard table header must bind to the local scroll-owner origin")
    if "transform" in header:
        errors.append("standard table header must not simulate sticky positioning with transforms")

    desktop_page = {}
    for declarations in declarations_for(rules, ".page[data-product-page-mode='list']"):
        desktop_page.update(declarations)
    if (
        desktop_page.get("overflow") != "visible"
        or desktop_page.get("min-height") != "100%"
        or desktop_page.get("height") != "auto"
    ):
        errors.append("desktop list page must use natural height and delegate vertical scrolling to the router host")
    desktop_table_shell = {}
    for declarations in declarations_for(rules, ".page[data-product-page-mode='list'] .table > .sc-table-shell"):
        desktop_table_shell.update(declarations)
    if (
        desktop_table_shell.get("overflow-x") not in {"auto", "scroll"}
        or desktop_table_shell.get("overflow-y") in {"auto", "scroll"}
        or desktop_table_shell.get("flex") != "0 0 auto"
    ):
        errors.append("desktop table shell must use natural height and own horizontal scrolling only")

    for selector, declarations in rules:
        normalized = " ".join(selector.split())
        position = declarations.get("position", "")
        if ".pagination-footer" in normalized and position in {"sticky", "fixed"}:
            errors.append(f"pagination must remain in document flow: {selector}")

    if 'class="table sc-product-main-surface"' not in template:
        errors.append("standard list surface identity is missing")
    if "data-workspace-primary-content" not in template:
        errors.append("standard list primary-content contract is missing")
    if re.search(r"table[^>]*contained-scroll|contained-scroll[^>]*table", template):
        errors.append("standard business list must not opt into contained scrolling")
    if "scrollLeft" in header_source or "--sc-list-inline-scroll-offset" in header_source:
        errors.append("query bar must never compensate for horizontal scrolling")
    if "isolation: isolate" not in css:
        errors.append("standard list must contain sticky/frozen layers below application overlays")
    return errors


def validate_shell_contract(css: str) -> list[str]:
    errors: list[str] = []
    rules = iter_rules(css)
    content = {}
    router = {}
    for declarations in declarations_for(rules, ".content"):
        content.update(declarations)
    for declarations in declarations_for(rules, ".router-host"):
        router.update(declarations)
    if content.get("overflow") != "hidden":
        errors.append("AppShell content grid must clip at the application boundary")
    if router.get("overflow-y") not in {"auto", "scroll"}:
        errors.append("router host must own business-page vertical scrolling")
    if router.get("overflow-x") != "hidden":
        errors.append("router host must prevent page-level horizontal overflow")
    return errors


def run_self_tests() -> list[str]:
    template = '<section class="table sc-product-main-surface" data-workspace-primary-content></section>'
    header_source = "const queryBar = ref(null);"
    valid = """
      .page.sc-product-workspace-stack { isolation: isolate; }
      .table { width: 100%; overflow: hidden; }
      .table > .sc-table-shell { overflow-x: auto; overflow-y: hidden; }
      .page[data-product-page-mode='list'] { height: auto; min-height: 100%; overflow: visible; }
      .page[data-product-page-mode='list'] .table > .sc-table-shell { flex: 0 0 auto; min-height: auto; overflow-x: auto; overflow-y: hidden; }
      .table thead th { position: sticky; top: 0; }
      .pagination-footer { position: static; }
    """
    fixtures = {
        "valid": (valid, False),
        "vertical-auto": (valid + ".table { overflow-y: auto; }", True),
        "shell-vertical-auto": (valid + ".table > .sc-table-shell { overflow-y: auto; }", True),
        "desktop-bounded-two-axis": (
            valid + ".page[data-product-page-mode='list'] .table > .sc-table-shell { flex: 1 1 auto; min-height: 0; overflow: auto; }",
            True,
        ),
        "desktop-page-clipping": (
            valid + ".page[data-product-page-mode='list'] { height: 100%; min-height: 0; overflow: hidden; }",
            True,
        ),
        "viewport-height": (valid + ".table { max-height: calc(100vh - 12px); }", True),
        "fixed-height": (valid + ".table { height: 600px; }", True),
        "sticky-pagination": (valid + ".pagination-footer { position: sticky; }", True),
        "fixed-pagination": (valid + ".pagination-footer { position: fixed; }", True),
        "missing-horizontal": (
            valid + ".table > .sc-table-shell { overflow-x: hidden; }",
            True,
        ),
        "transform-sticky": (
            valid + ".table thead th { position: relative; transform: translateY(4px); }",
            True,
        ),
    }
    failures: list[str] = []
    for name, (css, should_fail) in fixtures.items():
        actual_failed = bool(validate_contract(css, template, header_source))
        if actual_failed != should_fail:
            failures.append(f"self-test {name}: expected_fail={should_fail} actual_fail={actual_failed}")
    shell_fixtures = {
        "valid-shell": (
            ".content { overflow: hidden; } .router-host { overflow-x: hidden; overflow-y: auto; }",
            False,
        ),
        "content-scroll": (
            ".content { overflow: auto; } .router-host { overflow-x: hidden; overflow-y: auto; }",
            True,
        ),
        "router-no-scroll": (
            ".content { overflow: hidden; } .router-host { overflow-x: hidden; overflow-y: visible; }",
            True,
        ),
        "router-horizontal-leak": (
            ".content { overflow: hidden; } .router-host { overflow-x: auto; overflow-y: auto; }",
            True,
        ),
    }
    for name, (css, should_fail) in shell_fixtures.items():
        actual_failed = bool(validate_shell_contract(css))
        if actual_failed != should_fail:
            failures.append(f"self-test {name}: expected_fail={should_fail} actual_fail={actual_failed}")
    return failures


def main() -> int:
    errors = run_self_tests()
    errors.extend(
        validate_contract(
            LIST_STYLES.read_text(encoding="utf-8"),
            LIST_PAGE.read_text(encoding="utf-8"),
            LIST_HEADER.read_text(encoding="utf-8"),
        )
    )
    errors.extend(validate_shell_contract(SHELL_STYLES.read_text(encoding="utf-8")))
    if errors:
        print("[frontend_standard_list_scroll_contract_guard] FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[frontend_standard_list_scroll_contract_guard] PASS")
    print("vertical_owner=router-host")
    print("app_header_boundary=isolated-grid-row")
    print("table_horizontal_owner=sc-table-shell")
    print("query_bar_horizontal_motion=none")
    print("pagination_document_flow=true")
    print("header_native_sticky=true")
    print("list_overlay_containment=isolated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
