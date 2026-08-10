#!/usr/bin/env python3
"""Bind an isolated acceptance plan report to one immutable candidate."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CHECKSUM = re.compile(r"^[0-9a-f]{64}$")
IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
RESTORE_ID = re.compile(r"^sc_restore_[0-9]{8}t[0-9]{6}z_[0-9a-f]{8}$")
TENANT_KEY = re.compile(r"^[a-z][a-z0-9_]{2,62}$")


class EvidenceError(ValueError):
    pass


def load_json(path: Path, label: str) -> dict:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError(f"{label} is unavailable")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{label} is invalid") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} is invalid")
    return value


def parse_plan(text: str) -> dict:
    rows = [row for row in text.splitlines() if row.strip().startswith("{")]
    if not rows:
        raise EvidenceError("isolated plan report is missing")
    try:
        value = json.loads(rows[-1])
    except json.JSONDecodeError as exc:
        raise EvidenceError("isolated plan report is invalid") from exc
    if not isinstance(value, dict):
        raise EvidenceError("isolated plan report is invalid")
    return value


def build(candidate_dir: Path, plan: dict) -> dict:
    candidate_dir = candidate_dir.resolve()
    report = load_json(candidate_dir / "release-report.json", "candidate report")
    manifest = load_json(candidate_dir / "image-manifest.json", "image manifest")
    source = report.get("source") or {}
    restore_id = str(plan.get("restore_id") or "")
    tenant_key = str(plan.get("tenant_key") or "")
    before = str(plan.get("business_state_digest_before") or "")
    after = str(plan.get("business_state_digest_after") or "")
    if (
        report.get("status") != "ready"
        or report.get("CANDIDATE_READY") is not True
        or source.get("commit_sha") != manifest.get("source_sha")
        or source.get("tree_sha") != manifest.get("source_tree_sha")
        or source.get("product_version") != manifest.get("product_version")
        or not FULL_SHA.fullmatch(str(source.get("commit_sha") or ""))
        or not FULL_SHA.fullmatch(str(source.get("tree_sha") or ""))
        or not IMAGE_ID.fullmatch(str(manifest.get("local_image_id") or ""))
    ):
        raise EvidenceError("candidate identity is invalid")
    if (
        plan.get("status") != "PASS"
        or plan.get("action") != "plan"
        or plan.get("mode") != "plan"
        or plan.get("production_database_connected") is not False
        or plan.get("database_write_count") != 0
        or plan.get("filestore_write_count") != 0
        or not RESTORE_ID.fullmatch(restore_id)
        or not str(plan.get("isolated_network") or "").startswith(restore_id)
        or not TENANT_KEY.fullmatch(tenant_key)
        or not CHECKSUM.fullmatch(str(plan.get("payload_checksum") or ""))
        or not isinstance(plan.get("planned_records"), int)
        or plan["planned_records"] <= 0
        or not isinstance(plan.get("planned_relationships"), int)
        or plan["planned_relationships"] <= 0
        or not CHECKSUM.fullmatch(before)
        or before != after
        or plan.get("payload_batches_before") != plan.get("payload_batches_after")
        or plan.get("historical_facts_before") != plan.get("historical_facts_after")
    ):
        raise EvidenceError("isolated plan contract failed")
    return {
        "schema_version": "final_image_real_plan.v2",
        "status": "PASS",
        "source_sha": source["commit_sha"],
        "source_tree": source["tree_sha"],
        "release_version": source["product_version"],
        "image_content_id": manifest["local_image_id"],
        "image_revision": source["commit_sha"],
        "command_contract": "release.production.tenant_payload.plan",
        "production_command_parity": True,
        "database_role": "isolated_customer_tenant_rehearsal",
        "environment_id": restore_id,
        "runtime_isolation": True,
        "production_resource_overlap": False,
        "target_database": "sc_production",
        "tenant_key": tenant_key,
        "payload_digest": plan["payload_checksum"],
        "plan_computation_completed": True,
        "planned_records": plan["planned_records"],
        "planned_relationships": plan["planned_relationships"],
        "database_write_count": 0,
        "payload_batches_before": plan["payload_batches_before"],
        "payload_batches_after": plan["payload_batches_after"],
        "historical_facts_before": plan["historical_facts_before"],
        "historical_facts_after": plan["historical_facts_after"],
        "business_state_digest_before": before,
        "business_state_digest_after": after,
    }


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.exists():
        if path.is_symlink() or path.read_text(encoding="utf-8") != serialized:
            raise EvidenceError("existing final-image evidence differs")
        return
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        payload = build(args.candidate_dir, parse_plan(sys.stdin.read()))
        atomic_write(args.output, payload)
    except (EvidenceError, OSError) as exc:
        raise SystemExit(f"[final-image.real-plan] BLOCKED: {exc}") from exc
    print(json.dumps({"status": "PASS", "output": str(args.output.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
