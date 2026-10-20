"""Pure binding plan for the local.dev public namespace alias."""

from __future__ import annotations

import hashlib
from typing import Any


def plan_binding(
    aliases: list[dict[str, Any]],
    namespaces: list[dict[str, Any]],
    database: str,
) -> dict[str, Any]:
    db = str(database or "").strip()
    if not db:
        raise ValueError("database is required")

    demo_aliases = [
        row
        for row in aliases
        if str(row.get("alias") or "") == "demo"
        and str(row.get("alias_kind") or "path") == "path"
    ]
    if len(demo_aliases) > 1:
        raise ValueError("multiple demo path aliases")

    by_id: dict[str, dict[str, Any]] = {}
    for row in namespaces:
        namespace_id = str(row.get("namespace_id") or "").strip()
        if not namespace_id:
            continue
        if namespace_id in by_id:
            raise ValueError("duplicate namespace id: %s" % namespace_id)
        by_id[namespace_id] = row

    db_namespaces = [
        row
        for row in namespaces
        if str(row.get("database_name") or "").strip() == db
    ]
    if len(db_namespaces) > 1:
        raise ValueError("multiple namespaces bind database: %s" % db)

    if demo_aliases:
        alias = demo_aliases[0]
        namespace_id = str(alias.get("namespace_id") or "").strip()
        namespace = by_id.get(namespace_id)
        if not namespace:
            raise ValueError("demo alias points to unknown namespace: %s" % namespace_id)
        if bool(alias.get("retired")):
            target = db_namespaces[0] if db_namespaces else namespace
            return {
                "action": "reactivate_alias",
                "namespace_id": str(target["namespace_id"]),
                "reason": "demo alias is retired",
            }
        if str(namespace.get("database_name") or "").strip() == db:
            return {
                "action": "noop",
                "namespace_id": namespace_id,
                "reason": "demo alias already binds the local database",
            }
        if db_namespaces:
            return {
                "action": "reassign_alias",
                "namespace_id": str(db_namespaces[0]["namespace_id"]),
                "reason": "a namespace for the local database already exists",
            }
        return {
            "action": "update_database",
            "namespace_id": namespace_id,
            "reason": "demo namespace points at another database",
        }

    if db_namespaces:
        return {
            "action": "create_alias",
            "namespace_id": str(db_namespaces[0]["namespace_id"]),
            "reason": "local database namespace exists without demo alias",
        }

    namespace_id = "ns_" + hashlib.sha256(db.encode("utf-8")).hexdigest()[:12]
    return {
        "action": "create_namespace",
        "namespace_id": namespace_id,
        "reason": "no namespace exists for the local database",
    }
