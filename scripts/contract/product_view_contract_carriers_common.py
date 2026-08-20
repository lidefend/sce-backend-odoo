#!/usr/bin/env python3
"""Pure helpers for governed product-view carrier evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


TYPE_REQUIRED_KEYS = {
    "form": ("layout", "statusbar", "header_buttons", "field_modifiers", "subviews", "capabilities"),
    "tree": ("columns", "columns_schema", "row_actions", "page_size", "collection_presentation"),
    "search": ("search",),
    "kanban": ("kanban",),
    "pivot": ("pivot", "measures", "dimensions"),
    "graph": ("graph", "type", "measure", "dimension"),
    "calendar": ("calendar", "date_start"),
    "gantt": ("gantt", "date_start"),
    "activity": ("activity", "field"),
    "dashboard": ("dashboard",),
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def with_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result.pop("manifest_sha256", None)
    result["manifest_sha256"] = sha256_json(result)
    return result


def pointer_get(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ValueError(f"invalid JSON pointer: {pointer}")
    current = value
    for raw in pointer.split("/")[1:]:
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not token.isdigit():
                raise ValueError(f"invalid list token in JSON pointer: {pointer}")
            current = current[int(token)]
        elif isinstance(current, dict):
            current = current[token]
        else:
            raise ValueError(f"JSON pointer traverses scalar: {pointer}")
    return current


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(canonical_bytes(payload) + b"\n")
    temporary.replace(path)


def stable_selector_payload(entry: dict[str, Any], authority: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_ref": entry["contract_ref"],
        "menu_xmlid": entry["menu_xmlid"],
        "action_xmlid": entry["action_xmlid"],
        "model": entry["model"],
        "view_type": entry["view_type"],
        "view_ref": entry["view_ref"],
        "resolved_arch_sha256": entry["hashes"]["resolved_arch_sha256"],
        "runtime_authority": {
            "module_set_sha256": authority["module_set_sha256"],
            "user": authority["user"],
            "company": authority["company"],
            "language": authority["language"],
        },
    }


def expected_normalized_selectors(view_type: str) -> tuple[str, ...]:
    if view_type not in TYPE_REQUIRED_KEYS:
        raise ValueError(f"unsupported canonical view type: {view_type}")
    primary = f"/data/views/{view_type}"
    return (primary, "/data/search") if view_type == "search" else (primary,)


def normalized_value_errors(view_type: str, model: str, selector: str, value: Any) -> list[str]:
    if selector == "/data/search":
        return [] if view_type == "search" and isinstance(value, dict) else ["invalid data.search carrier"]
    if selector != f"/data/views/{view_type}" or not isinstance(value, dict):
        return ["invalid data.views carrier"]
    errors = []
    if value.get("model") != model or value.get("view_type") != view_type:
        errors.append("normalized carrier identity mismatch")
    missing = [key for key in TYPE_REQUIRED_KEYS[view_type] if key not in value]
    if missing:
        errors.append(f"normalized carrier missing required keys: {missing}")
    return errors


def enable_database_read_only(cursor: Any) -> None:
    cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
    cursor.execute("SET TRANSACTION READ ONLY")
    cursor.execute("SHOW transaction_read_only")
    if cursor.fetchone()[0] != "on":
        raise ValueError("database transaction is not read-only")


def restore_database_read_write(cursor: Any) -> None:
    cursor.rollback()
    cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE")
    cursor.commit()
    cursor.execute("SHOW transaction_read_only")
    if cursor.fetchone()[0] != "off":
        raise ValueError("database connection did not restore read-write default")
    cursor.rollback()


def assert_system_identity(runtime_uid: int, superuser_id: int, declared_user: str) -> None:
    if runtime_uid != superuser_id or declared_user != "__system__":
        raise ValueError("carrier collector requires exact superuser identity")
