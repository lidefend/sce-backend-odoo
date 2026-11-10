#!/usr/bin/env python3
"""Record and verify one daily runtime build/deployment identity.

The daily source deployment already binds the served code, frontend artifact
and entry namespace. This tool adds the missing deployment receipt and proves
that the served build metadata, runtime API, deployment checkout and receipt
all name the same commit. It never changes product code or business data.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REMOTE_ROOT = "/opt/projects/repos/sce-product-odoo"
REMOTE_RECEIPT = REMOTE_ROOT + "/.deployed.json"
ENTRY_DECLARATION = Path("config/ops/daily_runtime_entry.v1.json")
DUTY_DECLARATION = Path("config/ops/daily_runtime_database_duties.v1.json")
DEFAULT_RECEIPT_ROOT = ".runtime/final-acceptance/daily-deployed/daily"
DEFAULT_REPORT = ".runtime/final-acceptance/daily-deployed/build-identity-verification.json"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
ENVIRONMENT = re.compile(r"^[a-z][a-z0-9_-]*$")
SSH_HOST = re.compile(r"^[A-Za-z0-9._-]+$")
TIMESTAMP_DIR = re.compile(r"^\d{8}T\d{9,12}Z$")


class BuildIdentityError(RuntimeError):
    pass


def identity_mismatches(
    expected_sha: str,
    deployment_environment: str,
    build_info: object,
    runtime_versions: object,
    git_head: str,
    receipt: object,
) -> list[dict[str, object]]:
    """Return every disagreement among the four identity carriers.

    This function is embedded verbatim in the remote program so local negative
    tests and live verification use one comparison authority.
    """

    build = build_info if isinstance(build_info, dict) else {}
    runtimes = runtime_versions if isinstance(runtime_versions, dict) else {}
    record = receipt if isinstance(receipt, dict) else {}
    demo = runtimes.get("demo") if isinstance(runtimes.get("demo"), dict) else {}
    platform = (
        runtimes.get("platform_control")
        if isinstance(runtimes.get("platform_control"), dict)
        else {}
    )
    expected_frontend = build.get("frontend_build_sha256", "")
    expected_demo_build = demo.get("frontend_build_sha256", "")
    expected_platform_build = platform.get("frontend_build_sha256", "")
    checks = (
        ("build_info.schema", build.get("schema"), "frontend.build_info.v1"),
        ("build_info.sha", build.get("sha"), expected_sha),
        ("build_info.environment", build.get("environment"), deployment_environment),
        ("build_info.built_at", bool(str(build.get("built_at") or "").strip()), True),
        ("build_info.version", bool(str(build.get("version") or "").strip()), True),
        ("runtime_demo.git_sha", demo.get("git_sha"), expected_sha),
        ("runtime_demo.environment", demo.get("environment"), deployment_environment),
        ("runtime_platform.git_sha", platform.get("git_sha"), expected_sha),
        (
            "runtime_platform.environment",
            platform.get("environment"),
            deployment_environment,
        ),
        ("git_head", git_head, expected_sha),
        ("receipt.git_head", record.get("git_head"), expected_sha),
        ("receipt.env", record.get("env"), deployment_environment),
        (
            "receipt.frontend_build_sha256",
            bool(
                re.fullmatch(
                    r"^[0-9a-f]{64}$",
                    str(record.get("frontend_build_sha256") or ""),
                )
            ),
            True,
        ),
        (
            "runtime_frontend_fingerprints",
            {expected_demo_build, expected_platform_build},
            {record.get("frontend_build_sha256")},
        ),
        (
            "receipt.backend_git_sha",
            record.get("backend_git_sha"),
            expected_sha,
        ),
        (
            "receipt.database",
            bool(str(record.get("database") or "").strip()),
            True,
        ),
        (
            "receipt.containers",
            bool(record.get("containers")),
            True,
        ),
        (
            "receipt.health_readback",
            isinstance(record.get("health_readback"), dict)
            and record["health_readback"].get("healthy") is True,
            True,
        ),
        (
            "receipt.operator",
            bool(str(record.get("operator") or "").strip()),
            True,
        ),
        (
            "receipt.deployed_at",
            bool(str(record.get("deployed_at") or "").strip()),
            True,
        ),
    )
    return [
        {"key": key, "observed": observed, "expected": expected}
        for key, observed, expected in checks
        if observed != expected
    ]


REMOTE_PROGRAM = r'''
import getpass, json, os, re, subprocess, sys, tempfile, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

__IDENTITY_HELPER__

(mode, expected_sha, deployment_environment, operator, product_root,
 receipt_path, entry_json, duties_json) = sys.argv[1:9]

ENTRY = json.loads(entry_json)
DUTIES = json.loads(duties_json)
root = Path(product_root)
receipt_file = Path(receipt_path)
full_sha = re.compile(r"^[0-9a-f]{40}$")
full_fp = re.compile(r"^[0-9a-f]{64}$")
environment_re = re.compile(r"^[a-z][a-z0-9_-]*$")
tag = "[daily.runtime.build_identity]"

if mode not in {"record", "verify"}:
    raise SystemExit(tag + " BLOCKED invalid mode")
if str(root) != "/opt/projects/repos/sce-product-odoo" or not root.is_dir():
    raise SystemExit(tag + " BLOCKED invalid remote repository")
if str(receipt_file) != "/opt/projects/repos/sce-product-odoo/.deployed.json":
    raise SystemExit(tag + " BLOCKED invalid remote receipt path")
if not full_sha.fullmatch(expected_sha):
    raise SystemExit(tag + " BLOCKED invalid expected SHA")
if not environment_re.fullmatch(deployment_environment):
    raise SystemExit(tag + " BLOCKED invalid deployment environment")

public = ENTRY["public_entry"]
base_url = "http://127.0.0.1:%d" % int(public["port"])
demo_prefix = str(public["demo_path"]).rstrip("/")
platform_prefix = str(public["platform_admin_path"]).rstrip("/")
route_by_duty = {
    str(route.get("duty") or ""): route
    for route in ENTRY.get("routes") or []
}
duty_by_name = {
    str(duty.get("duty") or ""): duty
    for duty in DUTIES.get("duties") or []
}


def clean(value, encoding="utf-8"):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(encoding, "replace").strip()
    return str(value).strip()


def run(argv):
    return subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def git_head():
    result = run(["git", "-C", str(root), "rev-parse", "HEAD"])
    return clean(result.stdout) if result.returncode == 0 else ""


def http_json(path):
    try:
        with urllib.request.urlopen(base_url + path, timeout=20) as response:
            return response.getcode(), json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, {}
    except Exception:
        return 0, {}


def file_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def container_facts():
    rows = []
    for duty_name in ("demo", "platform_control"):
        duty = duty_by_name.get(duty_name) or {}
        project = str((duty.get("cluster") or {}).get("compose_project") or "")
        services = (duty.get("stack") or {}).get("services") or []
        for service in services:
            name = "%s-%s-1" % (project, service) if project else ""
            if not name:
                continue
            inspected = run(["docker", "inspect", "--format", "{{json .State}}", name])
            state = {}
            if inspected.returncode == 0:
                try:
                    state = json.loads(inspected.stdout)
                except ValueError:
                    state = {}
            health = (state.get("Health") or {}).get("Status", "")
            rows.append({
                "duty": duty_name,
                "service": service,
                "name": name,
                "status": state.get("Status", ""),
                "running": state.get("Running") is True,
                "health": health,
            })
    return rows


def snapshot():
    demo_status, demo_runtime = http_json(demo_prefix + "/api/runtime-version")
    platform_status, platform_runtime = http_json(
        platform_prefix + "/api/runtime-version"
    )
    build_status, build_info = http_json("/build-info.json")
    containers = container_facts()
    head = git_head()
    healthy_containers = bool(containers) and all(
        row["running"] and row["health"] in {"", "healthy"} for row in containers
    )
    health = {
        "healthy": bool(
            demo_status == 200
            and platform_status == 200
            and build_status == 200
            and healthy_containers
        ),
        "http": {
            "build_info": build_status,
            "runtime_demo": demo_status,
            "runtime_platform": platform_status,
        },
        "containers_healthy": healthy_containers,
    }
    deployed_at = (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )
    receipt = {
        "schema": "b2.deployment_receipt.v1",
        "env": deployment_environment,
        "git_head": head,
        "frontend_build_sha256": demo_runtime.get("frontend_build_sha256", ""),
        "backend_git_sha": demo_runtime.get("git_sha", ""),
        "database": demo_runtime.get("database", ""),
        "containers": containers,
        "health_readback": health,
        "operator": operator,
        "remote_operator": getpass.getuser(),
        "deployed_at": deployed_at,
        "build_info": build_info,
        "runtime_versions": {
            "demo": demo_runtime,
            "platform_control": platform_runtime,
        },
    }
    return receipt, {
        "demo": demo_runtime,
        "platform_control": platform_runtime,
    }, build_info, head


def write_receipt(receipt):
    receipt_file.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".deployed-", suffix=".tmp", dir=str(receipt_file.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(receipt, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, receipt_file)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if mode == "record":
    receipt, runtimes, build_info, head = snapshot()
    mismatches = identity_mismatches(
        expected_sha, deployment_environment, build_info, runtimes, head, receipt
    )
    if mismatches:
        print("DAILY_BUILD_IDENTITY=" + json.dumps({
            "status": "FAIL",
            "mode": mode,
            "mismatches": mismatches,
        }, ensure_ascii=False, sort_keys=True))
        sys.exit(1)
    write_receipt(receipt)
    readback = file_json(receipt_file)
    readback_mismatches = identity_mismatches(
        expected_sha, deployment_environment, build_info, runtimes, head, readback
    )
    payload = {
        "status": "PASS" if not readback_mismatches else "FAIL",
        "mode": mode,
        "receipt": readback,
        "receipt_path": str(receipt_file),
        "mismatches": readback_mismatches,
    }
elif mode == "verify":
    receipt, runtimes, build_info, head = snapshot()
    stored = file_json(receipt_file)
    mismatches = identity_mismatches(
        expected_sha, deployment_environment, build_info, runtimes, head, stored
    )
    payload = {
        "status": "PASS" if not mismatches else "FAIL",
        "mode": mode,
        "expected_sha": expected_sha,
        "deployment_environment": deployment_environment,
        "git_head": head,
        "build_info": build_info,
        "runtime_versions": runtimes,
        "receipt_path": str(receipt_file),
        "receipt": stored,
        "mismatches": mismatches,
    }

print("DAILY_BUILD_IDENTITY=" + json.dumps(payload, ensure_ascii=False, sort_keys=True))
sys.exit(0 if payload["status"] == "PASS" else 1)
'''.replace("__IDENTITY_HELPER__", inspect.getsource(identity_mismatches))


def _load_declaration(repository: Path, path: Path) -> dict:
    try:
        payload = json.loads((repository / path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BuildIdentityError(f"{path} is unreadable: {exc}") from exc
    if not isinstance(payload, dict):
        raise BuildIdentityError(f"{path} must contain a JSON object")
    return payload


def preflight(
    expected_sha: str,
    ssh_host: str,
    deployment_environment: str,
    operator: str = "",
) -> None:
    if not FULL_SHA.fullmatch(expected_sha or ""):
        raise BuildIdentityError("expected SHA must be a full lowercase commit SHA")
    if not SSH_HOST.fullmatch(ssh_host or ""):
        raise BuildIdentityError("ssh host must be a configured host alias")
    if not ENVIRONMENT.fullmatch(deployment_environment or ""):
        raise BuildIdentityError("deployment environment is invalid")
    if operator and not operator.strip():
        raise BuildIdentityError("operator must not be blank")


def remote_command(
    mode: str,
    expected_sha: str,
    deployment_environment: str,
    operator: str,
    entry: dict,
    duties: dict,
) -> str:
    return " ".join(
        shlex.quote(item)
        for item in (
            "python3",
            "-c",
            REMOTE_PROGRAM,
            mode,
            expected_sha,
            deployment_environment,
            operator or os.getenv("USER") or "unknown",
            REMOTE_ROOT,
            REMOTE_RECEIPT,
            json.dumps(entry, ensure_ascii=False, sort_keys=True),
            json.dumps(duties, ensure_ascii=False, sort_keys=True),
        )
    )


def run_remote(
    repository: Path,
    mode: str,
    expected_sha: str,
    ssh_host: str,
    deployment_environment: str,
    operator: str,
) -> dict:
    preflight(expected_sha, ssh_host, deployment_environment, operator)
    entry = _load_declaration(repository, ENTRY_DECLARATION)
    duties = _load_declaration(repository, DUTY_DECLARATION)
    result = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "ServerAliveInterval=15",
            "-o",
            "ServerAliveCountMax=4",
            ssh_host,
            remote_command(
                mode,
                expected_sha,
                deployment_environment,
                operator,
                entry,
                duties,
            ),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    payload = None
    marker = "DAILY_BUILD_IDENTITY="
    for line in result.stdout.splitlines():
        if line.startswith(marker):
            try:
                payload = json.loads(line[len(marker):])
            except ValueError as exc:
                raise BuildIdentityError("remote build-identity evidence is invalid") from exc
    if payload is None:
        message = result.stderr.strip() or result.stdout.strip() or "no evidence"
        raise BuildIdentityError(f"remote build-identity {mode} failed: {message[:1000]}")
    if result.returncode or payload.get("status") != "PASS":
        mismatches = payload.get("mismatches") or []
        raise BuildIdentityError(
            "remote build-identity mismatch: "
            + json.dumps(mismatches[:10], ensure_ascii=False, sort_keys=True)
        )
    return payload


def receipt_directory(root: Path, deployed_at: str) -> Path:
    try:
        instant = datetime.fromisoformat(deployed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BuildIdentityError("receipt deployed_at is not ISO-8601") from exc
    stamp = instant.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = root / stamp
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def retain_recent(root: Path, keep: int = 30) -> list[str]:
    if keep < 1:
        raise BuildIdentityError("receipt retention must keep at least one deployment")
    if not root.exists():
        return []
    directories = sorted(
        (
            path
            for path in root.iterdir()
            if path.is_dir() and TIMESTAMP_DIR.fullmatch(path.name)
        ),
        key=lambda path: path.name,
        reverse=True,
    )
    removed = []
    for directory in directories[keep:]:
        shutil.rmtree(directory)
        removed.append(str(directory))
    return removed


def write_local_receipt(root: Path, receipt: dict, keep: int = 30) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    directory = receipt_directory(root, str(receipt.get("deployed_at") or ""))
    path = directory / "receipt.json"
    path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    retain_recent(root, keep)
    return path


def record(
    repository: Path,
    expected_sha: str,
    ssh_host: str,
    deployment_environment: str,
    receipt_root: Path,
    operator: str,
) -> dict:
    payload = run_remote(
        repository,
        "record",
        expected_sha,
        ssh_host,
        deployment_environment,
        operator,
    )
    receipt = payload.get("receipt")
    if not isinstance(receipt, dict):
        raise BuildIdentityError("remote record did not return a receipt")
    local_path = write_local_receipt(receipt_root, receipt)
    local_receipt = json.loads(local_path.read_text(encoding="utf-8"))
    if local_receipt != receipt:
        raise BuildIdentityError("local receipt differs from the server readback")
    return {
        **payload,
        "local_receipt": str(local_path),
    }


def verify(
    repository: Path,
    expected_sha: str,
    ssh_host: str,
    deployment_environment: str,
) -> dict:
    return run_remote(
        repository,
        "verify",
        expected_sha,
        ssh_host,
        deployment_environment,
        os.getenv("USER") or "unknown",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("record", "verify"))
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--ssh-host", required=True)
    parser.add_argument("--deployment-environment", default="daily")
    parser.add_argument("--receipt-root", default=DEFAULT_RECEIPT_ROOT)
    parser.add_argument("--receipt", default="")
    parser.add_argument("--operator", default=os.getenv("USER") or "unknown")
    parser.add_argument("--report", default=DEFAULT_REPORT)
    args = parser.parse_args()
    repository = args.repo_root.resolve()
    try:
        if args.mode == "record":
            payload = record(
                repository,
                args.expected_sha,
                args.ssh_host,
                args.deployment_environment,
                repository / args.receipt_root,
                args.operator,
            )
        else:
            payload = verify(
                repository,
                args.expected_sha,
                args.ssh_host,
                args.deployment_environment,
            )
    except BuildIdentityError as exc:
        raise SystemExit(f"[daily.runtime.build_identity] BLOCKED: {exc}") from exc
    report = Path(args.report)
    if not report.is_absolute():
        report = repository / report
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"[daily.runtime.build_identity] PASS mode={args.mode} report={report}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
