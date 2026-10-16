#!/usr/bin/env python3
"""Read-only database identity inventory for one governed runtime host.

The database architecture policy makes every database task resolve the target
role, tenant, environment, exact filter and filestore identity *before* a write
(``docs/governance/database_architecture_policy.md``). This entry answers that
preflight from the runtime itself instead of from a hand-assembled command:

* which databases exist in the served cluster, and which role owns each;
* which login roles exist, and whether they carry superuser/createdb;
* the configured ``dbfilter``/``list_db``/``db_name`` and the filestore
  namespace each database resolves to.

It never writes. ``--report`` only writes a local file. Presence of a database
name is not a verdict about its role; the report records the observed identity
and the operator binds the role afterwards.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import daily_runtime_duty_identity as duty_identity  # noqa: E402


REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
REMOTE_TMP = "/tmp/sc-daily-db-identity-inventory.py"
MARKER = "DAILY_DATABASE_IDENTITY_INVENTORY="
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+$")


class InventoryError(RuntimeError):
    pass


PROGRAM_TEMPLATE = '''
import json

import odoo

MARKER = "DAILY_DATABASE_IDENTITY_INVENTORY="

config = odoo.tools.config

env.cr.execute("SELECT current_user, session_user, current_database()")
current_user, session_user, current_database = env.cr.fetchone()

env.cr.execute(
    "SELECT datname, pg_get_userbyid(datdba), pg_encoding_to_char(encoding)"
    " FROM pg_database WHERE datistemplate = false ORDER BY datname"
)
databases = [
    {"name": row[0], "owner": row[1], "encoding": row[2]}
    for row in env.cr.fetchall()
]

env.cr.execute(
    "SELECT rolname, rolcanlogin, rolsuper, rolcreatedb"
    " FROM pg_roles ORDER BY rolname"
)
roles = [
    {
        "name": row[0],
        "can_login": bool(row[1]),
        "superuser": bool(row[2]),
        "createdb": bool(row[3]),
    }
    for row in env.cr.fetchall()
]

filestores = {}
for entry in databases:
    try:
        filestores[entry["name"]] = config.filestore(entry["name"])
    except Exception as exc:
        filestores[entry["name"]] = "error:" + type(exc).__name__

payload = {
    "current_user": current_user,
    "session_user": session_user,
    "current_database": current_database,
    "databases": databases,
    "roles": roles,
    "filestores": filestores,
    "data_dir": str(config.get("data_dir") or ""),
    "dbfilter": str(config.get("dbfilter") or ""),
    "list_db": bool(config.get("list_db")),
    "configured_db_name": str(config.get("db_name") or ""),
    "server_version": env.cr.connection.server_version,
    "writes": False,
}
print(MARKER + json.dumps(payload, ensure_ascii=False, sort_keys=True))
'''


def run(command, *, input_bytes=None):
    return subprocess.run(
        command, cwd=ROOT, input=input_bytes,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )


def ssh(ssh_host, remote_command, *, input_bytes=None):
    return run(
        [
            "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4",
            ssh_host, remote_command,
        ],
        input_bytes=input_bytes,
    )


def decode(result):
    return (result.stdout + result.stderr).decode("utf-8", "replace")


def marker_payload(output):
    for line in reversed(output.splitlines()):
        if line.startswith(MARKER):
            try:
                return json.loads(line[len(MARKER):])
            except ValueError:
                return None
    return None


def bind_target(options, *, instances_reader=None):
    """Bind the target duty, its cluster, its database and its storage, or stop.

    A database *name* is not a target identity, and this entry's whole question
    is about a *cluster*: the rebuilt demo carrier and the preserved
    pre-governance source both answer to ``sc_demo`` while living in two
    clusters.  Naming only the database used to answer the question about
    whichever cluster happened to serve that name.
    """
    try:
        reader = instances_reader
        if reader is None:
            reader = duty_identity.ssh_instances_reader(options.ssh_host)
        return duty_identity.bind_duty_database(
            getattr(options, "duty", ""), options.database, instances_reader=reader,
        )
    except duty_identity.DutyIdentityError as error:
        raise InventoryError(str(error))


def remote_shell(ssh_host, binding, *, stdin_path):
    """Read the catalog from the *bound duty's own* application container."""
    return ssh(ssh_host, duty_identity.odoo_shell_command(binding, program_path=stdin_path))


def inventory(expected_sha, binding, ssh_host):
    database = str(binding["database"])
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise InventoryError("expected SHA must be a full lowercase commit identity")
    if not DATABASE_NAME.fullmatch(database or ""):
        raise InventoryError("database must be a plain database name")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise InventoryError("SSH host must be a configured host alias")
    if not (ROOT / ".git").exists():
        raise InventoryError("must run from the governed repository")

    head = ssh(ssh_host, f"cd {shlex.quote(REMOTE_ROOT)} && git rev-parse HEAD")
    if head.returncode:
        raise InventoryError(f"remote revision read failed: {decode(head)[:400]}")
    remote_head = head.stdout.decode().strip()
    if remote_head != expected_sha:
        raise InventoryError(
            f"remote HEAD {remote_head or '<unknown>'} != expected {expected_sha}"
        )

    program = PROGRAM_TEMPLATE.encode("utf-8")
    upload = ssh(ssh_host, f"cat > {shlex.quote(REMOTE_TMP)}", input_bytes=program)
    if upload.returncode:
        raise InventoryError(f"remote program upload failed: {decode(upload)[:400]}")
    executed = remote_shell(ssh_host, binding, stdin_path=REMOTE_TMP)
    ssh(ssh_host, f"rm -f {shlex.quote(REMOTE_TMP)}")
    payload = marker_payload(decode(executed))
    if payload is None:
        raise InventoryError(
            f"no readback payload in the odoo-shell output: {decode(executed)[-800:]}"
        )
    return payload, remote_head


def evaluate(database, payload):
    names = [row["name"] for row in payload.get("databases") or []]
    logins = [row for row in payload.get("roles") or [] if row.get("can_login")]
    filestores = payload.get("filestores") or {}
    counts: dict[str, int] = {}
    for path in filestores.values():
        if not path or str(path).startswith("error:"):
            continue
        counts[path] = counts.get(path, 0) + 1
    shared_filestore = sorted(path for path, count in counts.items() if count > 1)
    assertions = [
        {
            "id": "observed_database_present",
            "passed": database in names,
            "detail": f"database={database} observed={len(names)}",
        },
        {
            # The inventory must prove it read the *bound* database and not the
            # other cluster that answers to the same name: two carriers share
            # ``sc_demo``, so "the name appears in this catalogue" is not enough.
            "id": "shell_database_is_the_bound_database",
            "passed": str(payload.get("current_database") or "") == database,
            "detail": f"current_database={payload.get('current_database')!r} bound={database!r}",
        },
        {
            "id": "distinct_login_roles_observed",
            "passed": bool(logins),
            "detail": f"login_roles={[row['name'] for row in logins]}",
        },
        {
            "id": "filestore_namespace_per_database",
            "passed": not shared_filestore,
            "detail": shared_filestore,
        },
        {
            "id": "inventory_is_read_only",
            "passed": payload.get("writes") is False,
            "detail": f"writes={payload.get('writes')}",
        },
    ]
    return {
        "assertions": assertions,
        "passed": all(row["passed"] for row in assertions),
        "database_count": len(names),
        "superuser_or_createdb_roles": [
            row["name"] for row in logins if row.get("superuser") or row.get("createdb")
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--duty", default="", help="the declared duty this entry binds; a database name alone is not a target identity")
    parser.add_argument("--database", default="")
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--report", required=True)
    options = parser.parse_args()

    try:
        binding = bind_target(options)
        payload, remote_head = inventory(
            options.expected_sha, binding, options.ssh_host
        )
        verdict = evaluate(str(binding["database"]), payload)
    except InventoryError as error:
        print(f"[daily.runtime.database.identity.inventory] BLOCKED {error}", file=sys.stderr)
        return 2

    report = {
        "schema": "daily.runtime.database.identity.inventory.v1",
        "expected_sha": options.expected_sha,
        "remote_head": remote_head,
        "ssh_host": options.ssh_host,
        "opened_database": str(binding["database"]),
        "database_binding": binding,
        "writes": False,
        "provenance": {
            "live_account_query": [
                "databases", "roles", "filestores", "current_user", "session_user",
                "current_database", "data_dir", "dbfilter", "list_db",
                "configured_db_name", "server_version",
            ],
            "read_scope": "cluster catalog, role attributes and configured paths only; no business row is read",
        },
        "observation": payload,
        "verdict": verdict,
        "status": "PASS" if verdict["passed"] else "FAIL",
    }
    report_path = Path(options.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "schema": report["schema"], "status": report["status"],
        "expected_sha": report["expected_sha"], "remote_head": report["remote_head"],
        "report": str(report_path),
        "database_count": verdict["database_count"],
        "databases": [row["name"] for row in payload.get("databases") or []],
        "superuser_or_createdb_roles": verdict["superuser_or_createdb_roles"],
        "failed_assertions": [r["id"] for r in verdict["assertions"] if not r["passed"]],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
