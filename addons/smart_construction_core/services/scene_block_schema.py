# -*- coding: utf-8 -*-
from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:
    from odoo.addons.smart_core.core.page_block_data_contract import (
        build_data_contract,
        build_page_orchestration_page_block_data,
        descriptor_ref,
        field_descriptor,
    )
except ModuleNotFoundError:
    _provider_path = Path(__file__).resolve().parents[2] / "smart_core" / "core" / "page_block_data_contract.py"
    _provider_spec = spec_from_file_location("scene_block_page_block_data_contract", _provider_path)
    if _provider_spec is None or _provider_spec.loader is None:
        raise
    _provider = module_from_spec(_provider_spec)
    _provider_spec.loader.exec_module(_provider)
    build_data_contract = _provider.build_data_contract
    build_page_orchestration_page_block_data = _provider.build_page_orchestration_page_block_data
    descriptor_ref = _provider.descriptor_ref
    field_descriptor = _provider.field_descriptor


CONTRACT_SCHEMA_VERSION = "2.0.0"
ALLOWED_BLOCK_TYPES = {
    "metric_card",
    "shortcut_grid",
    "todo_list",
    "warning_list",
    "native_view_ref",
}

BLOCK_SCHEMA = {
    "metric_card": {"required": ["key", "type", "title", "value", "target"]},
    "shortcut_grid": {"required": ["key", "type", "title", "items"]},
    "todo_list": {"required": ["key", "type", "title", "items"]},
    "warning_list": {"required": ["key", "type", "title", "items"]},
    "native_view_ref": {"required": ["key", "type", "title", "model", "view_mode", "target"]},
}


def text(value: Any) -> str:
    return str(value or "").strip()


def as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def action_target(*, action_xmlid: str = "", intent: str = "", params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if action_xmlid:
        return {"type": "action", "action_xmlid": text(action_xmlid)}
    if intent:
        return {"type": "intent", "intent": text(intent), "params": dict(params or {})}
    return {"type": "none"}


def metric_card(key: str, title: str, value: Any, *, subtitle: str = "", tone: str = "neutral", target=None) -> Dict[str, Any]:
    return {
        "key": text(key),
        "type": "metric_card",
        "title": text(title),
        "value": value,
        "subtitle": text(subtitle),
        "tone": text(tone) or "neutral",
        "target": target or {"type": "none"},
    }


def shortcut_grid(key: str, title: str, items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "key": text(key),
        "type": "shortcut_grid",
        "title": text(title),
        "items": [row for row in list(items or []) if isinstance(row, dict)],
    }


def todo_list(key: str, title: str, items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "key": text(key),
        "type": "todo_list",
        "title": text(title),
        "items": [row for row in list(items or []) if isinstance(row, dict)],
        "empty_text": "暂无待办",
    }


def warning_list(key: str, title: str, items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "key": text(key),
        "type": "warning_list",
        "title": text(title),
        "items": [row for row in list(items or []) if isinstance(row, dict)],
        "empty_text": "暂无预警",
    }


def native_view_ref(
    key: str,
    title: str,
    *,
    action_xmlid: str,
    model: str,
    view_mode: str,
    count: int = 0,
    summary: str = "",
) -> Dict[str, Any]:
    return {
        "key": text(key),
        "type": "native_view_ref",
        "title": text(title),
        "model": text(model),
        "view_mode": text(view_mode),
        "count": as_int(count),
        "summary": text(summary),
        "target": action_target(action_xmlid=action_xmlid),
    }


def _page_block(block: Dict[str, Any], index: int) -> Dict[str, Any]:
    key = text(block.get("key")) or f"block_{index + 1}"
    block_type = {
        "metric_card": "metric",
        "shortcut_grid": "entry_grid",
        "warning_list": "alert_panel",
        "native_view_ref": "record_summary",
    }.get(text(block.get("type")).lower(), text(block.get("type")).lower() or "record_summary")
    target = block.get("target") if isinstance(block.get("target"), dict) else {}
    return {
        "key": key,
        "block_type": block_type,
        "title": "" if block.get("type") == "metric_card" else text(block.get("title")),
        "subtitle": text(block.get("subtitle")),
        "priority": 100 - index,
        "tone": text(block.get("tone")).lower() if text(block.get("tone")).lower() in {"success", "warning", "danger", "info", "neutral"} else "neutral",
        "data_source": f"ds_{key}",
        "actions": ([{"key": f"open_{key}", "label": "打开明细" if block.get("type") == "native_view_ref" else "打开"}] if target else []),
    }


def _dataset(block: Dict[str, Any]) -> Any:
    key = text(block.get("key"))
    block_type = text(block.get("type"))
    target = block.get("target") if isinstance(block.get("target"), dict) else {}
    if block_type == "metric_card":
        return [{
            "key": key,
            "label": text(block.get("title")),
            "value": block.get("value", "--"),
            "hint": text(block.get("subtitle")),
            "tone": text(block.get("tone")) or "neutral",
            "action_key": f"open_{key}",
            "target": target,
        }]
    if block_type == "shortcut_grid":
        return [
            {
                "id": text(item.get("key")) or f"entry-{index + 1}",
                "title": text(item.get("label") or item.get("title")) or f"入口 {index + 1}",
                "hint": text(item.get("subtitle") or item.get("hint")),
                "action_key": f"open_{key}_{text(item.get('key')) or index + 1}",
                "target": item.get("target") if isinstance(item.get("target"), dict) else {},
            }
            for index, item in enumerate(block.get("items") or [])
            if isinstance(item, dict)
        ]
    if block_type in {"todo_list", "warning_list"}:
        return [
            {
                "id": text(item.get("key")) or f"{block_type}-{index + 1}",
                "title": text(item.get("title") or item.get("label")) or f"事项 {index + 1}",
                "description": text(item.get("description") or item.get("subtitle")),
                "count": as_int(item.get("count")),
                "source": text(item.get("source") or item.get("model") or block.get("model")) or "business",
                "source_label": text(item.get("source_label") or item.get("sourceLabel")),
                "tone": "warning" if block_type == "warning_list" else "info",
                "action_label": "打开",
                "action_key": f"open_{key}_{text(item.get('key')) or index + 1}",
                "target": item.get("target") if isinstance(item.get("target"), dict) else {},
            }
            for index, item in enumerate(block.get("items") or [])
            if isinstance(item, dict)
        ]
    if block_type == "native_view_ref":
        return [
            {"key": "summary", "label": "说明", "value": text(block.get("summary")) or "可继续打开原生明细。"},
            {"key": "model", "label": "业务对象", "value": text(block.get("model")) or "--"},
            {"key": "count", "label": "记录数", "value": as_int(block.get("count"))},
        ]
    return block


def guard_contract_shape(contract: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(contract, dict):
        raise ValueError("scene contract must be a dict")
    contract.setdefault("schema_version", CONTRACT_SCHEMA_VERSION)
    scene = contract.get("scene")
    page = contract.get("page")
    if not isinstance(scene, dict) or not text(scene.get("key")):
        raise ValueError("scene contract requires scene.key")
    if not isinstance(page, dict):
        raise ValueError("scene contract requires page")
    blocks = page.get("blocks")
    if not isinstance(blocks, list):
        raise ValueError("scene contract requires page.blocks")
    seen = set()
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise ValueError("scene block must be a dict")
        key = text(block.get("key")) or f"block_{index + 1}"
        block["key"] = key
        if key in seen:
            raise ValueError("scene block key must be unique")
        seen.add(key)
        block_type = text(block.get("type"))
        if block_type not in ALLOWED_BLOCK_TYPES:
            raise ValueError("unsupported scene block type: %s" % block_type)
        required = BLOCK_SCHEMA.get(block_type, {}).get("required") or []
        missing = [field for field in required if field not in block]
        if missing:
            raise ValueError("scene block %s missing fields: %s" % (key, ", ".join(missing)))
    return contract


def build_contract(
    *,
    scene_key: str,
    title: str,
    blocks: List[Dict[str, Any]],
    subtitle: str = "",
    page_block_data_enabled: bool = False,
    timezone: str = "UTC",
) -> Dict[str, Any]:
    contract = guard_contract_shape(
        {
            "schema_version": CONTRACT_SCHEMA_VERSION,
            "scene": {
                "key": text(scene_key),
                "title": text(title),
                "subtitle": text(subtitle),
            },
            "page": {
                "layout": "block_grid",
                "blocks": list(blocks or []),
            },
            "block_schema": {
                "version": "2.0.0",
                "types": BLOCK_SCHEMA,
            },
        }
    )
    normalized_blocks = [_page_block(block, index) for index, block in enumerate(blocks or [])]
    page_block_data = _page_block_data_projection(
        blocks or [],
        timezone=timezone,
        enabled=page_block_data_enabled,
    )
    contract["page_orchestration"] = {
        "contract_version": page_block_data.pop("contract_version"),
        "schema_version": page_block_data.pop("schema_version"),
        "scene_key": text(scene_key),
        "page": {
            "key": text(scene_key),
            "title": text(title),
            "subtitle": text(subtitle),
            "page_type": "dashboard",
            "layout_mode": "block_grid",
        },
        "zones": [{
            "key": "main",
            "title": "",
            "display_mode": "grid",
            "zone_type": "primary",
            "priority": 100,
            "blocks": normalized_blocks,
        }],
        **page_block_data,
    }
    contract["datasets"] = {
        f"ds_{text(block.get('key')) or f'block_{index + 1}'}": _dataset(block)
        for index, block in enumerate(blocks or [])
        if isinstance(block, dict)
    }
    return contract


def _page_block_data_projection(
    blocks: List[Dict[str, Any]],
    *,
    timezone: str,
    enabled: bool,
) -> Dict[str, Any]:
    descriptors: Dict[str, Any] = {}
    data_contracts: Dict[str, Any] = {}
    if enabled:
        for index, block in enumerate(blocks):
            if not isinstance(block, dict) or text(block.get("type")) != "metric_card":
                continue
            key = text(block.get("key")) or f"block_{index + 1}"
            descriptor_id = f"{key}.value"
            declared = block.get("value_descriptor")
            descriptor = (
                declared
                if isinstance(declared, dict)
                else field_descriptor(
                    field_code=descriptor_id,
                    label=text(block.get("title")) or key,
                    field_type="integer",
                    widget_type="number",
                    component_key="sc.input.number",
                    semantic_type="number",
                )
            )
            descriptors[descriptor_id] = descriptor
            values: Dict[str, Any] = {}
            if "value" in block:
                values["value"] = block.get("value")
            data_contracts[f"ds_{key}"] = build_data_contract(
                rows=[{"rowKey": key, "values": values}],
                field_refs={
                    "value": descriptor_ref(
                        descriptor_id=descriptor_id,
                        raw_value_path="value",
                    ),
                },
                currencies=block.get("currencies") if isinstance(block.get("currencies"), dict) else {},
                timezone=timezone,
            )
    return build_page_orchestration_page_block_data(
        descriptors=descriptors,
        data_contracts=data_contracts,
        enabled=enabled,
    )
