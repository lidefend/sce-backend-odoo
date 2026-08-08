#!/usr/bin/env python3
"""Activate a verified production restore as a persistent, no-egress clone."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from pathlib import Path


RESTORE_ID = re.compile(r"^sc_restore_[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}$")
SHA = re.compile(r"^[0-9a-f]{40}$")
IMAGE = re.compile(r"^sha256:[0-9a-f]{64}$")
MODULE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
CONFIRMATION = "ACTIVATE_ISOLATED_PRODUCTION_ACCEPTANCE_CLONE"


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


def validate_identity(restore_id: str, tenant_sha: str, tenant_module: str, image: str, port: int) -> None:
    if not RESTORE_ID.fullmatch(restore_id) or not SHA.fullmatch(tenant_sha):
        raise CloneRuntimeError("invalid immutable clone identity")
    if not MODULE.fullmatch(tenant_module):
        raise CloneRuntimeError("invalid tenant module identity")
    if not IMAGE.fullmatch(image) or not 18095 <= port <= 18120:
        raise CloneRuntimeError("invalid immutable image or loopback port")


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
            }
        time.sleep(1)
    raise CloneRuntimeError("acceptance clone did not remain running")


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
