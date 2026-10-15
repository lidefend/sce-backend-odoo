#!/usr/bin/env python3
"""Single authority for which database, cluster and storage a duty owns.

A *duty* is one of the governed daily-runtime databases: the platform control
plane, the demo, or one customer development tenant.  Every governed entry that
reads or writes a duty resolves its runtime identity here, from
``config/ops/daily_runtime_database_duties.v1.json``; no tool may carry its own
database name, container name, volume name, role name, filestore scope or
backup namespace.

The declaration is an ops-side authority.  It does not replace the platform
model that owns database lifecycle registration.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DUTY_DECLARATION = ROOT / "config" / "ops" / "daily_runtime_database_duties.v1.json"

SAFE_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]*")
SAFE_COMPOSE_PROJECT = re.compile(r"[a-z0-9][a-z0-9-]*")
FILESTORE_ROOT = "/var/lib/odoo/filestore"
DATABASE_MOUNT = "/var/lib/postgresql/data"
ODOO_DATA_MOUNT = "/var/lib/odoo"
DRILL_ROLE = "odoo"


class DutyIdentityError(RuntimeError):
    pass


def load_declaration(path: Path | None = None) -> dict:
    target = path or DUTY_DECLARATION
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DutyIdentityError("duty declaration is missing or invalid") from exc
    if not isinstance(payload, dict):
        raise DutyIdentityError("duty declaration is not an object")
    return payload


def load_duties(path: Path | None = None) -> dict:
    """Read the single authority for which database each duty owns."""
    declared = load_declaration(path).get("duties")
    if not isinstance(declared, list) or not declared:
        raise DutyIdentityError("duty declaration carries no duties")
    table: dict[str, dict] = {}
    for entry in declared:
        name = entry.get("duty") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not name:
            raise DutyIdentityError("duty entry without a name")
        if name in table:
            raise DutyIdentityError(f"duplicate duty declaration: {name}")
        table[name] = entry
    return table


def duty_identity(duty: dict) -> dict:
    """Resolve runtime identity from the duty declaration, never from a contract.

    A contract may restate these fields for assertion, but the declaration is
    the only owner: a disagreement is a stop, not a vote.
    """

    def required(mapping: dict, key: str, source: str) -> str:
        value = mapping.get(key)
        if not isinstance(value, str) or not value:
            raise DutyIdentityError(f"duty declaration lacks {source}.{key}")
        return value

    cluster = duty.get("cluster")
    storage = duty.get("storage")
    if not isinstance(cluster, dict) or not isinstance(storage, dict):
        raise DutyIdentityError("duty declaration lacks cluster or storage")
    compose_project = required(cluster, "compose_project", "cluster")
    if not SAFE_COMPOSE_PROJECT.fullmatch(compose_project):
        raise DutyIdentityError("duty compose project is not a safe identifier")
    identity = {
        "duty": duty["duty"],
        "environment_id": required(duty, "environment_id", "duty"),
        "tenant_key": duty.get("tenant_key") or "",
        "data_purpose": required(duty, "data_purpose", "duty"),
        "database": required(duty, "database", "duty"),
        "database_role": required(duty, "database_role", "duty"),
        "dbfilter": required(duty, "dbfilter", "duty"),
        "compose_project": compose_project,
        "database_container": required(cluster, "container", "cluster"),
        "odoo_container": f"{compose_project}-odoo-1",
        "database_volume": required(cluster, "data_volume", "cluster"),
        "odoo_data_volume": required(storage, "odoo_data_volume", "storage"),
        "filestore_scope": required(storage, "filestore_scope", "storage"),
        "backup_root": required(storage, "backup_namespace", "storage"),
        "filestore_root": FILESTORE_ROOT,
    }
    for key in ("database", "database_role", "database_volume", "odoo_data_volume"):
        if not SAFE_IDENTIFIER.fullmatch(identity[key]):
            raise DutyIdentityError(f"duty declaration {key} is not a safe identifier")
    if identity["filestore_scope"] != identity["database"]:
        raise DutyIdentityError("duty filestore scope no longer matches its database")
    if identity["dbfilter"] != f"^{identity['database']}$":
        raise DutyIdentityError("duty filter no longer selects exactly its database")
    return identity


def resolve(duty_name: str, path: Path | None = None) -> dict:
    """Resolve one declared duty, or stop."""
    duties = load_duties(path)
    if duty_name not in duties:
        raise DutyIdentityError(f"undeclared duty: {duty_name}")
    return duty_identity(duties[duty_name])
