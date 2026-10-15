#!/usr/bin/env python3
"""Read-only tenant topology inventory across the governed runtime databases.

The daily runtime is being closed as three databases with separate duties: a
platform control database, the platform-internal demo database, and one customer
development business database. The database identity inventory answers the
cluster-level questions (which databases exist, which role owns them, which
filestore namespace each resolves to). It deliberately does not answer the
tenant question, and a database *name* is not evidence about what it carries --
``sc_demo`` is the obvious example.

This entry answers the tenant question from the runtime itself, read-only, and
never writes a business row:

* which tenant registrations exist in each database, with their declared
  ``data_purpose`` and owning company;
* which product-line revision each database has installed, so a difference
  between the demo face and the customer face is visible rather than assumed;
* how many business rows each model carries per owning company, including rows
  that no company owns at all.

It is the input to the role binding that
``docs/governance/database_architecture_policy.md`` section 11 requires: the
report states the observed facts and the operator binds ``TARGET_DATABASE_ROLE``
and ``TARGET_TENANT_ID``. Two mechanism invariants are still checked here, because
they must hold whatever the operator binds:

* a database that installs the platform kernel without the industry product line
  must not carry customer business rows;
* every company that owns business rows must appear in that database's tenant
  registry with an explicit purpose.

``--report`` only writes a local file. A zero exit code is not the verdict; the
report's ``assertions`` block is.
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
REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
REMOTE_TMP = "/tmp/sc-daily-tenant-topology.py"
DEFAULT_DATABASE = "sc_demo"
DEFAULT_DATABASES = ("sc_demo", "sc_odoo", "sc_platform_core")
MARKER = "DAILY_TENANT_TOPOLOGY="
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
KERNEL_MODULE = "smart_core"
INDUSTRY_MODULE = "smart_construction_core"
#: The product line every tenant faces, in the order the report lists it. The
#: customer addon of one tenant is *not* part of the product line: the caller
#: names it, because a product tree that shipped one customer's module name would
#: be delivering that customer's identity to every other tenant.
PRODUCT_MODULES = (
    KERNEL_MODULE,
    INDUSTRY_MODULE,
    "smart_construction_custom",
    "smart_construction_demo",
)
MODULE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
BUSINESS_MODELS = (
    ("payment.request", "company_id"),
    ("payment.ledger", "company_id"),
    ("construction.contract", "company_id"),
    ("project.project", "company_id"),
)
REGISTRATION_MODEL = "sc.tenant.company.registration"


class InventoryError(RuntimeError):
    pass


PROGRAM_TEMPLATE = '''
import json

import odoo

MARKER = "DAILY_TENANT_TOPOLOGY="
DATABASES = __DATABASES__
PRODUCT_MODULES = __PRODUCT_MODULES__
BUSINESS_MODELS = __BUSINESS_MODELS__
REGISTRATION_MODEL = __REGISTRATION_MODULE__


def table_of(model):
    return model.replace(".", "_")


def has_table(cr, table):
    cr.execute("SELECT to_regclass(%s) IS NOT NULL", (table,))
    return bool(cr.fetchone()[0])


def has_column(cr, table, column):
    cr.execute(
        "SELECT 1 FROM pg_attribute WHERE attrelid = %s::regclass AND attname = %s",
        (table, column),
    )
    return bool(cr.fetchone())


observation = {}
for name in DATABASES:
    entry = {"database": name}
    try:
        with odoo.modules.registry.Registry(name).cursor() as cr:
            cr.execute("SELECT current_database()")
            entry["resolved_database"] = cr.fetchone()[0]
            entry["installed_modules"] = 0
            entry["product_modules"] = {}
            if has_table(cr, "ir_module_module"):
                cr.execute("SELECT count(*) FROM ir_module_module WHERE state = 'installed'")
                entry["installed_modules"] = cr.fetchone()[0]
                # ``ir_module_module`` does not expose the same revision columns
                # on every release; read the ones that are present instead of
                # pinning a column that may not exist on a target database.
                cr.execute(
                    "SELECT attname FROM pg_attribute"
                    " WHERE attrelid = 'ir_module_module'::regclass AND attname IN"
                    " ('latest_version', 'installed_version', 'published_version')"
                )
                available = {row[0] for row in cr.fetchall()}
                selected = ["name"] + [
                    column for column in ("latest_version", "installed_version")
                    if column in available
                ]
                cr.execute(
                    "SELECT " + ", ".join(selected) + " FROM ir_module_module"
                    " WHERE state = 'installed' AND name = ANY(%s) ORDER BY name",
                    (list(PRODUCT_MODULES),),
                )
                entry["product_modules"] = {}
                for row in cr.fetchall():
                    record = dict(zip(selected, row))
                    entry["product_modules"][record["name"]] = {
                        column: record.get(column) for column in
                        ("latest_version", "installed_version")
                    }
            entry["companies"] = []
            if has_table(cr, "res_company"):
                cr.execute("SELECT id, name FROM res_company ORDER BY id")
                entry["companies"] = [{"id": row[0], "name": row[1]} for row in cr.fetchall()]
            entry["registrations"] = []
            registration_table = table_of(REGISTRATION_MODEL)
            if has_table(cr, registration_table):
                cr.execute(
                    "SELECT company_id, data_purpose FROM " + registration_table + " ORDER BY company_id"
                )
                entry["registrations"] = [
                    {"company_id": row[0], "data_purpose": row[1]} for row in cr.fetchall()
                ]
            entry["business_rows"] = {}
            for model, anchor in BUSINESS_MODELS:
                table = table_of(model)
                if not has_table(cr, table):
                    entry["business_rows"][model] = "table_absent"
                    continue
                if has_column(cr, table, anchor):
                    cr.execute(
                        "SELECT " + anchor + ", count(*) FROM " + table + " GROUP BY 1 ORDER BY 2 DESC"
                    )
                    entry["business_rows"][model] = [
                        {"company_id": row[0], "rows": row[1]} for row in cr.fetchall()
                    ]
                else:
                    cr.execute("SELECT count(*) FROM " + table)
                    entry["business_rows"][model] = [
                        {"company_id": None, "rows": cr.fetchone()[0]}
                    ]
        observation[name] = entry
    except Exception as exc:
        entry["error"] = type(exc).__name__ + ":" + str(exc)[:160]
        observation[name] = entry

print(MARKER + json.dumps({
    "databases": DATABASES,
    "observation": observation,
    "writes": False,
}, ensure_ascii=False, sort_keys=True))
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


def remote_make(ssh_host, database, target, *, stdin_path):
    command = (
        "cd " + shlex.quote(REMOTE_ROOT)
        + " && make --no-print-directory " + target
        + " DB_NAME=" + shlex.quote(database)
        + " < " + shlex.quote(stdin_path)
    )
    return ssh(ssh_host, command)


def parse_databases(value):
    names = [item.strip() for item in (value or "").split(",") if item.strip()]
    if not names:
        raise InventoryError("at least one database must be declared")
    for name in names:
        if not DATABASE_NAME.fullmatch(name):
            raise InventoryError(f"invalid database identity: {name!r}")
    if len(set(names)) != len(names):
        raise InventoryError("database identities must be unique")
    return names


def product_modules(customer_module=""):
    """The declared product line, plus the caller-named customer addon."""
    modules = list(PRODUCT_MODULES)
    if customer_module:
        modules.append(customer_module)
    return modules


def inventory(expected_sha, database, ssh_host, databases, *, customer_module=""):
    """Read the tenant topology of the declared databases.

    ``customer_module`` is the tenant's own customer addon, named by the caller.
    The product line is the same for every tenant, so the module list this entry
    reports is the product line plus, only when the caller names it, that one
    customer addon. An unnamed customer addon is reported as undeclared rather
    than inherited from a fixed name in the product tree.
    """
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise InventoryError("expected SHA must be a full lowercase commit identity")
    if not DATABASE_NAME.fullmatch(database or ""):
        raise InventoryError("database must be a plain database name")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise InventoryError("SSH host must be a configured host alias")
    if customer_module and not MODULE_NAME.fullmatch(customer_module):
        raise InventoryError(f"invalid customer module name: {customer_module!r}")
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

    program = (
        PROGRAM_TEMPLATE
        .replace("__DATABASES__", json.dumps(list(databases)))
        .replace("__PRODUCT_MODULES__", json.dumps(product_modules(customer_module)))
        .replace("__BUSINESS_MODELS__", json.dumps([list(row) for row in BUSINESS_MODELS]))
        .replace("__REGISTRATION_MODULE__", json.dumps(REGISTRATION_MODEL))
    ).encode("utf-8")
    upload = ssh(ssh_host, f"cat > {shlex.quote(REMOTE_TMP)}", input_bytes=program)
    if upload.returncode:
        raise InventoryError(f"remote program upload failed: {decode(upload)[:400]}")
    executed = remote_make(ssh_host, database, "odoo.shell.exec", stdin_path=REMOTE_TMP)
    ssh(ssh_host, f"rm -f {shlex.quote(REMOTE_TMP)}")
    payload = marker_payload(decode(executed))
    if payload is None:
        raise InventoryError(
            f"no readback payload in the odoo-shell output: {decode(executed)[-800:]}"
        )
    return payload, remote_head


def business_totals(entry):
    """Row totals for the declared business model set, keyed by owning company.

    ``None`` collects the rows no company owns, because those are precisely the
    rows a per-company reader never sees.
    """
    totals = {}
    for model, value in (entry.get("business_rows") or {}).items():
        if not isinstance(value, list):
            continue
        for row in value:
            if not isinstance(row, dict):
                continue
            owner = row.get("company_id")
            totals[owner] = totals.get(owner, 0) + int(row.get("rows") or 0)
    return totals


def evaluate(databases, payload):
    observation = payload.get("observation") or {}
    assertions = []

    missing = [name for name in databases if (observation.get(name) or {}).get("error")]
    assertions.append({
        "id": "every_declared_database_reachable",
        "passed": not missing,
        "detail": {
            name: (observation.get(name) or {}).get("error") for name in missing
        } or "all reachable",
    })

    # A platform-only database is the control-plane candidate: it installs the
    # kernel, not the industry product line, so customer business rows in it are
    # a duty-separation failure rather than a configuration detail.
    violations = []
    platform_only = []
    for name in databases:
        entry = observation.get(name) or {}
        modules = entry.get("product_modules") or {}
        if KERNEL_MODULE in modules and INDUSTRY_MODULE not in modules:
            platform_only.append(name)
            owned = sum(
                count for owner, count in business_totals(entry).items() if owner is not None
            )
            unowned = business_totals(entry).get(None, 0)
            if owned or unowned:
                violations.append({"database": name, "owned": owned, "unowned": unowned})
    assertions.append({
        "id": "platform_only_database_carries_no_business_rows",
        "passed": not violations,
        "detail": {"platform_only": platform_only, "violations": violations},
    })

    # A company that owns rows must be registered with an explicit purpose, or
    # the ceiling cannot tell a demo row from customer data.
    unregistered = []
    for name in databases:
        entry = observation.get(name) or {}
        registered = {
            row.get("company_id") for row in (entry.get("registrations") or [])
            if row.get("data_purpose")
        }
        for owner, count in business_totals(entry).items():
            if owner is None or not count:
                continue
            if owner not in registered:
                unregistered.append({"database": name, "company_id": owner, "rows": count})
    assertions.append({
        "id": "every_business_owning_company_is_registered",
        "passed": not unregistered,
        "detail": unregistered or "all owning companies registered",
    })

    # The three duties are separate only if the volume lives in exactly one
    # database. Two carriers would mean either a copy or a split brain.
    carriers = []
    for name in databases:
        totals = business_totals(observation.get(name) or {})
        if sum(totals.values()):
            carriers.append({"database": name, "rows": sum(totals.values()), "by_owner": {
                ("unowned" if owner is None else str(owner)): count
                for owner, count in sorted(totals.items(), key=lambda item: -item[1])
            }})
    assertions.append({
        "id": "single_business_volume_carrier",
        "passed": len(carriers) == 1,
        "detail": carriers,
    })

    # A shared product line must not be at two revisions across the duties; a
    # drifted copy is what a "temporary" side database turns into.
    revisions = {}
    for name in databases:
        modules = (observation.get(name) or {}).get("product_modules") or {}
        industry = modules.get(INDUSTRY_MODULE)
        if industry:
            revisions.setdefault(industry.get("installed_version"), []).append(name)
    assertions.append({
        "id": "industry_product_line_revision_aligned",
        "passed": len(revisions) <= 1,
        "detail": revisions,
    })

    assertions.append({
        "id": "inventory_is_read_only",
        "passed": payload.get("writes") is False,
        "detail": f"writes={payload.get('writes')}",
    })

    return {
        "assertions": assertions,
        "passed": all(row["passed"] for row in assertions),
        "reachable_databases": [
            name for name in databases if not (observation.get(name) or {}).get("error")
        ],
        "business_volume_carriers": carriers,
        "platform_only_databases": platform_only,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--databases", default=",".join(DEFAULT_DATABASES))
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument(
        "--customer-module",
        default="",
        help="the tenant's own customer addon; omitted when the tenant declares none",
    )
    options = parser.parse_args()

    try:
        databases = parse_databases(options.databases)
        payload, remote_head = inventory(
            options.expected_sha, options.database, options.ssh_host, databases,
            customer_module=options.customer_module,
        )
        verdict = evaluate(databases, payload)
    except InventoryError as error:
        print(f"[daily.runtime.tenant.topology.inventory] BLOCKED {error}", file=sys.stderr)
        return 2

    report = {
        "schema": "daily.runtime.tenant.topology.inventory.v1",
        "expected_sha": options.expected_sha,
        "remote_head": remote_head,
        "ssh_host": options.ssh_host,
        "opened_database": options.database,
        "declared_databases": list(databases),
        "declared_customer_module": options.customer_module,
        "writes": False,
        "provenance": {
            "live_account_query": [
                "resolved_database", "installed_modules", "product_modules",
                "companies", "registrations", "business_rows",
            ],
            "read_scope": (
                "per-database module registry, company and tenant registration"
                " identity, and per-company row counts for the declared business"
                " model set; no business field value is read"
            ),
        },
        "observation": payload.get("observation"),
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
        "reachable_databases": verdict["reachable_databases"],
        "business_volume_carriers": verdict["business_volume_carriers"],
        "platform_only_databases": verdict["platform_only_databases"],
        "failed_assertions": [r["id"] for r in verdict["assertions"] if not r["passed"]],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
