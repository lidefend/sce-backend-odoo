#!/usr/bin/env python3
"""Activate a verified production restore as a persistent, no-egress clone."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


RESTORE_ID = re.compile(r"^sc_restore_[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
IMAGE = re.compile(r"^sha256:[0-9a-f]{64}$")
MODULE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
RELEASE_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
CONFIRMATION = "ACTIVATE_ISOLATED_PRODUCTION_ACCEPTANCE_CLONE"
PUBLIC_CONFIRMATION = "PUBLISH_ISOLATED_ACCEPTANCE_FRONTEND_TO_APPROVED_PORT"
PLATFORM_SNAPSHOT_CONFIRMATION = "I_ACKNOWLEDGE_COLOCATED_PLATFORM_SNAPSHOT_INITIALIZATION"
PLATFORM_PRODUCT_KEY = "construction.standard"
MODULE_SET_PATH = Path(__file__).resolve().parents[2] / "config/tenant/module_sets.v1.json"


class CloneRuntimeError(RuntimeError):
    pass


def product_modules() -> tuple[str, ...]:
    try:
        payload = json.loads(MODULE_SET_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CloneRuntimeError("authoritative product module set is unavailable") from exc
    modules = payload.get("product_modules")
    if not isinstance(modules, list) or not modules or not all(
        isinstance(name, str) and MODULE.fullmatch(name) for name in modules
    ):
        raise CloneRuntimeError("authoritative product module set is invalid")
    if len(modules) != len(set(modules)):
        raise CloneRuntimeError("authoritative product module set contains duplicates")
    return tuple(modules)


def run(args: list[str], check: bool = True) -> str:
    completed = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if check and completed.returncode:
        detail = completed.stderr.strip().splitlines() or ["command failed"]
        raise CloneRuntimeError(detail[-1][:300])
    return completed.stdout.strip()


def validate_identity(restore_id: str, tenant_sha: str, tenant_module: str, image: str, port: int) -> None:
    if not RESTORE_ID.fullmatch(restore_id) or not SHA.fullmatch(tenant_sha):
        raise CloneRuntimeError("invalid immutable clone identity")
    if not MODULE.fullmatch(tenant_module):
        raise CloneRuntimeError("invalid tenant module identity")
    if not IMAGE.fullmatch(image) or not (port == 18081 or 18095 <= port <= 18120):
        raise CloneRuntimeError("invalid immutable image or loopback port")


def database_snapshot(db_container: str, database: str) -> dict[str, int]:
    output = run(
        [
            "docker",
            "exec",
            db_container,
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "odoo",
            "-d",
            database,
            "-At",
            "-F",
            "|",
            "-c",
            "SELECT (SELECT count(*) FROM res_users),"
            "(SELECT count(*) FROM project_project),"
            "(SELECT count(*) FROM ir_attachment);",
        ]
    )
    try:
        users, projects, attachments = (int(value) for value in output.split("|"))
    except (TypeError, ValueError) as exc:
        raise CloneRuntimeError("acceptance data snapshot is invalid") from exc
    return {"res_users": users, "project_project": projects, "ir_attachment": attachments}


def module_state(db_container: str, database: str, modules: tuple[str, ...]) -> dict[str, int]:
    names = ",".join(modules)
    output = run(
        [
            "docker",
            "exec",
            db_container,
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "odoo",
            "-d",
            database,
            "-At",
            "-F",
            "|",
            "-c",
            "SELECT (SELECT count(*) FROM ir_module_module "
            f"WHERE name = ANY(string_to_array('{names}', ',')) AND state='installed'),"
            "(SELECT count(*) FROM ir_module_module "
            "WHERE state IN ('to install','to upgrade','to remove'));",
        ]
    )
    try:
        installed, pending = (int(value) for value in output.split("|"))
    except (TypeError, ValueError) as exc:
        raise CloneRuntimeError("acceptance module state is invalid") from exc
    return {"installed": installed, "pending": pending}


def rebind_platform_release_database(db_container: str, database: str) -> bool:
    """Bind a renamed isolated restore to its own release snapshot authority."""
    if not re.fullmatch(r"r10e_sc_restore_[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}", database):
        raise CloneRuntimeError("acceptance platform database identity is invalid")
    output = run(
        [
            "docker",
            "exec",
            db_container,
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-v",
            f"target_db={database}",
            "-U",
            "odoo",
            "-d",
            database,
            "-At",
            "-F",
            "|",
            "-c",
            "WITH current AS ("
            "SELECT count(*) AS record_count,"
            "coalesce(bool_and(value = :'target_db')::int, 0) AS already_bound "
            "FROM ir_config_parameter WHERE key='smart_core.platform_release_db'"
            "), rebound AS ("
            "UPDATE ir_config_parameter SET value=:'target_db', write_date=now() "
            "WHERE key='smart_core.platform_release_db' AND value <> :'target_db' "
            "RETURNING value"
            ") SELECT current.record_count,current.already_bound,"
            "(SELECT count(*) FROM rebound),"
            "coalesce((SELECT bool_and(value = :'target_db')::int FROM rebound),"
            "current.already_bound) FROM current;",
        ]
    )
    if output not in {"1|0|1|1", "1|1|0|1"}:
        raise CloneRuntimeError("acceptance platform release database was not rebound")
    return output == "1|0|1|1"


def tenant_module_operation(db_container: str, database: str, tenant_module: str) -> str:
    if not MODULE.fullmatch(tenant_module):
        raise CloneRuntimeError("invalid tenant module identity")
    state = run(
        [
            "docker",
            "exec",
            db_container,
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            "odoo",
            "-d",
            database,
            "-At",
            "-c",
            "SELECT state FROM ir_module_module "
            f"WHERE name = '{tenant_module}';",
        ]
    )
    if state == "installed":
        return "upgrade"
    if state in {"", "uninstalled"}:
        return "install"
    raise CloneRuntimeError("tenant module state is not eligible for controlled activation")


def odoo_container_args(
    *,
    name: str,
    network: str,
    filestore: str,
    tenant_root: Path,
    config: Path,
    image: str,
) -> list[str]:
    return [
        "docker",
        "run",
        "--name",
        name,
        "--network",
        network,
        "--label",
        "sc.production-acceptance-clone=true",
        "--group-add",
        "0",
        "-v",
        f"{filestore}:/var/lib/odoo/filestore",
        "-v",
        f"{tenant_root}:/mnt/tenant-addons:ro",
        "-v",
        f"{config}:/etc/odoo/odoo.conf:ro",
        "--entrypoint",
        "odoo",
        image,
        "-c",
        "/etc/odoo/odoo.conf",
    ]


def image_release_version(image: str) -> str:
    version = run(
        [
            "docker",
            "image",
            "inspect",
            image,
            "--format",
            '{{index .Config.Labels "org.opencontainers.image.version"}}',
        ]
    )
    if not RELEASE_VERSION.fullmatch(version):
        raise CloneRuntimeError("immutable image release version is unavailable")
    return version


def platform_snapshot_container_args(
    *,
    name: str,
    network: str,
    filestore: str,
    tenant_root: Path,
    config: Path,
    image: str,
    database: str,
    version: str,
) -> list[str]:
    if not RELEASE_VERSION.fullmatch(version):
        raise CloneRuntimeError("invalid platform snapshot release version")
    args = odoo_container_args(
        name=name,
        network=network,
        filestore=filestore,
        tenant_root=tenant_root,
        config=config,
        image=image,
    )
    args.insert(2, "--rm")
    entrypoint_index = args.index("--entrypoint")
    args[entrypoint_index + 1] = "/bin/sh"
    image_index = args.index(image)
    args[image_index:image_index] = [
        "-e",
        f"SC_COLOCATED_PLATFORM_SNAPSHOT_APPLY={PLATFORM_SNAPSHOT_CONFIRMATION}",
        "-e",
        f"PLATFORM_RELEASE_DB={database}",
        "-e",
        f"PLATFORM_RELEASE_PRODUCT_KEY={PLATFORM_PRODUCT_KEY}",
        "-e",
        f"PLATFORM_RELEASE_VERSION={version}",
    ]
    image_index = args.index(image)
    del args[image_index + 1 :]
    args.extend(
        [
            "-eu",
            "-c",
            "odoo shell -c /etc/odoo/odoo.conf -d \"$PLATFORM_RELEASE_DB\" --no-http "
            "< /usr/local/share/sce/initialize_colocated_platform_snapshot.py",
        ]
    )
    return args


def url_ready(url: str, expected: str = "") -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status == 200 and (not expected or expected in body)
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        return False


def container_endpoint(
    container: str,
    container_port: int,
    path: str,
    *,
    loopback_port: int | None = None,
    expected: str = "",
) -> tuple[str, bool]:
    if loopback_port is not None:
        loopback = f"http://127.0.0.1:{loopback_port}{path}"
        if url_ready(loopback, expected):
            return loopback, True
    address = run(
        [
            "docker",
            "inspect",
            container,
            "--format",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
        ],
        False,
    )
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return "", False
    if not parsed.is_private:
        return "", False
    internal = f"http://{address}:{container_port}{path}"
    return (internal, False) if url_ready(internal, expected) else ("", False)


def remove_verified_failed_upgrade(restore_id: str, network: str) -> bool:
    """Remove only a stopped upgrade container inside the locked restore network."""
    container = f"{restore_id}_acceptance_upgrade"
    observed = run(
        [
            "docker",
            "inspect",
            container,
            "--format",
            '{{.State.Status}}|{{.State.Running}}|{{.HostConfig.NetworkMode}}|'
            '{{index .Config.Labels "sc.production-acceptance-clone"}}',
        ],
        False,
    )
    if not observed:
        return False
    try:
        status, running, observed_network, label = observed.split("|", 3)
    except ValueError as exc:
        raise CloneRuntimeError("stale acceptance upgrade identity is invalid") from exc
    if running != "false" or status not in {"exited", "dead"}:
        raise CloneRuntimeError("stale acceptance upgrade is not safely stopped")
    # Empty label admits upgrade containers created by the governed tool before
    # the label was introduced. The exact isolated network remains mandatory.
    if observed_network != network or label not in {"", "true"}:
        raise CloneRuntimeError("stale acceptance upgrade identity differs")
    run(["docker", "rm", container])
    return True


def ensure_retryable_runtime_root(runtime_root: Path) -> None:
    """Create or admit only the incomplete runtime directory produced by this tool."""
    if runtime_root.is_symlink():
        raise CloneRuntimeError("acceptance runtime root must not be a symlink")
    if not runtime_root.exists():
        runtime_root.mkdir(mode=0o700, parents=True)
        return
    if not runtime_root.is_dir():
        raise CloneRuntimeError("acceptance runtime root is not a directory")
    entries = {entry.name: entry for entry in runtime_root.iterdir()}
    if set(entries) - {"odoo.conf"}:
        raise CloneRuntimeError("acceptance runtime root contains unmanaged files")
    config = entries.get("odoo.conf")
    if config is not None and (config.is_symlink() or not config.is_file()):
        raise CloneRuntimeError("acceptance runtime config is unsafe")
    runtime_root.chmod(0o700)


def start_frontend(
    *,
    web_container: str,
    network: str,
    image: str,
    database: str,
    host: str,
    port: int,
    ingress_network: str = "",
) -> None:
    action = "create" if ingress_network else "run"
    primary_network = ingress_network or network
    run(
        [
            "docker",
            action,
            *([] if ingress_network else ["-d"]),
            "--name",
            web_container,
            "--network",
            primary_network,
            "--user",
            "root",
            "--publish",
            f"{host}:{port}:80",
            "--label",
            "sc.production-acceptance-clone=true",
            "-e",
            f"ODOO_DB={database}",
            "--entrypoint",
            "/usr/local/bin/render_nginx_conf.sh",
            image,
        ]
    )
    if ingress_network:
        run(["docker", "network", "connect", network, web_container])
        run(["docker", "start", web_container])


def ensure_public_ingress_network(restore_id: str) -> str:
    network = f"{restore_id}_public_ingress"
    observed = run(
        [
            "docker",
            "network",
            "inspect",
            network,
            "--format",
            '{{.Internal}}|{{index .Options "com.docker.network.bridge.enable_ip_masquerade"}}|'
            '{{index .Labels "sc.production-acceptance-clone"}}',
        ],
        False,
    )
    if observed:
        if observed != "false|false|true":
            raise CloneRuntimeError("public ingress network identity differs")
        return network
    run(
        [
            "docker",
            "network",
            "create",
            "--driver",
            "bridge",
            "--opt",
            "com.docker.network.bridge.enable_ip_masquerade=false",
            "--label",
            "sc.production-acceptance-clone=true",
            network,
        ]
    )
    return network


def wait_frontend(web_container: str, database: str, port: int) -> tuple[str, bool]:
    for _ in range(60):
        state = run(
            ["docker", "inspect", web_container, "--format", "{{.State.Running}}|{{.State.ExitCode}}"],
            False,
        )
        endpoint, loopback_bound = container_endpoint(
            web_container,
            80,
            "/runtime-config.js",
            loopback_port=port,
            expected=database,
        )
        if state.startswith("true|") and endpoint:
            return endpoint.removesuffix("/runtime-config.js"), loopback_bound
        if state and not state.startswith("true|"):
            raise CloneRuntimeError("acceptance frontend exited before readiness")
        time.sleep(1)
    raise CloneRuntimeError("acceptance frontend did not become ready")


def remove_verified_runtime(restore_id: str, network: str) -> bool:
    backend = f"{restore_id}_acceptance_odoo"
    frontend = f"{restore_id}_acceptance_web"
    backend_identity = run(
        [
            "docker",
            "inspect",
            backend,
            "--format",
            '{{index .Config.Labels "sc.production-acceptance-clone"}}|{{.HostConfig.NetworkMode}}',
        ],
        False,
    )
    if not backend_identity:
        return False
    if backend_identity != f"true|{network}":
        raise CloneRuntimeError("existing acceptance backend identity differs")
    frontend_identity = run(
        [
            "docker",
            "inspect",
            frontend,
            "--format",
            '{{index .Config.Labels "sc.production-acceptance-clone"}}|{{.HostConfig.NetworkMode}}',
        ],
        False,
    )
    allowed_frontend_networks = {network, f"{restore_id}_public_ingress"}
    if frontend_identity:
        label, separator, frontend_network = frontend_identity.partition("|")
        if label != "true" or not separator or frontend_network not in allowed_frontend_networks:
            raise CloneRuntimeError("existing acceptance frontend identity differs")
        run(["docker", "rm", "-f", frontend])
    run(["docker", "rm", "-f", backend])
    return True


def activate(
    restore_id: str,
    tenant_sha: str,
    tenant_module: str,
    image: str,
    port: int,
    *,
    replace_existing: bool = False,
) -> dict[str, object]:
    if os.environ.get("CONFIRM_PRODUCTION_ACCEPTANCE_CLONE_RUNTIME") != CONFIRMATION:
        raise CloneRuntimeError("exact acceptance clone activation confirmation is required")
    validate_identity(restore_id, tenant_sha, tenant_module, image, port)

    report_path = Path(f"/data/backups/sc_production/restore-rehearsals/{restore_id}.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS" or report.get("production_database_connected") is not False:
        raise CloneRuntimeError("verified isolated restore report is required")
    resources = report.get("resources") or {}
    db_container, network, filestore = (
        resources.get(key) for key in ("db_container", "network", "filestore_volume")
    )
    if any(not str(value).startswith(restore_id) for value in (db_container, network, filestore)):
        raise CloneRuntimeError("restore resources escaped the isolated namespace")

    tenant_root = Path(f"/opt/sce/tenant-addons/acceptance/{tenant_sha}")
    if not (tenant_root / tenant_module / "__manifest__.py").is_file():
        raise CloneRuntimeError("immutable tenant addon is unavailable")

    rows = run(["docker", "inspect", str(db_container), "--format", "{{range .Config.Env}}{{println .}}{{end}}"])
    password = next(
        (row.split("=", 1)[1] for row in rows.splitlines() if row.startswith("POSTGRES_PASSWORD=")),
        "",
    )
    if not password:
        raise CloneRuntimeError("isolated database credential is unavailable")

    database = f"r10e_{restore_id}"
    runtime_root = Path(f"/data/backups/sc_production/acceptance-runtimes/{restore_id}")
    if replace_existing:
        replaced = remove_verified_runtime(restore_id, str(network))
        if not replaced:
            raise CloneRuntimeError("replace requested but verified acceptance runtime is absent")
    else:
        replaced = False
    ensure_retryable_runtime_root(runtime_root)
    config = runtime_root / "odoo.conf"
    config.write_text(
        "[options]\n"
        "addons_path = /mnt/product-addons,/mnt/tenant-addons,/mnt/addons_external/oca_server_ux,/usr/lib/python3/dist-packages/odoo/addons\n"
        f"db_host = {db_container}\n"
        "db_port = 5432\n"
        "db_user = odoo\n"
        f"db_password = {password}\n"
        f"dbfilter = ^{database}$\n"
        "list_db = False\n"
        "workers = 0\n"
        "max_cron_threads = 0\n"
        "data_dir = /var/lib/odoo\n"
        "smtp_server = 127.0.0.1\n",
        encoding="utf-8",
    )
    config.chmod(0o640)
    product_module_set = product_modules()
    modules = (*product_module_set, tenant_module)
    tenant_operation = tenant_module_operation(str(db_container), database, tenant_module)
    before = database_snapshot(str(db_container), database)
    platform_release_db_rebound = rebind_platform_release_database(
        str(db_container), database,
    )
    upgrade_container = f"{restore_id}_acceptance_upgrade"
    remove_verified_failed_upgrade(restore_id, str(network))
    upgrade_args = odoo_container_args(
        name=upgrade_container,
        network=str(network),
        filestore=str(filestore),
        tenant_root=tenant_root,
        config=config,
        image=image,
    )
    module_args = ["-u", ",".join(product_module_set)]
    module_args.extend(
        ["-i" if tenant_operation == "install" else "-u", tenant_module]
    )
    run(
        [
            *upgrade_args[:2],
            *upgrade_args[2:],
            "-d",
            database,
            "--no-http",
            "--workers=0",
            "--max-cron-threads=0",
            "--without-demo=all",
            "--stop-after-init",
            *module_args,
        ]
    )
    release_version = image_release_version(image)
    run(
        platform_snapshot_container_args(
            name=f"{restore_id}_acceptance_snapshot",
            network=str(network),
            filestore=str(filestore),
            tenant_root=tenant_root,
            config=config,
            image=image,
            database=database,
            version=release_version,
        )
    )
    after = database_snapshot(str(db_container), database)
    if after != before:
        raise CloneRuntimeError("acceptance upgrade changed protected business-data counts")
    state = module_state(str(db_container), database, modules)
    if state != {"installed": len(modules), "pending": 0}:
        raise CloneRuntimeError("acceptance module upgrade did not converge")
    run(["docker", "rm", upgrade_container])

    container = f"{restore_id}_acceptance_odoo"
    runtime_args = odoo_container_args(
        name=container,
        network=str(network),
        filestore=str(filestore),
        tenant_root=tenant_root,
        config=config,
        image=image,
    )
    run(
        [
            *runtime_args[:2],
            "-d",
            *runtime_args[2:8],
            "--network-alias",
            "odoo",
            "--label",
            "sc.production-acceptance-clone=true",
            *runtime_args[8:],
            "-d",
            database,
        ]
    )
    for _ in range(120):
        state = run(["docker", "inspect", container, "--format", "{{.State.Running}}|{{.State.ExitCode}}"], False)
        health_url, _unused = container_endpoint(container, 8069, "/web/health")
        if state.startswith("true|") and health_url:
            break
        if state and not state.startswith("true|"):
            raise CloneRuntimeError("acceptance clone exited before HTTP readiness")
        time.sleep(1)
    else:
        raise CloneRuntimeError("acceptance clone did not remain running")

    web_container = f"{restore_id}_acceptance_web"
    start_frontend(
        web_container=web_container,
        network=str(network),
        image=image,
        database=database,
        host="127.0.0.1",
        port=port,
    )
    frontend_url, loopback_bound = wait_frontend(web_container, database, port)
    return {
        "status": "PASS",
        "database": database,
        "container": container,
        "web_container": web_container,
        "loopback_port": port if loopback_bound else None,
        "frontend_url": frontend_url,
        "host_private_health_url": health_url,
        "exact_dbfilter": True,
        "tenant_sha": tenant_sha,
        "tenant_module": tenant_module,
        "tenant_module_operation": tenant_operation,
        "upgraded_modules": list(modules),
        "protected_counts_before": before,
        "protected_counts_after": after,
        "pending_modules": 0,
        "platform_release_product_key": PLATFORM_PRODUCT_KEY,
        "platform_release_version": release_version,
        "platform_release_db_rebound": platform_release_db_rebound,
        "platform_snapshot_refreshed": True,
        "http_health": 200,
        "external_egress": False,
        "replaced_existing_runtime": replaced,
    }


def publish_existing(restore_id: str, image: str, port: int) -> dict[str, object]:
    if os.environ.get("CONFIRM_PRODUCTION_ACCEPTANCE_PUBLIC_FRONTEND") != PUBLIC_CONFIRMATION:
        raise CloneRuntimeError("exact public acceptance frontend confirmation is required")
    if not RESTORE_ID.fullmatch(restore_id) or not IMAGE.fullmatch(image) or port != 18081:
        raise CloneRuntimeError("public acceptance identity must use the approved port")
    report_path = Path(f"/data/backups/sc_production/restore-rehearsals/{restore_id}.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS" or report.get("production_database_connected") is not False:
        raise CloneRuntimeError("verified isolated restore report is required")
    resources = report.get("resources") or {}
    network = str(resources.get("network") or "")
    if not network.startswith(restore_id):
        raise CloneRuntimeError("restore network escaped the isolated namespace")
    database = f"r10e_{restore_id}"
    runtime_root = Path(f"/data/backups/sc_production/acceptance-runtimes/{restore_id}")
    config = runtime_root / "odoo.conf"
    if not config.is_file() or f"dbfilter = ^{database}$" not in config.read_text(encoding="utf-8"):
        raise CloneRuntimeError("exact acceptance database filter is unavailable")
    odoo_container = f"{restore_id}_acceptance_odoo"
    observed = run(
        [
            "docker",
            "inspect",
            odoo_container,
            "--format",
            "{{.State.Running}}|{{index .Config.Labels \"sc.production-acceptance-clone\"}}|{{.HostConfig.NetworkMode}}|{{.Image}}",
        ]
    )
    if observed != f"true|true|{network}|{image}":
        raise CloneRuntimeError("running isolated acceptance backend identity differs")
    ingress_network = ensure_public_ingress_network(restore_id)
    web_container = f"{restore_id}_acceptance_web"
    existing = run(
        [
            "docker",
            "inspect",
            web_container,
            "--format",
            "{{index .Config.Labels \"sc.production-acceptance-clone\"}}|{{.HostConfig.NetworkMode}}",
        ],
        False,
    )
    if existing:
        if existing not in (f"true|{network}", f"true|{ingress_network}"):
            raise CloneRuntimeError("existing acceptance frontend identity differs")
        run(["docker", "rm", "-f", web_container])
    start_frontend(
        web_container=web_container,
        network=network,
        image=image,
        database=database,
        host="0.0.0.0",
        port=port,
        ingress_network=ingress_network,
    )
    frontend_url, loopback_bound = wait_frontend(web_container, database, port)
    if not loopback_bound:
        raise CloneRuntimeError("approved public acceptance port was not bound")
    return {
        "status": "PASS",
        "database": database,
        "public_url": f"http://1.95.85.92:{port}/",
        "frontend_url": frontend_url,
        "exact_dbfilter": True,
        "external_egress": False,
        "production_database_connected": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore-id", required=True)
    parser.add_argument("--tenant-sha", default="")
    parser.add_argument("--tenant-module", default="")
    parser.add_argument("--image", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--publish-existing", action="store_true")
    parser.add_argument("--replace-existing", action="store_true")
    args = parser.parse_args()
    result = (
        publish_existing(args.restore_id, args.image, args.port)
        if args.publish_existing
        else activate(
            args.restore_id,
            args.tenant_sha,
            args.tenant_module,
            args.image,
            args.port,
            replace_existing=args.replace_existing,
        )
    )
    print(
        json.dumps(
            result,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
