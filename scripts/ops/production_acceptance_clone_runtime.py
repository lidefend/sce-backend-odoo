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
CONFIRMATION = "ACTIVATE_ISOLATED_PRODUCTION_ACCEPTANCE_CLONE"
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
    if not IMAGE.fullmatch(image) or not 18095 <= port <= 18120:
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


def url_ready(url: str, expected: str = "") -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status == 200 and (not expected or expected in body)
    except (urllib.error.URLError, TimeoutError):
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


def activate(restore_id: str, tenant_sha: str, tenant_module: str, image: str, port: int) -> dict[str, object]:
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
    runtime_root.mkdir(mode=0o700, parents=True, exist_ok=False)
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
        "smtp_server = 127.0.0.1\n",
        encoding="utf-8",
    )
    config.chmod(0o640)
    modules = (*product_modules(), tenant_module)
    before = database_snapshot(str(db_container), database)
    upgrade_container = f"{restore_id}_acceptance_upgrade"
    upgrade_args = odoo_container_args(
        name=upgrade_container,
        network=str(network),
        filestore=str(filestore),
        tenant_root=tenant_root,
        config=config,
        image=image,
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
            "-u",
            ",".join(modules),
        ]
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
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            web_container,
            "--network",
            str(network),
            "--user",
            "root",
            "--publish",
            f"127.0.0.1:{port}:80",
            "--label",
            "sc.production-acceptance-clone=true",
            "-e",
            f"ODOO_DB={database}",
            "--entrypoint",
            "/usr/local/bin/render_nginx_conf.sh",
            image,
        ]
    )
    frontend_url = ""
    loopback_bound = False
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
            frontend_url = endpoint.removesuffix("/runtime-config.js")
            break
        if state and not state.startswith("true|"):
            raise CloneRuntimeError("acceptance frontend exited before readiness")
        time.sleep(1)
    if not frontend_url:
        raise CloneRuntimeError("acceptance frontend did not become ready")
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
        "upgraded_modules": list(modules),
        "protected_counts_before": before,
        "protected_counts_after": after,
        "pending_modules": 0,
        "http_health": 200,
        "external_egress": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore-id", required=True)
    parser.add_argument("--tenant-sha", required=True)
    parser.add_argument("--tenant-module", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    print(
        json.dumps(
            activate(args.restore_id, args.tenant_sha, args.tenant_module, args.image, args.port),
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
