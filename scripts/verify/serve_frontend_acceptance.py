#!/usr/bin/env python3
"""Serve a governed acceptance run on loopback with an exclusive target lease."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/verify/frontend_acceptance_environment_cli.mjs"


def resolved_environment() -> dict:
    result = subprocess.run(
        ["node", str(CLI), "--tool", "acceptance-report-server", "--operation", "managed-service"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if result.returncode:
        raise SystemExit(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


class Utf8AcceptanceHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
    }


def main() -> None:
    environment = resolved_environment()
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--directory", type=Path, default=Path(environment["artifacts"]["runRoot"]))
    args = parser.parse_args()
    if args.bind not in {"127.0.0.1", "::1", "localhost"}:
        raise SystemExit("acceptance report server must bind to loopback")
    directory = args.directory.resolve()
    artifact_root = Path(environment["artifacts"]["root"]).resolve()
    if directory != artifact_root and artifact_root not in directory.parents:
        raise SystemExit("acceptance report directory escapes the governed artifact root")
    directory.mkdir(parents=True, exist_ok=True)

    lease_root = Path(environment["concurrency"]["leaseRoot"])
    lease_root.mkdir(parents=True, exist_ok=True)
    lock_path = lease_root / f"{environment['concurrency']['targetKey']}.lock"
    metadata = lease_root / f"{environment['concurrency']['targetKey']}-{environment['artifacts']['runId']}.json"
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SystemExit("acceptance lease conflict: target is already in use") from error
        metadata.write_text(json.dumps({
            "schema": "frontend_acceptance_lease.v1", "mode": "exclusive-service",
            "pid": os.getpid(), "run_id": environment["artifacts"]["runId"],
            "target_key": environment["concurrency"]["targetKey"], "created_at": time.time(),
        }) + "\n", encoding="utf-8")
        os.chmod(metadata, 0o600)
        handler = partial(Utf8AcceptanceHandler, directory=str(directory))
        try:
            with ThreadingHTTPServer((args.bind, args.port), handler) as server:
                port = server.server_address[1]
                print(f"Serving UTF-8 acceptance artifacts from {directory} at http://{args.bind}:{port}", flush=True)
                server.serve_forever()
        finally:
            metadata.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
