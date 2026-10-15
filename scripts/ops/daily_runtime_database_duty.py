#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Governed creation and custody check for the daily runtime database duties.

The database architecture policy makes every database duty a governed object:
a database is not an ambient convention, it has a declared role, tenant,
environment, storage namespace and exact route (`docs/governance/database_architecture_policy.md`
sections 2, 6, 7 and 11). The owner ruling of 2026-10-15 scopes this entry to
the *daily development server*: the platform control duty, the demo duty and one
customer development duty. It never touches production, and it never decides a
tenant, a purpose or a storage namespace by itself -- it consumes
``config/ops/daily_runtime_database_duties.v1.json``.

The platform model owns registration, lifecycle state, the managed operation
entry and the result readback. This entry is the *ops tool* that performs the
part the model cannot: it renders the duty's stack environment, creates the
cluster objects (application role plus database) and proves the custody facts.
It never registers a lifecycle state and never installs a module.

Three properties are fail-closed rather than best effort:

* a duty whose declaration says the database or the role does not exist yet is
  never mutated by the read-only plan, and an ``--apply`` refuses when the live
  facts contradict the declaration in either direction (a declared gap that was
  closed is as much a contradiction as a missing object);
* an application role must be able to log in yet must not be a superuser, must
  not create databases or roles, and must own its database; the declared
  ``role_compliance`` values are ``compliant``, ``declared_gap`` (with a reason
  and an owner task) and ``to_be_created``;
* a duty database is owned by exactly one cluster data volume, and one cluster
  data volume has exactly one owning container. The 2026-10-15 incident was two
  postmasters on one data directory, so the declaration may never reintroduce
  that shape.

``--report`` writes a local file only. The read-only path never writes remotely.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REMOTE_TMP = "/tmp/sc-daily-database-duty.py"
MARKER = "DAILY_RUNTIME_DATABASE_DUTY="
DEFAULT_DECLARATION = "config/ops/daily_runtime_database_duties.v1.json"
SCHEMA = "daily.runtime.database_duties.v1"
CONFIRMATION = "PROVISION_DAILY_RUNTIME_DATABASE_DUTY"
CONFIRM_ENV = "SC_CONFIRM_DAILY_RUNTIME_DATABASE_DUTY"
POSTGRES_DATA_DESTINATION = "/var/lib/postgresql/data"
PHASES = ("plan", "stack", "database", "all")
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
#: Every value the declaration must supply before a duty stack can be rendered.
#: A missing key is a fail-closed stop, never a default: a silent fallback is
#: exactly how one database ends up served by another duty's environment.
STACK_KEYS = (
    "compose_file", "env_template", "runtime_env", "odoo_image", "postgres_image",
    "product_root", "frontend_dist_dir", "demo_addons_root", "customer_addons_root",
)
#: Secret material generated once per duty and kept only on the governed host.
SECRET_KEYS = (
    "DB_PASSWORD", "DB_MAINTENANCE_PASSWORD", "ADMIN_PASSWD", "JWT_SECRET",
    "SC_BOOTSTRAP_SECRET",
)
#: The duty env keys whose readback proves the rendered file describes *this*
#: duty; a mismatch means the file on the host is not the reviewed declaration.
ENV_READBACK_KEYS = (
    "DUTY_NAME", "COMPOSE_PROJECT_NAME", "DB_NAME", "DB_USER", "DB_MAINTENANCE_USER",
    "DB_DATA", "REDIS_DATA", "ODOO_DATA", "ODOO_DBFILTER", "ODOO_PORT", "NGINX_PORT",
    "LIST_DB",
)
PLACEHOLDER = re.compile(r"@[A-Z0-9_]+@")
#: The cluster readback is one argument vector on purpose. A combined short
#: option cluster such as ``-Atc`` makes psql take the *next* argv as the value
#: of ``-c``, so a following ``-F`` and the statement become extra arguments:
#: psql then prints the query as a warning and reports an empty row, which is
#: indistinguishable from "the object is absent". Separate long options keep the
#: readback honest.
PSQL_READBACK = ("psql", "--no-align", "--tuples-only", "--field-separator=|")
DUTY_KEYS = (
    "duty", "database", "database_role", "dbfilter", "environment_id", "tenant_key",
    "data_purpose", "cluster", "custody", "storage", "routing", "section_11",
)
SECTION_11_KEYS = (
    "TARGET_DATABASE_ROLE", "TARGET_TENANT_ID", "TARGET_ENVIRONMENT_ID",
    "IS_PLATFORM_CONTROL_DATABASE", "IS_INDUSTRY_CATALOG_DATABASE",
    "IS_CUSTOMER_TENANT_DATABASE", "IS_ISOLATED_REHEARSAL_DATABASE",
    "CUSTOMER_BUSINESS_DATA_ALLOWED", "FIXTURE_ALLOWED",
    "EXACT_DATABASE_FILTER_CONFIRMED", "FILESTORE_IDENTITY_CONFIRMED",
)
DATABASE_ROLES = ("platform_control", "industry_catalog", "customer_tenant", "isolated_rehearsal")
CUSTODY_COMPLIANCE = ("compliant", "declared_gap", "to_be_created")


class DutyError(RuntimeError):
    """Any fail-closed refusal or unverifiable outcome of this entry."""


# ----------------------------------------------------------------------
# declaration
# ----------------------------------------------------------------------
def load_declaration(path):
    declaration_path = Path(path)
    if not declaration_path.is_file():
        raise DutyError("DAILY_DUTY_DECLARATION_MISSING:%s" % (declaration_path,))
    try:
        declaration = json.loads(declaration_path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise DutyError("DAILY_DUTY_DECLARATION_INVALID_JSON:%s" % (error,)) from error
    if declaration.get("schema") != SCHEMA:
        raise DutyError("DAILY_DUTY_DECLARATION_SCHEMA_UNEXPECTED:%s" % (declaration.get("schema"),))
    if not isinstance(declaration.get("duties"), list) or not declaration["duties"]:
        raise DutyError("DAILY_DUTY_DECLARATION_EMPTY")
    return declaration


def declaration_digest(declaration):
    payload = json.dumps(declaration, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def declared_duties(declaration, wanted):
    """Return the selected duties; ``all`` selects every declared duty."""
    duties = declaration["duties"]
    names = [duty.get("duty") for duty in duties]
    if len(set(names)) != len(names):
        raise DutyError("DAILY_DUTY_NAME_DUPLICATED")
    if not wanted or wanted == ["all"]:
        return duties
    unknown = sorted(set(wanted) - set(names))
    if unknown:
        raise DutyError("DAILY_DUTY_UNDECLARED:%s" % (",".join(unknown),))
    return [duty for duty in duties if duty["duty"] in wanted]


def validate_declaration(declaration):
    """Every reason the declaration cannot govern a daily database duty."""
    failures = []
    naming = declaration.get("naming") or {}
    database_pattern = naming.get("database") or ""
    role_pattern = naming.get("database_role") or ""
    project_pattern = naming.get("compose_project") or ""
    for label, pattern in (
        ("database", database_pattern), ("database_role", role_pattern),
        ("compose_project", project_pattern),
    ):
        if not pattern:
            failures.append("naming.%s is not declared" % (label,))
        else:
            try:
                re.compile(pattern)
            except re.error as error:
                failures.append("naming.%s is not a regular expression: %s" % (label, error))
    if failures:
        return failures

    admin_database = str(declaration.get("platform_admin_database") or "")
    if not re.fullmatch(database_pattern, admin_database):
        failures.append(
            "declaration platform_admin_database %s breaks the naming convention" % (admin_database,)
        )
    ops_root = str(declaration.get("ops_root") or "")
    if not ops_root.startswith("/") or ops_root.endswith("/"):
        failures.append("declaration ops_root must be one absolute directory path")
    build_env_file = str(declaration.get("frontend_build_env_file") or "")
    if not build_env_file.startswith("/") or build_env_file.endswith("/"):
        failures.append(
            "declaration frontend_build_env_file must be one absolute file path"
        )

    seen = {key: {} for key in (
        "duty", "database", "database_role", "dbfilter", "compose_project",
        "nginx_host_port", "odoo_loopback_port", "cluster_container", "data_volume",
        "backup_namespace", "environment_id",
    )}
    volume_owners = {}
    for duty in declaration["duties"]:
        name = str(duty.get("duty") or "")
        missing = [key for key in DUTY_KEYS if key not in duty]
        if missing:
            failures.append("duty %s: missing keys %s" % (name or "<unnamed>", ",".join(missing)))
            continue
        database = str(duty.get("database") or "")
        role = str(duty.get("database_role") or "")
        cluster = duty.get("cluster") or {}
        custody = duty.get("custody") or {}
        storage = duty.get("storage") or {}
        routing = duty.get("routing") or {}
        stack = duty.get("stack") or {}
        maintenance_role = str(cluster.get("maintenance_role") or "")

        if not re.fullmatch(database_pattern, database):
            failures.append("duty %s: database %s breaks the naming convention" % (name, database))
        compliance = custody.get("role_compliance")
        if compliance == "declared_gap":
            # A declared gap is a historical fact that must be described exactly,
            # not a target name that may be normalised away: the only gap this
            # entry accepts is an application role that is still the cluster
            # bootstrap role, which is what policy section 6 forbids.
            if custody.get("gap_kind") != "shared_bootstrap_role":
                failures.append(
                    "duty %s: a declared role gap must say gap_kind=shared_bootstrap_role" % (name,)
                )
        elif not re.fullmatch(role_pattern, role):
            failures.append("duty %s: database_role %s breaks the naming convention" % (name, role))
        if compliance not in CUSTODY_COMPLIANCE:
            failures.append("duty %s: custody.role_compliance %s is not declared" % (name, compliance))
        elif compliance == "compliant" and role != database + naming.get("database_role_must_be_database_name_suffixed", ""):
            failures.append(
                "duty %s: a compliant application role must be the database name plus %s"
                % (name, naming.get("database_role_must_be_database_name_suffixed", ""))
            )
        if compliance == "declared_gap":
            for key in ("gap_reason", "gap_owner_task"):
                if not str(custody.get(key) or "").strip():
                    failures.append("duty %s: a declared gap needs %s" % (name, key))
        failures.extend(_validate_stack(name, duty, stack, naming, ops_root))
        if not maintenance_role:
            failures.append("duty %s: cluster.maintenance_role is required" % (name,))
        elif compliance == "declared_gap":
            if maintenance_role != role:
                failures.append(
                    "duty %s: gap_kind=shared_bootstrap_role requires the declared application "
                    "role to still be the cluster bootstrap role, otherwise the gap is closed "
                    "and the declaration is stale" % (name,)
                )
        elif maintenance_role == role:
            failures.append(
                "duty %s: the cluster bootstrap role and the application role must differ; "
                "one role cannot both bootstrap the cluster and obey least privilege" % (name,)
            )
        elif not re.fullmatch(naming.get("database_maintenance_role") or "", maintenance_role):
            failures.append(
                "duty %s: cluster.maintenance_role %s breaks the naming convention"
                % (name, maintenance_role)
            )
        if duty.get("dbfilter") != "^%s$" % (database,):
            failures.append("duty %s: dbfilter must be the exact anchored filter of its database" % (name,))
        project = str(cluster.get("compose_project") or "")
        if not re.fullmatch(project_pattern, project):
            failures.append("duty %s: cluster.compose_project %s breaks the naming convention" % (name, project))
        if str(storage.get("compose_project") or "") != project:
            failures.append("duty %s: storage.compose_project must equal cluster.compose_project" % (name,))
        if not str(cluster.get("data_volume") or ""):
            failures.append("duty %s: cluster.data_volume is required" % (name,))
        for key in ("odoo_data_volume", "redis_data_volume", "filestore_scope",
                    "session_namespace", "backup_namespace"):
            if not str(storage.get(key) or ""):
                failures.append("duty %s: storage.%s is required" % (name, key))
        if str(storage.get("filestore_scope") or "") != database:
            failures.append(
                "duty %s: storage.filestore_scope must equal the database so one database has one filestore"
                % (name,)
            )
        if routing.get("list_db") is not False:
            failures.append("duty %s: routing.list_db must be false (database enumeration closed)" % (name,))
        for key in ("nginx_host_port", "odoo_loopback_port"):
            port = routing.get(key)
            if not isinstance(port, int) or not (1 < port < 65536):
                failures.append("duty %s: routing.%s must be a port number" % (name, key))

        failures.extend(_validate_section_11(name, duty))
        failures.extend(_validate_scope(name, duty, compliance))

        for key, value in (
            ("duty", name), ("database", database), ("database_role", role),
            ("dbfilter", duty.get("dbfilter")), ("compose_project", project),
            ("nginx_host_port", routing.get("nginx_host_port")),
            ("odoo_loopback_port", routing.get("odoo_loopback_port")),
            ("cluster_container", cluster.get("container")),
            ("data_volume", cluster.get("data_volume")),
            ("backup_namespace", storage.get("backup_namespace")),
            ("environment_id", duty.get("environment_id")),
        ):
            owner = seen[key].get(value)
            if owner is not None and owner != name:
                failures.append(
                    "duties %s and %s share %s=%s" % (owner, name, key, value)
                )
            seen[key][value] = name
        container = str(cluster.get("container") or "")
        volume = str(cluster.get("data_volume") or "")
        if volume and container:
            volume_owners.setdefault(volume, set()).add(container)
    for volume, owners in sorted(volume_owners.items()):
        if len(owners) > 1:
            failures.append(
                "cluster data volume %s is declared by %s; one data directory has one writer"
                % (volume, ",".join(sorted(owners)))
            )
    return failures


def validate_stack_surface(compose_text, env_template):
    """Every compose variable must be resolved by the duty env, or fail closed.

    A compose reference without a default and without an env key is a stack that
    would render an empty value -- the exact shape that lets one instance come up
    against another duty's database or volume.
    """
    failures = []
    referenced = re.findall(r"\$\{([A-Z0-9_]+)(:?-[^}]*)?\}", compose_text)
    required = {name for name, default in referenced if not default}
    defined = set(re.findall(r"^([A-Z0-9_]+)=", env_template, re.MULTILINE))
    defined |= set(re.findall(r"@([A-Z0-9_]+)@", env_template))
    unresolved = sorted(required - defined)
    if unresolved:
        failures.append("compose variables without a duty env key: %s" % (",".join(unresolved),))
    unused = sorted(defined - {name for name, _ in referenced})
    return failures, unused


def _validate_stack(name, duty, stack, naming, ops_root):
    """The duty stack is a declaration, so an incomplete one never renders."""
    failures = []
    missing = [key for key in STACK_KEYS if not str(stack.get(key) or "").strip()]
    if missing:
        failures.append("duty %s: stack is incomplete, missing %s" % (name, ",".join(missing)))
        return failures
    for key in ("compose_file", "env_template"):
        value = str(stack[key])
        if value.startswith("/") or ".." in Path(value).parts:
            failures.append("duty %s: stack.%s must be a repository-relative path" % (name, key))
    for key in ("product_root", "frontend_dist_dir", "demo_addons_root", "customer_addons_root"):
        if not str(stack[key]).startswith("/"):
            failures.append("duty %s: stack.%s must be an absolute host path" % (name, key))
    if stack["product_root"].rstrip("/") != str(ops_root).rstrip("/") and not str(
        stack["product_root"]
    ).startswith("/opt/projects/"):
        failures.append("duty %s: stack.product_root is outside the governed /opt/projects root" % (name,))
    if str(stack["frontend_dist_dir"]).startswith(str(stack["product_root"]) + "/") is False:
        failures.append("duty %s: stack.frontend_dist_dir must live under stack.product_root" % (name,))
    if stack["runtime_env"] not in ("dev", "test"):
        failures.append("duty %s: stack.runtime_env must be a non-production runtime env" % (name,))
    return failures


def _validate_section_11(name, duty):
    failures = []
    table = duty.get("section_11") or {}
    missing = [key for key in SECTION_11_KEYS if key not in table]
    if missing:
        failures.append("duty %s: section 11 is incomplete, missing %s" % (name, ",".join(missing)))
        return failures
    if table["TARGET_DATABASE_ROLE"] not in DATABASE_ROLES:
        failures.append("duty %s: section 11 TARGET_DATABASE_ROLE %s is unknown" % (name, table["TARGET_DATABASE_ROLE"]))
    if table["TARGET_ENVIRONMENT_ID"] != duty.get("environment_id"):
        failures.append("duty %s: section 11 TARGET_ENVIRONMENT_ID must equal environment_id" % (name,))
    tenant = table["TARGET_TENANT_ID"]
    if tenant is not None and tenant != (duty.get("tenant_key") or None):
        failures.append("duty %s: section 11 TARGET_TENANT_ID must equal tenant_key" % (name,))
    for key in ("EXACT_DATABASE_FILTER_CONFIRMED", "FILESTORE_IDENTITY_CONFIRMED"):
        if table[key] is not True:
            failures.append("duty %s: section 11 %s must be confirmed true before a write" % (name, key))
    if table["IS_INDUSTRY_CATALOG_DATABASE"]:
        failures.append("duty %s: no industry catalog duty is authorized on this host" % (name,))
    if table["IS_ISOLATED_REHEARSAL_DATABASE"]:
        failures.append("duty %s: a rehearsal database is not a duty of this host" % (name,))
    expected_control = duty.get("data_purpose") == "platform_control"
    if table["IS_PLATFORM_CONTROL_DATABASE"] is not expected_control:
        failures.append("duty %s: section 11 platform-control flag contradicts data_purpose" % (name,))
    expected_tenant = duty.get("data_purpose") == "customer"
    if table["IS_CUSTOMER_TENANT_DATABASE"] is not expected_tenant:
        failures.append("duty %s: section 11 customer-tenant flag contradicts data_purpose" % (name,))
    if table["CUSTOMER_BUSINESS_DATA_ALLOWED"] is not expected_tenant:
        failures.append("duty %s: section 11 customer business data must follow the customer duty" % (name,))
    if table["IS_PLATFORM_CONTROL_DATABASE"] and table["FIXTURE_ALLOWED"]:
        failures.append("duty %s: the platform control duty never carries fixture data" % (name,))
    if table["IS_PLATFORM_CONTROL_DATABASE"] and duty.get("tenant_key"):
        failures.append("duty %s: the platform control duty is not a tenant data space" % (name,))
    return failures


def _validate_scope(name, duty, compliance):
    """The owner ruling covers the daily host; nothing here may claim production."""
    failures = []
    purpose = duty.get("data_purpose")
    if purpose not in ("platform_control", "demo", "test", "customer"):
        failures.append("duty %s: data_purpose %s is not declared" % (name, purpose))
    table = duty.get("section_11") or {}
    if purpose == "platform_control" and not table.get("IS_PLATFORM_CONTROL_DATABASE"):
        failures.append("duty %s: a platform control duty must say so in section 11" % (name,))
    if duty.get("environment_id", "").startswith("production"):
        failures.append("duty %s: this entry is not authorized to build a production environment" % (name,))
    if compliance == "to_be_created" and table.get("CUSTOMER_BUSINESS_DATA_ALLOWED"):
        # Creating an empty customer database is authorized; loading customer
        # data into it belongs to the user module, not to this entry.
        pass
    return failures


# ----------------------------------------------------------------------
# remote carrier
# ----------------------------------------------------------------------
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


REMOTE_PROGRAM = r'''
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys

MARKER = __MARKER__
PAYLOAD = json.loads(__PAYLOAD_JSON__)
MODE = PAYLOAD["mode"]
PHASE = PAYLOAD["phase"]
OPS_ROOT = PAYLOAD["ops_root"]
STACK = PAYLOAD["stack"]
ENV_TEMPLATE = PAYLOAD["env_template"]
DATA_DESTINATION = PAYLOAD["data_destination"]
PSQL_READBACK = __PSQL_READBACK__
PLACEHOLDER = re.compile(r"@[A-Z0-9_]+@")
SECRET_KEYS = (
    "DB_PASSWORD", "DB_MAINTENANCE_PASSWORD", "ADMIN_PASSWD", "JWT_SECRET",
    "SC_BOOTSTRAP_SECRET",
)
ENV_READBACK_KEYS = (
    "DUTY_NAME", "COMPOSE_PROJECT_NAME", "DB_NAME", "DB_USER", "DB_MAINTENANCE_USER",
    "DB_DATA", "REDIS_DATA", "ODOO_DATA", "ODOO_DBFILTER", "ODOO_PORT", "NGINX_PORT",
    "LIST_DB",
)

report = {"mode": MODE, "phase": PHASE, "writes": False, "duties": []}


def run(command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, check=False, **kwargs)


def inspect(names):
    if not names:
        return []
    result = run(["docker", "inspect", *names])
    if result.returncode:
        return []
    return json.loads(result.stdout or "[]")


def cluster_facts(container, duty):
    facts = {"present": False, "running": False, "system_identifier": "",
             "data_volume_owner": "", "project": "", "config_files": "", "error": ""}
    entries = inspect([container])
    if not entries:
        return facts
    entry = entries[0]
    facts["present"] = True
    facts["running"] = bool((entry.get("State") or {}).get("Running"))
    labels = (entry.get("Config") or {}).get("Labels") or {}
    facts["project"] = labels.get("com.docker.compose.project") or ""
    facts["config_files"] = labels.get("com.docker.compose.project.config_files") or ""
    for mount in entry.get("Mounts") or []:
        if mount.get("Destination") == DATA_DESTINATION and mount.get("Name"):
            facts["data_volume_owner"] = mount["Name"]
    if not facts["running"]:
        return facts
    role = duty["cluster"]["maintenance_role"]
    query = run(["docker", "exec", container, "psql", "-U", role, "-d", "postgres",
                 *PSQL_READBACK, "--command",
                 "SELECT system_identifier FROM pg_control_system()"])
    if query.returncode:
        facts["error"] = (query.stderr or query.stdout or "").strip()[:300]
    else:
        facts["system_identifier"] = query.stdout.strip()
    return facts


def database_facts(container, duty):
    facts = {"database_present": False, "database_owner": "", "allow_connections": None,
             "role_present": False, "role_superuser": None, "role_createdb": None,
             "role_createrole": None, "role_canlogin": None, "public_connects": None,
             "database_role_connects": None, "error": ""}
    name = duty["database"]
    role = duty["database_role"]
    maintenance_role = duty["cluster"]["maintenance_role"]
    statement = (
        "SELECT coalesce((SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %(name)s), ''),"
        " coalesce((SELECT datallowconn::text FROM pg_database WHERE datname = %(name)s), ''),"
        " coalesce((SELECT rolsuper::text FROM pg_roles WHERE rolname = %(role)s), ''),"
        " coalesce((SELECT rolcreatedb::text FROM pg_roles WHERE rolname = %(role)s), ''),"
        " coalesce((SELECT rolcreaterole::text FROM pg_roles WHERE rolname = %(role)s), ''),"
        " coalesce((SELECT rolcanlogin::text FROM pg_roles WHERE rolname = %(role)s), ''),"
        " coalesce((SELECT has_database_privilege('public', %(name)s, 'CONNECT')::text), ''),"
        " coalesce((SELECT has_database_privilege(%(role)s, %(name)s, 'CONNECT')::text), '')"
    ) % {"name": "'" + name.replace("'", "''") + "'", "role": "'" + role.replace("'", "''") + "'"}
    query = run(["docker", "exec", container, "psql", "-U", maintenance_role, "-d", "postgres",
                 *PSQL_READBACK, "--command", statement])
    if query.returncode:
        facts["error"] = (query.stderr or query.stdout or "").strip()[:300]
        return facts
    row = (query.stdout.strip().splitlines() or [""])[0].split("|")
    if len(row) != 8:
        facts["error"] = "unexpected catalog readback shape"
        return facts
    (owner, allow, superuser, createdb, createrole, canlogin, public_connects, role_connects) = row
    facts.update({
        "database_owner": owner,
        "allow_connections": None if allow == "" else allow == "true",
        "role_present": superuser != "",
        "role_superuser": None if superuser == "" else superuser == "true",
        "role_createdb": None if createdb == "" else createdb == "true",
        "role_createrole": None if createrole == "" else createrole == "true",
        "role_canlogin": None if canlogin == "" else canlogin == "true",
        "public_connects": None if public_connects == "" else public_connects == "true",
        "database_role_connects": None if role_connects == "" else role_connects == "true",
    })
    facts["database_present"] = bool(owner) or allow != ""
    return facts


# ----------------------------------------------------------------------
# governed write material
# ----------------------------------------------------------------------
def ensure_ops_root():
    if not os.path.isdir(OPS_ROOT):
        os.makedirs(OPS_ROOT, mode=0o700, exist_ok=True)
    os.chmod(OPS_ROOT, 0o700)


def frontend_build_facts():
    """Read the deployed frontend build environment back.

    ``VITE_PLATFORM_ADMIN_DB`` is a *build-time* variable: the duty nginx and
    odoo never read it, and neither does the browser. Rendering it into a duty
    env file would therefore be a decorative binding that can silently disagree
    with the bundle users actually load. The honest check is to read the file the
    frontend build consumed and refuse when it names another database.
    """
    path = PAYLOAD["frontend_build_env_file"]
    declared = PAYLOAD["platform_admin_database"]
    present = os.path.exists(path)
    digest = ""
    if present:
        with open(path, "rb") as stream:
            digest = hashlib.sha256(stream.read()).hexdigest()
    observed = read_env_file(path).get("VITE_PLATFORM_ADMIN_DB", "")
    error = ""
    if not present:
        error = "the declared frontend build environment file is missing"
    elif observed != declared:
        error = "the deployed frontend build names %s, not the declared %s" % (
            observed or "<unset>", declared,
        )
    return {
        "path": path,
        "present": present,
        "sha256": digest,
        "platform_admin_db": observed,
        "error": error,
    }


def read_env_file(path):
    values = {}
    if not os.path.exists(path):
        return values
    with open(path) as stream:
        for line in stream:
            line = line.rstrip("\n")
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key] = value
    return values


def credentials_path(duty):
    return os.path.join(OPS_ROOT, duty["duty"] + ".env")


def duty_credentials(duty):
    """Read or create the governed identity and secret material of one duty."""
    ensure_ops_root()
    path = credentials_path(duty)
    values = read_env_file(path)
    created = False
    for key in SECRET_KEYS:
        if not values.get(key):
            values[key] = secrets.token_hex(32)
            created = True
    for key, value in (("DB_NAME", duty["database"]),
                       ("DB_USER", duty["database_role"]),
                       ("DB_MAINTENANCE_USER", duty["cluster"]["maintenance_role"])):
        if values.get(key) and values[key] != value:
            raise RuntimeError("DAILY_DUTY_CREDENTIAL_IDENTITY_DRIFT:%s:%s" % (key, duty["duty"]))
        values[key] = value
    if created or not os.path.exists(path):
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write("# governed credential and identity material for the %s duty\n"
                         % (duty["duty"],))
            stream.write("# written by scripts/ops/daily_runtime_database_duty.py; never committed\n")
            for key in ("DB_NAME", "DB_USER", "DB_MAINTENANCE_USER") + SECRET_KEYS:
                stream.write("%s=%s\n" % (key, values[key]))
    return values, path, created


def render_env(duty, credentials):
    values = {
        "DUTY_NAME": duty["duty"],
        "COMPOSE_PROJECT_NAME": duty["cluster"]["compose_project"],
        "ENV": duty["stack"]["runtime_env"],
        "SC_ENVIRONMENT": duty["stack"]["runtime_env"],
        "SC_PRODUCT_ROOT": duty["stack"]["product_root"],
        "SC_SOURCE_REVISION": PAYLOAD["source_revision"],
        "POSTGRES_IMAGE": duty["stack"]["postgres_image"],
        "DB_NAME": duty["database"],
        "DB_USER": duty["database_role"],
        "DB_PASSWORD": credentials["DB_PASSWORD"],
        "DB_MAINTENANCE_USER": duty["cluster"]["maintenance_role"],
        "DB_MAINTENANCE_PASSWORD": credentials["DB_MAINTENANCE_PASSWORD"],
        "ODOO_DBFILTER": duty["dbfilter"],
        "DB_DATA": duty["cluster"]["data_volume"],
        "REDIS_DATA": duty["storage"]["redis_data_volume"],
        "ODOO_DATA": duty["storage"]["odoo_data_volume"],
        "ODOO_IMAGE": duty["stack"]["odoo_image"],
        "ODOO_PORT": str(duty["routing"]["odoo_loopback_port"]),
        "NGINX_PORT": str(duty["routing"]["nginx_host_port"]),
        "FRONTEND_DIST_DIR": duty["stack"]["frontend_dist_dir"],
        "DEMO_ADDONS_ROOT": duty["stack"]["demo_addons_root"],
        "CUSTOMER_ADDONS_ROOT": duty["stack"]["customer_addons_root"],
        "ADMIN_PASSWD": credentials["ADMIN_PASSWD"],
        "JWT_SECRET": credentials["JWT_SECRET"],
        "SC_BOOTSTRAP_SECRET": credentials["SC_BOOTSTRAP_SECRET"],
    }
    rendered = ENV_TEMPLATE
    for key, value in values.items():
        rendered = rendered.replace("@" + key + "@", str(value))
    return rendered


def stack_compose_path():
    return os.path.join(OPS_ROOT, "duty-stack-%s.yml" % PAYLOAD["compose_sha256"][:12])


def write_file(path, text, mode=0o600):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(descriptor, "w") as stream:
        stream.write(text)


def materialise_stack_files(duty):
    """Write the reviewed definition and its environment, then read them back."""
    ensure_ops_root()
    compose_text = STACK["compose_text"]
    digest = hashlib.sha256(compose_text.encode("utf-8")).hexdigest()
    if digest != PAYLOAD["compose_sha256"]:
        raise RuntimeError("DAILY_DUTY_COMPOSE_DIGEST_UNSTABLE")
    compose_path = stack_compose_path()
    if read_text(compose_path) != compose_text:
        write_file(compose_path, compose_text)
    credentials, credential_path, created = duty_credentials(duty)
    env_path = os.path.join(OPS_ROOT, duty["duty"] + ".env")
    rendered = render_env(duty, credentials)
    if read_text(env_path) != rendered:
        write_file(env_path, rendered)
    observed = read_env_file(env_path)
    return {
        "compose_path": compose_path,
        "compose_sha256": digest,
        "env_path": env_path,
        "env_sha256": hashlib.sha256(read_text(env_path).encode("utf-8")).hexdigest(),
        "credentials_path": credential_path,
        "credentials_created": created,
        "credentials_mode": oct(os.stat(credential_path).st_mode & 0o777),
        "env_mode": oct(os.stat(env_path).st_mode & 0o777),
        "env_keys": {key: observed.get(key, "") for key in ENV_READBACK_KEYS},
        "unresolved_placeholders": sorted(set(PLACEHOLDER.findall(read_text(env_path)))),
    }


def read_text(path):
    if not os.path.exists(path):
        return ""
    with open(path) as stream:
        return stream.read()


def start_cluster(duty):
    command = [
        "docker", "compose",
        "-f", stack_compose_path(),
        "--project-name", duty["cluster"]["compose_project"],
        "--env-file", os.path.join(OPS_ROOT, duty["duty"] + ".env"),
        "up", "-d", "--wait", "db",
    ]
    result = run(command, cwd=OPS_ROOT)
    return {"command": " ".join(command), "returncode": result.returncode,
            "error": (result.stderr or result.stdout or "").strip()[:600]}


def create_database(container, duty, password):
    name = duty["database"]
    role = duty["database_role"]
    maintenance_role = duty["cluster"]["maintenance_role"]
    quoted_role = '"' + role.replace('"', '""') + '"'
    quoted_name = '"' + name.replace('"', '""') + '"'
    statements = [
        "DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '%s') THEN"
        " EXECUTE format('CREATE ROLE %%I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD %%L', '%s', '%s');"
        " END IF; END $$;" % (role, role, password.replace("'", "''")),
        "CREATE DATABASE %s OWNER %s ENCODING 'UTF8' TEMPLATE template0" % (quoted_name, quoted_role),
        "REVOKE CONNECT ON DATABASE %s FROM PUBLIC" % (quoted_name,),
        "GRANT CONNECT ON DATABASE %s TO %s" % (quoted_name, quoted_role),
    ]
    steps = []
    for statement in statements:
        result = run(["docker", "exec", "-i", container, "psql", "-U", maintenance_role,
                      "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-Atc", statement])
        steps.append({"statement": statement.split(" ")[0], "returncode": result.returncode,
                      "error": (result.stderr or "").strip()[:200]})
        if result.returncode:
            return steps
    return steps


for duty in PAYLOAD["duties"]:
    wants_creation = duty["custody"]["role_compliance"] == "to_be_created"
    entry = {"duty": duty["duty"], "cluster": None, "custody": None, "stack": None, "create": None}
    if MODE == "apply" and PHASE in ("stack", "all"):
        if wants_creation:
            entry["stack"] = materialise_stack_files(duty)
            entry["stack"]["start"] = start_cluster(duty)
        else:
            entry["stack"] = {"skipped": "custody is not to_be_created; an existing duty stack is "
                                         "never restarted or re-rendered by this entry"}
    entry["cluster"] = cluster_facts(duty["cluster"]["container"], duty)
    if entry["cluster"].get("present") and entry["cluster"].get("running"):
        entry["custody"] = database_facts(duty["cluster"]["container"], duty)
    else:
        entry["custody"] = {"database_present": False, "database_owner": "",
                            "allow_connections": None, "role_present": False,
                            "role_superuser": None, "role_createdb": None,
                            "role_createrole": None, "role_canlogin": None,
                            "public_connects": None, "database_role_connects": None,
                            "error": "cluster container is not running"}
    if MODE == "apply" and PHASE in ("database", "all"):
        if not (entry["cluster"].get("present") and entry["cluster"].get("running")):
            entry["create"] = {"error": "cluster container is not running; start the duty stack first"}
        elif not wants_creation:
            entry["create"] = {"skipped": "custody is not to_be_created; no role or database is created"}
        elif entry["custody"].get("database_present"):
            entry["create"] = {"error": "the declared to-be-created database is already present; "
                                         "refusing to mutate an existing duty"}
        elif entry["custody"].get("role_present") and (
                not entry["custody"].get("role_canlogin")
                or entry["custody"].get("role_superuser")
                or entry["custody"].get("role_createdb")
                or entry["custody"].get("role_createrole")):
            entry["create"] = {"error": "the declared application role already exists with attributes "
                                         "that violate least privilege; refusing to reuse it implicitly"}
        else:
            password = read_env_file(credentials_path(duty)).get("DB_PASSWORD", "")
            if not password:
                entry["create"] = {"error": "the governed credential material is missing; run the stack phase"}
            else:
                entry["create"] = {"steps": create_database(duty["cluster"]["container"], duty, password)}
                entry["custody"] = database_facts(duty["cluster"]["container"], duty)
    report["duties"].append(entry)

report["frontend_build"] = frontend_build_facts()
report["writes"] = MODE == "apply"
print(MARKER + json.dumps(report, ensure_ascii=False, sort_keys=True))
'''


def render_remote_program(payload):
    """Render the reviewed remote carrier for one payload.

    The payload carries booleans and a whole compose document, so it is embedded
    as a JSON *string literal* and decoded on the host: substituting the bare
    object would leave Python ``True``/``False``/``None`` out of reach, and a
    compose line could break the program text. Rendering is a separate function
    so the embedding itself can be unit tested instead of only the decision
    layer.
    """
    return REMOTE_PROGRAM.replace("__MARKER__", json.dumps(MARKER)).replace(
        "__PSQL_READBACK__", json.dumps(list(PSQL_READBACK)),
    ).replace(
        "__PAYLOAD_JSON__",
        json.dumps(json.dumps(payload, ensure_ascii=False, sort_keys=True)),
    )


def remote_duties(ssh_host, payload, *, remote_head=None):
    program = render_remote_program(payload)
    upload = ssh(ssh_host, "cat > %s" % (shlex.quote(REMOTE_TMP),), input_bytes=program.encode("utf-8"))
    if upload.returncode:
        raise DutyError("remote program upload failed: %s" % (decode(upload)[:400],))
    executed = ssh(
        ssh_host,
        "python3 %s; rc=$?; rm -f %s; exit $rc" % (shlex.quote(REMOTE_TMP), shlex.quote(REMOTE_TMP)),
    )
    if executed.returncode:
        raise DutyError("remote duty %s failed: %s" % (payload["mode"], decode(executed)[:800]))
    result = marker_payload(decode(executed))
    if result is None:
        raise DutyError("no readback payload: %s" % (decode(executed)[-600:],))
    return result


# ----------------------------------------------------------------------
# evaluation
# ----------------------------------------------------------------------
def evaluate(duty, observation, declaration, *, phase="plan"):
    """Return the per-duty assertions that decide the verdict.

    The two phases ask different questions about the same observation. A plan
    asks whether the world still matches the declaration as written. An apply
    asks whether the duty now exists in its *target* shape, because the
    declaration legitimately still says ``to_be_created`` until the observed
    facts are written back into it; judging a freshly created duty against its
    own pre-write declaration would report a successful creation as a failure.
    """
    cluster = observation.get("cluster") or {}
    custody = observation.get("custody") or {}
    declared_cluster = duty["cluster"]
    declared_custody = duty["custody"]
    assertions = []

    def add(identifier, passed, detail):
        assertions.append({"id": identifier, "passed": bool(passed), "detail": detail})

    declared_compliance = declared_custody.get("role_compliance")
    wants_creation = declared_compliance == "to_be_created"
    creation_expected = wants_creation and phase == "apply"
    add("cluster_container_state_matches_declaration",
        (not wants_creation) or phase == "apply" or not cluster.get("present"),
        {"declared_to_be_created": wants_creation, "container_present": cluster.get("present"),
         "phase": phase})
    if cluster.get("present"):
        add("cluster_compose_project_matches_declaration",
            cluster.get("project") == declared_cluster.get("compose_project"),
            {"observed": cluster.get("project"), "declared": declared_cluster.get("compose_project")})
        add("cluster_data_volume_matches_declaration",
            cluster.get("data_volume_owner") == declared_cluster.get("data_volume"),
            {"observed": cluster.get("data_volume_owner"), "declared": declared_cluster.get("data_volume")})
        declared_identifier = str(declared_cluster.get("system_identifier") or "")
        if declared_identifier and cluster.get("system_identifier"):
            add("cluster_system_identifier_matches_declaration",
                cluster["system_identifier"] == declared_identifier,
                {"observed": cluster["system_identifier"], "declared": declared_identifier})
        if cluster.get("running"):
            add("cluster_catalog_is_readable_by_the_declared_maintenance_role",
                not cluster.get("error"),
                {"maintenance_role": declared_cluster.get("maintenance_role"),
                 "error": cluster.get("error")})

    stack = observation.get("stack")
    if wants_creation and stack is not None:
        if stack.get("skipped"):
            add("stack_definition_is_the_reviewed_one", False,
                {"skipped": stack.get("skipped"),
                 "note": "a to-be-created duty must be rendered and started by this entry"})
        else:
            observed_keys = stack.get("env_keys") or {}
            expected_keys = {
                "DUTY_NAME": duty["duty"],
                "COMPOSE_PROJECT_NAME": declared_cluster.get("compose_project"),
                "DB_NAME": duty["database"],
                "DB_USER": duty["database_role"],
                "DB_MAINTENANCE_USER": declared_cluster.get("maintenance_role"),
                "DB_DATA": declared_cluster.get("data_volume"),
                "REDIS_DATA": duty["storage"]["redis_data_volume"],
                "ODOO_DATA": duty["storage"]["odoo_data_volume"],
                "ODOO_DBFILTER": duty["dbfilter"],
                "ODOO_PORT": str(duty["routing"]["odoo_loopback_port"]),
                "NGINX_PORT": str(duty["routing"]["nginx_host_port"]),
                "LIST_DB": "false",
            }
            add("stack_environment_matches_declaration",
                observed_keys == expected_keys,
                {"observed": observed_keys, "declared": expected_keys})
            add("stack_environment_has_no_unresolved_placeholder",
                not stack.get("unresolved_placeholders"),
                {"unresolved": stack.get("unresolved_placeholders")})
            add("stack_secret_material_is_not_world_readable",
                stack.get("env_mode") == "0o600" and stack.get("credentials_mode") == "0o600",
                {"env_mode": stack.get("env_mode"),
                 "credentials_mode": stack.get("credentials_mode")})
            start = stack.get("start") or {}
            add("stack_was_created_from_the_reviewed_definition",
                start.get("returncode") == 0
                and stack.get("compose_path", "") in (cluster.get("config_files") or ""),
                {"start_returncode": start.get("returncode"), "start_error": start.get("error"),
                 "compose_path": stack.get("compose_path"),
                 "container_config_files": cluster.get("config_files")})
    if not (cluster.get("present") and cluster.get("running")):
        add("custody_absent_as_declared", wants_creation or not declared_custody.get("database_present"),
            {"declared_database_present": declared_custody.get("database_present"), "phase": phase})
        return assertions

    if creation_expected:
        add("created_database_is_present", custody.get("database_present"),
            {"observed": custody.get("database_present")})
        add("created_role_is_present", custody.get("role_present"),
            {"observed": custody.get("role_present")})
    else:
        add("custody_database_presence_matches_declaration",
            bool(custody.get("database_present")) == bool(declared_custody.get("database_present")),
            {"observed": custody.get("database_present"), "declared": declared_custody.get("database_present")})
        add("custody_role_presence_matches_declaration",
            bool(custody.get("role_present")) == bool(declared_custody.get("database_role_present")),
            {"observed": custody.get("role_present"), "declared": declared_custody.get("database_role_present")})
    if not custody.get("database_present"):
        return assertions

    if declared_compliance == "compliant" or creation_expected:
        add("application_role_is_least_privilege",
            custody.get("role_present") and custody.get("role_canlogin")
            and not custody.get("role_superuser") and not custody.get("role_createdb")
            and not custody.get("role_createrole"),
            {"superuser": custody.get("role_superuser"), "createdb": custody.get("role_createdb"),
             "createrole": custody.get("role_createrole"), "canlogin": custody.get("role_canlogin")})
        add("application_role_owns_its_database",
            custody.get("database_owner") == duty["database_role"],
            {"observed": custody.get("database_owner"), "declared": duty["database_role"]})
        add("public_cannot_connect",
            custody.get("public_connects") is False,
            {"public_connects": custody.get("public_connects")})
        add("application_role_can_connect",
            custody.get("database_role_connects") is True,
            {"database_role_connects": custody.get("database_role_connects")})
    else:
        # A declared gap must still be a *real* gap, otherwise the declaration
        # is stale and the plan would report a closed gap as open.
        add("declared_gap_is_still_open",
            bool(custody.get("role_superuser") or custody.get("role_createdb")),
            {"superuser": custody.get("role_superuser"), "createdb": custody.get("role_createdb"),
             "reason": declared_custody.get("gap_reason", "")})
    add("database_accepts_the_declared_duty",
        custody.get("allow_connections") is True,
        {"allow_connections": custody.get("allow_connections")})
    return assertions


def deployment_binding(declaration, frontend_build):
    """Judge the deployed frontend build environment against the declaration.

    ``VITE_PLATFORM_ADMIN_DB`` is baked into the served bundle at build time,
    so this is one fact about the whole deployment rather than a property of a
    single duty: every duty on this host is served by the same bundle. Keeping
    it out of the per-duty custody verdict also keeps one receipt honest -- a
    duty that was created exactly as declared must not be reported as a failed
    creation because an explicitly sequenced binding switch is still pending.
    """
    fact = frontend_build or {}
    declared = declaration.get("platform_admin_database")
    observed = fact.get("platform_admin_db")
    return {
        "id": "frontend_build_env_names_the_declared_platform_admin_database",
        "passed": bool(fact.get("present")) and not fact.get("error"),
        "detail": {
            "path": fact.get("path") or declaration.get("frontend_build_env_file"),
            "observed": observed,
            "declared": declared,
            "error": fact.get("error") or "",
        },
    }


def plan_verdict(declaration, selected, observations, *, phase="plan"):
    failures = validate_declaration(declaration)
    rows = []
    for duty in selected:
        observation = observations.get(duty["duty"]) or {}
        assertions = evaluate(duty, observation, declaration, phase=phase)
        rows.append({
            "duty": duty["duty"],
            "database": duty["database"],
            "database_role": duty["database_role"],
            "dbfilter": duty["dbfilter"],
            "declared_custody": duty["custody"].get("role_compliance"),
            "assertions": assertions,
            "passed": all(row["passed"] for row in assertions),
        })
    return failures, rows


def plan_payload(declaration, selected, rows, failures, remote_head, binding):
    return {
        "schema": "daily.runtime.database_duty.plan.v1",
        "declaration_sha256": declaration_digest(declaration),
        "remote_head": remote_head or "",
        "declaration_failures": failures,
        "deployment_binding": binding,
        "duties": [
            {"duty": row["duty"], "database": row["database"],
             "database_role": row["database_role"], "dbfilter": row["dbfilter"],
             "declared_custody": row["declared_custody"],
             "failed_assertions": [a["id"] for a in row["assertions"] if not a["passed"]]}
            for row in rows
        ],
        "selected": [duty["duty"] for duty in selected],
    }


def payload_digest(payload):
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--declaration", default=DEFAULT_DECLARATION)
    parser.add_argument("--duty", action="append", default=[], help="repeatable; default all")
    parser.add_argument("--expected-sha", default="")
    parser.add_argument("--phase", choices=PHASES, default="plan")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--expect-declaration-digest", default="")
    parser.add_argument("--report", required=True)
    options = parser.parse_args(argv)

    try:
        if not SSH_HOST.fullmatch(options.ssh_host or ""):
            raise DutyError("SSH host must be a configured host alias")
        if options.expected_sha and not FULL_SHA.fullmatch(options.expected_sha):
            raise DutyError("expected SHA must be a full lowercase commit identity")
        declaration = load_declaration(options.declaration)
        selected = declared_duties(declaration, options.duty)
        if options.apply:
            import os
            confirmation = os.environ.get(CONFIRM_ENV, "").strip()
            if confirmation != CONFIRMATION:
                raise DutyError("DAILY_DUTY_CONFIRMATION_REQUIRED:%s" % (CONFIRM_ENV,))
            if not options.expect_declaration_digest:
                raise DutyError("DAILY_DUTY_REVIEWED_DECLARATION_DIGEST_REQUIRED")
            if options.expect_declaration_digest != declaration_digest(declaration):
                raise DutyError("DAILY_DUTY_DECLARATION_DIGEST_MISMATCH")
        product_roots = sorted({duty["stack"]["product_root"] for duty in selected})
        compose_files = sorted({duty["stack"]["compose_file"] for duty in selected})
        env_templates = sorted({duty["stack"]["env_template"] for duty in selected})
        if len(product_roots) != 1 or len(compose_files) != 1 or len(env_templates) != 1:
            raise DutyError(
                "DAILY_DUTY_STACK_NOT_SHARED: one invocation runs one duty stack definition"
            )
        product_root = product_roots[0]
        compose_path = ROOT / compose_files[0]
        env_template_path = ROOT / env_templates[0]
        for path in (compose_path, env_template_path):
            if not path.is_file():
                raise DutyError("DAILY_DUTY_STACK_FILE_MISSING:%s" % (path,))
        compose_text = compose_path.read_text(encoding="utf-8")
        env_template_text = env_template_path.read_text(encoding="utf-8")
        surface_failures, unused_env_keys = validate_stack_surface(compose_text, env_template_text)
        if surface_failures:
            raise DutyError("DAILY_DUTY_STACK_SURFACE:%s" % ("; ".join(surface_failures),))
        head = ssh(options.ssh_host, "cd %s && git rev-parse HEAD" % (product_root,))
        if head.returncode:
            raise DutyError("remote revision read failed: %s" % (decode(head)[:300],))
        remote_head = head.stdout.decode().strip()
        if not FULL_SHA.fullmatch(remote_head or ""):
            raise DutyError("remote HEAD is not a commit identity: %s" % (remote_head or "<unknown>",))
        if options.expected_sha and remote_head != options.expected_sha:
            raise DutyError(
                "remote HEAD %s != expected %s" % (remote_head or "<unknown>", options.expected_sha)
            )
        payload = {
            "mode": "apply" if options.apply else "plan",
            "phase": options.phase if options.apply else "plan",
            "product_root": product_root,
            "ops_root": declaration["ops_root"],
            "platform_admin_database": declaration["platform_admin_database"],
            "frontend_build_env_file": declaration["frontend_build_env_file"],
            "source_revision": remote_head,
            "compose_sha256": hashlib.sha256(compose_text.encode("utf-8")).hexdigest(),
            "stack": {"compose_text": compose_text},
            "env_template": env_template_text,
            "data_destination": POSTGRES_DATA_DESTINATION,
            "duties": selected,
        }
        result = remote_duties(options.ssh_host, payload)
        observations = {row["duty"]: row for row in result.get("duties") or []}
        failures, rows = plan_verdict(
            declaration, selected, observations, phase="apply" if options.apply else "plan"
        )
    except DutyError as error:
        print("[daily.runtime.database.duty] BLOCKED %s" % (error,), file=sys.stderr)
        return 2

    binding = deployment_binding(declaration, result.get("frontend_build") or {})
    summary = plan_payload(declaration, selected, rows, failures, remote_head, binding)
    # One name, one value: the digest an ``--apply`` must echo is the digest of
    # the reviewed declaration, and the plan's own digest is reported separately.
    # Printing a plan digest under the declaration's name would send an operator
    # to a mismatch on the one field that guards an unreviewed edit.
    summary["plan_sha256"] = payload_digest(summary)
    report = {
        "schema": "daily.runtime.database_duty.v1",
        "expected_sha": options.expected_sha,
        "remote_head": remote_head,
        "ssh_host": options.ssh_host,
        "declaration": options.declaration,
        "declaration_digest": summary["declaration_sha256"],
        "plan_digest": summary["plan_sha256"],
        "stack": {
            "compose_file": compose_files[0],
            "compose_sha256": payload["compose_sha256"],
            "env_template": env_templates[0],
            "unused_env_keys": unused_env_keys,
            "ops_root": payload["ops_root"],
        },
        "platform_admin_database": payload["platform_admin_database"],
        "frontend_build_env_file": payload["frontend_build_env_file"],
        "frontend_build": result.get("frontend_build") or {},
        "deployment_binding": binding,
        "phase": payload["phase"],
        "applied": bool(options.apply),
        "writes": bool(options.apply),
        "provenance": {
            "live_account_query": [
                "docker inspect: compose project, mounts and running state of each declared cluster container",
                "cluster catalog through the declared cluster container: system_identifier, database owner, ALLOW_CONNECTIONS, role attributes, CONNECT privileges",
            ],
            "read_scope": "container metadata and the cluster catalog only; no business row is read",
        },
        "observation": result,
        "plan": summary,
    }
    status = (
        "PASS"
        if not failures and all(row["passed"] for row in rows) and binding["passed"]
        else "FAIL"
    )
    report["status"] = status
    report_path = Path(options.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print(json.dumps({
        "schema": report["schema"],
        "status": status,
        "phase": payload["phase"],
        "applied": bool(options.apply),
        "remote_head": remote_head,
        "declaration_digest": summary["declaration_sha256"],
        "plan_digest": summary["plan_sha256"],
        "compose_sha256": payload["compose_sha256"],
        "platform_admin_database": payload["platform_admin_database"],
        "deployment_binding": binding,
        "report": str(report_path),
        "duties": [
            {"duty": row["duty"], "passed": row["passed"],
             "failed_assertions": [a["id"] for a in row["assertions"] if not a["passed"]]}
            for row in rows
        ],
        "declaration_failures": failures,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
