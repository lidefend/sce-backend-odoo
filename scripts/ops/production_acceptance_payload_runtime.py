#!/usr/bin/env python3
"""Run a signed tenant payload against one isolated production acceptance clone."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
from pathlib import Path


RESTORE_ID = re.compile(r"^sc_restore_[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}$")
PAYLOAD_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{2,127}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
CONFIRMATION = "IMPORT_SIGNED_PAYLOAD_INTO_ISOLATED_PRODUCTION_ACCEPTANCE_CLONE"
TENANT_KEY = "baosheng"
OPERATOR_XMLID = "base.user_admin"
IMPORTER_GROUP = "smart_core.group_smart_core_tenant_payload_importer"


class PayloadRuntimeError(RuntimeError):
    pass


def run(args: list[str], *, stdin=None, check: bool = True) -> str:
    completed = subprocess.run(
        args,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if check and completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip() or "command failed"
        raise PayloadRuntimeError(detail.splitlines()[-1][:500])
    return completed.stdout.strip()


def _conf_value(config: Path, key: str) -> str:
    prefix = f"{key} ="
    for row in config.read_text(encoding="utf-8").splitlines():
        if row.strip().startswith(prefix):
            return row.split("=", 1)[1].strip()
    return ""


def _load_manifest(payload_root: Path, expected_checksum: str) -> dict:
    manifest_path = payload_root / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise PayloadRuntimeError("signed payload manifest is unavailable")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("tenant_key") != TENANT_KEY:
        raise PayloadRuntimeError("payload tenant identity differs")
    if manifest.get("payload_checksum") != expected_checksum:
        raise PayloadRuntimeError("payload checksum differs")
    if not CHECKSUM.fullmatch(expected_checksum):
        raise PayloadRuntimeError("approved payload checksum is invalid")
    return manifest


def validate_identity(restore_id: str, payload_id: str, expected_checksum: str, action: str) -> None:
    if not RESTORE_ID.fullmatch(restore_id):
        raise PayloadRuntimeError("invalid isolated restore identity")
    if not PAYLOAD_ID.fullmatch(payload_id):
        raise PayloadRuntimeError("invalid payload identity")
    if not CHECKSUM.fullmatch(expected_checksum):
        raise PayloadRuntimeError("invalid approved payload checksum")
    if action not in {"plan", "import", "verify"}:
        raise PayloadRuntimeError("unsupported payload action")


def container_exists(name: str) -> bool:
    return bool(run(["docker", "inspect", "--format", "{{.Id}}", name], check=False))


def execute(restore_id: str, payload_id: str, expected_checksum: str, action: str) -> dict:
    validate_identity(restore_id, payload_id, expected_checksum, action)
    if action == "import" and os.environ.get("CONFIRM_PRODUCTION_ACCEPTANCE_PAYLOAD_IMPORT") != CONFIRMATION:
        raise PayloadRuntimeError("exact isolated acceptance payload import confirmation is required")

    report_path = Path(f"/data/backups/sc_production/restore-rehearsals/{restore_id}.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS" or report.get("production_database_connected") is not False:
        raise PayloadRuntimeError("verified production-disconnected restore report is required")
    resources = report.get("resources") or {}
    network = str(resources.get("network") or "")
    filestore = str(resources.get("filestore_volume") or "")
    if not network.startswith(restore_id) or not filestore.startswith(restore_id):
        raise PayloadRuntimeError("acceptance resources escaped the restore namespace")

    database = f"r10e_{restore_id}"
    runtime_root = Path(f"/data/backups/sc_production/acceptance-runtimes/{restore_id}")
    config = runtime_root / "odoo.conf"
    if _conf_value(config, "dbfilter") != f"^{database}$" or _conf_value(config, "list_db").lower() != "false":
        raise PayloadRuntimeError("exact acceptance database filter is not locked")

    payload_root = Path(f"/data/backups/production_acceptance/payloads/{payload_id}")
    manifest = _load_manifest(payload_root, expected_checksum)
    public_key = Path(f"/data/backups/production_acceptance/rehearsal-keys/{payload_id}/public.pem")
    if public_key.is_symlink() or not public_key.is_file():
        raise PayloadRuntimeError("payload verification key is unavailable")

    app_container = f"{restore_id}_acceptance_odoo"
    inspect = json.loads(run(["docker", "inspect", app_container]))[0]
    if inspect.get("State", {}).get("Running") is not True:
        raise PayloadRuntimeError("acceptance application is not running")
    if (inspect.get("Config", {}).get("Labels") or {}).get("sc.production-acceptance-clone") != "true":
        raise PayloadRuntimeError("target container is not an acceptance clone")
    networks = inspect.get("NetworkSettings", {}).get("Networks") or {}
    if set(networks) != {network}:
        raise PayloadRuntimeError("acceptance application network identity differs")
    image = str(inspect.get("Image") or "")
    tenant_mounts = [
        row for row in inspect.get("Mounts") or []
        if row.get("Destination") == "/mnt/tenant-addons" and row.get("RW") is False
    ]
    if len(tenant_mounts) != 1:
        raise PayloadRuntimeError("immutable tenant addon mount is unavailable")
    tenant_root = Path(str(tenant_mounts[0]["Source"]))

    tool_root = Path(__file__).resolve().parents[2]
    tool_marker = tool_root / "DEPLOYMENT_TOOL_SHA"
    if not tool_marker.is_file() or tool_marker.read_text(encoding="utf-8").strip() != tool_root.name:
        raise PayloadRuntimeError("immutable deployment tool identity differs")
    action_script = tool_root / "scripts/tenant_payload/odoo_action.py"
    if not action_script.is_file():
        raise PayloadRuntimeError("immutable tenant payload action is unavailable")

    maintenance_name = f"{restore_id}_payload_{action}"
    if container_exists(maintenance_name):
        raise PayloadRuntimeError("scoped payload maintenance container already exists")
    command = [
        "docker", "run", "--rm", "-i", "--name", maintenance_name,
        "--network", network,
        "--user", "0:0",
        "--label", "sc.production-acceptance-payload=true",
        "--mount", f"type=volume,src={filestore},dst=/var/lib/odoo/filestore",
        "--mount", f"type=bind,src={tenant_root},dst=/mnt/tenant-addons,readonly",
        "--mount", f"type=bind,src={config},dst=/etc/odoo/odoo.conf,readonly",
        "--mount", f"type=bind,src={payload_root},dst=/mnt/tenant-payload,readonly",
        "--mount", f"type=bind,src={public_key},dst=/mnt/tenant-payload-public-key,readonly",
        "-e", f"SC_TENANT_PAYLOAD_ACTION={action}",
        "-e", f"SC_TENANT_PAYLOAD_TENANT_KEY={TENANT_KEY}",
        "-e", "SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_TYPE=external_xmlid",
        "-e", f"SC_TENANT_PAYLOAD_OPERATOR_IDENTITY_KEY={OPERATOR_XMLID}",
        "-e", f'SC_TENANT_PAYLOAD_DIRECT_GRANT_TARGETS=["{IMPORTER_GROUP}"]',
        "-e", f"SC_TENANT_PAYLOAD_DB_ALLOWLIST={database}",
        "-e", f"SC_TENANT_PAYLOAD_APPROVED_CHECKSUM={expected_checksum}",
        "-e", "SC_TENANT_PAYLOAD_CHUNK_SIZE=100",
        "-e", "SC_TENANT_PAYLOAD_PUBLIC_KEY=/mnt/tenant-payload-public-key",
        "-e", f"SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY={secrets.token_hex(32)}",
        "--entrypoint", "odoo", image,
        "shell", "-c", "/etc/odoo/odoo.conf", "-d", database, "--no-http", "--log-level=error",
    ]
    with action_script.open("r", encoding="utf-8") as source:
        output = run(command, stdin=source)
    json_rows = [row for row in output.splitlines() if row.strip().startswith("{")]
    if not json_rows:
        raise PayloadRuntimeError("payload action did not emit an audit report")
    result = json.loads(json_rows[-1])
    if result.get("status") != "PASS":
        raise PayloadRuntimeError(f"payload {action} did not pass")
    result.update(
        {
            "action": action,
            "database": database,
            "payload_id": manifest["payload_id"],
            "production_database_connected": False,
            "isolated_network": network,
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore-id", required=True)
    parser.add_argument("--payload-id", required=True)
    parser.add_argument("--expected-checksum", required=True)
    parser.add_argument("--action", required=True)
    args = parser.parse_args()
    try:
        result = execute(args.restore_id, args.payload_id, args.expected_checksum, args.action)
    except (PayloadRuntimeError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"[production.acceptance.payload] BLOCKED: {exc}") from exc
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
