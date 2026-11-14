#!/usr/bin/env python3
"""Fail-closed profile and read-only preflight for the R10 isolated A/B runtime."""
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE = ROOT / "config/ops/r10_performance_ab_profile.v1.json"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9_.-]+$")
SAFE_DATABASE = re.compile(r"^[a-z][a-z0-9_]+$")
SAFE_PATH = re.compile(r"^/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+$")
EXPECTED_VIEWPORTS = ["1440x900", "390x844"]


class ProfileError(RuntimeError):
    pass


def load_profile(path: Path = DEFAULT_PROFILE) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"profile is unreadable or invalid: {path}") from exc
    if not isinstance(payload, dict):
        raise ProfileError("profile must be a JSON object")
    return validate_profile(payload, profile_path=path)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProfileError(message)


def validate_profile(payload: dict[str, Any], *, profile_path: Path = DEFAULT_PROFILE) -> dict[str, Any]:
    _require(
        payload.get("schema_version") == "r10.performance_ab.profile.v1",
        "profile schema mismatch",
    )
    _require(
        payload.get("environment_classification") == "R10_ISOLATED_PERFORMANCE_AB",
        "profile environment classification mismatch",
    )
    _require(payload.get("status") == "design_only", "profile status must remain design_only")

    source = payload.get("source") or {}
    for key in (
        "ssh_host",
        "duty",
        "compose_project",
        "database",
        "database_uuid",
        "served_source_revision",
        "tree",
        "frontend_build_sha256",
        "account",
        "project_model",
        "project_record_xmlid",
        "project_record_identity",
    ):
        _require(bool(str(source.get(key) or "").strip()), f"source.{key} is required")
    _require(FULL_SHA.fullmatch(str(source["served_source_revision"])), "invalid source revision")
    _require(FULL_SHA.fullmatch(str(source["tree"])), "invalid source tree")
    _require(re.fullmatch(r"[0-9a-f]{64}", str(source["frontend_build_sha256"])), "invalid bundle hash")
    _require(int(source.get("uid") or 0) == 42, "source uid must be demo_full uid 42")
    _require(int(source.get("company_id") or 0) == 1, "source company must be 1")
    _require(int(source.get("project_record_id") or 0) == 2, "source project must be record 2")

    arms = payload.get("arms") or {}
    _require(set(arms) == {"a", "b"}, "profile must declare exactly arms a and b")
    unique: dict[str, set[str]] = {
        "database": set(),
        "database_volume": set(),
        "redis_volume": set(),
        "odoo_volume": set(),
        "internal_network": set(),
        "source_root": set(),
        "frontend_dist": set(),
        "log_root": set(),
        "public_port": set(),
    }
    for arm_name, arm in arms.items():
        _require(isinstance(arm, dict), f"arm {arm_name} must be an object")
        _require(
            bool(SAFE_NAME.fullmatch(str(arm.get("compose_project") or ""))),
            f"arm {arm_name} has invalid compose project",
        )
        _require(
            bool(SAFE_DATABASE.fullmatch(str(arm.get("database") or ""))),
            f"arm {arm_name} has invalid database",
        )
        _require(
            arm.get("database_filter") == f"^{arm['database']}$",
            f"arm {arm_name} database filter must lock its database",
        )
        for key in ("source_root", "frontend_dist", "log_root"):
            _require(
                bool(SAFE_PATH.fullmatch(str(arm.get(key) or ""))),
                f"arm {arm_name}.{key} must be an absolute safe path",
            )
        port = arm.get("public_port")
        _require(
            isinstance(port, int) and 18095 <= port <= 18200,
            f"arm {arm_name} public port must be in the isolated range",
        )
        for key in unique:
            value = arm.get(key)
            _require(value not in (None, ""), f"arm {arm_name}.{key} is required")
            _require(value not in unique[key], f"arm resources overlap: {key}")
            unique[key].add(value)

    _require(
        arms["a"]["source_root"].startswith("/opt/projects/perf-r10/a/"),
        "A source root namespace mismatch",
    )
    _require(
        arms["b"]["source_root"].startswith("/opt/projects/perf-r10/b/"),
        "B source root namespace mismatch",
    )
    _require(
        arms["a"]["database"] != source["database"] and arms["b"]["database"] != source["database"],
        "A/B must not use the current source database",
    )

    ingress = payload.get("ingress") or {}
    _require(ingress.get("ip_masquerade") is False, "ingress must disable IP masquerade")
    _require(ingress.get("only_nginx_joined") is True, "only Nginx may join ingress")

    runtime = payload.get("runtime") or {}
    _require(runtime.get("workers") == 0, "workers must be 0")
    _require(runtime.get("max_cron_threads") == 0, "cron must be disabled")
    _require(runtime.get("external_egress_allowed") is False, "external egress must be disabled")
    _require(runtime.get("operator_workflow_allowed") is False, "operator workflows must be disabled")
    _require(runtime.get("business_mutation_allowed") is False, "business mutation must be disabled")
    _require(runtime.get("readonly_operation_only") is True, "runtime must be readonly")
    for key in ("independent_redis", "independent_filestore", "independent_frontend", "independent_logs"):
        _require(runtime.get(key) is True, f"runtime.{key} must be true")

    snapshot = payload.get("snapshot") or {}
    contract_path = contract_file(profile_path, str(snapshot.get("contract") or ""))
    _require(contract_path.is_file(), "snapshot continuity contract is missing")
    _require(
        snapshot.get("root") == "/data/backups/daily-demo-dev",
        "snapshot root must be the current demo duty backup namespace",
    )
    _require(snapshot.get("paired_restore_drill_required") is True, "paired restore drill is required")
    _require(snapshot.get("source_write_allowed") is False, "source writes must be disabled")

    measurement = payload.get("measurement") or {}
    _require(measurement.get("formal_viewports") == EXPECTED_VIEWPORTS, "viewport set mismatch")
    _require(measurement.get("cold_samples_per_arm_viewport") == 9, "cold sample count mismatch")
    _require(measurement.get("warm_smoke_per_arm") == 1, "warm smoke count mismatch")
    _require(measurement.get("warmups_per_arm") == 2, "warm-up count mismatch")
    _require(measurement.get("warm_samples_per_arm") == 9, "warm sample count mismatch")
    _require(measurement.get("formal_profiler") is False, "formal profiler must be disabled")

    forbidden = {str(item) for item in payload.get("forbidden_shared_resources") or []}
    _require(forbidden, "forbidden_shared_resources must not be empty")
    declared: set[str] = set()
    for arm in arms.values():
        declared.update(str(value) for key, value in arm.items() if key not in {"source_root", "frontend_dist", "log_root"})
    overlap = sorted(declared & forbidden)
    _require(not overlap, f"declared resources overlap the source runtime: {overlap}")

    cleanup = payload.get("cleanup") or {}
    _require(cleanup.get("current_a_untouched") is True, "cleanup must preserve current A")
    _require(cleanup.get("preserve_snapshot") is True, "cleanup must preserve snapshot")
    _require(cleanup.get("preserve_evidence") is True, "cleanup must preserve evidence")
    _require(bool(cleanup.get("exact_labels")), "cleanup labels are required")
    return payload


def contract_file(profile_path: Path, relative: str) -> Path:
    if not relative:
        raise ProfileError("snapshot continuity contract path is required")
    candidate = Path(relative)
    if candidate.is_absolute():
        return candidate
    return ROOT / candidate


def build_plan(payload: dict[str, Any]) -> dict[str, Any]:
    source = payload["source"]
    arms = payload["arms"]
    return {
        "schema": "r10.performance_ab.plan.v1",
        "mode": "plan",
        "creates_resources": False,
        "source": source,
        "arms": arms,
        "stages": [
            {
                "key": "snapshot",
                "commands": [
                    "make r10.performance_ab.snapshot",
                    "make r10.performance_ab.snapshot.validate",
                    "make r10.performance_ab.snapshot.restore_drill",
                ],
                "mutation": "snapshot-only; current A remains untouched",
            },
            {
                "key": "prepare-twins",
                "status": "requires-separate-resource-authorization",
                "resources": {
                    arm: {
                        key: value
                        for key, value in values.items()
                        if key
                        in {
                            "compose_project",
                            "database",
                            "database_volume",
                            "redis_volume",
                            "odoo_volume",
                            "internal_network",
                            "source_root",
                            "frontend_dist",
                            "log_root",
                            "public_port",
                        }
                    }
                    for arm, values in arms.items()
                },
            },
            {
                "key": "cold-warm",
                "cold_samples_per_arm_viewport": 9,
                "warm_samples_per_arm": 9,
                "viewports": EXPECTED_VIEWPORTS,
                "formal_profiler": False,
                "mutation": "read-only business operation only",
            },
            {
                "key": "teardown",
                "preserve": ["snapshot", "evidence"],
                "current_a_untouched": True,
            },
        ],
    }


REMOTE_PROBE = r'''
import json, os, re, shutil, subprocess

def run(args):
    return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False).stdout

containers = [row.strip() for row in run(["docker", "ps", "-a", "--format", "{{.Names}}"]).splitlines() if row.strip()]
volumes = [row.strip() for row in run(["docker", "volume", "ls", "--format", "{{.Name}}"]).splitlines() if row.strip()]
networks = [row.strip() for row in run(["docker", "network", "ls", "--format", "{{.Name}}"]).splitlines() if row.strip()]
listening = set()
for row in run(["ss", "-ltnH"]).splitlines():
    parts = row.split()
    if len(parts) >= 4:
        match = re.search(r":([0-9]+)$", parts[3])
        if match:
            listening.add(int(match.group(1)))
mem = {}
for line in open("/proc/meminfo", encoding="utf-8"):
    key, value = line.split(":", 1)
    mem[key] = int(value.strip().split()[0]) * 1024
disk = shutil.disk_usage("/")
paths = {path: os.path.exists(path) for path in json.loads(os.environ["R10_PATHS"])}
print("R10_REMOTE_PROBE=" + json.dumps({
    "containers": containers,
    "volumes": volumes,
    "networks": networks,
    "listening_ports": sorted(listening),
    "disk_free_bytes": disk.free,
    "memory_available_bytes": mem.get("MemAvailable", 0),
    "paths": paths,
}, sort_keys=True))
'''


def remote_probe(ssh_host: str, paths: list[str]) -> dict[str, Any]:
    _require(bool(SAFE_NAME.fullmatch(ssh_host or "")), "invalid SSH host")
    _require(bool(paths), "remote path list is required")
    remote_python = "R10_PATHS=%s python3 -" % shlex.quote(
        json.dumps(paths, separators=(",", ":"))
    )
    completed = subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=10",
            ssh_host,
            remote_python,
        ],
        input=REMOTE_PROBE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise ProfileError("remote preflight failed: " + completed.stderr.strip()[-500:])
    for line in completed.stdout.splitlines():
        if line.startswith("R10_REMOTE_PROBE="):
            try:
                payload = json.loads(line.split("=", 1)[1])
            except json.JSONDecodeError as exc:
                raise ProfileError("remote preflight payload is invalid") from exc
            if isinstance(payload, dict):
                return payload
    raise ProfileError("remote preflight payload is missing")


def evaluate_preflight(payload: dict[str, Any], observed: dict[str, Any]) -> dict[str, Any]:
    arms = payload["arms"]
    containers = set(observed.get("containers") or [])
    volumes = set(observed.get("volumes") or [])
    networks = set(observed.get("networks") or [])
    ports = set(observed.get("listening_ports") or [])
    checks = []

    def add(identifier: str, passed: bool, detail: Any = None) -> None:
        checks.append({"id": identifier, "passed": bool(passed), "detail": detail})

    add(
        "current_a_demo_containers_present",
        {"sc-demo-dev-db-1", "sc-demo-dev-redis-1", "sc-demo-dev-odoo-1", "sc-demo-dev-nginx-1"}
        <= containers,
    )
    for arm_name, arm in arms.items():
        add(
            f"{arm_name}_containers_absent",
            not bool({arm["odoo_container"], arm["db_container"], arm["redis_container"], arm["nginx_container"]} & containers),
        )
        add(
            f"{arm_name}_volumes_absent",
            not bool({arm["database_volume"], arm["redis_volume"], arm["odoo_volume"]} & volumes),
        )
        add(f"{arm_name}_network_absent", arm["internal_network"] not in networks)
        add(f"{arm_name}_port_free", arm["public_port"] not in ports)
        for key in ("source_root", "frontend_dist", "log_root"):
            add(
                f"{arm_name}_{key}_absent",
                observed.get("paths", {}).get(arm[key]) is False,
                str(arm[key]),
            )
    ingress = payload["ingress"]["network"]
    add("ingress_network_absent", ingress not in networks)
    add("disk_headroom", int(observed.get("disk_free_bytes") or 0) >= 2 * 1024**3)
    add("memory_headroom", int(observed.get("memory_available_bytes") or 0) >= 2 * 1024**3)
    passed = all(row["passed"] for row in checks)
    return {
        "schema": "r10.performance_ab.preflight.v1",
        "status": "PASS" if passed else "BLOCKED",
        "checks": checks,
        "observed": observed,
        "creates_resources": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "preflight"))
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--ssh-host")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        payload = load_profile(args.profile)
        if args.action == "plan":
            result = build_plan(payload)
        else:
            host = args.ssh_host or payload["source"]["ssh_host"]
            paths = [
                values[key]
                for values in payload["arms"].values()
                for key in ("source_root", "frontend_dist", "log_root")
            ]
            result = evaluate_preflight(payload, remote_probe(host, paths))
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(
                json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    except (ProfileError, OSError) as exc:
        print(f"[r10.performance_ab] BLOCKED {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("status", "PASS") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
