"""Collect the registered local.dev performance identity for the baseline record.

P4 collection helper. It reads docker metadata and process counters for the
registered ``sc-local-dev`` runtime and the registered env-file values. It never
starts, stops or reconfigures a container, never writes into the runtime, never
assembles credentials by hand and never invents a value: anything it cannot read
is simply omitted so the baseline registers an explicit gap instead.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTAINER_PATTERN = re.compile(r"^sc-local-dev-(odoo|db)-1$")


def _run(argv: list[str]) -> str:
    completed = subprocess.run(argv, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(argv)}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def _try_run(argv: list[str]) -> str | None:
    try:
        return _run(argv)
    except (OSError, RuntimeError):
        return None


def _inspect(container: str, template: str) -> dict:
    raw = _run(["docker", "inspect", container, "--format", template])
    return json.loads(raw)


def _env_value(env_file: Path, key: str) -> str | None:
    if not env_file.is_file():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return None


def _frontend_artifact_digest(env_file: Path) -> dict | None:
    """Digest the built entry document and the document nginx actually serves."""
    root = ROOT
    dist_value = _env_value(env_file, "FRONTEND_DIST_DIR")
    port = _env_value(env_file, "NGINX_PORT")
    if not dist_value or not port:
        return None
    dist_dir = Path(dist_value)
    if not dist_dir.is_absolute():
        dist_dir = (root / dist_value).resolve()
    index = dist_dir / "index.html"
    if not index.is_file():
        return None
    dist_digest = hashlib.sha256(index.read_bytes()).hexdigest()
    served_digest = None
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=15) as response:
            served_digest = hashlib.sha256(response.read()).hexdigest()
    except Exception:  # the served read is optional evidence, never fatal
        served_digest = None
    return {
        "frontend_index_sha256": dist_digest,
        "served_index_sha256": served_digest,
        "served_matches_build": served_digest == dist_digest if served_digest else None,
        "dist_dir": str(dist_dir),
        "source": "measured:built_index_and_served_nginx_document",
    }


def collect(odoo: str, db: str, env_file: Path) -> dict:
    for name in (odoo, db):
        if not CONTAINER_PATTERN.match(name):
            raise ValueError(f"refusing to inspect a non-registered container: {name}")

    odoo_info = _inspect(odoo, "{{json .}}")
    db_info = _inspect(db, "{{json .}}")
    host = odoo_info.get("HostConfig") or {}
    state = odoo_info.get("State") or {}
    container_id = odoo_info.get("Id") or ""

    runtime_version = _try_run(["docker", "exec", container_id, "python3", "-c",
                                "from odoo import release; print(release.version)"])
    loadavg = _try_run(["docker", "exec", container_id, "cat", "/proc/loadavg"])
    container_cpus = _try_run(["docker", "exec", container_id, "nproc"])
    stats = _try_run(["docker", "stats", "--no-stream", "--format", "{{.CPUPerc}}", container_id])

    image_digests = odoo_info.get("Image") or ""
    repo_digests = []
    image_name = (odoo_info.get("Config") or {}).get("Image") or ""
    limits = {
        "nano_cpus": host.get("NanoCpus"),
        "memory_bytes": host.get("Memory"),
        "cpu_quota": host.get("CpuQuota"),
        "cpu_period": host.get("CpuPeriod"),
        "container_visible_cpus": int(container_cpus) if container_cpus and container_cpus.isdigit() else None,
        "interpretation": "container-level cpu/memory limits as declared by HostConfig; 0 means unlimited",
    }
    background = {
        "odoo_container_cpu_percent": stats,
        "odoo_container_loadavg": loadavg,
        "sampled_at": datetime.now(timezone.utc).isoformat(),
    }
    return {
        "deployment_identity": {
            "compose_project": "sc-local-dev",
            "odoo_container": odoo,
            "odoo_container_id": container_id,
            "odoo_image": image_name,
            "odoo_image_id": image_digests,
            "odoo_started_at": state.get("StartedAt"),
            "db_container": db,
            "db_started_at": (db_info.get("State") or {}).get("StartedAt"),
        },
        "runtime_version": runtime_version,
        "cpu_memory_limits": limits,
        "data_snapshot_identity": {
            "database": _env_value(env_file, "DB_NAME"),
            "dbfilter": _env_value(env_file, "ODOO_DBFILTER"),
            "db_started_at": (db_info.get("State") or {}).get("StartedAt"),
        },
        "concurrency": {
            "mode": "serial_single_request",
            "value": 1,
            "provenance": "managed local.dev probes execute one request at a time in one process",
        },
        "background_load": background,
        "frontend_artifact_digest": _frontend_artifact_digest(env_file),
        "env_file": str(env_file),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--odoo-container", default="sc-local-dev-odoo-1")
    parser.add_argument("--db-container", default="sc-local-dev-db-1")
    parser.add_argument("--env-file", default=str(ROOT.parent / "sce-backend-odoo" / ".env.dev"))
    parser.add_argument("--out", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        identity = collect(args.odoo_container, args.db_container, Path(args.env_file))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"performance identity collection failed: {exc}", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(identity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PERFORMANCE_IDENTITY={json.dumps({'out': str(out), 'runtime_version': identity['runtime_version']}, ensure_ascii=False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
