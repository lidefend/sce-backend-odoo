"""Pure declarations shared by scenario organization producers and consumers."""
from __future__ import annotations

import json
from pathlib import Path


SURFACE_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "scenario_product_surface.json"
)


def _direct_platform_pages() -> tuple[dict[str, str], ...]:
    surface = json.loads(SURFACE_PATH.read_text(encoding="utf-8"))
    rows = surface.get("direct_platform_pages")
    if not isinstance(rows, list):
        raise ValueError("scenario product surface requires direct_platform_pages")
    declarations = []
    seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"direct_platform_pages[{index}] must be an object")
        menu_xmlid = str(row.get("menu_xmlid") or "").strip()
        kind = str(row.get("kind") or "").strip()
        if not menu_xmlid or menu_xmlid in seen:
            raise ValueError(f"invalid duplicate direct platform menu: {menu_xmlid!r}")
        if kind not in {
            "workbench_direct",
            "configuration",
            "platform_initialization",
        }:
            raise ValueError(f"invalid direct platform kind: {kind!r}")
        seen.add(menu_xmlid)
        declarations.append({"menu_xmlid": menu_xmlid, "kind": kind})
    return tuple(declarations)


DIRECT_PLATFORM_PAGES = _direct_platform_pages()
DIRECT_CONFIGURATION_MENU_XMLIDS = tuple(
    row["menu_xmlid"]
    for row in DIRECT_PLATFORM_PAGES
    if row["kind"] == "configuration"
)
DIRECT_WORKSPACE_MENU_XMLIDS = tuple(
    row["menu_xmlid"]
    for row in DIRECT_PLATFORM_PAGES
    if row["kind"] == "workbench_direct"
)
DIRECT_PLATFORM_MENU_XMLIDS = tuple(
    row["menu_xmlid"]
    for row in DIRECT_PLATFORM_PAGES
    if row["kind"] != "workbench_direct"
)
DIRECT_NAVIGATION_MENU_XMLIDS = tuple(
    row["menu_xmlid"] for row in DIRECT_PLATFORM_PAGES
)
