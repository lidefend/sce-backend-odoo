"""Pure declarations shared by scenario organization producers and consumers."""
from __future__ import annotations

import json
from pathlib import Path


SURFACE_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "scenario_product_surface.json"
)


def _load_surface() -> dict:
    surface = json.loads(SURFACE_PATH.read_text(encoding="utf-8"))
    if not isinstance(surface, dict):
        raise ValueError("scenario product surface must be an object")
    return surface


def _direct_platform_pages(surface: dict) -> tuple[dict[str, str], ...]:
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


def _scenario_owner_centers(surface: dict) -> dict[str, str]:
    centers = surface.get("centers")
    center_keys = {
        str(row.get("key") or "").strip()
        for row in centers or []
        if isinstance(row, dict) and str(row.get("key") or "").strip()
    }
    rows = surface.get("scenarios")
    if not isinstance(rows, list):
        raise ValueError("scenario product surface requires scenarios")
    owners: dict[str, str] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"scenarios[{index}] must be an object")
        scene_key = str(row.get("key") or "").strip()
        owner_center = str(row.get("owner_center") or "").strip()
        if not scene_key or scene_key in owners:
            raise ValueError(f"invalid duplicate scenario key: {scene_key!r}")
        if not owner_center or (center_keys and owner_center not in center_keys):
            raise ValueError(
                f"scenario {scene_key!r} requires a declared owner center"
            )
        owners[scene_key] = owner_center
    return owners


_SURFACE = _load_surface()
DIRECT_PLATFORM_PAGES = _direct_platform_pages(_SURFACE)
SCENARIO_OWNER_CENTER_BY_KEY = _scenario_owner_centers(_SURFACE)
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
