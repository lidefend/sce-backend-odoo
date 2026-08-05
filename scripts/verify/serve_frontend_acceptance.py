#!/usr/bin/env python3
"""Serve frontend acceptance artifacts with explicit UTF-8 content types."""

from __future__ import annotations

import argparse
import json
import os
import socket
import time
import uuid
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def governed_profile() -> tuple[str, Path]:
    environments = json.loads((ROOT / "config/frontend/acceptance_environments_v1.json").read_text(encoding="utf-8"))
    tools = json.loads((ROOT / "config/frontend/acceptance_tool_matrix_v1.json").read_text(encoding="utf-8"))
    name = os.getenv("SC_ACCEPTANCE_PROFILE", environments["default_profile"])
    profile = environments.get("profiles", {}).get(name)
    policy = tools.get("tools", {}).get("acceptance-report-server")
    if not profile or not policy:
        raise SystemExit(f"unknown acceptance profile/tool: {name}")
    if name not in policy["profiles"] or "managed-service" not in policy["operations"] or "managed-service" not in profile["allowed_operations"]:
        raise SystemExit(f"acceptance report server is forbidden for profile {name}")
    artifact_root = (ROOT / profile["artifact_root"]).resolve()
    if ROOT not in artifact_root.parents:
        raise SystemExit("acceptance artifact root escapes repository")
    return name, artifact_root


def acquire_service_lease(root: Path, profile: str) -> Path:
    lease_root = root / ".leases"
    lease_root.mkdir(parents=True, exist_ok=True)
    existing: list[Path] = []
    for candidate in lease_root.glob("*.json"):
        try:
            pid = int(json.loads(candidate.read_text(encoding="utf-8")).get("pid", 0))
            os.kill(pid, 0)
            existing.append(candidate)
        except ProcessLookupError:
            candidate.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            existing.append(candidate)
    if existing:
        raise SystemExit(f"acceptance lease conflict: {', '.join(path.name for path in existing)}")
    lease = lease_root / f"exclusive-service-{os.getpid()}-{uuid.uuid4()}.json"
    descriptor = os.open(lease, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump({"schema": "frontend_acceptance_lease.v1", "mode": "exclusive-service", "pid": os.getpid(), "profile": profile, "created_at": time.time()}, stream)
        stream.write("\n")
    return lease


class Utf8AcceptanceHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
    }


def main() -> None:
    profile, artifact_root = governed_profile()
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--directory", type=Path, default=Path(".runtime/final-acceptance"))
    args = parser.parse_args()
    try:
        socket.inet_pton(socket.AF_INET, args.bind)
    except OSError:
        if args.bind != "localhost":
            raise SystemExit("acceptance report server must bind to loopback")
    if args.bind not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("acceptance report server must bind to loopback")
    directory = args.directory.resolve(strict=True)
    if ROOT not in directory.parents:
        raise SystemExit("acceptance report directory escapes repository")
    lease = acquire_service_lease(artifact_root, profile)
    handler = partial(Utf8AcceptanceHandler, directory=str(directory))
    try:
        with ThreadingHTTPServer((args.bind, args.port), handler) as server:
            port = server.server_address[1]
            print(f"Serving UTF-8 acceptance artifacts from {directory} at http://{args.bind}:{port}", flush=True)
            server.serve_forever()
    finally:
        lease.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
