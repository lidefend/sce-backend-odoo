#!/usr/bin/env python3
"""Read-only, deterministic data sentinels for the daily candidate database."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import daily_candidate_data_continuity as continuity


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT = Path(__file__).with_name(
    "daily_candidate_data_sentinel_contract_v1.json"
)
DEFAULT_CONTINUITY_CONTRACT = Path(__file__).with_name(
    "daily_candidate_data_continuity_contract_v1.json"
)
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
SENTINEL_ID = re.compile(
    r"^sc_demo-sentinel-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$"
)
CLONE_PREFIX = "sc-daily-sentinel-clone-"


class SentinelError(RuntimeError):
    pass


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_contract(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SentinelError("sentinel contract is missing or invalid") from exc
    environment = payload.get("environment") or {}
    expected = {
        "classification": "DAILY_CANDIDATE_ENVIRONMENT",
        "database": "sc_demo",
        "database_uuid": "c838b4b6-4cd6-11f1-9590-82245e4e7b62",
        "database_container": "sc-backend-odoo-dev-db-1",
        "odoo_container": "sc-backend-odoo-dev-odoo-1",
        "continuity_backup_set_id": "sc_demo-20260724T032145Z-6eb277d1",
    }
    for key, value in expected.items():
        if environment.get(key) != value:
            raise SentinelError(f"sentinel environment identity mismatch: {key}")
    if payload.get("schema_version") != "daily_candidate_data_sentinel.v1":
        raise SentinelError("sentinel schema version mismatch")
    classes = set(payload.get("classification", {}).get("classes") or [])
    if "UNKNOWN_ORIGIN" not in classes:
        raise SentinelError("UNKNOWN_ORIGIN classification is required")
    if payload["classification"].get("unknown_origin_delete_allowed") is not False:
        raise SentinelError("UNKNOWN_ORIGIN must remain protected")
    for model in payload.get("models") or []:
        if model.get("expected") not in {
            "MODEL_PRESENT",
            "MODEL_ABSENT",
            "MODEL_REPLACED_BY",
        }:
            raise SentinelError("model mapping semantics are invalid")
        for key in ("table",):
            if not IDENTIFIER.fullmatch(str(model.get(key) or "")):
                raise SentinelError("unsafe model table identifier")
    return payload


def _run(
    args: list[str],
    *,
    input_bytes: bytes | None = None,
    check: bool = True,
) -> bytes:
    result = subprocess.run(
        args,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode:
        detail = result.stderr.decode(errors="replace").strip()
        raise SentinelError(f"command failed ({' '.join(args[:3])}): {detail}")
    return result.stdout


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _json_expr(field: str) -> str:
    if not IDENTIFIER.fullmatch(field):
        raise SentinelError("unsafe sample field")
    return f"'{field}', {field}"


def _mapping_status(contract: dict, db_container: str) -> dict[str, dict]:
    tables = sorted({row["table"] for row in contract["models"]})
    sql = (
        "SELECT relname FROM pg_class WHERE relnamespace='public'::regnamespace "
        f"AND relname IN ({','.join(_sql_literal(item) for item in tables)}) "
        "ORDER BY relname"
    )
    existing = set(
        _run(
            [
                "docker",
                "exec",
                db_container,
                "psql",
                "-X",
                "-U",
                "odoo",
                "-d",
                contract["environment"]["database"],
                "-At",
                "-c",
                sql,
            ]
        )
        .decode()
        .split()
    )
    by_model = {row["model"]: row for row in contract["models"]}
    result = {}
    for row in contract["models"]:
        expected = row["expected"]
        table_present = row["table"] in existing
        if expected == "MODEL_PRESENT":
            if not table_present:
                raise SentinelError(f"required model table is absent: {row['model']}")
            actual = "MODEL_PRESENT"
        elif expected == "MODEL_ABSENT":
            if table_present:
                raise SentinelError(f"declared absent model appeared: {row['model']}")
            actual = "MODEL_ABSENT"
        else:
            replacement = by_model.get(row.get("replacement_model"))
            if not replacement or replacement["table"] not in existing:
                raise SentinelError(
                    f"replacement model is unavailable: {row['model']}"
                )
            actual = "MODEL_REPLACED_BY"
        result[row["model"]] = {
            "status": actual,
            "table_present": table_present,
            "replacement_model": row.get("replacement_model"),
        }
    return result


def _column_inventory(contract: dict, db_container: str) -> dict[str, set[str]]:
    present_tables = [
        row["table"]
        for row in contract["models"]
        if row["expected"] == "MODEL_PRESENT"
    ]
    sql = (
        "SELECT table_name || '|' || column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name IN "
        f"({','.join(_sql_literal(item) for item in present_tables)}) "
        "ORDER BY table_name,column_name"
    )
    lines = (
        _run(
            [
                "docker",
                "exec",
                db_container,
                "psql",
                "-X",
                "-U",
                "odoo",
                "-d",
                contract["environment"]["database"],
                "-At",
                "-c",
                sql,
            ]
        )
        .decode()
        .splitlines()
    )
    inventory = {table: set() for table in present_tables}
    for line in lines:
        table, column = line.split("|", 1)
        inventory[table].add(column)
    for model in contract["models"]:
        if model["expected"] != "MODEL_PRESENT":
            continue
        required_columns = {
            "id",
            *model.get("required_fields", []),
            *model.get("sample_fields", []),
            *model.get("amount_fields", []),
        }
        for optional_key in ("active_field", "company_field", "state_field"):
            if model.get(optional_key):
                required_columns.add(model[optional_key])
        missing = required_columns - inventory[model["table"]]
        if missing:
            raise SentinelError(
                f"unannounced model schema change: {model['model']}:{sorted(missing)}"
            )
    return inventory


def _aggregate_sql(model: dict, columns: set[str]) -> str:
    table = model["table"]
    active = model.get("active_field")
    company = model.get("company_field")
    state = model.get("state_field")
    active_expr = (
        f"count(*) FILTER (WHERE {active} IS TRUE)" if active else "NULL"
    )
    inactive_expr = (
        f"count(*) FILTER (WHERE {active} IS NOT TRUE)" if active else "NULL"
    )
    company_expr = (
        "(SELECT COALESCE(json_object_agg(k, n), '{}'::json) FROM "
        f"(SELECT COALESCE({company},0)::text k,count(*) n FROM {table} "
        f"GROUP BY COALESCE({company},0) ORDER BY COALESCE({company},0)) d)"
        if company
        else "'{}'::json"
    )
    state_expr = (
        "(SELECT COALESCE(json_object_agg(k, n), '{}'::json) FROM "
        f"(SELECT COALESCE({state},'') k,count(*) n FROM {table} "
        f"GROUP BY COALESCE({state},'') ORDER BY COALESCE({state},'')) d)"
        if state
        else "'{}'::json"
    )
    create_min = "min(create_date)::text" if "create_date" in columns else "NULL"
    create_max = "max(create_date)::text" if "create_date" in columns else "NULL"
    write_min = "min(write_date)::text" if "write_date" in columns else "NULL"
    write_max = "max(write_date)::text" if "write_date" in columns else "NULL"
    null_parts = []
    for field in model.get("required_fields", []):
        null_parts.extend([_sql_literal(field), f"count(*) FILTER (WHERE {field} IS NULL)"])
    null_expr = (
        f"json_build_object({','.join(null_parts)})"
        if null_parts
        else "'{}'::json"
    )
    return (
        "SELECT 'AGG|' || json_build_object("
        f"'model',{_sql_literal(model['model'])},'record_count',count(*),"
        f"'active_count',{active_expr},'inactive_count',{inactive_expr},"
        f"'company_distribution',{company_expr},'state_distribution',{state_expr},"
        f"'create_date_min',{create_min},'create_date_max',{create_max},"
        f"'write_date_min',{write_min},'write_date_max',{write_max},"
        f"'null_required_fields',{null_expr})::text FROM {table};"
    )


def _sample_sql(model: dict) -> str | None:
    limit = int(model.get("sample_limit") or 0)
    if limit <= 0:
        return None
    table = model["table"]
    company = model.get("company_field")
    state = model.get("state_field")
    active = model.get("active_field")
    partition = [
        f"COALESCE({company},0)" if company else "0::integer",
        f"COALESCE({state},'')" if state else "''::text",
        f"COALESCE({active},false)" if active else "false::boolean",
    ]
    relationship_fields = [
        field
        for field in model.get("sample_fields", [])
        if field.endswith("_id")
    ]
    relationship_score = (
        " + ".join(
            f"CASE WHEN {field} IS NULL THEN 0 ELSE 1 END"
            for field in relationship_fields
        )
        or "0"
    )
    fields = ["'id',id"]
    for field in model.get("sample_fields", []):
        fields.append(_json_expr(field))
    for field in model.get("amount_fields", []):
        fields.extend(
            [
                _sql_literal(f"{field}_profile"),
                (
                    f"CASE WHEN {field} IS NULL THEN 'null' "
                    f"WHEN {field}=0 THEN 'zero' WHEN {field}>0 THEN 'positive' "
                    "ELSE 'negative' END"
                ),
            ]
        )
    fields.extend(
        [
            "'direct_attachment_count'",
            "attachment_score",
        ]
    )
    if model["model"] == "res.users":
        fields.extend(
            [
                "'group_count'",
                "(SELECT count(*) FROM res_groups_users_rel g WHERE g.uid=ranked.id)",
            ]
        )
    order = ", ".join(
        partition + ["attachment_score DESC", "relationship_score DESC", "id"]
    )
    per_partition = 2 if any((company, state, active)) else limit
    return (
        "WITH scored AS (SELECT *,"
        "(SELECT count(*) FROM ir_attachment a "
        f"WHERE a.res_model={_sql_literal(model['model'])} AND a.res_id={table}.id) attachment_score,"
        f"({relationship_score}) relationship_score FROM {table}), "
        "ranked AS (SELECT *,row_number() OVER "
        f"(PARTITION BY {','.join(partition)} ORDER BY attachment_score DESC,relationship_score DESC,id) rn FROM scored), "
        f"chosen AS (SELECT * FROM ranked WHERE rn<={per_partition} ORDER BY "
        f"{order} LIMIT {limit}) "
        "SELECT 'SAMPLE|' || json_build_object("
        f"'model',{_sql_literal(model['model'])},'records',"
        f"COALESCE(json_agg(json_build_object({','.join(fields)}) ORDER BY {order}),'[]'::json)"
        ")::text FROM chosen ranked;"
    )


def _classification_sql(model: dict, classification: dict) -> str:
    table = model["table"]
    model_name = model["model"]
    if model.get("origin_policy") == "SYSTEM_CONFIGURATION":
        return (
            "SELECT 'CLASS|' || json_build_object("
            f"'model',{_sql_literal(model_name)},'SYSTEM_CONFIGURATION',count(*),"
            "'CANDIDATE_USER_DATA',0,'ACCEPTANCE_FIXTURE_DATA',0,'DEMO_DATA',0,"
            "'UNKNOWN_ORIGIN',0)::text "
            f"FROM {table};"
        )
    demo = classification["demo_module_namespaces"]
    fixture = classification["fixture_module_patterns"]
    demo_predicate = " OR ".join(
        f"module={_sql_literal(item)}" for item in demo
    ) or "false"
    fixture_predicate = " OR ".join(
        f"module LIKE {_sql_literal('%' + item + '%')}" for item in fixture
    ) or "false"
    return (
        "WITH owned AS (SELECT DISTINCT res_id,module FROM ir_model_data "
        f"WHERE model={_sql_literal(model_name)}), classified AS ("
        "SELECT res_id,CASE "
        f"WHEN {demo_predicate} THEN 'DEMO_DATA' "
        f"WHEN {fixture_predicate} THEN 'ACCEPTANCE_FIXTURE_DATA' "
        "ELSE 'UNKNOWN_ORIGIN' END class FROM owned), totals AS ("
        f"SELECT count(*) total FROM {table}) "
        "SELECT 'CLASS|' || json_build_object("
        f"'model',{_sql_literal(model_name)},"
        "'SYSTEM_CONFIGURATION',0,'CANDIDATE_USER_DATA',0,"
        "'ACCEPTANCE_FIXTURE_DATA',(SELECT count(DISTINCT res_id) FROM classified WHERE class='ACCEPTANCE_FIXTURE_DATA'),"
        "'DEMO_DATA',(SELECT count(DISTINCT res_id) FROM classified WHERE class='DEMO_DATA'),"
        "'UNKNOWN_ORIGIN',(SELECT total FROM totals)-"
        "(SELECT count(DISTINCT res_id) FROM classified WHERE class IN ('ACCEPTANCE_FIXTURE_DATA','DEMO_DATA'))"
        ")::text;"
    )


def _relationship_sql(relation: list[str]) -> str:
    source, field, target, target_id = relation
    for identifier in relation:
        if not IDENTIFIER.fullmatch(identifier):
            raise SentinelError("unsafe relationship identifier")
    key = f"{source}.{field}->{target}.{target_id}"
    return (
        "SELECT 'REL|' || json_build_object("
        f"'relationship',{_sql_literal(key)},'orphan_count',count(*))::text "
        f"FROM {source} s LEFT JOIN {target} t ON t.{target_id}=s.{field} "
        f"WHERE s.{field} IS NOT NULL AND t.{target_id} IS NULL;"
    )


def _build_snapshot_sql(
    contract: dict,
    columns: dict[str, set[str]],
    mapping: dict[str, dict],
) -> str:
    transaction = contract["transaction"]
    statements = [
        "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;",
        f"SET LOCAL statement_timeout={_sql_literal(transaction['statement_timeout'])};",
        f"SET LOCAL lock_timeout={_sql_literal(transaction['lock_timeout'])};",
        (
            "SELECT 'META|' || json_build_object("
            "'scan_started_at',clock_timestamp()::text,"
            "'transaction_read_only',current_setting('transaction_read_only'),"
            "'transaction_isolation',current_setting('transaction_isolation'),"
            "'snapshot',txid_current_snapshot()::text,"
            "'database',current_database(),"
            "'database_uuid',(SELECT value FROM ir_config_parameter WHERE key='database.uuid' LIMIT 1)"
            ")::text;"
        ),
        (
            "SELECT 'MODULES|' || COALESCE(json_agg(json_build_object("
            "'module',name,'version',COALESCE(latest_version,'')) ORDER BY name),'[]'::json)::text "
            "FROM ir_module_module WHERE state='installed' AND name IN "
            f"({','.join(_sql_literal(item) for item in contract['core_modules'])});"
        ),
        (
            "SELECT 'COMPANIES|' || COALESCE(json_agg(json_build_object("
            "'id',id,'partner_id',partner_id,'currency_id',currency_id,'active',active) "
            "ORDER BY id),'[]'::json)::text FROM res_company;"
        ),
    ]
    for model in contract["models"]:
        if mapping[model["model"]]["status"] != "MODEL_PRESENT":
            continue
        statements.append(_aggregate_sql(model, columns[model["table"]]))
        sample = _sample_sql(model)
        if sample:
            statements.append(sample)
        statements.append(_classification_sql(model, contract["classification"]))
    for relationship in contract["relationships"]:
        statements.append(_relationship_sql(relationship))
    statements.extend(
        [
            (
                "SELECT 'ATTACH|' || json_build_object("
                "'record_count',count(*),"
                "'stored_row_count',count(*) FILTER (WHERE store_fname IS NOT NULL AND btrim(store_fname)<>''),"
                "'distinct_stored_file_count',count(DISTINCT store_fname) FILTER (WHERE store_fname IS NOT NULL AND btrim(store_fname)<>''),"
                "'direct_reference_count',count(*) FILTER (WHERE res_model IS NOT NULL AND res_id IS NOT NULL AND res_id<>0)"
                ")::text FROM ir_attachment;"
            ),
            (
                "SELECT 'FILE|' || json_build_object('attachment_id',min(id),'path',store_fname)::text "
                "FROM ir_attachment WHERE store_fname IS NOT NULL AND btrim(store_fname)<>'' "
                "GROUP BY store_fname ORDER BY min(id);"
            ),
            (
                "SELECT 'SCHEMA|' || COALESCE(string_agg("
                "table_name||':'||column_name||':'||data_type||':'||is_nullable,';' "
                "ORDER BY table_name,column_name),'') "
                "FROM information_schema.columns WHERE table_schema='public' AND table_name IN "
                f"({','.join(_sql_literal(row['table']) for row in contract['models'] if row['expected']=='MODEL_PRESENT')});"
            ),
            "SELECT 'FINISH|' || clock_timestamp()::text;",
            "ROLLBACK;",
        ]
    )
    return "\n".join(statements) + "\n"


def _database_stats(container: str, database: str) -> dict[str, int]:
    sql = (
        "SELECT tup_inserted||'|'||tup_updated||'|'||tup_deleted "
        f"FROM pg_stat_database WHERE datname={_sql_literal(database)}"
    )
    raw = (
        _run(
            [
                "docker",
                "exec",
                container,
                "psql",
                "-X",
                "-U",
                "odoo",
                "-d",
                "postgres",
                "-At",
                "-c",
                sql,
            ]
        )
        .decode()
        .strip()
    )
    inserted, updated, deleted = raw.split("|")
    return {
        "inserted": int(inserted),
        "updated": int(updated),
        "deleted": int(deleted),
    }


def _scan_filestore(
    contract: dict, odoo_container: str, files: list[dict]
) -> dict:
    database = contract["environment"]["database"]
    root = f"{contract['environment']['filestore_root']}/{database}"
    safe_files = []
    for row in files:
        path = str(row["path"])
        if (
            path.startswith("/")
            or ".." in Path(path).parts
            or not re.fullmatch(r"[A-Za-z0-9._/-]+", path)
        ):
            raise SentinelError("unsafe filestore path in database")
        safe_files.append(
            {"attachment_id": int(row["attachment_id"]), "path": path}
        )
    script = r"""
import json, os, sys
root=sys.argv[1]
rows=json.load(sys.stdin)
missing=[]; unreadable=[]; readable=[]
referenced=set()
for row in rows:
    rel=row["path"]; referenced.add(rel)
    target=os.path.join(root,rel)
    if not os.path.isfile(target):
        missing.append(row["attachment_id"])
    elif not os.access(target,os.R_OK):
        unreadable.append(row["attachment_id"])
    elif len(readable)<10:
        readable.append(row["attachment_id"])
physical=set()
for base,_dirs,names in os.walk(root):
    for name in names:
        physical.add(os.path.relpath(os.path.join(base,name),root))
print(json.dumps({
    "referenced_file_count":len(referenced),
    "physical_file_count":len(physical),
    "missing_file_count":len(missing),
    "missing_attachment_ids":missing[:20],
    "unreadable_file_count":len(unreadable),
    "unreadable_attachment_ids":unreadable[:20],
    "readable_sample_attachment_ids":readable,
    "unreferenced_physical_file_count":len(physical-referenced),
    "unreferenced_files_deleted":0
},sort_keys=True))
"""
    result = _run(
        [
            "docker",
            "exec",
            "-i",
            odoo_container,
            "python3",
            "-c",
            script,
            root,
        ],
        input_bytes=json.dumps(safe_files).encode(),
    )
    return json.loads(result)


def _runtime_identity(contract: dict) -> dict:
    environment = contract["environment"]
    db = continuity._inspect(environment["database_container"])
    odoo = continuity._inspect(environment["odoo_container"])
    for item, service in ((db, "db"), (odoo, "odoo")):
        labels = item.get("Config", {}).get("Labels") or {}
        if labels.get("com.docker.compose.project") != environment["compose_project"]:
            raise SentinelError("daily compose project identity mismatch")
        if labels.get("com.docker.compose.service") != service:
            raise SentinelError("daily compose service identity mismatch")
        if item.get("State", {}).get("Health", {}).get("Status") != "healthy":
            raise SentinelError(f"daily service is not healthy: {service}")
    repository = Path(environment["source_repository"])
    revision = _run(["git", "-C", str(repository), "rev-parse", "HEAD"]).decode().strip()
    if not revision.startswith(environment["expected_running_revision_prefix"]):
        raise SentinelError("daily running repository revision changed")
    if _run(["git", "-C", str(repository), "status", "--porcelain"]).strip():
        raise SentinelError("daily running repository is dirty")
    return {
        "database_container_id": db["Id"],
        "database_started_at": db["State"]["StartedAt"],
        "database_restart_count": db["RestartCount"],
        "odoo_container_id": odoo["Id"],
        "odoo_started_at": odoo["State"]["StartedAt"],
        "odoo_restart_count": odoo["RestartCount"],
        "running_application_revision": revision,
    }


def _parse_snapshot(output: str) -> tuple[dict, list[dict]]:
    result: dict[str, Any] = {
        "aggregates": {},
        "samples": {},
        "classifications": {},
        "relationships": {},
    }
    files = []
    schema_text = ""
    for line in output.splitlines():
        if "|" not in line:
            continue
        tag, payload = line.split("|", 1)
        if tag == "META":
            result["snapshot"] = json.loads(payload)
        elif tag == "MODULES":
            result["installed_core_modules"] = json.loads(payload)
        elif tag == "COMPANIES":
            result["companies"] = json.loads(payload)
        elif tag == "AGG":
            row = json.loads(payload)
            result["aggregates"][row.pop("model")] = row
        elif tag == "SAMPLE":
            row = json.loads(payload)
            result["samples"][row["model"]] = row["records"]
        elif tag == "CLASS":
            row = json.loads(payload)
            result["classifications"][row.pop("model")] = row
        elif tag == "REL":
            row = json.loads(payload)
            result["relationships"][row["relationship"]] = row["orphan_count"]
        elif tag == "ATTACH":
            result["attachments"] = json.loads(payload)
        elif tag == "FILE":
            files.append(json.loads(payload))
        elif tag == "SCHEMA":
            schema_text = payload
        elif tag == "FINISH":
            result["scan_finished_at"] = payload
    required = {
        "snapshot",
        "installed_core_modules",
        "companies",
        "attachments",
        "scan_finished_at",
    }
    if not required.issubset(result):
        raise SentinelError("snapshot output is incomplete")
    result["database_schema_identity_sha256"] = hashlib.sha256(
        schema_text.encode()
    ).hexdigest()
    return result, files


def _assert_no_sensitive_output(contract: dict, payload: Any) -> None:
    denied = set(contract["sensitive_field_denylist"])

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if str(key).lower() in denied:
                    raise SentinelError(f"sensitive output key refused: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)


def capture(
    contract: dict,
    *,
    db_container: str | None = None,
    odoo_container: str | None = None,
    source_kind: str = "PRIMARY_DAILY_CANDIDATE",
    runtime: dict | None = None,
) -> dict:
    environment = contract["environment"]
    db_container = db_container or environment["database_container"]
    odoo_container = odoo_container or environment["odoo_container"]
    if source_kind == "PRIMARY_DAILY_CANDIDATE":
        runtime = _runtime_identity(contract)
    elif runtime is None:
        raise SentinelError("clone runtime identity is required")
    mapping = _mapping_status(contract, db_container)
    columns = _column_inventory(contract, db_container)
    before_stats = _database_stats(db_container, environment["database"])
    sql = _build_snapshot_sql(contract, columns, mapping)
    started = _utc()
    output = _run(
        [
            "docker",
            "exec",
            "-i",
            db_container,
            "psql",
            "-X",
            "-q",
            "-U",
            "odoo",
            "-d",
            environment["database"],
            "-A",
            "-t",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input_bytes=sql.encode(),
    ).decode()
    after_stats = _database_stats(db_container, environment["database"])
    parsed, private_files = _parse_snapshot(output)
    if parsed["snapshot"]["database"] != environment["database"]:
        raise SentinelError("database name identity mismatch")
    if parsed["snapshot"]["database_uuid"] != environment["database_uuid"]:
        raise SentinelError("database UUID identity mismatch")
    if parsed["snapshot"]["transaction_read_only"] != "on":
        raise SentinelError("sentinel transaction was not read-only")
    if parsed["snapshot"]["transaction_isolation"] != "repeatable read":
        raise SentinelError("sentinel transaction isolation mismatch")
    parsed["attachments"]["filestore"] = _scan_filestore(
        contract, odoo_container, private_files
    )
    parsed["model_mappings"] = mapping
    parsed["schema_version"] = contract["schema_version"]
    parsed["environment_classification"] = environment["classification"]
    parsed["database"] = environment["database"]
    parsed["database_uuid"] = environment["database_uuid"]
    parsed["source_kind"] = source_kind
    parsed["scan_invoked_at"] = started
    parsed["runtime"] = runtime
    parsed["transaction_contract"] = {
        "read_only": True,
        "isolation": "repeatable read",
        "statement_timeout": contract["transaction"]["statement_timeout"],
        "lock_timeout": contract["transaction"]["lock_timeout"],
        "persistent_objects_created": 0,
        "primary_database_write_count": 0,
    }
    deltas = {
        key: after_stats[key] - before_stats[key] for key in before_stats
    }
    parsed["global_database_activity_observed"] = any(
        value > 0 for value in deltas.values()
    )
    parsed["global_database_activity_delta"] = deltas
    parsed["unknown_origin_record_group_count"] = sum(
        1
        for row in parsed["classifications"].values()
        if row.get("UNKNOWN_ORIGIN", 0) > 0
    )
    parsed["fixed_sample_count"] = sum(
        len(rows) for rows in parsed["samples"].values()
    )
    parsed["attachment_sample_count"] = len(
        parsed["attachments"]["filestore"]["readable_sample_attachment_ids"]
    )
    parsed["core_relationship_baseline_pass"] = all(
        count == 0 for count in parsed["relationships"].values()
    )
    filestore = parsed["attachments"]["filestore"]
    parsed["attachment_readability_baseline_pass"] = (
        filestore["missing_file_count"] == 0
        and filestore["unreadable_file_count"] == 0
    )
    _assert_no_sensitive_output(contract, parsed)
    return parsed


def _sample_map(rows: list[dict]) -> dict[int, dict]:
    return {int(row["id"]): row for row in rows}


def compare(
    contract: dict,
    baseline: dict,
    candidate: dict,
    *,
    restore_equivalence: bool = False,
    allowed_core_module_versions: dict[str, str] | None = None,
) -> dict:
    failures = []
    warnings = []
    if baseline.get("database_uuid") != candidate.get("database_uuid"):
        failures.append("DATABASE_UUID_CHANGED")
    if baseline.get("model_mappings") != candidate.get("model_mappings"):
        failures.append("MODEL_MAPPING_CHANGED")
    if baseline.get("companies") != candidate.get("companies"):
        failures.append("COMPANY_IDENTITY_CHANGED")
    baseline_modules = baseline.get("installed_core_modules")
    candidate_modules = candidate.get("installed_core_modules")
    if allowed_core_module_versions is None:
        if baseline_modules != candidate_modules:
            failures.append("CORE_MODULE_IDENTITY_CHANGED")
    else:
        expected_modules = [
            {"module": name, "version": allowed_core_module_versions[name]}
            for name in sorted(allowed_core_module_versions)
        ]
        observed_modules = sorted(
            candidate_modules or [], key=lambda row: str(row.get("module") or "")
        )
        if observed_modules != expected_modules:
            failures.append("CORE_MODULE_VERSION_DRIFT")
    for model, base_aggregate in baseline.get("aggregates", {}).items():
        current = candidate.get("aggregates", {}).get(model)
        if current is None:
            failures.append(f"MODEL_AGGREGATE_MISSING:{model}")
            continue
        before_count = int(base_aggregate["record_count"])
        after_count = int(current["record_count"])
        if after_count < before_count:
            if restore_equivalence:
                warnings.append(f"RESTORE_SNAPSHOT_PRECEDES_BASELINE:{model}")
            else:
                failures.append(f"RECORD_COUNT_DECREASED:{model}")
        elif after_count > before_count:
            warnings.append(f"RECORD_COUNT_INCREASED:{model}")
        for field, before_nulls in base_aggregate[
            "null_required_fields"
        ].items():
            after_nulls = current["null_required_fields"].get(field)
            if after_nulls is None or int(after_nulls) > int(before_nulls):
                failures.append(f"REQUIRED_FIELD_NULLS_INCREASED:{model}:{field}")
    for model, base_rows in baseline.get("samples", {}).items():
        current_rows = _sample_map(candidate.get("samples", {}).get(model, []))
        for record_id, expected in _sample_map(base_rows).items():
            actual = current_rows.get(record_id)
            if actual is None:
                failures.append(f"FIXED_SAMPLE_MISSING:{model}:{record_id}")
            elif actual != expected:
                failures.append(f"FIXED_SAMPLE_RELATION_CHANGED:{model}:{record_id}")
    for relationship, before_count in baseline.get("relationships", {}).items():
        after_count = candidate.get("relationships", {}).get(relationship)
        if after_count is None or int(after_count) > int(before_count):
            failures.append(f"ORPHAN_COUNT_INCREASED:{relationship}")
    base_fs = baseline["attachments"]["filestore"]
    current_fs = candidate["attachments"]["filestore"]
    if current_fs["missing_file_count"] > base_fs["missing_file_count"]:
        failures.append("ATTACHMENT_MISSING_COUNT_INCREASED")
    if current_fs["unreadable_file_count"] > base_fs["unreadable_file_count"]:
        failures.append("ATTACHMENT_UNREADABLE_COUNT_INCREASED")
    required_attachment_ids = set(base_fs["readable_sample_attachment_ids"])
    if not required_attachment_ids.issubset(
        set(current_fs["readable_sample_attachment_ids"])
    ):
        failures.append("ATTACHMENT_FIXED_SAMPLE_UNREADABLE")
    result = {
        "schema_version": contract["schema_version"],
        "comparison_mode": (
            "RESTORE_EQUIVALENCE" if restore_equivalence else "UPGRADE_STRICT"
        ),
        "failures": sorted(failures),
        "warnings": sorted(warnings),
        "pass": not failures,
        "result": "PASS" if not failures else "FAIL",
    }
    _assert_no_sensitive_output(contract, result)
    return result


def _atomic_write(path: Path, payload: dict) -> str:
    if not path.is_absolute():
        raise SentinelError("sentinel output path must be absolute")
    path.parent.mkdir(mode=0o700, parents=False, exist_ok=True)
    path.parent.chmod(0o700)
    if path.exists() or path.is_symlink():
        raise SentinelError("sentinel output already exists")
    previous_umask = os.umask(0o077)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        os.rename(temporary, path)
        temporary = None
    finally:
        os.umask(previous_umask)
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_capture(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SentinelError("sentinel capture is missing or invalid") from exc


def _clone_capture_and_compare(
    contract: dict, baseline: dict, backup_dir: Path
) -> tuple[dict, dict]:
    continuity_contract = continuity._load_contract(DEFAULT_CONTINUITY_CONTRACT)
    manifest = continuity.validate_backup(
        continuity_contract, backup_dir, strict_permissions=True
    )
    if (
        manifest["backup_set_id"]
        != contract["environment"]["continuity_backup_set_id"]
    ):
        raise SentinelError("clone backup set identity mismatch")
    runtime = continuity._assert_runtime(continuity_contract)
    suffix = secrets.token_hex(4)
    prefix = f"{CLONE_PREFIX}{suffix}"
    network = f"{prefix}-net"
    db_volume = f"{prefix}-db"
    fs_volume = f"{prefix}-fs"
    db_container = f"{prefix}-postgres"
    fs_container = f"{prefix}-filestore"
    password = secrets.token_urlsafe(32)
    created = {
        "network": False,
        "db_volume": False,
        "fs_volume": False,
        "db_container": False,
        "fs_container": False,
    }
    started = time.monotonic()
    try:
        continuity._run(
            [
                "docker",
                "network",
                "create",
                "--internal",
                "--label",
                "sc.daily-sentinel=true",
                network,
            ]
        )
        created["network"] = True
        for volume, key in ((db_volume, "db_volume"), (fs_volume, "fs_volume")):
            continuity._run(
                [
                    "docker",
                    "volume",
                    "create",
                    "--label",
                    "sc.daily-sentinel=true",
                    volume,
                ]
            )
            created[key] = True
        continuity._run(
            [
                "docker",
                "run",
                "-d",
                "--pull",
                "never",
                "--name",
                db_container,
                "--network",
                network,
                "--label",
                "sc.daily-sentinel=true",
                "-e",
                "POSTGRES_USER=odoo",
                "-e",
                f"POSTGRES_PASSWORD={password}",
                "-e",
                "POSTGRES_DB=postgres",
                "-v",
                f"{db_volume}:/var/lib/postgresql/data",
                runtime["database_image_id"],
            ]
        )
        created["db_container"] = True
        continuity._wait_postgres(db_container)
        continuity._run(
            ["docker", "exec", db_container, "createdb", "-U", "odoo", "sc_demo"]
        )
        continuity._run_from_file(
            [
                "docker",
                "exec",
                "-i",
                db_container,
                "pg_restore",
                "-U",
                "odoo",
                "-d",
                "sc_demo",
                "--no-owner",
                "--no-privileges",
            ],
            backup_dir / "database.dump",
        )
        extract = (
            "set -eu; mkdir -p /var/lib/odoo/filestore; "
            "tar -C /var/lib/odoo/filestore -xzf -"
        )
        continuity._run_from_file(
            [
                "docker",
                "run",
                "--rm",
                "-i",
                "--pull",
                "never",
                "--network",
                "none",
                "--user",
                "0:0",
                "-v",
                f"{fs_volume}:/var/lib/odoo/filestore",
                "--entrypoint",
                "sh",
                runtime["odoo_image_id"],
                "-c",
                extract,
            ],
            backup_dir / "filestore.tar.gz",
        )
        continuity._run(
            [
                "docker",
                "run",
                "-d",
                "--pull",
                "never",
                "--name",
                fs_container,
                "--network",
                "none",
                "--user",
                "0:0",
                "--label",
                "sc.daily-sentinel=true",
                "-v",
                f"{fs_volume}:/var/lib/odoo/filestore:ro",
                "--entrypoint",
                "sh",
                runtime["odoo_image_id"],
                "-c",
                "sleep 3600",
            ]
        )
        created["fs_container"] = True
        clone_runtime = {
            "restored_from_backup_set_id": manifest["backup_set_id"],
            "source_application_revision": manifest["runtime"]["source_revision"],
            "network_egress": "internal_database_and_none_filestore",
        }
        clone = capture(
            contract,
            db_container=db_container,
            odoo_container=fs_container,
            source_kind="RESTORED_ISOLATED_CLONE",
            runtime=clone_runtime,
        )
        comparison = compare(
            contract, baseline, clone, restore_equivalence=True
        )
        if not comparison["pass"]:
            raise SentinelError(
                "original and restored clone sentinel comparison failed"
            )
        clone_summary = {
            "capture_pass": True,
            "database_uuid": clone["database_uuid"],
            "fixed_sample_count": clone["fixed_sample_count"],
            "attachment_sample_count": clone["attachment_sample_count"],
            "core_relationship_baseline_pass": clone[
                "core_relationship_baseline_pass"
            ],
            "attachment_readability_baseline_pass": clone[
                "attachment_readability_baseline_pass"
            ],
            "duration_seconds": int(time.monotonic() - started),
            "restored_from_backup_set_id": manifest["backup_set_id"],
        }
        return clone_summary, comparison
    finally:
        if created["fs_container"]:
            continuity._run(["docker", "rm", "-f", fs_container], check=False)
        if created["db_container"]:
            continuity._run(["docker", "rm", "-f", db_container], check=False)
        if created["db_volume"]:
            continuity._run(["docker", "volume", "rm", db_volume], check=False)
        if created["fs_volume"]:
            continuity._run(["docker", "volume", "rm", fs_volume], check=False)
        if created["network"]:
            continuity._run(["docker", "network", "rm", network], check=False)


def verify(contract: dict, backup_dir: Path) -> dict:
    if (
        os.environ.get("CONFIRM_DAILY_SENTINEL_VERIFY")
        != "READ_ONLY_CAPTURE_AND_ISOLATED_RESTORE"
    ):
        raise SentinelError("daily sentinel verification confirmation is required")
    environment = contract["environment"]
    if backup_dir != Path(environment["continuity_backup_root"]):
        raise SentinelError("continuity backup directory identity mismatch")
    runtime_before = _runtime_identity(contract)
    first = capture(contract)
    if not first["core_relationship_baseline_pass"]:
        raise SentinelError("existing fixed relationship baseline is damaged")
    if not first["attachment_readability_baseline_pass"]:
        raise SentinelError("existing attachment readability baseline is damaged")
    second = capture(contract)
    deterministic = (
        first["samples"] == second["samples"]
        and first["model_mappings"] == second["model_mappings"]
        and first["companies"] == second["companies"]
    )
    if not deterministic:
        raise SentinelError("repeated capture was not deterministic")
    clone, comparison = _clone_capture_and_compare(contract, first, backup_dir)
    runtime_after = _runtime_identity(contract)
    if runtime_before != runtime_after:
        raise SentinelError("daily runtime changed during sentinel task")
    leftovers = {
        "containers": _run(
            ["docker", "ps", "-aq", "--filter", "label=sc.daily-sentinel=true"]
        ).decode().split(),
        "volumes": _run(
            ["docker", "volume", "ls", "-q", "--filter", "label=sc.daily-sentinel=true"]
        ).decode().split(),
        "networks": _run(
            ["docker", "network", "ls", "-q", "--filter", "label=sc.daily-sentinel=true"]
        ).decode().split(),
    }
    if any(leftovers.values()):
        raise SentinelError("temporary sentinel clone resources remain")
    sentinel_id = (
        f"sc_demo-sentinel-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-"
        f"{secrets.token_hex(4)}"
    )
    if not SENTINEL_ID.fullmatch(sentinel_id):
        raise SentinelError("sentinel set identifier is invalid")
    payload = {
        **first,
        "sentinel_set_id": sentinel_id,
        "continuity_backup_set_id": environment["continuity_backup_set_id"],
        "verification": {
            "repeated_capture_count": 2,
            "deterministic_capture_pass": True,
            "restored_clone": clone,
            "original_vs_restore": comparison,
            "daily_runtime_unchanged": True,
            "temporary_resources_removed": True,
            "daily_application_upgraded": False,
            "daily_database_write_performed": False,
            "daily_filestore_write_performed": False,
            "production_accessed": False,
        },
        "result": "PASS_DAILY_DATA_SENTINEL_BASELINE",
    }
    output = Path(environment["sentinel_root"]) / f"{sentinel_id}.json"
    digest = _atomic_write(output, payload)
    return {
        "sentinel_set_id": sentinel_id,
        "sentinel_evidence_path": str(output),
        "sentinel_evidence_sha256": digest,
        "sentinel_model_count": len(first["model_mappings"]),
        "fixed_sample_count": first["fixed_sample_count"],
        "attachment_sample_count": first["attachment_sample_count"],
        "unknown_origin_record_group_count": first[
            "unknown_origin_record_group_count"
        ],
        "deterministic_capture_pass": True,
        "restored_clone_capture_pass": True,
        "original_vs_restore_compare_pass": True,
        "primary_database_write_count": 0,
        "temporary_resources_removed": True,
        "result": payload["result"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("capture", "compare", "verify"))
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--restore-equivalence", action="store_true")
    args = parser.parse_args()
    contract = _load_contract(args.contract)
    if args.action == "capture":
        result = capture(contract)
        if args.output:
            digest = _atomic_write(args.output, result)
            print(f"SENTINEL_EVIDENCE_SHA256={digest}")
    elif args.action == "compare":
        if not args.baseline or not args.candidate:
            raise SentinelError("--baseline and --candidate are required")
        result = compare(
            contract,
            _load_capture(args.baseline),
            _load_capture(args.candidate),
            restore_equivalence=args.restore_equivalence,
        )
        if not result["pass"]:
            raise SentinelError("sentinel comparison failed")
    else:
        if not args.backup_dir:
            raise SentinelError("--backup-dir is required")
        result = verify(contract, args.backup_dir)
    print("DAILY_DATA_SENTINEL=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (SentinelError, continuity.ContinuityError) as exc:
        raise SystemExit(f"DAILY_DATA_SENTINEL_ERROR={exc}") from exc
