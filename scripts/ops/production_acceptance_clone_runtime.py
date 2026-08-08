#!/usr/bin/env python3
"""Activate a verified production restore as a persistent, no-egress clone."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import time
from pathlib import Path


RESTORE_ID = re.compile(r"^sc_restore_[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
IMAGE = re.compile(r"^sha256:[0-9a-f]{64}$")
MODULE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
CONFIRMATION = "ACTIVATE_ISOLATED_PRODUCTION_ACCEPTANCE_CLONE"
REFRESH_CONFIRMATION = "REFRESH_ISOLATED_PRODUCTION_ACCEPTANCE_TENANT_RUNTIME"
IMAGE_REFRESH_CONFIRMATION = "REFRESH_ISOLATED_PRODUCTION_ACCEPTANCE_IMAGE_RUNTIME"


class CloneRuntimeError(RuntimeError):
    pass


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


def succeeds(args: list[str]) -> bool:
    return subprocess.run(
        args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    ).returncode == 0


def validate_identity(restore_id: str, tenant_sha: str, tenant_module: str, image: str, port: int) -> None:
    if not RESTORE_ID.fullmatch(restore_id) or not SHA.fullmatch(tenant_sha):
        raise CloneRuntimeError("invalid immutable clone identity")
    if not MODULE.fullmatch(tenant_module):
        raise CloneRuntimeError("invalid tenant module identity")
    if not IMAGE.fullmatch(image) or not 18095 <= port <= 18120:
        raise CloneRuntimeError("invalid immutable image or loopback port")


def ensure_runtime_secret(runtime_root: Path) -> Path:
    secret_file = runtime_root / "runtime.env"
    if secret_file.exists() or secret_file.is_symlink():
        if secret_file.is_symlink() or not secret_file.is_file():
            raise CloneRuntimeError("acceptance runtime secret file is invalid")
        rows = secret_file.read_text(encoding="utf-8").splitlines()
        values = [row.split("=", 1)[1] for row in rows if row.startswith("JWT_SECRET=")]
        if len(values) != 1 or len(values[0]) < 48:
            raise CloneRuntimeError("acceptance JWT secret is invalid")
        return secret_file
    descriptor = os.open(secret_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(f"JWT_SECRET={secrets.token_urlsafe(48)}\n")
    return secret_file


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
        "addons_path = /mnt/product-addons,/mnt/tenant-addons,/usr/lib/python3/dist-packages/odoo/addons\n"
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
    secret_file = ensure_runtime_secret(runtime_root)
    container = f"{restore_id}_acceptance_odoo"
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container,
            "--network",
            str(network),
            "--publish",
            f"127.0.0.1:{port}:8069",
            "--group-add",
            "0",
            "--label",
            "sc.production-acceptance-clone=true",
            "--env-file",
            str(secret_file),
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
            "-d",
            database,
        ]
    )
    for _ in range(60):
        state = run(["docker", "inspect", container, "--format", "{{.State.Running}}|{{.State.ExitCode}}"], False)
        if state.startswith("true|"):
            return {
                "status": "PASS",
                "database": database,
                "container": container,
                "loopback_port": port,
                "exact_dbfilter": True,
                "tenant_sha": tenant_sha,
                "tenant_module": tenant_module,
                "external_egress": False,
                "jwt_secret_configured": True,
            }
        time.sleep(1)
    raise CloneRuntimeError("acceptance clone did not remain running")


def refresh_tenant(restore_id: str, tenant_sha: str, tenant_module: str, image: str) -> dict[str, object]:
    """Replace only the acceptance Odoo container's immutable tenant mount."""
    if os.environ.get("CONFIRM_PRODUCTION_ACCEPTANCE_TENANT_REFRESH") != REFRESH_CONFIRMATION:
        raise CloneRuntimeError("exact acceptance tenant refresh confirmation is required")
    validate_identity(restore_id, tenant_sha, tenant_module, image, 18095)

    report_path = Path(f"/data/backups/sc_production/restore-rehearsals/{restore_id}.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS" or report.get("production_database_connected") is not False:
        raise CloneRuntimeError("verified isolated restore report is required")
    resources = report.get("resources") or {}
    network = str(resources.get("network") or "")
    filestore = str(resources.get("filestore_volume") or "")
    if network != f"{restore_id}_internal" or filestore != f"{restore_id}_filestore":
        raise CloneRuntimeError("acceptance resources escaped the isolated namespace")

    tenant_root = Path(f"/opt/sce/tenant-addons/acceptance/{tenant_sha}")
    if not (tenant_root / tenant_module / "__manifest__.py").is_file():
        raise CloneRuntimeError("immutable tenant addon is unavailable")
    config = Path(f"/data/backups/sc_production/acceptance-runtimes/{restore_id}/odoo.conf")
    secret_file = ensure_runtime_secret(config.parent)
    database = f"r10e_{restore_id}"
    config_text = config.read_text(encoding="utf-8")
    if f"dbfilter = ^{database}$" not in config_text or "list_db = False" not in config_text:
        raise CloneRuntimeError("exact acceptance database filter is not locked")

    container = f"{restore_id}_acceptance_odoo"
    inspect = json.loads(run(["docker", "inspect", container]))[0]
    if inspect.get("Image") != image or inspect.get("State", {}).get("Running") is not True:
        raise CloneRuntimeError("acceptance application identity differs")
    labels = inspect.get("Config", {}).get("Labels") or {}
    if labels.get("sc.production-acceptance-clone") != "true":
        raise CloneRuntimeError("target container is not an acceptance clone")
    networks = inspect.get("NetworkSettings", {}).get("Networks") or {}
    if set(networks) != {network}:
        raise CloneRuntimeError("acceptance application network identity differs")
    mounts = inspect.get("Mounts") or []
    old_tenant_mounts = [
        row for row in mounts
        if row.get("Destination") == "/mnt/tenant-addons"
        and row.get("RW") is False
        and str(row.get("Source") or "").startswith("/opt/sce/tenant-addons/acceptance/")
    ]
    filestore_mounts = [
        row for row in mounts
        if row.get("Destination") == "/var/lib/odoo/filestore"
        and row.get("Type") == "volume"
        and row.get("Name") == filestore
    ]
    if len(old_tenant_mounts) != 1 or len(filestore_mounts) != 1:
        raise CloneRuntimeError("acceptance immutable mounts differ")
    old_tenant_root = Path(str(old_tenant_mounts[0]["Source"]))

    def start(root: Path) -> None:
        run(
            [
                "docker", "run", "-d", "--name", container,
                "--network", network, "--network-alias", "odoo",
                "--group-add", "0",
                "--label", "sc.production-acceptance-clone=true",
                "--env-file", str(secret_file),
                "--mount", f"type=volume,src={filestore},dst=/var/lib/odoo/filestore",
                "--mount", f"type=bind,src={root},dst=/mnt/tenant-addons,readonly",
                "--mount", f"type=bind,src={config},dst=/etc/odoo/odoo.conf,readonly",
                "--entrypoint", "odoo", image,
                "-c", "/etc/odoo/odoo.conf", "-d", database,
            ]
        )

    run(["docker", "stop", "--time", "30", container])
    run(["docker", "rm", container])
    try:
        start(tenant_root)
        for _ in range(60):
            state = run(["docker", "inspect", container, "--format", "{{.State.Running}}|{{.State.ExitCode}}"], check=False)
            if state.startswith("true|"):
                return {
                    "status": "PASS",
                    "database": database,
                    "container": container,
                    "tenant_sha": tenant_sha,
                    "previous_tenant_sha": old_tenant_root.name,
                    "exact_dbfilter": True,
                    "external_egress": False,
                    "jwt_secret_configured": True,
                }
            time.sleep(1)
        raise CloneRuntimeError("refreshed acceptance application did not remain running")
    except Exception:
        run(["docker", "rm", "-f", container], check=False)
        start(old_tenant_root)
        raise


def refresh_image(
    restore_id: str, tenant_sha: str, tenant_module: str, image: str,
    source_sha: str, port: int,
) -> dict[str, object]:
    """Replace the acceptance Odoo and edge containers with one verified image."""
    if os.environ.get("CONFIRM_PRODUCTION_ACCEPTANCE_IMAGE_REFRESH") != IMAGE_REFRESH_CONFIRMATION:
        raise CloneRuntimeError("exact acceptance image refresh confirmation is required")
    validate_identity(restore_id, tenant_sha, tenant_module, image, 18095)
    if not SHA.fullmatch(source_sha) or not 18080 <= port <= 18120:
        raise CloneRuntimeError("invalid source revision or public acceptance port")

    report_path = Path(f"/data/backups/sc_production/restore-rehearsals/{restore_id}.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS" or report.get("production_database_connected") is not False:
        raise CloneRuntimeError("verified isolated restore report is required")
    resources = report.get("resources") or {}
    internal = str(resources.get("network") or "")
    filestore = str(resources.get("filestore_volume") or "")
    public = f"{restore_id}_public_ingress"
    if internal != f"{restore_id}_internal" or filestore != f"{restore_id}_filestore":
        raise CloneRuntimeError("acceptance resources escaped the isolated namespace")

    tenant_root = Path(f"/opt/sce/tenant-addons/acceptance/{tenant_sha}")
    if not (tenant_root / tenant_module / "__manifest__.py").is_file():
        raise CloneRuntimeError("immutable tenant addon is unavailable")
    runtime_root = Path(f"/data/backups/sc_production/acceptance-runtimes/{restore_id}")
    config = runtime_root / "odoo.conf"
    secret_file = ensure_runtime_secret(runtime_root)
    database = f"r10e_{restore_id}"
    config_text = config.read_text(encoding="utf-8")
    if f"dbfilter = ^{database}$" not in config_text or "list_db = False" not in config_text:
        raise CloneRuntimeError("exact acceptance database filter is not locked")

    image_identity = run([
        "docker", "image", "inspect", image, "--format",
        '{{.Id}}|{{index .Config.Labels "org.opencontainers.image.revision"}}',
    ])
    if image_identity != f"{image}|{source_sha}":
        raise CloneRuntimeError("replacement image identity differs")

    odoo = f"{restore_id}_acceptance_odoo"
    web = f"{restore_id}_acceptance_web"
    odoo_inspect, web_inspect = (
        json.loads(run(["docker", "inspect", name]))[0] for name in (odoo, web)
    )
    old_image = str(odoo_inspect.get("Image") or "")
    if old_image != str(web_inspect.get("Image") or "") or not IMAGE.fullmatch(old_image):
        raise CloneRuntimeError("current acceptance image identity differs across containers")
    if odoo_inspect.get("State", {}).get("Running") is not True:
        raise CloneRuntimeError("current acceptance application is not running")
    web_state = web_inspect.get("State", {})
    if web_state.get("Running") is not True and not (
        web_state.get("Status") == "exited" and web_state.get("ExitCode") == 1
    ):
        raise CloneRuntimeError("current acceptance edge state is not recoverable")
    for row in (odoo_inspect, web_inspect):
        labels = row.get("Config", {}).get("Labels") or {}
        if labels.get("sc.production-acceptance-clone") != "true":
            raise CloneRuntimeError("target container is not an acceptance clone")
    if set((odoo_inspect.get("NetworkSettings", {}).get("Networks") or {})) != {internal}:
        raise CloneRuntimeError("acceptance application network identity differs")
    if set((web_inspect.get("NetworkSettings", {}).get("Networks") or {})) != {internal, public}:
        raise CloneRuntimeError("acceptance edge network identity differs")
    bindings = web_inspect.get("HostConfig", {}).get("PortBindings") or {}
    if bindings.get("80/tcp") != [{"HostIp": "0.0.0.0", "HostPort": str(port)}]:
        raise CloneRuntimeError("acceptance public port identity differs")
    if web_state.get("Running") is True and web_inspect.get("Config", {}).get("User") != "root":
        raise CloneRuntimeError("acceptance edge runtime user identity differs")

    old_tenant = next((
        Path(str(row.get("Source"))) for row in odoo_inspect.get("Mounts") or []
        if row.get("Destination") == "/mnt/tenant-addons" and row.get("RW") is False
    ), None)
    old_filestore = [
        row for row in odoo_inspect.get("Mounts") or []
        if row.get("Destination") == "/var/lib/odoo/filestore"
        and row.get("Type") == "volume" and row.get("Name") == filestore
    ]
    if old_tenant is None or len(old_filestore) != 1:
        raise CloneRuntimeError("acceptance immutable mounts differ")

    def start(runtime_image: str, tenant: Path, exact_healthz: bool) -> None:
        run([
            "docker", "run", "-d", "--name", odoo,
            "--network", internal, "--network-alias", "odoo",
            "--group-add", "0", "--label", "sc.production-acceptance-clone=true",
            "--env-file", str(secret_file),
            "--mount", f"type=volume,src={filestore},dst=/var/lib/odoo/filestore",
            "--mount", f"type=bind,src={tenant},dst=/mnt/tenant-addons,readonly",
            "--mount", f"type=bind,src={config},dst=/etc/odoo/odoo.conf,readonly",
            "--entrypoint", "odoo", runtime_image,
            "-c", "/etc/odoo/odoo.conf", "-d", database,
        ])
        web_command = [
            "docker", "run", "-d", "--name", web,
            "--network", internal, "--publish", f"0.0.0.0:{port}:80",
            "--user", "root",
            "--label", "sc.production-acceptance-clone=true",
            "--env", f"ODOO_DB={database}",
        ]
        if exact_healthz:
            web_command.extend([
                "--health-cmd", "python3 -c 'import json,urllib.request; r=urllib.request.urlopen(\"http://127.0.0.1/healthz\"); assert r.status == 200 and json.load(r)[\"status\"] == \"ok\"'",
                "--health-interval", "5s", "--health-timeout", "3s", "--health-retries", "12",
            ])
        web_command.extend([
            "--entrypoint", "/usr/local/bin/render_nginx_conf.sh", runtime_image,
        ])
        run(web_command)
        run(["docker", "network", "connect", public, web])

    def wait_ready(exact_healthz: bool) -> None:
        probe = (
            "import json,sys,urllib.request; "
            "base=sys.argv[1]; db=sys.argv[2]; "
            + (
                "health=urllib.request.urlopen(base+'/healthz',timeout=3); "
                "assert health.status==200 and json.load(health)=={'status':'ok','service':'sce-web'}; "
                if exact_healthz else ""
            )
            + "app=urllib.request.urlopen(base+'/web/login?db='+db,timeout=10); assert app.status==200"
        )
        for _ in range(60):
            state = run(["docker", "inspect", odoo, web, "--format", "{{.State.Running}}"], check=False)
            ready = succeeds(["python3", "-c", probe, f"http://127.0.0.1:{port}", database])
            if state.splitlines() == ["true", "true"] and ready:
                return
            time.sleep(1)
        raise CloneRuntimeError("refreshed acceptance image runtime did not become ready")

    for name in (web, odoo):
        run(["docker", "stop", "--time", "30", name])
        run(["docker", "rm", name])
    try:
        start(image, tenant_root, True)
        wait_ready(True)
    except Exception:
        for name in (web, odoo):
            run(["docker", "rm", "-f", name], check=False)
        start(old_image, old_tenant, False)
        wait_ready(False)
        raise
    return {
        "status": "PASS", "database": database, "odoo_container": odoo,
        "web_container": web, "image": image, "previous_image": old_image,
        "source_sha": source_sha, "tenant_sha": tenant_sha, "public_port": port,
        "exact_dbfilter": True, "external_egress": False, "healthz": True,
        "jwt_secret_configured": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore-id", required=True)
    parser.add_argument("--tenant-sha", required=True)
    parser.add_argument("--tenant-module", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--refresh-tenant", action="store_true")
    parser.add_argument("--refresh-image", action="store_true")
    parser.add_argument("--source-sha")
    args = parser.parse_args()
    if args.refresh_tenant and args.refresh_image:
        raise CloneRuntimeError("select exactly one acceptance refresh mode")
    if args.refresh_image:
        result = refresh_image(
            args.restore_id, args.tenant_sha, args.tenant_module, args.image,
            args.source_sha or "", args.port,
        )
    elif args.refresh_tenant:
        result = refresh_tenant(args.restore_id, args.tenant_sha, args.tenant_module, args.image)
    else:
        result = activate(args.restore_id, args.tenant_sha, args.tenant_module, args.image, args.port)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
