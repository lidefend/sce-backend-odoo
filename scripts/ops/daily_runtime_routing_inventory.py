#!/usr/bin/env python3
"""Read-only routing and cluster-ownership inventory for one governed host.

The database architecture policy (``docs/governance/database_architecture_policy.md``
sections 6 and 7) makes a tenant environment a whole lifecycle unit
(``DATABASE + DATABASE_ROLE + FILESTORE + SESSIONS + ... + DOMAIN_OR_ROUTE``) and
requires every Odoo instance to carry an exact database constraint
(``ODOO_DB=<exact_database>``, ``ODOO_DBFILTER=^<exact_database>$``,
``LIST_DB=false``). "Only changing the port or the container name cannot prove
environment isolation."

The identity inventory answers the cluster question and the tenant topology
inventory answers the tenant question. Neither answers the routing question:
*which running Odoo instance serves which database, with which filter, which
published port and which data volume*, and *how many live postmasters own one
cluster data directory*. A database name is not evidence about its duty, so the
section 11 role binding reads this report before a database task may write.

Two invariants are checked mechanically because a violation is a data-integrity
hazard rather than a style problem:

* one cluster data directory has exactly one live postmaster -- two running
  containers that mount the same PostgreSQL data volume are two writers on one
  cluster;
* one database is served by at most one application instance, with an exact
  filter, on a unique published host port.

It never writes. ``--report`` only writes a local file.
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
REMOTE_TMP = "/tmp/sc-daily-routing-inventory.py"
DEFAULT_DATABASE = ""
MARKER = "DAILY_ROUTING_INVENTORY="
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
CONTAINER_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+$")
POSTGRES_DATA_DESTINATION = "/var/lib/postgresql/data"
#: Cluster maintenance databases exist in every Odoo cluster and are never
#: served by an application instance; they are reported but never counted as
#: an unbound duty.
MAINTENANCE_DATABASES = ("postgres", "template0", "template1")


class InventoryError(RuntimeError):
    pass


PROGRAM_TEMPLATE = '''
import json
import subprocess

MARKER = "DAILY_ROUTING_INVENTORY="
CLUSTER_CONTAINER = __CLUSTER_CONTAINER__
DATABASE = __DATABASE__
DATA_DESTINATION = __DATA_DESTINATION__


def run(command):
    return subprocess.run(command, capture_output=True, text=True, check=False)


running = [row for row in run(["docker", "ps", "--format", "{{.Names}}"]).stdout.split() if row]
inspected = json.loads(run(["docker", "inspect", *running]).stdout or "[]")


def env_map(entry):
    values = {}
    for item in (entry.get("Config") or {}).get("Env") or []:
        if "=" in item:
            key, value = item.split("=", 1)
            values[key] = value
    return values


instances = []
data_volume_owners = {}
for entry in inspected:
    name = str(entry.get("Name") or "").lstrip("/")
    labels = (entry.get("Config") or {}).get("Labels") or {}
    environment = env_map(entry)
    volumes = [
        {
            "type": mount.get("Type") or "",
            "name": mount.get("Name") or "",
            "destination": mount.get("Destination") or "",
        }
        for mount in entry.get("Mounts") or []
    ]
    for volume in volumes:
        if volume["name"] and volume["destination"] == DATA_DESTINATION:
            data_volume_owners.setdefault(volume["name"], []).append(name)
    database = environment.get("ODOO_DB") or environment.get("DB_NAME") or ""
    dbfilter = environment.get("ODOO_DBFILTER") or ""
    if not (database or dbfilter):
        continue
    ports = []
    seen_bindings = set()
    for container_port, bindings in (
        (entry.get("NetworkSettings") or {}).get("Ports") or {}
    ).items():
        for binding in bindings or []:
            host_port = str(binding.get("HostPort") or "")
            if not host_port or (container_port, host_port) in seen_bindings:
                # Docker lists one binding per address family; the same
                # container port published on the same host port is one fact.
                continue
            seen_bindings.add((container_port, host_port))
            ports.append(
                {"container_port": container_port, "host_port": host_port}
            )
    instances.append(
        {
            "container": name,
            "project": labels.get("com.docker.compose.project") or "",
            "service": labels.get("com.docker.compose.service") or "",
            "image": (entry.get("Config") or {}).get("Image") or "",
            "database": database,
            "dbfilter": dbfilter,
            "list_db_env": environment.get("ODOO_LIST_DB") or "",
            "host_ports": ports,
            "volumes": volumes,
        }
    )

cluster_databases = []
cluster_error = ""
probe = run(
    [
        "docker",
        "exec",
        CLUSTER_CONTAINER,
        "psql",
        "-U",
        "odoo",
        "-d",
        "postgres",
        "-Atc",
        "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname",
    ]
)
if probe.returncode:
    cluster_error = (probe.stderr or probe.stdout or "").strip()[:400]
else:
    cluster_databases = [row for row in probe.stdout.split() if row]

system_identifier = ""
identity_probe = run(
    [
        "docker",
        "exec",
        CLUSTER_CONTAINER,
        "psql",
        "-U",
        "odoo",
        "-d",
        "postgres",
        "-Atc",
        "SELECT system_identifier FROM pg_control_system()",
    ]
)
if not identity_probe.returncode:
    system_identifier = identity_probe.stdout.strip()

payload = {
    "cluster_container": CLUSTER_CONTAINER,
    "cluster_database": DATABASE,
    "cluster_databases": cluster_databases,
    "cluster_error": cluster_error,
    "cluster_system_identifier": system_identifier,
    "postgres_data_volume_owners": data_volume_owners,
    "instances": instances,
    "running_containers": sorted(running),
    "data_destination": DATA_DESTINATION,
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


def inventory(expected_sha, database, ssh_host, cluster_container):
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise InventoryError("expected SHA must be a full lowercase commit identity")
    if not DATABASE_NAME.fullmatch(database or ""):
        raise InventoryError("database must be a plain database name")
    if not CONTAINER_NAME.fullmatch(cluster_container or ""):
        raise InventoryError("cluster container must be a container name")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise InventoryError("SSH host must be a configured host alias")
    if not (ROOT / ".git").exists():
        raise InventoryError("must run from the governed repository")

    head = ssh(ssh_host, "cd /opt/projects/repos/sce-product-odoo && git rev-parse HEAD")
    if head.returncode:
        raise InventoryError(f"remote revision read failed: {decode(head)[:400]}")
    remote_head = head.stdout.decode().strip()
    if remote_head != expected_sha:
        raise InventoryError(
            f"remote HEAD {remote_head or '<unknown>'} != expected {expected_sha}"
        )

    program = (
        PROGRAM_TEMPLATE
        .replace("__CLUSTER_CONTAINER__", json.dumps(cluster_container))
        .replace("__DATABASE__", json.dumps(database))
        .replace("__DATA_DESTINATION__", json.dumps(POSTGRES_DATA_DESTINATION))
        .encode("utf-8")
    )
    upload = ssh(ssh_host, f"cat > {shlex.quote(REMOTE_TMP)}", input_bytes=program)
    if upload.returncode:
        raise InventoryError(f"remote program upload failed: {decode(upload)[:400]}")
    executed = ssh(
        ssh_host,
        f"python3 {shlex.quote(REMOTE_TMP)}; rc=$?; rm -f {shlex.quote(REMOTE_TMP)}; exit $rc",
    )
    if executed.returncode:
        raise InventoryError(f"remote inventory failed: {decode(executed)[:800]}")
    payload = marker_payload(decode(executed))
    if payload is None:
        raise InventoryError(f"no readback payload: {decode(executed)[-800:]}")
    return payload, remote_head


def _exact_filter(instance):
    expected = f"^{instance.get('database') or ''}$"
    return instance.get("dbfilter") == expected


def retired_container_names(declaration_path):
    """Read the retired-stack declaration the routing guard refuses on.

    A retired stack that is running again is a second writer on a shared data
    volume, so the routing verdict must be able to refuse on it. The declaration
    is the single source of the retired identities; this tool never restates
    them.
    """
    if declaration_path is None:
        return []
    path = Path(declaration_path)
    if not path.exists():
        raise InventoryError(f"retired-stack declaration missing: {path}")
    try:
        declaration = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise InventoryError(f"retired-stack declaration is not valid JSON: {error}")
    if declaration.get("schema") != "daily.runtime.retired_stacks.v1":
        raise InventoryError("unexpected retired-stack declaration schema")
    names = []
    for stack in declaration.get("stacks") or []:
        for container in stack.get("containers") or []:
            if container.get("name"):
                names.append(container["name"])
    return sorted(set(names))


def evaluate(database, payload, retired=()):
    instances = payload.get("instances") or []
    cluster_databases = payload.get("cluster_databases") or []
    volume_owners = payload.get("postgres_data_volume_owners") or {}

    missing_filter = [
        row.get("container") for row in instances if not row.get("database")
    ]
    bad_filter = [
        row.get("container")
        for row in instances
        if row.get("dbfilter") and not _exact_filter(row)
    ]
    # A *serving* instance is one that publishes a host port. A database stack
    # legitimately passes its ODOO_DB/ODOO_DBFILTER environment to its database
    # and ingress containers as well, so membership in the routing environment
    # alone must not be read as "this container serves the database".
    served = {}
    for row in instances:
        if not row.get("host_ports"):
            continue
        served.setdefault(row.get("database") or "", []).append(row.get("container"))
    duplicated = sorted(
        name for name, owners in served.items() if name and len(owners) > 1
    )
    port_owners = {}
    for row in instances:
        for host_port in sorted(
            {port.get("host_port") for port in row.get("host_ports") or [] if port.get("host_port")}
        ):
            port_owners.setdefault(host_port, []).append(row.get("container"))
    duplicated_ports = sorted(
        port for port, owners in port_owners.items() if len(owners) > 1
    )
    shared_data_volumes = sorted(
        name for name, owners in volume_owners.items() if len(owners) > 1
    )
    running_names = set(payload.get("running_containers") or [])
    running_retired = sorted(name for name in retired if name in running_names)
    data_volume_reuse = {}
    for row in instances:
        for volume in row.get("volumes") or []:
            if volume.get("name") and volume.get("destination") == "/var/lib/odoo":
                data_volume_reuse.setdefault(volume["name"], []).append(row.get("container"))
    shared_instance_volumes = sorted(
        name for name, owners in data_volume_reuse.items() if len(owners) > 1
    )

    assertions = [
        {
            "id": "cluster_databases_observed",
            "passed": bool(cluster_databases) and not payload.get("cluster_error"),
            "detail": {
                "cluster_container": payload.get("cluster_container"),
                "databases": cluster_databases,
                "error": payload.get("cluster_error") or "",
            },
        },
        {
            "id": "application_instance_declares_a_database",
            "passed": not missing_filter,
            "detail": missing_filter,
        },
        {
            "id": "application_instance_filter_is_exact",
            "passed": not bad_filter,
            "detail": bad_filter,
        },
        {
            "id": "single_serving_instance_per_database",
            "passed": not duplicated,
            "detail": {name: served[name] for name in duplicated},
        },
        {
            "id": "published_host_port_unique",
            "passed": not duplicated_ports,
            "detail": {port: port_owners[port] for port in duplicated_ports},
        },
        {
            "id": "one_live_postmaster_per_cluster_data_volume",
            "passed": not shared_data_volumes,
            "detail": {name: volume_owners[name] for name in shared_data_volumes},
        },
        {
            "id": "instance_data_volume_distinct",
            "passed": not shared_instance_volumes,
            "detail": {name: data_volume_reuse[name] for name in shared_instance_volumes},
        },
        {
            "id": "retired_stack_is_not_running",
            "passed": not running_retired,
            "detail": {
                "declared_retired": sorted(set(retired)),
                "running_retired": running_retired,
            },
        },
        {
            "id": "inventory_is_read_only",
            "passed": payload.get("writes") is False,
            "detail": f"writes={payload.get('writes')}",
        },
    ]
    served_databases = sorted(name for name in served if name)
    declared_databases = sorted({row.get("database") for row in instances if row.get("database")})
    unserved = sorted(
        name
        for name in set(cluster_databases) - set(served_databases)
        if name and name not in MAINTENANCE_DATABASES
    )
    return {
        "assertions": assertions,
        "passed": all(row["passed"] for row in assertions),
        "instance_count": len(instances),
        "cluster_databases": cluster_databases,
        "declared_databases": declared_databases,
        "served_databases": served_databases,
        "unserved_databases": unserved,
        "cluster_system_identifier": payload.get("cluster_system_identifier") or "",
        "duty_gap": {
            "databases_without_serving_instance": unserved,
            "instances_without_exact_filter": bad_filter,
        },
    }




def resolve_cluster_container(explicit: str, binding: dict) -> str:
    """Return the cluster container whose catalog this entry reads.

    The cluster belongs to the *bound duty*: the rebuilt demo carrier runs its own
    cluster, so a remembered container name would silently inventory a different
    carrier. An explicit value stays available only for a deliberate cross-carrier
    audit, and the report records which of the two was used.
    """
    return explicit or binding["database_container"]


def bind_target(options, *, instances_reader=None) -> dict:
    """Bind the target duty, its cluster, its database and its storage, or stop.

    A routing fact about the wrong carrier is a wrong fact: which database a face serves only means something once the carrier is named.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--duty", default="", help="the declared duty this entry binds; a database name alone is not a target identity")
    parser.add_argument("--ssh-host", required=True)
    # The cluster this entry reads the catalog from is the *bound duty's* cluster,
    # never a remembered container name: the daily demo carrier now runs its own
    # cluster, and a hard-coded legacy name would silently inventory the historic
    # source instead. An explicit value stays available for a cross-carrier audit.
    parser.add_argument("--cluster-container", default="", help="container whose cluster catalog is read; defaults to the bound duty's cluster")
    parser.add_argument("--retired-stacks", default="")
    parser.add_argument("--report", required=True)
    options = parser.parse_args()

    try:
        binding = bind_target(options)
        retired = retired_container_names(options.retired_stacks or None)
        cluster_container = resolve_cluster_container(
            options.cluster_container, binding,
        )
        payload, remote_head = inventory(
            options.expected_sha, binding["database"], options.ssh_host,
            cluster_container,
        )
        verdict = evaluate(binding["database"], payload, retired=retired)
    except InventoryError as error:
        print(f"[daily.runtime.routing.inventory] BLOCKED {error}", file=sys.stderr)
        return 2

    report = {
        "schema": "daily.runtime.routing.inventory.v1",
        "expected_sha": options.expected_sha,
        "remote_head": remote_head,
        "ssh_host": options.ssh_host,
        "database_binding": binding,
        "cluster_container": cluster_container,
        "cluster_container_source": (
            "argument" if options.cluster_container else "bound_duty"
        ),
        "cluster_database": binding["database"],
        "retired_stacks_declaration": options.retired_stacks,
        "writes": False,
        "provenance": {
            "live_account_query": [
                "running container names",
                "docker inspect: compose project/service, image, environment, mounts, published ports",
                "cluster catalog through the declared cluster db container",
            ],
            "read_scope": "container metadata and the cluster catalog only; no business row is read",
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
        "schema": report["schema"],
        "status": report["status"],
        "expected_sha": report["expected_sha"],
        "remote_head": report["remote_head"],
        "report": str(report_path),
        "instance_count": verdict["instance_count"],
        "cluster_databases": verdict["cluster_databases"],
        "unserved_databases": verdict["unserved_databases"],
        "cluster_system_identifier": verdict["cluster_system_identifier"],
        "failed_assertions": [r["id"] for r in verdict["assertions"] if not r["passed"]],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
