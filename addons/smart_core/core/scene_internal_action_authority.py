#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Server-authoritative scene internal action resolution.

Scene contracts keep ``action_xmlid`` as the stable product reference.  This
module resolves it against the current database and returns a controlled
runtime descriptor.  It never accepts a client-supplied numeric action_id and
never mutates the scene payload's handling-entry targets (which would preempt
canonical navigation resolution).
"""

from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def _catalog_items(scene: dict) -> list[dict]:
    catalog = scene.get("handling_entry_catalog") if isinstance(scene, dict) else None
    if not isinstance(catalog, dict):
        return []
    items: list[dict] = []
    for group in (catalog.get("groups") if isinstance(catalog.get("groups"), list) else []):
        if not isinstance(group, dict):
            continue
        for item in (group.get("items") if isinstance(group.get("items"), list) else []):
            if isinstance(item, dict):
                items.append(item)
    return items


def build_scene_internal_actions(env, scenes: list[dict] | None) -> dict[str, dict]:
    """Return a ``scene_key:item_key`` -> runtime action descriptor map."""
    out: dict[str, dict] = {}
    if env is None:
        return out
    for scene in scenes or []:
        if not isinstance(scene, dict):
            continue
        scene_key = _text(scene.get("code") or scene.get("key"))
        if not scene_key:
            continue
        for item in _catalog_items(scene):
            target = item.get("target") if isinstance(item.get("target"), dict) else {}
            action_xmlid = _text(item.get("action_xmlid") or target.get("action_xmlid"))
            if not action_xmlid:
                continue
            action = env.ref(action_xmlid, raise_if_not_found=False)
            if action is None:
                continue
            action_id = int(action.id)
            if action_id <= 0:
                continue
            declared_model = _text(item.get("model") or target.get("model"))
            action_model = _text(getattr(action, "res_model", ""))
            if declared_model and action_model and declared_model != action_model:
                continue
            menu_xmlid = _text(item.get("menu_xmlid") or target.get("menu_xmlid"))
            menu = env.ref(menu_xmlid, raise_if_not_found=False) if menu_xmlid else None
            menu_id = int(menu.id) if menu else 0
            item_key = _text(item.get("key"))
            if not item_key:
                item_key = action_xmlid
            key = f"{scene_key}:{item_key}"
            if key in out:
                continue
            out[key] = {
                "scene_key": scene_key,
                "item_key": item_key,
                "action_xmlid": action_xmlid,
                "action_id": action_id,
                "menu_id": menu_id,
                "menu_xmlid": menu_xmlid,
                "model": action_model,
                "name": _text(getattr(action, "name", "")),
                "view_modes": list(getattr(action, "view_mode", "") and getattr(action, "view_mode").split(",") or []),
                "allowed": True,
            }
    return out
