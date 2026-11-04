#!/usr/bin/env python3
"""Minimal module-change observation closed loop (CAP-02C-03-02).

Orchestrates: before runtime snapshot -> (optional) module upgrade -> after
runtime snapshot -> ir.module.module version reconciliation -> observation
record -> baseline admission. It is a governance side-channel: observation
failure never rolls back or retries an Odoo upgrade.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
import importlib.util
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_obsmod():
    spec = importlib.util.spec_from_file_location(
        "module_change_observation", ROOT / "scripts/verify/module_change_observation.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


obsmod = _load_obsmod()

CONTAINER = "sc-local-dev-odoo-1"
CONF = "/var/lib/odoo/odoo.conf"


def _odoo_shell(db: str, script: str) -> str:
    proc = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "odoo", "shell", "-d", db, "-c", CONF],
        input=script, text=True, capture_output=True, timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"odoo shell failed: {proc.stderr[-2000:]}")
    return proc.stdout


def _runtime_snapshot(db: str) -> dict:
    script = (ROOT / "scripts/verify/odoo_runtime_facts.py").read_text(encoding="utf-8")
    raw = _odoo_shell(db, script)
    marker = '"schema": "module.runtime.facts.v1"'
    idx = raw.rfind(marker)
    start = raw.rfind("{", 0, idx)
    depth = 0
    for i in range(start, len(raw)):
        if raw[i] == "{":
            depth += 1
        elif raw[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(raw[start:i + 1])
    raise RuntimeError("runtime facts JSON not found in shell output")


def _upgrade(db: str, modules: list[str]) -> int:
    cmd = ["docker", "exec", CONTAINER, "odoo", "-d", db, "-c", CONF,
           "--stop-after-init", "-u", ",".join(modules)]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=1800)
        return proc.returncode
    except subprocess.TimeoutExpired:
        return 124
    except OSError as exc:
        print(f"[upgrade] OSError: {exc}", file=sys.stderr)
        return 125


def _module_versions(snapshot: dict, modules: list[str]) -> dict:
    items = snapshot.get("modules", {}).get("items", {})
    return {m: items.get(m, {}).get("installed_version") for m in modules}


def observe(db: str, modules: list[str], *, do_upgrade: bool, origin: str,
            outdir: Path) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    operation_id = f"cap02c-{db}-{int(time.time())}-{uuid.uuid4().hex[:8]}"
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    before = _runtime_snapshot(db)
    before_sha = hashlib.sha256(json.dumps(before, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    before_versions = _module_versions(before, modules)
    before_path = outdir / f"runtime_snapshot_before_{operation_id}.json"
    before_path.write_text(json.dumps(before, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    before_sha = hashlib.sha256(before_path.read_bytes()).hexdigest()

    exit_code = 0
    upgrade_ok = True
    if do_upgrade:
        exit_code = _upgrade(db, modules)
        upgrade_ok = exit_code == 0

    after = None
    after_sha = ""
    after_versions = {}
    artifact_path = outdir / f"runtime_snapshot_{operation_id}.json"
    try:
        after = _runtime_snapshot(db)
        artifact_path.write_text(json.dumps(after, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        after_sha = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        after_versions = _module_versions(after, modules)
        registry_ready = bool(after.get("registry", {}).get("ready"))
        db_matches = bool(after.get("registry", {}).get("db_matches"))
    except Exception as exc:
        registry_ready = False
        db_matches = False

    if not upgrade_ok:
        result = "failed"
    elif not after:
        result = "failed"
    elif not registry_ready or not db_matches:
        result = "partial" if after else "failed"
    else:
        result = "success"

    version_changed = any(
        before_versions.get(m) != after_versions.get(m) for m in modules
    )
    # partial: some target modules are not in an installed state after upgrade
    module_states = {
        m: after.get("modules", {}).get("items", {}).get(m, {}).get("state")
        for m in modules
    } if after else {}
    if result == "success" and do_upgrade and any(
        module_states.get(m) != "installed" for m in modules
    ):
        result = "partial"

    # save after snapshot artifact when present
    artifact_sha = after_sha

    observation = {
        "schema": "module.change.observation.v1",
        "operation_id": operation_id,
        "db_name": db,
        "operation_origin": origin,
        "timestamp": started,
        "target_modules": modules,
        "result": result,
        "version_changed": version_changed,
        "registry": {"ready": registry_ready, "rebuilt": do_upgrade, "db_matches": db_matches},
        "observer": {"name": "module_upgrade_observation", "version": "1", "odoo_version": "17.0", "schema_version": "1"},
        "module_versions": [
            {"module": m, "before": before_versions.get(m), "after": after_versions.get(m)}
            for m in modules
        ],
        "before": {
            "snapshot_sha256": before_sha,
            "fact_digest": before_sha,
            "module_digests": {m: before_versions.get(m) or "" for m in modules},
        },
        "after": {
            "snapshot_sha256": after_sha,
            "fact_digest": after_sha,
            "module_digests": {m: after_versions.get(m) or "" for m in modules},
        },
        "snapshot_artifact": {"path": str(artifact_path.relative_to(ROOT)), "sha256": artifact_sha} if after is not None else {},
    }
    observation["_upgrade_exit_code"] = exit_code
    obs_path = outdir / f"observation_{operation_id}.json"
    obs_path.write_text(json.dumps(observation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return observation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--modules", required=True, help="comma-separated module names")
    parser.add_argument("--upgrade", action="store_true")
    parser.add_argument("--origin", default="cli_wrapper")
    parser.add_argument("--outdir", type=Path, default=ROOT / "artifacts/backend/module_observations")
    args = parser.parse_args()
    modules = [m for m in args.modules.split(",") if m]
    observation = observe(args.db, modules, do_upgrade=args.upgrade, origin=args.origin, outdir=args.outdir)
    assessment = obsmod.assess(observation)
    print(json.dumps({
        "operation_id": observation["operation_id"],
        "db_name": observation["db_name"],
        "result": observation["result"],
        "upgrade_exit_code": observation.get("_upgrade_exit_code"),
        "module_versions": observation["module_versions"],
        "baseline_admissible": assessment["baseline_admissible"],
        "admission_reason": assessment["admission_reason"],
        "artifact_persisted": assessment["artifact_persisted"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
