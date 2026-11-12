# -*- coding: utf-8 -*-
"""Compile executable final-navigation leaves through scene routes."""
from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


CONTENT_DESIGNED_SCENE = "designed_scene"
CONTENT_NATIVE_DELEGATE = "native_delegate"
CONTENT_CONTAINER = "container"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _to_int(value: Any) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", _text(value).lower()).strip("_") or "entry"


def _target(node: dict) -> dict:
    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    entry_target = (
        node.get("entry_target")
        if isinstance(node.get("entry_target"), dict)
        else meta.get("entry_target")
        if isinstance(meta.get("entry_target"), dict)
        else {}
    )
    refs = (
        entry_target.get("compatibility_refs")
        if isinstance(entry_target.get("compatibility_refs"), dict)
        else {}
    )
    return {
        "menu_id": _to_int(
            node.get("menu_id")
            or node.get("config_menu_id")
            or meta.get("menu_id")
            or meta.get("config_menu_id")
            or refs.get("menu_id")
        ),
        "action_id": _to_int(
            node.get("action_id")
            or meta.get("action_id")
            or refs.get("action_id")
        ),
        "menu_xmlid": _text(
            node.get("menu_xmlid")
            or node.get("xmlid")
            or node.get("xml_id")
            or meta.get("menu_xmlid")
        ),
        "action_xmlid": _text(node.get("action_xmlid") or meta.get("action_xmlid")),
        "scene_key": _text(
            node.get("scene_key")
            or meta.get("scene_key")
            or entry_target.get("scene_key")
        ),
        "route": _text(
            node.get("route")
            or meta.get("route")
            or entry_target.get("route")
        ),
        "model": _text(
            node.get("model")
            or meta.get("model")
            or refs.get("model")
        ),
        "view_modes": (
            list(node.get("view_modes"))
            if isinstance(node.get("view_modes"), list)
            else list(meta.get("view_modes"))
            if isinstance(meta.get("view_modes"), list)
            else list(refs.get("view_modes"))
            if isinstance(refs.get("view_modes"), list)
            else []
        ),
        "entry_target": deepcopy(entry_target),
    }


def _native_scene_key(target: dict) -> str:
    menu_xmlid = _text(target.get("menu_xmlid"))
    if menu_xmlid:
        owner, _, tail = menu_xmlid.partition(".")
        return "entry.%s.%s" % (_slug(owner or "odoo"), _slug(tail or menu_xmlid))
    action_xmlid = _text(target.get("action_xmlid"))
    if action_xmlid:
        owner, _, tail = action_xmlid.partition(".")
        return "entry.%s.%s" % (_slug(owner or "odoo"), _slug(tail or action_xmlid))
    return "entry.runtime.menu_%s_action_%s" % (
        _to_int(target.get("menu_id")) or 0,
        _to_int(target.get("action_id")) or 0,
    )


def _native_target(node: dict, scene_key: str) -> dict:
    target = _target(node)
    return {
        "type": "action",
        "route": "/s/%s" % scene_key,
        "menu_id": target["menu_id"],
        "action_id": target["action_id"],
        **({"model": target["model"]} if target["model"] else {}),
        **({"view_modes": target["view_modes"]} if target["view_modes"] else {}),
        "compatibility_refs": {
            "menu_id": target["menu_id"],
            "action_id": target["action_id"],
            **({"model": target["model"]} if target["model"] else {}),
        },
    }


@dataclass(frozen=True)
class SceneShellCompilation:
    nav: list[dict]
    scene_shell_rows: list[dict] = field(default_factory=list)
    designed_scene_keys: list[str] = field(default_factory=list)
    native_delegate_scene_keys: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)


class SceneShellCompiler:
    """Create scene shells without creating menu/action/view facts."""

    SOURCE_KIND = "scene_shell_final_contract_projection"

    def compile(
        self,
        nav: list[dict],
        *,
        designed_scene_keys,
    ) -> SceneShellCompilation:
        designed = {_text(key) for key in designed_scene_keys or [] if _text(key)}
        seen_scene_keys: set[str] = set()
        shell_rows: list[dict] = []
        designed_keys: list[str] = []
        delegate_keys: list[str] = []
        sequence = 0

        def compile_node(node: dict) -> dict | None:
            nonlocal sequence
            if not isinstance(node, dict):
                return None
            candidate = deepcopy(node)
            meta = dict(candidate.get("meta") if isinstance(candidate.get("meta"), dict) else {})
            children = [
                child
                for raw_child in candidate.get("children") or []
                if (child := compile_node(raw_child)) is not None
            ]
            if children:
                for key in (
                    "route",
                    "scene_key",
                    "entry_target",
                    "action_id",
                    "target",
                ):
                    candidate.pop(key, None)
                    meta.pop(key, None)
                candidate.update({
                    "children": children,
                    "content_kind": CONTENT_CONTAINER,
                    "target_type": "directory",
                    "delivery_mode": "none",
                    "is_clickable": False,
                    "reason_code": "DIRECTORY_ONLY",
                    "meta": meta,
                })
                return candidate

            target = _target(candidate)
            scene_key = target["scene_key"]
            if scene_key:
                if scene_key not in designed:
                    raise ValueError(
                        "scene target lacks an explicitly designed scene contract: %s"
                        % scene_key
                    )
                candidate["content_kind"] = CONTENT_DESIGNED_SCENE
                candidate["scene_key"] = scene_key
                candidate["route"] = "/s/%s" % scene_key
                meta.update({
                    "content_kind": CONTENT_DESIGNED_SCENE,
                    "scene_key": scene_key,
                    "route": candidate["route"],
                })
                candidate["meta"] = meta
                if scene_key not in seen_scene_keys:
                    seen_scene_keys.add(scene_key)
                    designed_keys.append(scene_key)
                return candidate

            if target["action_id"] <= 0:
                return None
            scene_key = _native_scene_key(target)
            if scene_key in seen_scene_keys:
                raise ValueError("duplicate generated scene key: %s" % scene_key)
            seen_scene_keys.add(scene_key)
            delegate_keys.append(scene_key)
            sequence += 1
            native_target = _native_target(candidate, scene_key)
            candidate["scene_key"] = scene_key
            candidate["route"] = "/s/%s" % scene_key
            candidate["content_kind"] = CONTENT_NATIVE_DELEGATE
            candidate["entry_target"] = {
                "type": "scene",
                "scene_key": scene_key,
                "route": "/s/%s" % scene_key,
                "content_kind": CONTENT_NATIVE_DELEGATE,
                "native_target": native_target,
            }
            meta.update({
                "scene_key": scene_key,
                "route": candidate["route"],
                "content_kind": CONTENT_NATIVE_DELEGATE,
                "entry_target": deepcopy(candidate["entry_target"]),
            })
            candidate["meta"] = meta
            shell_rows.append(
                self._scene_ready_row(
                    scene_key=scene_key,
                    label=_text(
                        candidate.get("label")
                        or candidate.get("title")
                        or candidate.get("name")
                        or scene_key
                    ),
                    native_target=native_target,
                    sequence=sequence,
                )
            )
            return candidate

        compiled_nav = [
            row
            for node in nav or []
            if (row := compile_node(node)) is not None
        ]
        return SceneShellCompilation(
            nav=compiled_nav,
            scene_shell_rows=shell_rows,
            designed_scene_keys=sorted(designed_keys),
            native_delegate_scene_keys=sorted(delegate_keys),
            diagnostics={
                "source_kind": self.SOURCE_KIND,
                "designed_scene_count": len(designed_keys),
                "native_delegate_scene_count": len(delegate_keys),
                "total_scene_count": len(seen_scene_keys),
            },
        )

    @staticmethod
    def _scene_ready_row(
        *,
        scene_key: str,
        label: str,
        native_target: dict,
        sequence: int,
    ) -> dict:
        target = {
            "route": "/s/%s" % scene_key,
            "action_id": native_target.get("action_id"),
            "menu_id": native_target.get("menu_id"),
            "model": native_target.get("model"),
            "view_mode": ",".join(native_target.get("view_modes") or []),
        }
        return {
            "scene": {
                "key": scene_key,
                "title": label,
            },
            "page": {
                "scene_key": scene_key,
                "title": label,
                "route": "/s/%s" % scene_key,
                "page_type": CONTENT_NATIVE_DELEGATE,
                "layout_mode": "single_flow",
            },
            "target": deepcopy(target),
            "permission_surface": {
                "visible": True,
                "allowed": True,
                "reason_code": "",
                "required_capabilities": [],
            },
            "meta": {
                "mode": "scene_shell",
                "content_kind": CONTENT_NATIVE_DELEGATE,
                "designed": False,
                "sequence": sequence,
                "target": deepcopy(target),
                "source_authority": {
                    "kind": SceneShellCompiler.SOURCE_KIND,
                    "projection_only": True,
                    "no_business_fact_authority": True,
                },
            },
        }

    @staticmethod
    def merge_scene_ready_contract(contract: dict | None, shell_rows: list[dict] | None) -> dict:
        result = deepcopy(contract) if isinstance(contract, dict) else {}
        rows = [
            deepcopy(row)
            for row in result.get("scenes") or []
            if isinstance(row, dict)
        ]
        seen = {
            _text(
                (row.get("scene") or {}).get("key")
                if isinstance(row.get("scene"), dict)
                else ""
            )
            for row in rows
        }
        for row in shell_rows or []:
            if not isinstance(row, dict):
                continue
            scene = row.get("scene") if isinstance(row.get("scene"), dict) else {}
            scene_key = _text(scene.get("key"))
            if not scene_key or scene_key in seen:
                continue
            rows.append(deepcopy(row))
            seen.add(scene_key)
        result["scenes"] = rows
        meta = dict(result.get("meta") if isinstance(result.get("meta"), dict) else {})
        meta["scene_count"] = len(rows)
        meta["scene_shell_count"] = sum(
            1
            for row in rows
            if _text(
                (row.get("meta") or {}).get("mode")
                if isinstance(row.get("meta"), dict)
                else ""
            ) == "scene_shell"
        )
        result["meta"] = meta
        return result
